"""
memory/retrieval.py

Parallel retrieval of patient context from:
1. Postgres (last 2 structured appointments — deterministic)
2. Qdrant (top-1 semantic hit on patient history)
3. Redis session cache

All fetches run in parallel. Total target: <20ms.
"""
import asyncio
import logging
import os

import asyncpg
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/voiceai")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

QDRANT_COLLECTION = "patient_context"
SIMILARITY_THRESHOLD = 0.78   # Min cosine similarity to inject semantic context
MAX_CONTEXT_TOKENS = 400      # Hard cap on injected context


class MemoryRetriever:
    def __init__(self):
        self._pg_pool: asyncpg.Pool | None = None
        self._qdrant = AsyncQdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self._embedding_client = None  # lazy init

    async def _get_pg(self) -> asyncpg.Pool:
        if self._pg_pool is None:
            self._pg_pool = await asyncpg.create_pool(
                DATABASE_URL, min_size=2, max_size=10
            )
        return self._pg_pool

    async def fetch_all(
        self, session_id: str, patient_id: str, query: str
    ) -> dict:
        """
        Parallel fetch from all memory sources.
        Returns merged context dict ready for prompt injection.
        """
        # Run all fetches in parallel
        pg_task = asyncio.create_task(self._fetch_structured(patient_id))
        qdrant_task = asyncio.create_task(self._fetch_semantic(patient_id, query))
        session_task = asyncio.create_task(self._fetch_session(session_id))

        structured, semantic, session = await asyncio.gather(
            pg_task, qdrant_task, session_task,
            return_exceptions=True,
        )

        # Handle partial failures gracefully
        if isinstance(structured, Exception):
            logger.warning("Postgres fetch failed: %s", structured)
            structured = {}
        if isinstance(semantic, Exception):
            logger.warning("Qdrant fetch failed: %s", semantic)
            semantic = None
        if isinstance(session, Exception):
            logger.warning("Session fetch failed: %s", session)
            session = {}

        patient_context = {**structured}
        if semantic and semantic.get("score", 0) >= SIMILARITY_THRESHOLD:
            patient_context["semantic_summary"] = semantic.get("summary", "")

        return {"patient": patient_context, "session": session}

    async def _fetch_structured(self, patient_id: str) -> dict:
        """Fetch last 2 appointments + patient profile from Postgres."""
        pool = await self._get_pg()
        async with pool.acquire() as conn:
            # Patient profile
            row = await conn.fetchrow(
                """
                SELECT name, preferred_lang, preferred_doctor, preferred_name
                FROM patient_profiles WHERE patient_id = $1
                """,
                patient_id,
            )
            if not row:
                return {}

            profile = dict(row)

            # Last 2 appointments
            appts = await conn.fetch(
                """
                SELECT doctor_name, start_time, status, specialty
                FROM appointments
                WHERE patient_id = $1 AND start_time < now()
                ORDER BY start_time DESC LIMIT 2
                """,
                patient_id,
            )
            profile["last_appointment"] = dict(appts[0]) if appts else None
            profile["appointment_history"] = [dict(a) for a in appts]

            return profile

    async def _fetch_semantic(self, patient_id: str, query: str) -> dict | None:
        """Top-1 semantic hit from Qdrant on patient's history."""
        query_vector = await self._embed(query)
        if query_vector is None:
            return None

        results = await self._qdrant.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            query_filter=Filter(
                must=[FieldCondition(key="patient_id", match=MatchValue(value=patient_id))]
            ),
            limit=1,
            score_threshold=SIMILARITY_THRESHOLD,
        )

        if not results:
            return None

        hit = results[0]
        return {
            "score": hit.score,
            "summary": hit.payload.get("summary", ""),
        }

    async def _fetch_session(self, session_id: str) -> dict:
        """Fetch current session state from Redis (via session store)."""
        from .session_store import SessionStore
        store = SessionStore()
        return await store.get_session(session_id)

    async def _embed(self, text: str) -> list[float] | None:
        """Embed text using a small local model or OpenAI embeddings."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=0.05) as client:  # 50ms timeout
                resp = await client.post(
                    "http://llm-service:8001/v1/embeddings",
                    json={"model": "text-embedding-3-small", "input": text},
                )
                return resp.json()["data"][0]["embedding"]
        except Exception as e:
            logger.debug("Embedding failed: %s", e)
            return None

    async def store_patient_context(
        self, patient_id: str, summary: str, embedding: list[float]
    ):
        """
        Store or update patient context vector in Qdrant.
        Called after each call to update behavioral signals.
        """
        import uuid
        await self._qdrant.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[{
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, patient_id)),
                "vector": embedding,
                "payload": {
                    "patient_id": patient_id,
                    "summary": summary,
                },
            }],
        )

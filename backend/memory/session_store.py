"""
memory/session_store.py

Redis-backed session state for active calls.
Uses msgpack serialization (40% smaller + faster than JSON).
TTL: 30 minutes per session.
"""
import logging
import os
from typing import Any, TypedDict

import msgpack
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SESSION_TTL = 1800  # 30 minutes in seconds
SESSION_KEY_PREFIX = "session:"


class TurnRecord(TypedDict):
    user: str
    assistant: str
    intent: str
    timestamp: float


class SessionState(TypedDict):
    turn_history: list[TurnRecord]   # last 8 turns
    detected_lang: str               # en | hi | ta
    current_intent: str
    pending_slot: dict | None        # partially confirmed booking
    patient_id: str
    confirmed_doctor: str | None
    retry_count: int
    call_started_at: float


class SessionStore:
    def __init__(self):
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=False,  # raw bytes for msgpack
                max_connections=20,
            )
        return self._redis

    async def get_session(self, session_id: str) -> SessionState:
        """Fetch session state. Returns default state if not found."""
        r = await self._get_redis()
        key = f"{SESSION_KEY_PREFIX}{session_id}"

        raw = await r.get(key)
        if raw is None:
            return self._default_state()

        try:
            return msgpack.unpackb(raw, raw=False)
        except Exception as e:
            logger.error("Failed to deserialize session %s: %s", session_id, e)
            return self._default_state()

    async def update_session(
        self,
        session_id: str,
        intent: Any = None,
        transcript: str = "",
        tool_result: Any = None,
        assistant_response: str = "",
    ):
        """Append a turn to session history and persist."""
        r = await self._get_redis()
        key = f"{SESSION_KEY_PREFIX}{session_id}"

        # Read-modify-write (atomic enough for single-session access)
        state = await self.get_session(session_id)

        import time
        turn: TurnRecord = {
            "user": transcript,
            "assistant": assistant_response,
            "intent": intent.label if intent else "unknown",
            "timestamp": time.time(),
        }

        state["turn_history"] = (state["turn_history"] + [turn])[-8:]  # keep last 8
        state["current_intent"] = intent.label if intent else state.get("current_intent", "")

        if tool_result:
            if tool_result.status == "booked":
                state["pending_slot"] = None
                state["confirmed_doctor"] = tool_result.data.get("doctor_name")
            elif tool_result.status == "conflict":
                state["pending_slot"] = tool_result.data.get("alternatives", [{}])[0]

        packed = msgpack.packb(state, use_bin_type=True)
        await r.setex(key, SESSION_TTL, packed)

    async def delete_session(self, session_id: str):
        """Clean up session on call end."""
        r = await self._get_redis()
        await r.delete(f"{SESSION_KEY_PREFIX}{session_id}")

    def _default_state(self) -> SessionState:
        import time
        return {
            "turn_history": [],
            "detected_lang": "en",
            "current_intent": "",
            "pending_slot": None,
            "patient_id": "",
            "confirmed_doctor": None,
            "retry_count": 0,
            "call_started_at": time.time(),
        }

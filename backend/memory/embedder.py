"""
memory/embedder.py

Text embedding for Qdrant vector storage.
Uses a lightweight local model (all-MiniLM-L6-v2, 22M params, 384 dims).
Runs on CPU — embedding takes ~5ms per query.
"""
import asyncio
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _get_model():
    """Lazy-load the embedding model (cached after first call)."""
    from sentence_transformers import SentenceTransformer
    logger.info("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("Embedding model loaded")
    return model


async def embed_text(text: str) -> list[float]:
    """
    Embed text asynchronously (runs model in thread pool to avoid blocking event loop).
    Returns a 384-dim float vector.
    """
    loop = asyncio.get_event_loop()
    model = _get_model()
    vector = await loop.run_in_executor(None, lambda: model.encode(text).tolist())
    return vector

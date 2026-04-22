"""
llm_service/vllm_engine.py

Wrapper around the vLLM OpenAI-compatible endpoint.
Supports model routing: fast 7B model for conversational turns,
full model for complex slot resolution.
"""
import logging
import os
from typing import AsyncIterator

import httpx

logger = logging.getLogger(__name__)

# vLLM serves both models on different ports
FAST_MODEL_URL = os.getenv("FAST_MODEL_URL", "http://localhost:8001/v1")   # AWQ 7B
FULL_MODEL_URL = os.getenv("FULL_MODEL_URL", "http://localhost:8002/v1")   # Full model

FAST_MODEL_NAME = os.getenv("FAST_MODEL_NAME", "mistral-7b-instruct-awq")
FULL_MODEL_NAME = os.getenv("FULL_MODEL_NAME", "mistral-7b-instruct")

# Intents that warrant the full model
COMPLEX_INTENTS = {"reschedule", "cancel"}


class VLLMEngine:
    """
    Async streaming client for vLLM.
    Selects model based on intent complexity.
    """

    def __init__(self):
        self._fast_client = httpx.AsyncClient(
            base_url=FAST_MODEL_URL,
            timeout=httpx.Timeout(connect=0.5, read=10.0, write=1.0, pool=1.0),
        )
        self._full_client = httpx.AsyncClient(
            base_url=FULL_MODEL_URL,
            timeout=httpx.Timeout(connect=0.5, read=30.0, write=1.0, pool=1.0),
        )

    async def stream_completion(
        self,
        messages: list[dict],
        intent: str = "other",
        temperature: float = 0.6,
        max_tokens: int = 200,
    ) -> AsyncIterator[str]:
        """
        Stream tokens from the appropriate model.
        Yields token strings as they arrive.
        """
        use_full = intent in COMPLEX_INTENTS
        client = self._full_client if use_full else self._fast_client
        model = FULL_MODEL_NAME if use_full else FAST_MODEL_NAME

        logger.debug(
            "LLM request: model=%s intent=%s tokens=%d",
            model, intent, max_tokens
        )

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        async with client.stream("POST", "/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    import json
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"]
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (KeyError, json.JSONDecodeError):
                    continue

    async def close(self):
        await self._fast_client.aclose()
        await self._full_client.aclose()


# Module-level singleton
engine = VLLMEngine()

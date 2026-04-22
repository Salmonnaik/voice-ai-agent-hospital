"""
llm_service/token_stream.py

Streams LLM tokens and pipes them to TTS as soon as a sentence boundary is reached.
This is the key trick for achieving <450ms first audio:
  → Don't wait for full LLM response before starting TTS
  → Buffer tokens until first sentence boundary, then fire TTS immediately
  → Continue synthesizing rest of response while audio plays
"""
import asyncio
import logging
import re
from typing import AsyncIterator

import httpx

from tts_service.voice_selector import get_tts_stream

logger = logging.getLogger(__name__)

LLM_BASE_URL = "http://llm-service:8001/v1"

# Sentence boundary patterns
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+|(?<=[।॥])\s*")
MIN_SENTENCE_CHARS = 20   # Don't fire TTS for very short fragments
MAX_BUFFER_CHARS = 80     # Fire TTS even without punctuation after 80 chars


async def llm_to_tts_pipeline(
    prompt: list[dict],
    lang: str,
) -> AsyncIterator[bytes]:
    """
    Stream LLM tokens → detect sentence boundaries → synthesize TTS chunks.
    Yields raw PCM16 audio bytes as they become available.

    Latency breakdown:
      - LLM TTFT:          ~80ms (7B AWQ on A10G)
      - First sentence:    ~40-120ms of tokens
      - TTS first chunk:   ~50ms
      ─────────────────────
      First audio out:     ~170-250ms from prompt submission
    """
    tts_client = get_tts_client(lang)
    token_buffer = ""
    sentence_queue: asyncio.Queue[str] = asyncio.Queue()
    llm_done = asyncio.Event()

    # Task 1: Stream LLM tokens, detect sentences, enqueue for TTS
    async def stream_llm():
        nonlocal token_buffer
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    f"{LLM_BASE_URL}/chat/completions",
                    json={
                        "model": "mistral-7b-instruct-awq",
                        "messages": prompt,
                        "max_tokens": 200,
                        "temperature": 0.7,
                        "stream": True,
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            import json
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if not delta:
                                continue

                            token_buffer += delta

                            # Check for sentence boundary
                            parts = SENTENCE_END_RE.split(token_buffer, maxsplit=1)
                            if len(parts) > 1:
                                sentence = parts[0].strip()
                                if len(sentence) >= MIN_SENTENCE_CHARS:
                                    await sentence_queue.put(sentence)
                                    token_buffer = parts[1] if len(parts) > 1 else ""
                            elif len(token_buffer) >= MAX_BUFFER_CHARS:
                                # Force flush on long unbounded text
                                await sentence_queue.put(token_buffer.strip())
                                token_buffer = ""
                        except Exception as e:
                            logger.debug("Token parse error: %s", e)
        except Exception as e:
            logger.error("LLM stream error: %s", e)
        finally:
            # Flush remaining buffer
            if token_buffer.strip():
                await sentence_queue.put(token_buffer.strip())
            llm_done.set()

    # Start LLM streaming in background
    llm_task = asyncio.create_task(stream_llm())

    # Task 2: Pull sentences from queue, synthesize, yield audio
    while True:
        try:
            sentence = await asyncio.wait_for(sentence_queue.get(), timeout=0.3)
        except asyncio.TimeoutError:
            if llm_done.is_set() and sentence_queue.empty():
                break
            continue

        logger.debug("Synthesizing sentence (%d chars): %r", len(sentence), sentence[:50])

        try:
            async for audio_chunk in tts_client.synthesize_stream(sentence, lang=lang):
                yield audio_chunk
        except Exception as e:
            logger.error("TTS synthesis failed: %s", e)

        if llm_done.is_set() and sentence_queue.empty():
            break

    await llm_task

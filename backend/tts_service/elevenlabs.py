"""
tts_service/elevenlabs.py

ElevenLabs streaming TTS client.
Uses the streaming endpoint to get first audio chunk in ~60ms.
"""
import logging
import os
from typing import AsyncIterator

import httpx

logger = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"


class ElevenLabsStream:
    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=ELEVENLABS_BASE_URL,
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            timeout=httpx.Timeout(connect=1.0, read=30.0, write=5.0, pool=2.0),
        )

    async def stream(
        self,
        text: str,
        voice_id: str,
        model: str = "eleven_turbo_v2",
    ) -> AsyncIterator[bytes]:
        """Stream MP3 audio chunks for the given text."""
        payload = {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.3,
                "use_speaker_boost": False,  # saves ~20ms
            },
            "output_format": "mp3_44100_128",
        }

        url = f"/text-to-speech/{voice_id}/stream"
        async with self._client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=4096):
                if chunk:
                    yield chunk

    async def close(self):
        await self._client.aclose()

"""
tts_service/voice_selector.py

Routes TTS requests to the correct provider and voice based on detected language.
All three voices are pre-loaded and kept warm to avoid initialization latency.

Latency targets:
  ElevenLabs (EN): ~60ms to first audio chunk
  Azure Neural (HI): ~45ms to first chunk
  Azure Neural (TA): ~45ms to first chunk
"""
import logging
import os
from typing import AsyncIterator

from .elevenlabs import ElevenLabsStream
from .azure_tts import AzureTTSStream

logger = logging.getLogger(__name__)

# Voice configuration per language
VOICE_CONFIG = {
    "en": {
        "provider": "elevenlabs",
        "voice_id": os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB"),  # Priya (Indian accent)
        "model": "eleven_turbo_v2",
    },
    "hi": {
        "provider": "azure",
        "voice": "hi-IN-SwaraNeural",
        "style": "customerservice",
    },
    "ta": {
        "provider": "azure",
        "voice": "ta-IN-PallaviNeural",
        "style": None,
    },
}

# Warm TTS clients (initialized at module load)
_eleven = ElevenLabsStream()
_azure = AzureTTSStream() if os.getenv("AZURE_TTS_KEY") else None


async def get_tts_stream(text: str, lang: str = "en") -> AsyncIterator[bytes]:
    """
    Yield raw audio bytes (PCM16 or MP3) for the given text and language.
    """
    config = VOICE_CONFIG.get(lang, VOICE_CONFIG["en"])
    provider = config["provider"]

    logger.debug("TTS: provider=%s lang=%s chars=%d", provider, lang, len(text))

    if provider == "elevenlabs":
        async for chunk in _eleven.stream(
            text=text,
            voice_id=config["voice_id"],
            model=config["model"],
        ):
            yield chunk

    elif provider == "azure":
        if not _azure:
            # Fallback to ElevenLabs for non-English languages when Azure is not available
            logger.warning("Azure TTS not configured, falling back to ElevenLabs for lang=%s", lang)
            async for chunk in _eleven.stream(
                text=text,
                voice_id=VOICE_CONFIG["en"]["voice_id"],
                model=VOICE_CONFIG["en"]["model"],
            ):
                yield chunk
        else:
            async for chunk in _azure.stream(
                text=text,
                voice=config["voice"],
                style=config.get("style"),
            ):
                yield chunk

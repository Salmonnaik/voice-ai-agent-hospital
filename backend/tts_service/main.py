"""
tts_service/main.py

FastAPI TTS service. Streams audio bytes for a given text+lang.
"""
import logging
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from .voice_selector import get_tts_stream

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TTS Service")


class TTSRequest(BaseModel):
    text: str
    lang: str = "en"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tts"}


@app.post("/synthesize/stream")
async def synthesize_stream(req: TTSRequest):
    """Stream synthesized audio for the given text and language."""
    async def audio_gen():
        async for chunk in get_tts_stream(req.text, lang=req.lang):
            yield chunk

    return StreamingResponse(audio_gen(), media_type="audio/mpeg")

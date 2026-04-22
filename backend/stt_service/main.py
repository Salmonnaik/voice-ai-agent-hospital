"""
stt_service/main.py

HTTP + gRPC gateway for the STT service.
The HTTP endpoint accepts raw PCM audio and returns a transcript.
The real production path uses the persistent Deepgram WS per session.
"""
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from deepgram_stream import stt_pool as connection_pool, DeepgramSession
from lang_signal import detect_lang_switch, normalize_lang

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="STT Service")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "stt", "active_connections": len(connection_pool._sessions)}


@app.post("/transcribe")
async def transcribe(request: Request):
    """
    One-shot transcription endpoint (for testing/fallback).
    Production path: use Deepgram WS streaming via DeepgramStream.
    """
    lang = request.headers.get("X-Language", "en")
    lang = normalize_lang(lang)
    audio = await request.body()

    if not audio:
        raise HTTPException(status_code=400, detail="No audio data provided")

    results = []
    done = False

    stream = DeepgramStream(lang=lang)
    await stream.start(
        on_interim=lambda t: None,
        on_final=lambda t: results.append(t),
    )
    await stream.send_audio(audio)
    await stream.finish()

    transcript = " ".join(results).strip()
    return JSONResponse({"transcript": transcript, "lang": lang})


@app.post("/session/start")
async def session_start(body: dict):
    """Start a persistent Deepgram WS for a call session."""
    session_id = body.get("session_id")
    lang = body.get("lang", "en")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    stream = await connection_pool.get_or_create(session_id, lang)
    return {"status": "started", "session_id": session_id}


@app.post("/session/end")
async def session_end(body: dict):
    """Release a Deepgram WS connection back to the pool."""
    session_id = body.get("session_id")
    if session_id:
        await connection_pool.release(session_id)
    return {"status": "released"}

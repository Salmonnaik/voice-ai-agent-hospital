"""
orchestrator/main.py

FastAPI + gRPC server for the orchestrator service.
Receives audio events from the gateway, runs the agent loop, streams TTS back.
"""
import asyncio
import logging
from concurrent import futures

import grpc
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from .agent_loop import agent_turn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Orchestrator Service")

# --- OpenTelemetry setup ---
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}


class VoiceOrchestratorServicer:
    """gRPC servicer — handles bidirectional streaming from the gateway."""

    async def ProcessCall(self, request_iterator, context):
        session_id = None
        patient_id = None
        lang = "en"
        audio_buffer = bytearray()

        async for event in request_iterator:
            event_type = event.type

            if event_type == "SESSION_INIT":
                session_id = event.call_id
                logger.info("Session init: %s", session_id)
                patient_id = f"patient_{session_id[:8]}"

            elif event_type == "AUDIO_CHUNK":
                audio_buffer.extend(event.audio)
                lang = event.lang or lang

            elif event_type == "UTTERANCE_END":
                if not session_id:
                    logger.warning("UTTERANCE_END before SESSION_INIT — skipping")
                    audio_buffer.clear()
                    continue

                transcript = await _transcribe(bytes(audio_buffer), lang)
                audio_buffer.clear()

                if transcript:
                    async for audio_chunk in agent_turn(
                        session_id=session_id,
                        patient_id=patient_id,
                        transcript=transcript,
                        lang=lang,
                    ):
                        yield {"audio": audio_chunk, "type": "AUDIO_CHUNK"}

                    yield {"audio": b"", "type": "STREAM_END"}

            elif event_type == "BARGE_IN":
                logger.info("Barge-in received for session %s", session_id)
                yield {"audio": b"", "type": "BARGE_IN_ACK"}


async def _transcribe(audio: bytes, lang: str) -> str:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post(
                "http://stt-service:8002/transcribe",
                content=audio,
                headers={"X-Language": lang},
            )
            return resp.json().get("transcript", "")
    except Exception as e:
        logger.error("STT call failed: %s", e)
        return ""


def start_grpc_server():
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=20),
        options=[
            ("grpc.max_receive_message_length", 4 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 30000),
        ],
    )
    server.add_insecure_port("[::]:50052")
    return server


if __name__ == "__main__":
    import uvicorn

    async def main():
        grpc_server = start_grpc_server()
        await grpc_server.start()
        logger.info("gRPC server started on :50052")
        # Start uvicorn in the same event loop
        config = uvicorn.Config(app, host="0.0.0.0", port=8002, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(main())

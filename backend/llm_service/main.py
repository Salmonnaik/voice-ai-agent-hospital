"""
llm_service/main.py

Thin FastAPI wrapper that exposes vLLM streaming to internal services.
Also handles model routing (7B fast vs full model).
"""
import logging
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from vllm_engine import engine
from model_router import route_intent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Service")


class CompletionRequest(BaseModel):
    messages: list[dict]
    intent: str = "other"
    temperature: float = 0.6
    max_tokens: int = 200


@app.get("/health")
async def health():
    return {"status": "ok", "service": "llm"}


@app.post("/complete/stream")
async def stream_completion(req: CompletionRequest):
    """Stream tokens from the LLM (SSE format)."""
    async def generate():
        async for token in engine.stream_completion(
            messages=req.messages,
            intent=req.intent,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        ):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

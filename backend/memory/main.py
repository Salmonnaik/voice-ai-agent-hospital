"""
memory/main.py

FastAPI memory service — session state + patient context retrieval.
"""
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from .session_store import SessionStore
from .retrieval import MemoryRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Memory Service")
store = SessionStore()
retriever = MemoryRetriever()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "memory"}


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    return await store.get_session(session_id)


class ContextRequest(BaseModel):
    session_id: str
    patient_id: str
    query: str


@app.post("/context")
async def get_context(req: ContextRequest):
    return await retriever.fetch_all(
        session_id=req.session_id,
        patient_id=req.patient_id,
        query=req.query,
    )


@app.delete("/patient/{patient_id}")
async def gdpr_delete(patient_id: str):
    """GDPR deletion — removes all patient vectors and session data."""
    await retriever.delete_patient_data(patient_id)
    return {"status": "deleted", "patient_id": patient_id}

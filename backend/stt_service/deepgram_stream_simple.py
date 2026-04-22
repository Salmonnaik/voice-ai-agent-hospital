"""
Simplified Deepgram streaming adapter
"""
import asyncio
import logging
import os
from typing import AsyncIterator

from deepgram import DeepgramClient

logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = os.environ["DEEPGRAM_API_KEY"]

class DeepgramStream:
    """Simplified Deepgram streaming implementation"""
    
    def __init__(self):
        self.client = DeepgramClient(DEEPGRAM_API_KEY)
    
    async def stream(self, audio_data: bytes, lang: str = "en") -> AsyncIterator[str]:
        """Stream audio and get transcription results"""
        try:
            # For now, return a placeholder transcription
            # In a real implementation, this would use Deepgram's streaming API
            yield f"Transcription placeholder for language {lang}"
        except Exception as e:
            logger.error(f"Deepgram streaming error: {e}")
            yield "Transcription failed"

# Connection pool for sessions
connection_pool = {}

def get_deepgram_session(session_id: str, lang: str = "en"):
    """Get or create a Deepgram session"""
    if session_id not in connection_pool:
        connection_pool[session_id] = DeepgramStream()
    return connection_pool[session_id]

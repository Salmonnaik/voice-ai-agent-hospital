"""
Simplified Deepgram streaming adapter
"""
import asyncio
import logging
import os
from typing import AsyncIterator, Callable

from deepgram import DeepgramClient

logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = os.environ["DEEPGRAM_API_KEY"]

class DeepgramSession:
    """Simplified Deepgram streaming session"""
    
    def __init__(self, session_id: str, lang: str = "en"):
        self.session_id = session_id
        self.lang = lang
        self._client = DeepgramClient(DEEPGRAM_API_KEY)
        self._connected = False

    async def connect(
        self,
        on_interim: Callable[[str], None],
        on_final: Callable[[str, float], None],
    ):
        """Simplified connection - just mark as connected"""
        self._interim_callback = on_interim
        self._final_callback = on_final
        self._connected = True
        logger.info("Deepgram session connected | session=%s | lang=%s", self.session_id, self.lang)

    async def send_audio(self, audio_bytes: bytes):
        """Placeholder for sending audio"""
        if self._connected:
            # For now, just log that we received audio
            logger.debug("Received %d bytes of audio", len(audio_bytes))

    async def disconnect(self):
        """Disconnect session"""
        self._connected = False

class STTConnectionPool:
    """Pool of Deepgram sessions"""
    
    def __init__(self):
        self._sessions: dict[str, DeepgramSession] = {}

    async def get_or_create(
        self,
        session_id: str,
        lang: str,
        on_interim: Callable,
        on_final: Callable,
    ) -> DeepgramSession:
        if session_id not in self._sessions:
            session = DeepgramSession(session_id=session_id, lang=lang)
            await session.connect(on_interim=on_interim, on_final=on_final)
            self._sessions[session_id] = session
        return self._sessions[session_id]

    async def close(self, session_id: str):
        session = self._sessions.pop(session_id, None)
        if session:
            await session.disconnect()

    async def close_all(self):
        for session in self._sessions.values():
            await session.disconnect()
        self._sessions.clear()

# Module-level singleton pool
stt_pool = STTConnectionPool()

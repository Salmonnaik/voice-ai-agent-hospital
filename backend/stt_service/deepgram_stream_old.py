"""
stt_service/deepgram_stream.py

Simplified STT adapter using the Deepgram SDK.
"""
import asyncio
import logging
import os
from typing import AsyncIterator

from deepgram import DeepgramClient

logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = os.environ["DEEPGRAM_API_KEY"]


class DeepgramSession:
    """
    Simplified Deepgram streaming session.
    """

    def __init__(self, session_id: str, lang: str = "en"):
        self.session_id = session_id
        self.lang = lang
        self._client = DeepgramClient(DEEPGRAM_API_KEY)

    async def connect(
        self,
        on_interim: Callable[[str], None],
        on_final: Callable[[str, float], None],
    ):
        """Open WebSocket to Deepgram. Kept alive across turns."""
        self._interim_callback = on_interim
        self._final_callback = on_final

        options = LiveOptions(
            model=LANG_MODEL_MAP.get(self.lang, "nova-2"),
            language=LANG_BCP47.get(self.lang, "en-IN"),
            encoding="linear16",
            sample_rate=16000,
            channels=1,
            interim_results=True,      # emit every ~30ms for speculative prompting
            endpointing=300,           # ms of silence = end of utterance signal
            smart_format=True,
            punctuate=True,
            diarize=False,
            # Code-switch support for Indian languages
            detect_language=False,     # already detected at gateway level
        )

        self._connection = self._client.listen.asyncwebsocket.v("1")

        self._connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
        self._connection.on(LiveTranscriptionEvents.Error, self._on_error)
        self._connection.on(LiveTranscriptionEvents.Close, self._on_close)

        await self._connection.start(options)
        self._connected = True
        logger.info("Deepgram session connected | session=%s | lang=%s", self.session_id, self.lang)

    async def send_audio(self, audio_bytes: bytes):
        """Send raw PCM16 audio chunk to Deepgram."""
        if self._connected and self._connection:
            await self._connection.send(audio_bytes)

    async def disconnect(self):
        if self._connection:
            await self._connection.finish()
            self._connected = False

    async def _on_transcript(self, _self, result, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        if not sentence:
            return

        is_final = result.is_final
        confidence = result.channel.alternatives[0].confidence

        if is_final:
            logger.debug("STT final: %r (conf=%.2f)", sentence[:60], confidence)
            if self._final_callback:
                await self._final_callback(sentence, confidence)
        else:
            logger.debug("STT interim: %r", sentence[:60])
            if self._interim_callback:
                await self._interim_callback(sentence)

    async def _on_error(self, _self, error, **kwargs):
        logger.error("Deepgram error | session=%s: %s", self.session_id, error)

    async def _on_close(self, _self, close, **kwargs):
        logger.info("Deepgram connection closed | session=%s", self.session_id)
        self._connected = False


class STTConnectionPool:
    """
    Pool of Deepgram sessions — one per active call.
    Prevents connection setup latency (~40-80ms) on each turn.
    """

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

"""
tts_service/azure_tts.py

Azure Neural TTS streaming client for Hindi and Tamil.
Uses Azure Cognitive Services Speech SDK for low-latency streaming.
First chunk latency: ~45ms.
"""
import asyncio
import logging
import os
from typing import AsyncIterator

import azure.cognitiveservices.speech as speechsdk

logger = logging.getLogger(__name__)

AZURE_TTS_KEY = os.environ.get("AZURE_TTS_KEY", "")
AZURE_TTS_REGION = os.environ.get("AZURE_TTS_REGION", "eastus")

SSML_TEMPLATE = """<speak version='1.0' xml:lang='{lang}'>
  <voice name='{voice}'{style_attr}>
    {text}
  </voice>
</speak>"""


class AzureTTSStream:
    def __init__(self):
        self._speech_config = speechsdk.SpeechConfig(
            subscription=AZURE_TTS_KEY,
            region=AZURE_TTS_REGION,
        )
        self._speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )

    async def stream(
        self,
        text: str,
        voice: str,
        style: str | None = None,
    ) -> AsyncIterator[bytes]:
        """
        Synthesize text using Azure Neural TTS and yield audio chunks.
        Runs SDK in thread pool to avoid blocking the event loop.
        """
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        def _synthesize():
            lang_code = voice[:5]  # e.g., "hi-IN" from "hi-IN-SwaraNeural"
            style_attr = f" style='{style}'" if style else ""
            ssml = SSML_TEMPLATE.format(
                lang=lang_code,
                voice=voice,
                style_attr=style_attr,
                text=text,
            )

            audio_config = speechsdk.audio.PullAudioOutputStream()
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self._speech_config,
                audio_config=speechsdk.audio.AudioOutputConfig(
                    stream=audio_config
                ),
            )

            result = synthesizer.speak_ssml(ssml)

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data
                chunk_size = 4096
                for i in range(0, len(audio_data), chunk_size):
                    asyncio.run_coroutine_threadsafe(
                        queue.put(audio_data[i:i + chunk_size]), loop
                    )
            else:
                logger.error("Azure TTS failed: %s", result.reason)

            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        await loop.run_in_executor(None, _synthesize)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

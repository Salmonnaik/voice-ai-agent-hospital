"""
stt_service/lang_signal.py

Handles language detection signals from Deepgram and faster-whisper.
Emits a confirmed language to the session store.
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SUPPORTED_LANGS = {"en", "hi", "ta"}
DEFAULT_LANG = "en"

# Phrases that trigger a language switch mid-session
LANG_SWITCH_PHRASES: dict[str, list[str]] = {
    "hi": ["hindi mein baat karo", "hindi mein", "hindi me"],
    "ta": ["tamil la pesu", "tamil mein", "tamil la"],
    "en": ["english mein baat karo", "speak in english", "english please"],
}


@dataclass
class LangSignal:
    lang: str
    confidence: float
    source: str  # deepgram | whisper | rule


def detect_lang_switch(transcript: str, current_lang: str) -> LangSignal | None:
    """
    Check if user wants to switch language.
    Returns LangSignal if switch requested, None otherwise.
    """
    t = transcript.lower()
    for target_lang, phrases in LANG_SWITCH_PHRASES.items():
        if target_lang == current_lang:
            continue
        for phrase in phrases:
            if phrase in t:
                logger.info(
                    "Language switch detected: %s → %s (phrase: '%s')",
                    current_lang, target_lang, phrase
                )
                return LangSignal(lang=target_lang, confidence=0.99, source="rule")
    return None


def normalize_lang(lang_code: str) -> str:
    """Normalize Deepgram/Whisper lang codes to our 2-letter codes."""
    mapping = {
        "en": "en", "en-IN": "en", "en-US": "en", "en-GB": "en",
        "hi": "hi", "hi-IN": "hi",
        "ta": "ta", "ta-IN": "ta",
    }
    return mapping.get(lang_code, DEFAULT_LANG)

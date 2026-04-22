"""
orchestrator/intent_classifier.py

Fast intent classification using a small cached model.
Routes to 7B quantized model for speed — this must complete in <20ms.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

FAST_MODEL_URL = "http://llm-service:8001/v1/chat/completions"


@dataclass
class IntentResult:
    label: str                        # book | reschedule | cancel | check_slots | greeting | faq | other
    confidence: float
    entities: dict[str, Any] = field(default_factory=dict)
    raw: str = ""


SYSTEM_PROMPT = """You are a medical appointment intent classifier.
Classify the user's message into ONE of these intents:
- book: wants to book/schedule an appointment
- reschedule: wants to change an existing appointment
- cancel: wants to cancel an appointment
- check_slots: wants to know available times/doctors
- greeting: hello/hi/general opener
- faq: general question about hospital, timings, services
- other: anything else

Also extract entities:
- doctor_name: mentioned doctor (if any)
- specialty: medical specialty (if any)
- preferred_time: time/date mentioned (if any)
- appointment_id: if rescheduling/cancelling

Respond ONLY with valid JSON:
{"intent": "<label>", "confidence": 0.0-1.0, "entities": {...}}"""


class IntentClassifier:
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=0.1)  # 100ms hard timeout

    async def classify(self, transcript: str, lang: str = "en") -> IntentResult:
        """
        Classify intent. Uses the fast 7B model.
        Falls back to rule-based classifier on timeout/error.
        """
        try:
            resp = await self._client.post(
                FAST_MODEL_URL,
                json={
                    "model": "mistral-7b-instruct-awq",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"[lang={lang}] {transcript}"},
                    ],
                    "max_tokens": 150,
                    "temperature": 0.0,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return IntentResult(
                label=parsed.get("intent", "other"),
                confidence=float(parsed.get("confidence", 0.5)),
                entities=parsed.get("entities", {}),
                raw=content,
            )
        except Exception as e:
            logger.warning("Intent classifier failed (%s), using rule-based fallback", e)
            return self._rule_based(transcript)

    def _rule_based(self, transcript: str) -> IntentResult:
        """Simple keyword-based fallback — always returns in <1ms."""
        t = transcript.lower()
        if any(w in t for w in ["book", "schedule", "appointment", "chahiye", "booking"]):
            return IntentResult("book", 0.7)
        if any(w in t for w in ["reschedule", "change", "postpone", "badal"]):
            return IntentResult("reschedule", 0.7)
        if any(w in t for w in ["cancel", "drop", "hatao"]):
            return IntentResult("cancel", 0.7)
        if any(w in t for w in ["available", "slots", "free", "when", "time"]):
            return IntentResult("check_slots", 0.65)
        if any(w in t for w in ["hello", "hi", "namaste", "vanakkam"]):
            return IntentResult("greeting", 0.9)
        return IntentResult("other", 0.5)

"""
llm_service/model_router.py

Routes intents to the appropriate model:
  - Fast path: AWQ quantized 7B (TTFT ~80ms) — conversational turns
  - Full path: standard model (TTFT ~300ms) — complex resolution only

The router is called by the orchestrator before invoking the LLM.
"""

FAST_INTENTS = {"greeting", "faq", "check_slots", "other", "book"}
FULL_INTENTS = {"reschedule", "cancel"}


def route_intent(intent: str) -> str:
    """
    Returns 'fast' or 'full' based on the intent label.
    Default: fast (fail safe — better to be quick than thorough for unknown intents).
    """
    if intent in FULL_INTENTS:
        return "full"
    return "fast"


def should_use_full_model(intent: str, confidence: float) -> bool:
    """
    Returns True if the full model should be used.
    Also considers confidence — very low confidence suggests ambiguity needing more capacity.
    """
    if intent in FULL_INTENTS:
        return True
    if confidence < 0.5:
        return True  # ambiguous — use more powerful model for safety
    return False

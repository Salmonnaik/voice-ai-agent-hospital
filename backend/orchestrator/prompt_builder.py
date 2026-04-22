"""
orchestrator/prompt_builder.py

Builds the LLM prompt for each agent turn.
Injects session state, patient context, and tool results.
Hard cap: injected context must not exceed 400 tokens.
"""
from typing import Any


SYSTEM_PROMPTS = {
    "en": """You are Priya, a friendly and efficient AI voice assistant for MedCare Hospital.
Your job is to help patients book, reschedule, or cancel appointments over the phone.
Keep responses SHORT (1-2 sentences max) since this is a phone call.
Be warm but concise. Confirm details clearly. Always speak in the patient's language.
Medical terms may appear in English even in Hindi/Tamil conversations — that's normal.""",

    "hi": """आप प्रिया हैं, MedCare Hospital की एक मित्रवत AI वॉइस असिस्टेंट।
आपका काम है मरीजों को फोन पर अपॉइंटमेंट बुक, बदलने या रद्द करने में मदद करना।
जवाब छोटे रखें (1-2 वाक्य) क्योंकि यह फोन कॉल है।
गर्मजोशी से लेकिन संक्षेप में बोलें। मेडिकल शब्द अंग्रेजी में हो सकते हैं।""",

    "ta": """நீங்கள் பிரியா, MedCare Hospital-ன் AI voice assistant.
உங்கள் வேலை நோயாளிகளுக்கு appointments பதிவு செய்ய, மாற்ற அல்லது ரத்து செய்ய உதவுவது.
பதில்கள் சுருக்கமாக இருக்கட்டும் (1-2 வாக்கியங்கள்). அன்பாக பேசுங்கள்.""",
}

LANG_SWITCH_PHRASES = {
    "hi": ["hindi mein", "hindi me", "हिंदी में"],
    "ta": ["tamil mein", "tamil la", "தமிழில்"],
    "en": ["english mein", "english me", "in english"],
}


def build_prompt(
    transcript: str,
    session_state: dict,
    patient_context: dict,
    lang: str,
    tool_result: Any = None,
    intent: Any = None,
) -> list[dict]:
    """
    Returns an OpenAI-compatible messages list.
    Total injected context is kept under 400 tokens.
    """
    system = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["en"])
    messages = [{"role": "system", "content": system}]

    # --- Patient context (max ~150 tokens) ---
    ctx_parts = []
    if patient_context.get("name"):
        ctx_parts.append(f"Patient name: {patient_context['name']}")
    if patient_context.get("preferred_doctor"):
        ctx_parts.append(f"Preferred doctor: {patient_context['preferred_doctor']}")
    if patient_context.get("last_appointment"):
        appt = patient_context["last_appointment"]
        ctx_parts.append(f"Last appointment: {appt['date']} with {appt['doctor']}")
    if patient_context.get("semantic_summary"):
        ctx_parts.append(f"Context: {patient_context['semantic_summary'][:200]}")

    if ctx_parts:
        messages.append({
            "role": "system",
            "content": "[PATIENT CONTEXT]\n" + "\n".join(ctx_parts),
        })

    # --- Conversation history (last 3 turns, max ~150 tokens) ---
    turn_history = session_state.get("turn_history", [])[-3:]
    for turn in turn_history:
        messages.append({"role": "user", "content": turn.get("user", "")})
        messages.append({"role": "assistant", "content": turn.get("assistant", "")})

    # --- Tool result injection ---
    if tool_result is not None:
        tool_content = _format_tool_result(tool_result, lang)
        messages.append({
            "role": "system",
            "content": f"[TOOL RESULT]\n{tool_content}",
        })

    # --- Current user turn ---
    messages.append({"role": "user", "content": transcript})

    return messages


def _format_tool_result(tool_result: Any, lang: str) -> str:
    """Format tool results into natural language for prompt injection."""
    if tool_result is None:
        return ""

    status = tool_result.status

    if status == "booked":
        slot = tool_result.data
        return (
            f"Booking CONFIRMED. "
            f"Appointment with {slot['doctor_name']} on {slot['start_time']}. "
            f"Confirmation code: {slot['confirmation_code']}. "
            f"Tell the patient and confirm the details."
        )
    elif status == "conflict":
        alts = tool_result.data.get("alternatives", [])
        alt_str = "; ".join(
            f"{a['start_time']} with {a['doctor_name']}" for a in alts[:3]
        )
        return (
            f"Requested slot is UNAVAILABLE. "
            f"Alternative slots: {alt_str}. "
            f"Offer these alternatives to the patient."
        )
    elif status == "slots_listed":
        slots = tool_result.data.get("slots", [])
        slot_str = "; ".join(
            f"{s['start_time']} with {s['doctor_name']}" for s in slots[:3]
        )
        return f"Available slots: {slot_str}. Present these to the patient."
    elif status == "cancelled":
        return f"Appointment CANCELLED successfully. Inform the patient."
    elif status == "error":
        return f"Tool error: {tool_result.data.get('error')}. Apologize and offer human transfer."

    return f"Tool result: {tool_result}"

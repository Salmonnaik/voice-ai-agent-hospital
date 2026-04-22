"""
orchestrator/agent_loop.py

The main agent turn loop. Called once per utterance.
Handles intent classification, memory retrieval, tool dispatch, and LLM→TTS streaming.
"""
import asyncio
import logging
from typing import AsyncIterator

from opentelemetry import trace

from .intent_classifier import IntentClassifier, IntentResult
from .prompt_builder import build_prompt
from .tool_dispatcher import TOOL_MAP, ToolResult
from memory.session_store import SessionStore
from memory.retrieval import MemoryRetriever
from llm_service.token_stream import llm_to_tts_pipeline

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("orchestrator.agent_loop")

# Intents that require tool calls (vs pure conversational)
TOOL_INTENTS = {"book", "reschedule", "cancel", "check_slots"}

# Confidence threshold: below this, ask clarifying question instead of acting
TOOL_CONFIDENCE_THRESHOLD = 0.82

intent_classifier = IntentClassifier()
memory = SessionStore()
retriever = MemoryRetriever()


async def agent_turn(
    session_id: str,
    patient_id: str,
    transcript: str,
    lang: str,
) -> AsyncIterator[bytes]:
    """
    Process one agent turn: transcript in → TTS audio chunks out.

    Latency-critical path:
      1. Classify intent       ~15ms  (cached 7B)
      2. Fetch memory          ~20ms  (parallel with intent)
      3. [optional] Tool call  ~50ms
      4. Build prompt          ~1ms
      5. LLM TTFT              ~80ms
      6. TTS first chunk       ~50ms
      ─────────────────────────────
      Total p95 target:        <450ms
    """
    with tracer.start_as_current_span(
        "agent_turn",
        attributes={"session_id": session_id, "lang": lang},
    ) as span:
        # === Step 1+2: Intent classification and memory fetch in PARALLEL ===
        intent_task = asyncio.create_task(
            intent_classifier.classify(transcript, lang=lang)
        )
        memory_task = asyncio.create_task(
            retriever.fetch_all(session_id=session_id, patient_id=patient_id, query=transcript)
        )

        intent: IntentResult
        context: dict
        intent, context = await asyncio.gather(intent_task, memory_task)

        span.set_attribute("intent.label", intent.label)
        span.set_attribute("intent.confidence", intent.confidence)
        logger.info(
            "Intent: %s (%.2f) | Lang: %s | Session: %s",
            intent.label, intent.confidence, lang, session_id
        )

        # === Step 3: Tool dispatch (if high-confidence tool intent) ===
        tool_result: ToolResult | None = None

        if intent.label in TOOL_INTENTS and intent.confidence >= TOOL_CONFIDENCE_THRESHOLD:
            with tracer.start_as_current_span("tool_execution") as tool_span:
                tool_fn = TOOL_MAP.get(intent.label)
                if tool_fn:
                    try:
                        tool_result = await tool_fn(
                            entities=intent.entities,
                            patient_id=patient_id,
                            session_id=session_id,
                        )
                        tool_span.set_attribute("tool.outcome", tool_result.status)
                    except Exception as e:
                        logger.error("Tool execution failed: %s", e)
                        tool_span.record_exception(e)
                        # Graceful degradation: treat as conversational turn
                        tool_result = None

        # === Step 4: Build prompt ===
        prompt = build_prompt(
            transcript=transcript,
            session_state=context["session"],
            patient_context=context["patient"],
            lang=lang,
            tool_result=tool_result,
            intent=intent,
        )

        # === Step 5+6: Stream LLM tokens → TTS audio ===
        audio_chunks = []
        async for audio_chunk in llm_to_tts_pipeline(prompt=prompt, lang=lang):
            audio_chunks.append(audio_chunk)
            yield audio_chunk

        # === Step 7: Update session state (non-blocking, fire-and-forget) ===
        asyncio.create_task(
            memory.update_session(
                session_id=session_id,
                intent=intent,
                transcript=transcript,
                tool_result=tool_result,
            )
        )

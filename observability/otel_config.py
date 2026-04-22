"""
observability/otel_config.py

OpenTelemetry setup for distributed tracing across all Python services.

Spans emitted per agent turn:
  - vad_detection
  - stt_interim_first
  - stt_final
  - memory_fetch (parallel)
  - intent_classify
  - tool_execution (if applicable)
  - llm_ttft
  - tts_first_chunk
  - total_turn  ← alert if p95 > 450ms

Prometheus metrics also exported on :9090/metrics.
"""
import os
import logging
from functools import wraps
from time import perf_counter

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import Histogram, Counter, Gauge, start_http_server

logger = logging.getLogger(__name__)

OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "voice-ai-platform")


def setup_telemetry(service_name: str = SERVICE_NAME):
    """Initialize OTel tracing + Prometheus metrics. Call once at service startup."""

    # --- Tracing ---
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=OTEL_ENDPOINT),
            max_queue_size=2048,
            max_export_batch_size=512,
        )
    )
    trace.set_tracer_provider(tracer_provider)

    # --- Metrics ---
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=OTEL_ENDPOINT),
        export_interval_millis=10000,
    )
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # --- Prometheus sidecar (for Grafana dashboards) ---
    try:
        start_http_server(9090)
        logger.info("Prometheus metrics server started on :9090")
    except OSError:
        pass  # already started in this process

    logger.info("OpenTelemetry configured: service=%s endpoint=%s", service_name, OTEL_ENDPOINT)


# ─── Prometheus Metrics ────────────────────────────────────────────────────────

voice_turn_latency = Histogram(
    "voice_turn_latency_ms",
    "End-to-end agent turn latency in milliseconds",
    ["service", "intent", "lang"],
    buckets=[100, 200, 300, 400, 450, 500, 600, 800, 1000, 2000],
)

llm_ttft = Histogram(
    "llm_time_to_first_token_ms",
    "Time from LLM request to first token",
    ["model"],
    buckets=[50, 80, 120, 200, 300, 500, 1000],
)

tts_first_chunk_latency = Histogram(
    "tts_first_chunk_ms",
    "TTS latency to first audio chunk",
    ["provider", "lang"],
    buckets=[30, 50, 80, 120, 200, 500],
)

stt_final_latency = Histogram(
    "stt_final_transcript_ms",
    "Time from audio start to final STT transcript",
    ["lang"],
    buckets=[50, 100, 150, 200, 300, 500],
)

tool_execution_duration = Histogram(
    "tool_execution_duration_ms",
    "Duration of tool calls",
    ["tool_name", "outcome"],
    buckets=[10, 30, 50, 100, 200, 500, 1000],
)

session_abandonment = Counter(
    "session_abandonment_total",
    "Sessions abandoned before completion",
    ["stage"],
)

active_sessions = Gauge(
    "active_sessions_total",
    "Currently active voice sessions",
)

outbound_call_attempts = Counter(
    "outbound_call_attempts_total",
    "Outbound call attempts",
    ["outcome"],   # dialed | no_answer | busy | failed | sms_fallback
)


# ─── Latency Decorator ────────────────────────────────────────────────────────

def track_latency(metric: Histogram, labels: dict):
    """Decorator to time async functions and record to a Prometheus histogram."""
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            start = perf_counter()
            try:
                return await fn(*args, **kwargs)
            finally:
                elapsed_ms = (perf_counter() - start) * 1000
                metric.labels(**labels).observe(elapsed_ms)
        return wrapper
    return decorator


# ─── Alert Thresholds (for reference in Grafana alerting) ────────────────────
ALERT_THRESHOLDS = {
    "voice_turn_latency_p95_ms": 450,    # page on-call
    "voice_turn_latency_p99_ms": 600,    # auto-scale trigger
    "llm_ttft_p95_ms": 200,
    "stt_final_p95_ms": 200,
    "tts_first_chunk_p95_ms": 100,
    "error_rate_pct": 0.5,               # 99.5% success target
}

# Voice AI Platform — Medical Appointment System

A low-latency (<450ms), multilingual (EN/HI/TA) voice AI platform for hospital appointment booking.

## Architecture

```
WebRTC/WS → realtime-gateway → STT → Orchestrator → LLM → TTS → Audio
                                         ↕
                                  Memory / Scheduler
```

## Services

| Service | Runtime | Port |
|---|---|---|
| `realtime-gateway` | TypeScript/Node | 8080 |
| `stt-service` | Python/FastAPI | 50051 (gRPC) |
| `orchestrator` | Python/FastAPI | 50052 (gRPC) |
| `llm-service` | Python/vLLM | 50053 (gRPC) |
| `tts-service` | Python/FastAPI | 50054 (gRPC) |
| `memory-service` | Python/FastAPI | 50055 (gRPC) |
| `scheduler-service` | Python/FastAPI | 50056 (gRPC) |
| `outbound-worker` | Python/Celery | — |

## Quick Start

```bash
# Prerequisites: Docker, Docker Compose
cp .env.example .env
# Fill in API keys: DEEPGRAM_API_KEY, ELEVENLABS_API_KEY, AZURE_TTS_KEY, OPENAI_API_KEY

docker compose up --build
```

## 30-Day Execution Plan

- **Days 1–7**: Gateway + STT + LLM passthrough → validate <450ms
- **Days 8–14**: Booking engine + tool calls → validate conflict logic
- **Days 15–21**: Multilingual TTS + memory layer → validate Hindi/Tamil
- **Days 22–28**: Outbound calls + monitoring → end-to-end
- **Days 29–30**: Load test 100 concurrent calls, tune vLLM + TTS pool

## Latency Budget (per turn)

| Stage | Target |
|---|---|
| VAD detection | 0–20ms |
| STT interim first | 30ms |
| STT final | 100ms |
| Memory fetch (parallel) | 20ms |
| LLM TTFT (7B fast) | 80ms |
| TTS first chunk | 50ms |
| **Total p95** | **<450ms** |

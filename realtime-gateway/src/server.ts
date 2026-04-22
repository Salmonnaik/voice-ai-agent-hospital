import express from "express";
import { WebSocketServer, WebSocket } from "ws";
import { createServer } from "http";
import { v4 as uuidv4 } from "uuid";
import pino from "pino";
import { SileroVAD } from "./vad/silero";
import { AudioSplitter } from "./streams/audio-splitter";
import { BargeInDetector } from "./streams/barge-in";
import { LangFingerprint } from "./lang-detect/fingerprint";
import { GrpcClient } from "./grpc/client";

const logger = pino({ level: process.env.LOG_LEVEL || "info" });
const app = express();

// Add CORS middleware
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
  next();
});

const httpServer = createServer(app);
const wss = new WebSocketServer({ server: httpServer });

app.get("/health", (_req, res) => res.json({ status: "ok" }));

wss.on("connection", async (ws: WebSocket, req) => {
  const callId = uuidv4();
  const log = logger.child({ callId });
  log.info({ url: req.url }, "New WebSocket connection");

  const vad = new SileroVAD();
  const splitter = new AudioSplitter(callId);
  const bargeIn = new BargeInDetector();
  const langDetect = new LangFingerprint();
  const grpc = new GrpcClient();

  let sessionLang = "en";
  let isSpeaking = false;
  let ttsActive = false;

  // Initialize gRPC session
  const orchestratorStream = await grpc.openOrchestratorStream(callId);

  // Pipe orchestrator audio responses back to client
  orchestratorStream.on("data", (audioChunk: Buffer) => {
    ttsActive = true;
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(audioChunk);
    }
  });

  orchestratorStream.on("end", () => {
    ttsActive = false;
  });

  ws.on("message", async (data: Buffer) => {
    try {
      // Check for control messages (JSON)
      if (data[0] === 0x7b) {
        const msg = JSON.parse(data.toString());
        if (msg.type === "session.start") {
          sessionLang = msg.lang || "en";
          log.info({ sessionLang }, "Session started");
        }
        return;
      }

      // Raw audio bytes (PCM 16-bit, 16kHz, mono)
      const vadResult = await vad.process(data);

      // Barge-in detection while TTS is playing
      if (ttsActive && bargeIn.detect(data)) {
        log.info("Barge-in detected — interrupting TTS");
        orchestratorStream.write({ type: "BARGE_IN", callId });
        ttsActive = false;
      }

      if (vadResult.speechStart && !isSpeaking) {
        isSpeaking = true;
        log.debug("Speech start detected");

        // Language fingerprint on first utterance
        if (sessionLang === "en") {
          const detectedLang = await langDetect.detect(data);
          if (detectedLang.confidence > 0.8) {
            sessionLang = detectedLang.lang;
            log.info({ detectedLang }, "Language detected");
          }
        }
      }

      if (isSpeaking) {
        // Forward audio chunk to STT via gRPC
        const chunk = splitter.process(data);
        orchestratorStream.write({
          type: "AUDIO_CHUNK",
          callId,
          audio: chunk,
          lang: sessionLang,
        });
      }

      if (vadResult.speechEnd && isSpeaking) {
        isSpeaking = false;
        log.debug("Speech end detected — VAD fired");
        orchestratorStream.write({
          type: "UTTERANCE_END",
          callId,
          lang: sessionLang,
        });
      }
    } catch (err) {
      log.error({ err }, "Error processing audio chunk");
    }
  });

  ws.on("close", () => {
    log.info("WebSocket closed — cleaning up session");
    orchestratorStream.end();
    vad.destroy();
    grpc.closeSession(callId);
  });

  ws.on("error", (err) => {
    log.error({ err }, "WebSocket error");
  });
});

const PORT = process.env.PORT || 8080;
httpServer.listen(PORT, () => {
  logger.info({ port: PORT }, "Realtime gateway listening");
});

export default httpServer;

import * as ort from "onnxruntime-node";
import path from "path";

interface VADResult {
  speechStart: boolean;
  speechEnd: boolean;
  isSpeech: boolean;
  probability: number;
}

/**
 * Silero VAD — lightweight voice activity detection using ONNX Runtime.
 * Model: silero_vad.onnx (~1MB, runs in <5ms per 30ms chunk)
 *
 * Audio requirements: PCM 16-bit, 16kHz, mono
 * Chunk size: 512 samples (32ms) for 16kHz
 */
export class SileroVAD {
  private session: ort.InferenceSession | null = null;
  private h: ort.Tensor;
  private c: ort.Tensor;
  private sr: ort.Tensor;

  // State machine
  private wasActive = false;
  private silenceFrames = 0;
  private speechFrames = 0;

  // Thresholds
  private readonly SPEECH_THRESHOLD = 0.5;
  private readonly SILENCE_THRESHOLD = 0.35;
  private readonly MIN_SPEECH_FRAMES = 3;   // ~100ms before declaring speech start
  private readonly MIN_SILENCE_FRAMES = 8;  // ~250ms of silence before end-of-utterance

  constructor() {
    // Hidden state tensors (reset per session)
    this.h = new ort.Tensor("float32", new Float32Array(2 * 1 * 64), [2, 1, 64]);
    this.c = new ort.Tensor("float32", new Float32Array(2 * 1 * 64), [2, 1, 64]);
    this.sr = new ort.Tensor("int64", [16000n], [1]);
    this.loadModel();
  }

  private async loadModel() {
    const modelPath = path.join(__dirname, "../../models/silero_vad.onnx");
    this.session = await ort.InferenceSession.create(modelPath, {
      executionProviders: ["cpu"],
      graphOptimizationLevel: "all",
    });
  }

  async process(pcmBuffer: Buffer): Promise<VADResult> {
    if (!this.session) {
      return { speechStart: false, speechEnd: false, isSpeech: false, probability: 0 };
    }

    // Convert PCM16 buffer to float32 [-1, 1]
    const samples = new Float32Array(pcmBuffer.length / 2);
    for (let i = 0; i < samples.length; i++) {
      samples[i] = pcmBuffer.readInt16LE(i * 2) / 32768.0;
    }

    const input = new ort.Tensor("float32", samples, [1, samples.length]);

    const feeds = { input, h: this.h, c: this.c, sr: this.sr };
    const results = await this.session.run(feeds);

    const probability = (results["output"] as ort.Tensor).data[0] as number;
    this.h = results["hn"] as ort.Tensor;
    this.c = results["cn"] as ort.Tensor;

    const isSpeech = probability > this.SPEECH_THRESHOLD;
    const isSilence = probability < this.SILENCE_THRESHOLD;

    let speechStart = false;
    let speechEnd = false;

    if (isSpeech) {
      this.speechFrames++;
      this.silenceFrames = 0;
      if (!this.wasActive && this.speechFrames >= this.MIN_SPEECH_FRAMES) {
        this.wasActive = true;
        speechStart = true;
      }
    } else if (isSilence && this.wasActive) {
      this.silenceFrames++;
      this.speechFrames = 0;
      if (this.silenceFrames >= this.MIN_SILENCE_FRAMES) {
        this.wasActive = false;
        this.silenceFrames = 0;
        speechEnd = true;
      }
    }

    return { speechStart, speechEnd, isSpeech: this.wasActive, probability };
  }

  destroy() {
    // Release ONNX session resources
    this.session = null;
  }
}

/**
 * BargeInDetector — detects when a user starts speaking while TTS is playing.
 *
 * Uses energy-based detection as a fast pre-filter before Silero VAD.
 * We require >200ms of sustained energy above threshold to fire,
 * preventing interrupts from background noise.
 *
 * Frame size: 320 samples = 20ms @ 16kHz
 */
export class BargeInDetector {
  private energyHistory: number[] = [];
  private readonly windowFrames = 10; // 200ms window
  private readonly energyThreshold = 0.02; // RMS threshold (tunable)
  private readonly requiredActiveFrames = 7; // 70% of window must be active

  detect(pcmBuffer: Buffer): boolean {
    const rms = this.computeRMS(pcmBuffer);
    this.energyHistory.push(rms);

    if (this.energyHistory.length > this.windowFrames) {
      this.energyHistory.shift();
    }

    if (this.energyHistory.length < this.windowFrames) {
      return false; // not enough history
    }

    const activeFrames = this.energyHistory.filter(
      (e) => e > this.energyThreshold
    ).length;

    return activeFrames >= this.requiredActiveFrames;
  }

  reset() {
    this.energyHistory = [];
  }

  private computeRMS(buffer: Buffer): number {
    let sumSquares = 0;
    const samples = buffer.length / 2;
    for (let i = 0; i < buffer.length; i += 2) {
      const sample = buffer.readInt16LE(i) / 32768.0;
      sumSquares += sample * sample;
    }
    return Math.sqrt(sumSquares / samples);
  }
}

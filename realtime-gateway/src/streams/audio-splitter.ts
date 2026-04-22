/**
 * AudioSplitter — accumulates raw PCM audio into fixed-size chunks
 * for efficient gRPC streaming to the STT service.
 *
 * Chunk size: 4096 bytes = 2048 samples @ 16kHz = 128ms of audio
 * This balances latency vs gRPC overhead.
 */
export class AudioSplitter {
  private buffer: Buffer[] = [];
  private bufferedBytes = 0;
  private readonly chunkSize: number;
  private readonly callId: string;

  constructor(callId: string, chunkSizeBytes = 4096) {
    this.callId = callId;
    this.chunkSize = chunkSizeBytes;
  }

  process(incoming: Buffer): Buffer {
    this.buffer.push(incoming);
    this.bufferedBytes += incoming.length;

    if (this.bufferedBytes >= this.chunkSize) {
      const chunk = Buffer.concat(this.buffer);
      this.buffer = [];
      this.bufferedBytes = 0;
      return chunk;
    }

    return Buffer.alloc(0); // still accumulating
  }

  flush(): Buffer {
    if (this.buffer.length === 0) return Buffer.alloc(0);
    const chunk = Buffer.concat(this.buffer);
    this.buffer = [];
    this.bufferedBytes = 0;
    return chunk;
  }
}

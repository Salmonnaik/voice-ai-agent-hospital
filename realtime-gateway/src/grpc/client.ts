import * as grpc from "@grpc/grpc-js";
import * as protoLoader from "@grpc/proto-loader";
import path from "path";
import { EventEmitter } from "events";

const ORCHESTRATOR_HOST =
  process.env.ORCHESTRATOR_GRPC_HOST || "localhost:50052";

const packageDef = protoLoader.loadSync(
  path.join(__dirname, "../../proto/voice.proto"),
  { keepCase: true, longs: String, enums: String, defaults: true }
);

/**
 * GrpcClient — manages gRPC streaming connections to the orchestrator.
 *
 * One persistent bidirectional stream per active call.
 * Connection pooling: connections are reused across turns within a session.
 */
export class GrpcClient {
  private streams: Map<string, grpc.ClientDuplexStream<any, any>> = new Map();
  private client: any;

  constructor() {
    const proto = grpc.loadPackageDefinition(packageDef) as any;
    this.client = new proto.voice.VoiceOrchestrator(
      ORCHESTRATOR_HOST,
      grpc.credentials.createInsecure(),
      {
        "grpc.keepalive_time_ms": 30000,
        "grpc.keepalive_timeout_ms": 5000,
        "grpc.keepalive_permit_without_calls": 1,
        "grpc.max_receive_message_length": 1024 * 1024 * 4, // 4MB
      }
    );
  }

  async openOrchestratorStream(callId: string): Promise<grpc.ClientDuplexStream<any, any>> {
    const stream = this.client.ProcessCall();
    this.streams.set(callId, stream);

    // Send session init
    stream.write({
      type: "SESSION_INIT",
      call_id: callId,
      timestamp_ms: Date.now(),
    });

    return stream;
  }

  closeSession(callId: string) {
    const stream = this.streams.get(callId);
    if (stream) {
      stream.end();
      this.streams.delete(callId);
    }
  }
}

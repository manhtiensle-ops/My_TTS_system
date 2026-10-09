import argparse
import asyncio
import json
import os
import signal
import sys
import struct
from typing import Optional


class IsolatedWorkerServer:
    """
    Inference Worker Process (Chạy ở PID độc lập).
    Chỉ nạp PyTorch & VieNeu khi tiến trình con này được Supervisor khởi chạy.
    """

    def __init__(self, socket_path: str, model_name: str = "v3turbo", voices: Optional[list[str]] = None):
        self.socket_path = socket_path
        self.model_name = model_name
        self.voices = voices or ["ngoc_huyen", "truc_ly"]
        self.tts = None
        self.engine = None
        self.is_ready = False

    def initialize_gpu(self):
        """Nạp model và warm-up CUDA Graph."""
        print(f"[Worker PID {os.getpid()}] Khởi tạo PyTorch & VieNeu-TTS ({self.model_name})...", flush=True)
        from src.engines.vieneu import VieNeuEngine

        self.engine = VieNeuEngine()
        self.engine.load_model()

        # Warm-up bổ sung cho các voices
        for v in self.voices:
            resolved = self.engine.resolve_voice(v)
            if resolved and self.engine.tts:
                try:
                    _ = self.engine.tts.infer("Warmup voice.", voice=resolved)
                except Exception as e:
                    print(f"[Worker] Warmup voice {v} notice: {e}", flush=True)

        self.is_ready = True
        print(f"[Worker PID {os.getpid()}] GPU initialization complete.", flush=True)

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Xử lý IPC request từ Supervisor."""
        try:
            length_bytes = await reader.readexactly(4)
            payload_length = struct.unpack("!I", length_bytes)[0]
            payload_data = await reader.readexactly(payload_length)
            request = json.loads(payload_data.decode("utf-8"))

            action = request.get("action")
            if action == "ping":
                response = {"status": "ok", "ready": self.is_ready, "pid": os.getpid()}
                resp_bytes = json.dumps(response).encode("utf-8")
                writer.write(struct.pack("!I", len(resp_bytes)) + resp_bytes)
                await writer.drain()

            elif action == "synthesize":
                if self.engine is None:
                    raise RuntimeError("Engine is not initialized")
                text = request.get("text", "")
                voice = request.get("voice", "Ngọc Huyền")
                speed = float(request.get("speed", 1.0))
                fmt = request.get("response_format", "wav")

                resolved_voice = self.engine.resolve_voice(voice) or voice
                audio_bytes = self.engine.synthesize(
                    text=text,
                    voice_name=resolved_voice,
                    speed=speed,
                    response_format=fmt,
                )

                response_hdr = json.dumps({"status": "ok", "size": len(audio_bytes)}).encode("utf-8")
                writer.write(struct.pack("!I", len(response_hdr)) + response_hdr)
                writer.write(audio_bytes)
                await writer.drain()

            elif action == "status":
                if self.engine is None:
                    raise RuntimeError("Engine is not initialized")
                loaded, device_name, vram_mb = self.engine.get_status()
                response = {
                    "status": "ok",
                    "loaded": loaded,
                    "device": device_name,
                    "vram_allocated_mb": vram_mb,
                    "pid": os.getpid(),
                }
                resp_bytes = json.dumps(response).encode("utf-8")
                writer.write(struct.pack("!I", len(resp_bytes)) + resp_bytes)
                await writer.drain()

            else:
                resp_bytes = json.dumps({"status": "error", "message": f"Unknown action: {action}"}).encode("utf-8")
                writer.write(struct.pack("!I", len(resp_bytes)) + resp_bytes)
                await writer.drain()

        except Exception as e:
            err_bytes = json.dumps({"status": "error", "message": str(e)}).encode("utf-8")
            writer.write(struct.pack("!I", len(err_bytes)) + err_bytes)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def run(self):
        self.initialize_gpu()

        # Dọn dẹp socket cũ nếu có
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        server = await asyncio.start_unix_server(self.handle_client, path=self.socket_path)
        print(f"WORKER_READY_SOCKET:{self.socket_path}", flush=True)

        try:
            await server.serve_forever()
        except asyncio.CancelledError:
            pass
        finally:
            server.close()
            await server.wait_closed()
            if os.path.exists(self.socket_path):
                try:
                    os.remove(self.socket_path)
                except OSError:
                    pass


def main():
    parser = argparse.ArgumentParser(description="Isolated TTS Worker Process")
    parser.add_argument("--socket", required=True, help="Path to Unix domain socket")
    parser.add_argument("--model", default="v3turbo", help="Model name")
    parser.add_argument("--voices", default="ngoc_huyen,truc_ly", help="Comma-separated voices to preload")
    args = parser.parse_args()

    voice_list = [v.strip() for v in args.voices.split(",") if v.strip()]
    worker = IsolatedWorkerServer(socket_path=args.socket, model_name=args.model, voices=voice_list)

    def handle_sigterm(signum, frame):
        print(f"[Worker PID {os.getpid()}] Shutting down gracefully via SIGTERM...", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)
    asyncio.run(worker.run())


if __name__ == "__main__":
    main()

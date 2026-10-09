import asyncio
import json
import os
import signal
import struct
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

from src.lifecycle.states import LifecycleState, LifecycleStateMachine, StateTransitionError
from src.lifecycle.watchdog import IdleWatchdog


class WorkerSupervisor:
    """
    Supervisor điều khiển tiến trình Worker độc lập.
    Không import hay giữ liên kết CUDA/torch trực tiếp trong tiến trình Mẹ.
    """

    def __init__(self, socket_path: str = "/tmp/vieneu_worker.sock", default_timeout: int = 600):
        self.socket_path = socket_path
        self.default_timeout = default_timeout
        self.fsm = LifecycleStateMachine(LifecycleState.SLEEP)
        self.worker_process: Optional[subprocess.Popen] = None
        self.lock = asyncio.Lock()
        self.watchdog = IdleWatchdog(
            timeout_seconds=default_timeout,
            on_timeout_callback=self._auto_evict_callback,
        )
        self.last_activity_time: float = time.time()
        self.loaded_voices: List[str] = []
        self.model_name: str = "v3turbo"

    @property
    def current_state(self) -> LifecycleState:
        return self.fsm.current_state

    async def _auto_evict_callback(self):
        """Callback tự động gọi khi IdleWatchdog hết thời gian chờ."""
        print("[Supervisor Watchdog] Idle timeout reached. Auto evicting GPU VRAM...", flush=True)
        try:
            await self.unload_model(force=False)
        except Exception as e:
            print(f"[Supervisor Watchdog] Auto evict error: {e}", flush=True)

    async def load_model(
        self,
        model_name: str = "v3turbo",
        voice_preload: Optional[List[str]] = None,
        idle_timeout_seconds: Optional[int] = None,
    ) -> Dict:
        """Nạp model lên VRAM qua Worker Subprocess."""
        async with self.lock:
            if self.current_state == LifecycleState.READY:
                # Cập nhật watchdog và trả về OK
                timeout = idle_timeout_seconds or self.default_timeout
                self.watchdog.reset(timeout)
                return {
                    "status": "ok",
                    "message": "Model is already loaded and READY.",
                    "state": self.current_state.value,
                    "worker_pid": self.worker_process.pid if self.worker_process else None,
                }

            if self.current_state != LifecycleState.SLEEP and self.current_state != LifecycleState.ERROR:
                raise StateTransitionError(f"Cannot load model while in state {self.current_state.value}")

            self.fsm.transition_to(LifecycleState.STARTING)
            self.model_name = model_name
            self.loaded_voices = voice_preload or ["ngoc_huyen", "truc_ly"]

            # Xóa socket cũ nếu có
            if os.path.exists(self.socket_path):
                try:
                    os.remove(self.socket_path)
                except OSError:
                    pass

            cmd = [
                sys.executable,
                "-m",
                "src.lifecycle.worker_process",
                "--socket",
                self.socket_path,
                "--model",
                model_name,
                "--voices",
                ",".join(self.loaded_voices),
            ]

            try:
                # Process group riêng để kill sạch khi SIGTERM
                kwargs = {}
                if os.name != "nt":
                    kwargs["preexec_fn"] = os.setsid

                self.worker_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    **kwargs
                )
            except Exception as e:
                self.fsm.transition_to(LifecycleState.ERROR)
                raise RuntimeError(f"Failed to spawn worker process: {e}")

            # Chờ worker tạo socket và hoàn tất nạp GPU (handshake)
            is_ready = await self._wait_for_worker_socket(timeout=60.0)
            if not is_ready:
                await self._force_kill_process()
                self.fsm.transition_to(LifecycleState.ERROR)
                raise RuntimeError("Worker process failed to become ready within timeout.")

            self.fsm.transition_to(LifecycleState.READY)
            timeout = idle_timeout_seconds or self.default_timeout
            self.watchdog.reset(timeout)
            self.last_activity_time = time.time()

            return {
                "status": "ok",
                "state": self.current_state.value,
                "worker_pid": self.worker_process.pid if self.worker_process else None,
                "idle_timeout_seconds": timeout,
            }

    async def unload_model(self, force: bool = False) -> Dict:
        """Giải phóng 100% VRAM: Gửi tín hiệu dừng hoặc kill Worker process."""
        async with self.lock:
            if self.current_state == LifecycleState.SLEEP:
                return {
                    "status": "already_sleeping",
                    "state": LifecycleState.SLEEP.value,
                    "vram_allocated_mb": 0.0,
                }

            if self.fsm.can_transition(LifecycleState.STOPPING):
                self.fsm.transition_to(LifecycleState.STOPPING)
            else:
                self._force_set_state(LifecycleState.STOPPING)

            self.watchdog.stop()

            if self.worker_process:
                try:
                    if force:
                        await self._force_kill_process()
                    else:
                        if os.name != "nt":
                            os.killpg(os.getpgid(self.worker_process.pid), signal.SIGTERM)
                        else:
                            self.worker_process.terminate()

                        try:
                            await asyncio.to_thread(self.worker_process.wait, timeout=3.0)
                        except (subprocess.TimeoutExpired, Exception):
                            await self._force_kill_process()
                except ProcessLookupError:
                    pass
                finally:
                    self.worker_process = None

            if os.path.exists(self.socket_path):
                try:
                    os.remove(self.socket_path)
                except OSError:
                    pass

            self.fsm.transition_to(LifecycleState.SLEEP)
            return {
                "status": "released",
                "state": LifecycleState.SLEEP.value,
                "vram_allocated_mb": 0.0,
            }

    async def synthesize(
        self,
        text: str,
        voice: str = "Ngọc Huyền",
        speed: float = 1.0,
        response_format: str = "wav",
    ) -> bytes:
        """Chuyển tiếp yêu cầu TTS sang Worker process qua Unix Socket."""
        if self.current_state not in (LifecycleState.READY, LifecycleState.PROCESSING):
            raise StateTransitionError(
                f"GPU is in {self.current_state.value} state. Please call /v1/lifecycle/load first."
            )

        self.fsm.transition_to(LifecycleState.PROCESSING)
        self.watchdog.pause()

        try:
            payload = {
                "action": "synthesize",
                "text": text,
                "voice": voice,
                "speed": speed,
                "response_format": response_format,
            }
            audio_bytes = await self._send_ipc_request(payload)
            self.last_activity_time = time.time()
            return audio_bytes
        finally:
            self.fsm.transition_to(LifecycleState.READY)
            self.watchdog.reset()

    async def get_status(self) -> Dict:
        """Truy vấn trạng thái của Worker và VRAM."""
        if self.current_state == LifecycleState.SLEEP or not self.worker_process:
            return {
                "state": self.current_state.value,
                "vram_allocated_mb": 0.0,
                "vram_total_mb": 8192.0,
                "worker_pid": None,
                "idle_seconds_remaining": 0.0,
                "model_name": self.model_name,
                "loaded_voices": self.loaded_voices,
            }

        try:
            status_data = await self._send_ipc_json({"action": "status"})
            vram_mb = status_data.get("vram_allocated_mb", 0.0)
            device = status_data.get("device", "cuda")
        except Exception:
            vram_mb = 0.0
            device = "unknown"

        return {
            "state": self.current_state.value,
            "vram_allocated_mb": vram_mb,
            "device": device,
            "worker_pid": self.worker_process.pid if self.worker_process else None,
            "idle_seconds_remaining": self.watchdog.remaining_seconds(),
            "model_name": self.model_name,
            "loaded_voices": self.loaded_voices,
        }

    async def heartbeat(self, idle_timeout_seconds: Optional[int] = None) -> Dict:
        """Gia hạn session và reset IdleWatchdog."""
        if self.current_state in (LifecycleState.READY, LifecycleState.PROCESSING):
            timeout = idle_timeout_seconds or self.watchdog.timeout_seconds
            self.watchdog.reset(timeout)
            return {
                "status": "ok",
                "state": self.current_state.value,
                "idle_seconds_remaining": self.watchdog.remaining_seconds(),
            }
        return {
            "status": "ignored",
            "message": f"Heartbeat ignored in state {self.current_state.value}",
            "state": self.current_state.value,
        }

    async def _wait_for_worker_socket(self, timeout: float = 60.0) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.worker_process and self.worker_process.poll() is not None:
                return False

            if os.path.exists(self.socket_path):
                try:
                    res = await self._send_ipc_json({"action": "ping"})
                    if res.get("status") == "ok":
                        return True
                except Exception:
                    pass
            await asyncio.sleep(0.5)
        return False

    async def _send_ipc_json(self, payload: Dict) -> Dict:
        reader, writer = await asyncio.open_unix_connection(self.socket_path)
        try:
            data = json.dumps(payload).encode("utf-8")
            writer.write(struct.pack("!I", len(data)) + data)
            await writer.drain()

            hdr = await reader.readexactly(4)
            resp_len = struct.unpack("!I", hdr)[0]
            resp_data = await reader.readexactly(resp_len)
            return json.loads(resp_data.decode("utf-8"))
        finally:
            writer.close()
            await writer.wait_closed()

    async def _send_ipc_request(self, payload: Dict) -> bytes:
        reader, writer = await asyncio.open_unix_connection(self.socket_path)
        try:
            data = json.dumps(payload).encode("utf-8")
            writer.write(struct.pack("!I", len(data)) + data)
            await writer.drain()

            hdr = await reader.readexactly(4)
            resp_len = struct.unpack("!I", hdr)[0]
            resp_bytes = await reader.readexactly(resp_len)

            resp_info = json.loads(resp_bytes.decode("utf-8"))
            if resp_info.get("status") != "ok":
                raise RuntimeError(resp_info.get("message", "Worker IPC Error"))

            audio_size = resp_info.get("size", 0)
            audio_bytes = await reader.readexactly(audio_size)
            return audio_bytes
        finally:
            writer.close()
            await writer.wait_closed()

    async def _force_kill_process(self):
        if self.worker_process:
            try:
                if os.name != "nt":
                    os.killpg(os.getpgid(self.worker_process.pid), signal.SIGKILL)
                else:
                    self.worker_process.kill()
                await asyncio.to_thread(self.worker_process.wait)
            except Exception:
                pass
            self.worker_process = None

    def _force_set_state(self, state: LifecycleState):
        self.fsm._state = state


# Singleton Supervisor Instance
_supervisor_instance: Optional[WorkerSupervisor] = None


def get_supervisor() -> WorkerSupervisor:
    global _supervisor_instance
    if _supervisor_instance is None:
        _supervisor_instance = WorkerSupervisor()
    return _supervisor_instance

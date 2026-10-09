import asyncio
import time
from typing import Callable, Optional


class IdleWatchdog:
    """
    Theo dõi thời gian không hoạt động của Worker.
    Kích hoạt callback thu hồi VRAM tự động khi chạm ngưỡng timeout.
    """

    def __init__(self, timeout_seconds: float, on_timeout_callback: Callable):
        self.timeout_seconds = timeout_seconds
        self.callback = on_timeout_callback
        self.task: Optional[asyncio.Task] = None
        self.last_reset = time.time()
        self.is_running = False

    def reset(self, new_timeout: Optional[int] = None):
        """Đặt lại đồng hồ đếm ngược mỗi khi hoàn thành request hoặc nhận heartbeat."""
        if new_timeout is not None:
            self.timeout_seconds = new_timeout
        self.last_reset = time.time()
        if not self.is_running and self.callback is not None:
            self.is_running = True
            try:
                loop = asyncio.get_running_loop()
                self.task = loop.create_task(self._monitor_loop())
            except RuntimeError:
                pass

    def pause(self):
        """Tạm dừng đếm ngược khi GPU đang bận tính toán."""
        self.is_running = False
        if self.task and not self.task.done():
            self.task.cancel()
            self.task = None

    def stop(self):
        """Dừng hoàn toàn bộ đếm khi model đã unload."""
        self.is_running = False
        if self.task and not self.task.done():
            self.task.cancel()
            self.task = None

    def remaining_seconds(self) -> float:
        """Tính số giây còn lại trước khi tự động unload."""
        if not self.is_running:
            return 0.0
        elapsed = time.time() - self.last_reset
        return max(0.0, float(self.timeout_seconds - elapsed))

    async def _monitor_loop(self):
        while self.is_running:
            elapsed = time.time() - self.last_reset
            if elapsed >= self.timeout_seconds:
                self.is_running = False
                if self.callback:
                    if asyncio.iscoroutinefunction(self.callback):
                        await self.callback()
                    else:
                        self.callback()
                break
            sleep_interval = min(1.0, max(0.05, self.timeout_seconds / 4))
            await asyncio.sleep(sleep_interval)

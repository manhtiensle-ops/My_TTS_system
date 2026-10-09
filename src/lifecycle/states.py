from enum import Enum
from typing import Dict, Set


class LifecycleState(str, Enum):
    SLEEP = "SLEEP"            # 0 MB VRAM, Worker chưa nạp
    STARTING = "STARTING"      # Đang khởi chạy Worker và nạp weights
    READY = "READY"            # Model đã sẵn sàng trong VRAM, chờ nhận task
    PROCESSING = "PROCESSING"  # Đang bận tính toán TTS
    STOPPING = "STOPPING"      # Đang dọn dẹp và giải phóng tài nguyên
    ERROR = "ERROR"            # Xảy ra lỗi OOM hoặc Worker crash


class StateTransitionError(Exception):
    """Ngoại lệ khi chuyển đổi trạng thái FSM không hợp lệ."""
    pass


class LifecycleStateMachine:
    """Quản lý trạng thái FSM tuân thủ quy tắc ma trận chuyển đổi."""

    VALID_TRANSITIONS: Dict[LifecycleState, Set[LifecycleState]] = {
        LifecycleState.SLEEP: {LifecycleState.STARTING},
        LifecycleState.STARTING: {LifecycleState.READY, LifecycleState.ERROR, LifecycleState.STOPPING},
        LifecycleState.READY: {LifecycleState.PROCESSING, LifecycleState.STOPPING, LifecycleState.ERROR},
        LifecycleState.PROCESSING: {LifecycleState.READY, LifecycleState.STOPPING, LifecycleState.ERROR},
        LifecycleState.STOPPING: {LifecycleState.SLEEP, LifecycleState.ERROR},
        LifecycleState.ERROR: {LifecycleState.STOPPING, LifecycleState.SLEEP},
    }

    def __init__(self, initial_state: LifecycleState = LifecycleState.SLEEP):
        self._state = initial_state

    @property
    def current_state(self) -> LifecycleState:
        return self._state

    def can_transition(self, target_state: LifecycleState) -> bool:
        allowed = self.VALID_TRANSITIONS.get(self._state, set())
        return target_state in allowed

    def transition_to(self, target_state: LifecycleState) -> LifecycleState:
        if not self.can_transition(target_state):
            raise StateTransitionError(
                f"Invalid FSM transition: {self._state.value} -> {target_state.value}"
            )
        self._state = target_state
        return self._state

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app import TTSApplication
from src.lifecycle.states import LifecycleState, StateTransitionError, LifecycleStateMachine
from src.lifecycle.watchdog import IdleWatchdog
from src.lifecycle.supervisor import WorkerSupervisor, get_supervisor
from vieneu_sdk.client import VieneuClient
from vieneu_sdk.lifecycle_session import GPUSession


def test_fsm_transitions():
    """Kiểm tra ma trận chuyển đổi hợp lệ và bất hợp lệ trong State Machine."""
    fsm = LifecycleStateMachine()
    assert fsm.current_state == LifecycleState.SLEEP

    # Hợp lệ: SLEEP -> STARTING -> READY -> PROCESSING -> READY -> STOPPING -> SLEEP
    fsm.transition_to(LifecycleState.STARTING)
    assert fsm.current_state == LifecycleState.STARTING

    fsm.transition_to(LifecycleState.READY)
    assert fsm.current_state == LifecycleState.READY

    fsm.transition_to(LifecycleState.PROCESSING)
    assert fsm.current_state == LifecycleState.PROCESSING

    fsm.transition_to(LifecycleState.READY)
    assert fsm.current_state == LifecycleState.READY

    fsm.transition_to(LifecycleState.STOPPING)
    assert fsm.current_state == LifecycleState.STOPPING

    fsm.transition_to(LifecycleState.SLEEP)
    assert fsm.current_state == LifecycleState.SLEEP

    # Bất hợp lệ: SLEEP -> PROCESSING (bị chặn và ném ngoại lệ)
    with pytest.raises(StateTransitionError):
        fsm.transition_to(LifecycleState.PROCESSING)


@pytest.mark.asyncio
async def test_watchdog_trigger():
    """Kiểm tra callback tự động xả VRAM của Watchdog khi hết hạn timeout."""
    callback_mock = AsyncMock()
    watchdog = IdleWatchdog(timeout_seconds=0.1, on_timeout_callback=callback_mock)

    watchdog.reset()
    await asyncio.sleep(0.3)

    callback_mock.assert_called_once()
    watchdog.stop()


@pytest.mark.asyncio
async def test_supervisor_mock_load_unload():
    """Kiểm tra Supervisor trong môi trường mock Subprocess."""
    supervisor = WorkerSupervisor(default_timeout=600)

    # Patch worker initialization to avoid real PyTorch GPU requirement in unit test environment
    with patch.object(supervisor, "_wait_for_worker_socket", return_value=True), \
         patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_popen.return_value = mock_proc

        res = await supervisor.load_model(model_name="v3turbo", voice_preload=["ngoc_huyen"])
        assert res["status"] == "ok"
        assert supervisor.current_state == LifecycleState.READY

        status_info = await supervisor.get_status()
        assert status_info["state"] == "READY"
        assert status_info["worker_pid"] == 9999

        unload_res = await supervisor.unload_model(force=True)
        assert unload_res["status"] == "released"
        assert supervisor.current_state == LifecycleState.SLEEP


def test_lifecycle_api_endpoints():
    """Kiểm tra các endpoint HTTP /v1/lifecycle qua TestClient."""
    app_instance = TTSApplication()
    client = TestClient(app_instance.app)

    supervisor = get_supervisor()
    # Reset supervisor state to SLEEP for isolated test
    asyncio.run(supervisor.unload_model(force=True))

    # 1. GET /v1/lifecycle/status
    res = client.get("/v1/lifecycle/status")
    assert res.status_code == 200
    data = res.json()
    assert data["state"] == "SLEEP"

    # 2. POST /v1/lifecycle/load
    with patch.object(supervisor, "_wait_for_worker_socket", return_value=True), \
         patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 8888
        mock_popen.return_value = mock_proc

        load_res = client.post("/v1/lifecycle/load", json={"model_name": "v3turbo", "idle_timeout_seconds": 300})
        assert load_res.status_code == 200

        status_after_load = client.get("/v1/lifecycle/status").json()
        assert status_after_load["state"] == "READY"

        # 3. POST /v1/lifecycle/heartbeat
        hb_res = client.post("/v1/lifecycle/heartbeat", json={"idle_timeout_seconds": 600})
        assert hb_res.status_code == 200

        # 4. POST /v1/lifecycle/unload
        unload_res = client.post("/v1/lifecycle/unload", json={"force": True})
        assert unload_res.status_code == 200
        assert client.get("/v1/lifecycle/status").json()["state"] == "SLEEP"


def test_sdk_gpu_session():
    """Kiểm tra SDK GPUSession Context Manager."""
    mock_client = MagicMock(spec=VieneuClient)
    session = GPUSession(client=mock_client, model_name="v3turbo", auto_unload=True)

    with session:
        mock_client.load_gpu.assert_called_once_with(
            model_name="v3turbo",
            voice_preload=["ngoc_huyen", "truc_ly"],
            idle_timeout_seconds=600,
        )

    mock_client.unload_gpu.assert_called_once_with(force=False)

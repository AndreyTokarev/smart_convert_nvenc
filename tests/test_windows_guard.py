from __future__ import annotations

from unittest.mock import MagicMock, patch

from smart_convert_nvenc.windows_guard import WindowsSessionGuard


def test_supported_property() -> None:
    guard = WindowsSessionGuard()
    with patch("smart_convert_nvenc.windows_guard.sys.platform", "linux"):
        assert guard.supported is False
    with patch("smart_convert_nvenc.windows_guard.sys.platform", "win32"):
        assert guard.supported is True


def test_start_stop_noop_when_unsupported() -> None:
    guard = WindowsSessionGuard()
    with patch("smart_convert_nvenc.windows_guard.sys.platform", "linux"):
        guard.start(hwnd=1)
        assert guard._active is False
        guard.stop()


def test_start_stop_windows_with_mocks() -> None:
    guard = WindowsSessionGuard(reason="test")
    kernel = MagicMock()
    user = MagicMock()
    wintypes = MagicMock()
    wintypes.HWND = lambda x: x
    with (
        patch("smart_convert_nvenc.windows_guard.sys.platform", "win32"),
        patch(
            "smart_convert_nvenc.windows_guard._ensure_windows_apis",
            return_value=(kernel, user, wintypes),
        ),
        patch("smart_convert_nvenc.windows_guard.threading.Thread") as thread_cls,
    ):
        thread = MagicMock()
        thread_cls.return_value = thread
        thread.is_alive.return_value = False
        guard.start(hwnd=123)
        assert guard._active is True
        kernel.SetThreadExecutionState.assert_called()
        user.ShutdownBlockReasonCreate.assert_called()
        guard.stop()
        assert guard._active is False
        user.ShutdownBlockReasonDestroy.assert_called()


def test_context_manager() -> None:
    guard = WindowsSessionGuard()
    with (
        patch.object(guard, "start") as start,
        patch.object(guard, "stop") as stop,
    ):
        with guard:
            start.assert_called_once()
        stop.assert_called_once()


def test_abort_loop_runs_shutdown_a() -> None:
    guard = WindowsSessionGuard()
    guard._stop.set()
    with patch("smart_convert_nvenc.windows_guard.subprocess.run") as run:
        guard._abort_pending_shutdown_loop()
        run.assert_not_called()

    guard2 = WindowsSessionGuard()
    calls = {"n": 0}

    def _wait(timeout: float) -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    guard2._stop.wait = _wait  # type: ignore[method-assign]
    with patch("smart_convert_nvenc.windows_guard.subprocess.run") as run:
        guard2._abort_pending_shutdown_loop()
        run.assert_called_once()
        assert run.call_args.args[0] == ["shutdown", "/a"]


def test_abort_loop_oserror_ignored() -> None:
    guard = WindowsSessionGuard()
    calls = {"n": 0}

    def _wait(timeout: float) -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    guard._stop.wait = _wait  # type: ignore[method-assign]
    with patch(
        "smart_convert_nvenc.windows_guard.subprocess.run",
        side_effect=OSError("no shutdown"),
    ):
        guard._abort_pending_shutdown_loop()

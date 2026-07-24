from __future__ import annotations

import subprocess
import sys
import threading
from typing import Any


ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

_kernel32: Any | None = None
_user32: Any | None = None
_wintypes: Any | None = None


def _ensure_windows_apis() -> tuple[Any, Any, Any]:
    global _kernel32, _user32, _wintypes
    if sys.platform != "win32":
        raise RuntimeError("Windows APIs are only available on win32")
    if _kernel32 is None or _user32 is None or _wintypes is None:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
        kernel32.SetThreadExecutionState.restype = wintypes.DWORD
        user32.ShutdownBlockReasonCreate.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        user32.ShutdownBlockReasonCreate.restype = wintypes.BOOL
        user32.ShutdownBlockReasonDestroy.argtypes = [wintypes.HWND]
        user32.ShutdownBlockReasonDestroy.restype = wintypes.BOOL
        _kernel32 = kernel32
        _user32 = user32
        _wintypes = wintypes
    return _kernel32, _user32, _wintypes


class WindowsSessionGuard:
    """Keep the PC awake and discourage reboot/shutdown while a job runs.

    No-op on non-Windows platforms (safe to import anywhere).
    """

    def __init__(self, reason: str = "Smart Convert NVENC is encoding courses") -> None:
        self.reason = reason
        self._hwnd: int | None = None
        self._active = False
        self._abort_thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def supported(self) -> bool:
        return sys.platform == "win32"

    def start(self, hwnd: int | None = None) -> None:
        if not self.supported or self._active:
            return
        kernel32, user32, wintypes = _ensure_windows_apis()
        self._hwnd = hwnd
        kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
        )
        if hwnd:
            user32.ShutdownBlockReasonCreate(wintypes.HWND(hwnd), self.reason)
        self._stop.clear()
        self._abort_thread = threading.Thread(
            target=self._abort_pending_shutdown_loop,
            name="wu-reboot-guard",
            daemon=True,
        )
        self._abort_thread.start()
        self._active = True

    def stop(self) -> None:
        if not self.supported or not self._active:
            return
        kernel32, user32, wintypes = _ensure_windows_apis()
        self._stop.set()
        if self._abort_thread and self._abort_thread.is_alive():
            self._abort_thread.join(timeout=2.0)
        self._abort_thread = None
        if self._hwnd:
            user32.ShutdownBlockReasonDestroy(wintypes.HWND(self._hwnd))
            self._hwnd = None
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        self._active = False

    def _abort_pending_shutdown_loop(self) -> None:
        while not self._stop.wait(45.0):
            try:
                subprocess.run(
                    ["shutdown", "/a"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except OSError:
                pass

    def __enter__(self) -> WindowsSessionGuard:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()

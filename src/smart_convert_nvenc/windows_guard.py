from __future__ import annotations

import ctypes
import subprocess
import sys
import threading
from ctypes import wintypes


ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_user32 = ctypes.WinDLL("user32", use_last_error=True)

_kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
_kernel32.SetThreadExecutionState.restype = wintypes.DWORD

_user32.ShutdownBlockReasonCreate.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
_user32.ShutdownBlockReasonCreate.restype = wintypes.BOOL
_user32.ShutdownBlockReasonDestroy.argtypes = [wintypes.HWND]
_user32.ShutdownBlockReasonDestroy.restype = wintypes.BOOL


class WindowsSessionGuard:
    """Keep the PC awake and discourage reboot/shutdown while a job runs."""

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
        self._hwnd = hwnd
        # Prevent sleep / idle suspend while encoding.
        _kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
        )
        if hwnd:
            _user32.ShutdownBlockReasonCreate(wintypes.HWND(hwnd), self.reason)
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
        self._stop.set()
        if self._abort_thread and self._abort_thread.is_alive():
            self._abort_thread.join(timeout=2.0)
        self._abort_thread = None
        if self._hwnd:
            _user32.ShutdownBlockReasonDestroy(wintypes.HWND(self._hwnd))
            self._hwnd = None
        _kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        self._active = False

    def _abort_pending_shutdown_loop(self) -> None:
        # Windows Update often schedules `shutdown /r` with a timer.
        # Aborting clears that countdown while our job is running.
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

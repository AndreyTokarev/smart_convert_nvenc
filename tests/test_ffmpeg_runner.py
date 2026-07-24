from __future__ import annotations

import subprocess
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from smart_convert_nvenc.ffmpeg_runner import (
    FFmpegCancelled,
    FFmpegError,
    kill_active_subprocesses,
    run_ffmpeg,
    terminate_process,
)


def test_run_ffmpeg_success_with_progress() -> None:
    lines: list[str] = []

    def _fake_popen(*args: object, **kwargs: object) -> MagicMock:
        proc = MagicMock()
        proc.pid = 12345
        proc.stdout = iter(
            [
                "frame=1 time=00:00:01.00 bitrate=N/A\n",
                "frame=2 fps=30\n",
            ]
        )
        proc.wait.return_value = 0
        proc.poll.return_value = 0
        return proc

    with (
        patch("smart_convert_nvenc.ffmpeg_runner.ffmpeg_executable", return_value="ffmpeg"),
        patch("smart_convert_nvenc.ffmpeg_runner.subprocess.Popen", side_effect=_fake_popen),
    ):
        elapsed = run_ffmpeg(["-version"], on_progress=lines.append)
    assert elapsed >= 0
    assert lines == ["frame=1 time=00:00:01.00 bitrate=N/A"]


def test_run_ffmpeg_nonzero_raises() -> None:
    def _fake_popen(*args: object, **kwargs: object) -> MagicMock:
        proc = MagicMock()
        proc.pid = 1
        proc.stdout = iter([])
        proc.wait.return_value = 7
        proc.poll.return_value = 7
        return proc

    with (
        patch("smart_convert_nvenc.ffmpeg_runner.ffmpeg_executable", return_value="ffmpeg"),
        patch("smart_convert_nvenc.ffmpeg_runner.subprocess.Popen", side_effect=_fake_popen),
    ):
        with pytest.raises(FFmpegError, match="code 7"):
            run_ffmpeg(["-i", "missing"])


def test_run_ffmpeg_cancelled_by_should_stop() -> None:
    stop = threading.Event()

    def _fake_popen(*args: object, **kwargs: object) -> MagicMock:
        proc = MagicMock()
        proc.pid = 42
        proc.poll.return_value = None

        def _stdout() -> object:
            stop.set()
            yield "time=00:00:01.00\n"
            yield "time=00:00:02.00\n"

        proc.stdout = _stdout()
        proc.wait.return_value = 1
        return proc

    with (
        patch("smart_convert_nvenc.ffmpeg_runner.ffmpeg_executable", return_value="ffmpeg"),
        patch("smart_convert_nvenc.ffmpeg_runner.subprocess.Popen", side_effect=_fake_popen),
        patch("smart_convert_nvenc.ffmpeg_runner.terminate_process", return_value=True) as term,
    ):
        with pytest.raises(FFmpegCancelled):
            run_ffmpeg(["x"], should_stop=stop.is_set)
        assert term.called


def test_terminate_process_already_done() -> None:
    proc = MagicMock()
    proc.poll.return_value = 0
    assert terminate_process(proc) is False


def test_terminate_process_windows_taskkill() -> None:
    proc = MagicMock()
    proc.poll.return_value = None
    proc.pid = 999
    with (
        patch("smart_convert_nvenc.ffmpeg_runner.sys.platform", "win32"),
        patch("smart_convert_nvenc.ffmpeg_runner.subprocess.run") as run,
    ):
        assert terminate_process(proc) is True
        run.assert_called()
        assert run.call_args.args[0][:3] == ["taskkill", "/F", "/T"]


def test_terminate_process_non_windows_kill() -> None:
    proc = MagicMock()
    proc.poll.return_value = None
    proc.pid = 999
    with patch("smart_convert_nvenc.ffmpeg_runner.sys.platform", "linux"):
        assert terminate_process(proc) is True
        proc.kill.assert_called()


def test_kill_active_subprocesses_registry() -> None:
    proc = MagicMock()
    proc.poll.return_value = None
    proc.pid = 1

    def _fake_popen(*args: object, **kwargs: object) -> MagicMock:
        proc.stdout = iter(["x\n"])
        # stay "running" until terminate
        def _wait(timeout: float | None = None) -> int:
            return 1

        proc.wait.side_effect = _wait
        return proc

    stop = threading.Event()

    def _progress(_: str) -> None:
        stop.set()

    with (
        patch("smart_convert_nvenc.ffmpeg_runner.subprocess.Popen", side_effect=_fake_popen),
        patch("smart_convert_nvenc.ffmpeg_runner.terminate_process", return_value=True) as term,
    ):
        # Register via run then kill from outside mid-flight is hard; call kill after register manually
        from smart_convert_nvenc import ffmpeg_runner as fr

        fr._register(proc)
        killed = kill_active_subprocesses()
        assert killed == 1
        assert term.called


def test_terminate_process_oserror() -> None:
    proc = MagicMock()
    proc.poll.return_value = None
    proc.pid = 1
    with (
        patch("smart_convert_nvenc.ffmpeg_runner.sys.platform", "linux"),
        patch.object(proc, "kill", side_effect=OSError("nope")),
    ):
        assert terminate_process(proc) is False

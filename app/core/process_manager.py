"""
Subprocess management with live stdout/stderr streaming.

ProcessManager runs a command asynchronously and emits lines to a
callback as they arrive.  It is designed to be used from:
  - The CLI runner (direct callback prints to terminal)
  - The GUI benchmark service (callback feeds a Qt signal)

Works on both Linux and Windows.

Usage::

    pm = ProcessManager()
    pm.start(["bash", "run_suite.sh", "quick"], env={...},
             on_line=print, on_done=lambda code: ...)
    pm.wait()  # blocks; or call pm.terminate() to cancel
"""

from __future__ import annotations

import logging
import os
import platform
import signal
import subprocess
import threading
from typing import Callable, Dict, List, Optional

log = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"

LineCallback = Callable[[str], None]
DoneCallback = Callable[[int], None]  # receives exit code


class ProcessManager:
    """Runs a subprocess and streams its combined output line-by-line."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        on_line: Optional[LineCallback] = None,
        on_done: Optional[DoneCallback] = None,
    ) -> None:
        """
        Start the command asynchronously.

        *on_line* is called for each output line (stdout + stderr merged).
        *on_done* is called with the exit code when the process finishes.
        """
        with self._lock:
            if self._running:
                raise RuntimeError("A process is already running")
            self._running = True

        merged_env = {**os.environ, **(env or {})}

        # On Windows, create the process in a new process group so that
        # we can send Ctrl-Break to the whole group for graceful cancel.
        creation_flags = 0
        if _IS_WINDOWS:
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merge stderr into stdout
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=merged_env,
            cwd=cwd,
            creationflags=creation_flags,
        )

        log.info("Started process PID=%d: %s", self._proc.pid, " ".join(str(c) for c in cmd))

        def _reader() -> None:
            assert self._proc is not None
            try:
                for line in iter(self._proc.stdout.readline, ""):  # type: ignore[union-attr]
                    stripped = line.rstrip("\n").rstrip("\r")
                    if on_line:
                        try:
                            on_line(stripped)
                        except Exception as exc:
                            log.debug("on_line callback error: %s", exc)
            except Exception as exc:
                log.debug("Reader thread error: %s", exc)
            finally:
                code = self._proc.wait()
                log.info("Process PID=%d exited with code %d", self._proc.pid, code)
                with self._lock:
                    self._running = False
                if on_done:
                    try:
                        on_done(code)
                    except Exception as exc:
                        log.debug("on_done callback error: %s", exc)

        self._thread = threading.Thread(target=_reader, daemon=True, name="process-reader")
        self._thread.start()

    def terminate(self) -> None:
        """Gracefully cancel the running process."""
        with self._lock:
            if not (self._proc and self._running):
                return
            log.info("Terminating process PID=%d", self._proc.pid)
            if _IS_WINDOWS:
                # Send Ctrl-Break to the process group (graceful PowerShell cancel)
                try:
                    self._proc.send_signal(signal.CTRL_BREAK_EVENT)
                except Exception:
                    self._proc.terminate()
            else:
                try:
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError, AttributeError):
                    self._proc.terminate()

    def kill(self) -> None:
        """Forcibly kill the running process."""
        with self._lock:
            if not (self._proc and self._running):
                return
            log.info("Killing process PID=%d", self._proc.pid)
            if _IS_WINDOWS:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            else:
                try:
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError, AttributeError):
                    self._proc.kill()

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        """Block until the process finishes; return exit code."""
        if self._thread:
            self._thread.join(timeout=timeout)
        if self._proc:
            return self._proc.returncode
        return None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def pid(self) -> Optional[int]:
        return self._proc.pid if self._proc else None

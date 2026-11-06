"""Single-key input without Enter, on POSIX terminals and the Windows console."""
import os
import sys

if os.name == "nt":
    import msvcrt
else:
    import select
    import termios
    import tty


class KeyReader:
    def __init__(self):
        self.enabled = sys.stdin.isatty()
        self._saved = None

    def __enter__(self):
        if self.enabled and os.name != "nt":
            fd = sys.stdin.fileno()
            self._saved = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        return self

    def __exit__(self, *exc):
        if self._saved is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._saved)

    def get(self, timeout):
        """A lower-case key pressed within `timeout` seconds, or None."""
        if not self.enabled:
            return None
        if os.name == "nt":
            import time
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                if msvcrt.kbhit():
                    return msvcrt.getwch().lower()
                time.sleep(0.02)
            return None
        r, _, _ = select.select([sys.stdin], [], [], timeout)
        return sys.stdin.read(1).lower() if r else None

import sys
import ctypes
import shlex
from pathlib import Path
from mapper_module import engine


def _is_admin() -> bool:
    """Checks if the script is running with Windows Administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _request_elevation():
    """Restarts the script with Windows UAC elevation."""
    script = Path(__file__).resolve()
    params = shlex.join(sys.argv[1:]) if sys.argv[1:] else ""
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{script}" {params}', str(script.parent), 1
    )


def elevate():
    """Handles process registration."""
    if not _is_admin():
        _request_elevation()
        sys.exit(0)

    else:
        engine.run()


if __name__ == "__main__":
    elevate()

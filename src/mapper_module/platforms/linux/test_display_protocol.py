import os
import sys
from mapper_module import engine


def _get_display_protocol():
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "wayland":
        if "DISPLAY" in os.environ:
            return "xwayland"
        return "wayland"
    if session == "x11" or "DISPLAY" in os.environ:
        return "x11"
    return None


def check_display_protocol():
    protocol = _get_display_protocol()
    if protocol is None:
        print("\n[!] - Display protocol not found.")
        sys.exit(1)
    elif not protocol == "x11":
        print("\n[!] - Ensure you are on X11.")
        sys.exit(1)
    else:
        engine.run()


if __name__ == "__main__":
    check_display_protocol()

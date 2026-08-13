import os


def _get_display_protocol():
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "wayland":
        if "DISPLAY" in os.environ:
            return "xwayland"
        return "wayland"
    if session == "x11" or "DISPLAY" in os.environ:
        return "x11"
    return None


def is_display_protocol_x11():
    protocol = _get_display_protocol()
    if not protocol:
        return False
    else:
        return protocol == "x11"


if __name__ == "__main__":
    is_display_protocol_x11()

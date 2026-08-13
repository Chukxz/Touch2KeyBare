import sys
from mapper_module.utils import SYSTEM


def run():
    print(f"--- Setting up for {SYSTEM} ---")

    if SYSTEM == "Windows":
        from mapper_module.platform.windows import elevate

        elevate()

    elif SYSTEM == "Linux":
        from mapper_module.platform.linux import is_display_protocol_x11

        is_display_protocol_x11()

    else:
        print(f"[!] Unsupported OS: {SYSTEM}")
        sys.exit(1)


if __name__ == "__main__":
    run()

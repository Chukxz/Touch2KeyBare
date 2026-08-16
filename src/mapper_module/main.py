import sys
from mapper_module.utils import SYSTEM


def run():
    if SYSTEM == "Windows":
        from mapper_module.platforms.windows import elevate

        elevate()

    elif SYSTEM == "Linux":
        from mapper_module.platforms.linux import check_display_protocol

        check_display_protocol()

    else:
        print(f"[!] Unsupported OS: {SYSTEM}")
        sys.exit(1)


if __name__ == "__main__":
    run()

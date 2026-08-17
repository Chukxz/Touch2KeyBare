import sys
from mapper_module.utils import SYSTEM
import argparse
PARSER = argparse.ArgumentParser(description="Touch2Key Main")

def run():
    if SYSTEM == "Windows":
        import argparse

        parser = argparse.ArgumentParser(description="Touch2Key Windows UAC Elevation")
        parser.add_argument(
            "--admin", action="store_true", help="Run with Administrator privileges."
        )
        args = parser.parse_args()

        if args.admin:
            from mapper_module.platforms.windows import elevate

            elevate()
        else:
            from mapper_module import engine

            engine.run(zzzz)

    elif SYSTEM == "Linux":
        from mapper_module.platforms.linux import check_display_protocol

        check_display_protocol()

    else:
        print(f"[!] Unsupported OS: {SYSTEM}")
        sys.exit(1)


if __name__ == "__main__":
    run()

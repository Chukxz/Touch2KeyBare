import sys
from mapper_module import SYSTEM

def run():
    print(f"--- Setting up for {SYSTEM} ---")

    if SYSTEM == "Windows":
        from mapper_module.platform.windows import setup_windows
        setup_windows()
    elif SYSTEM == "Linux":
        from mapper_module.platform.linux import setup_linux
        setup_linux()
    else:
        print(f"[!] Unsupported OS: {SYSTEM}")
        sys.exit(1)

if __name__ == "__main__":
    run()

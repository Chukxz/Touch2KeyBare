import shutil
from pathlib import Path
from mapper_module.utils import ADB


def run():
    resolved_path: Path | None = None

    if ADB.exists():
        resolved_path = ADB.resolve()
    else:
        system_adb = shutil.which("adb")
        if system_adb:
            resolved_path = Path(system_adb).resolve()

    if resolved_path:
        msg = f"ADB binary located at: {resolved_path}"
        print(f"[+] {msg}")
    else:
        msg = "ADB binary not found in project bin directory or system PATH."
        print(f"[!] {msg}")


if __name__ == "__main__":
    run()

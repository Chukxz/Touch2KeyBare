import os
import sys
import shutil
import requests
import zipfile
import subprocess
from pathlib import Path

from mapper_module.utils import PROJECT_ROOT

# Configuration
BIN_DIR = PROJECT_ROOT / "bin"

# Pointing to the Linux build of Google's Platform Tools
ADB_URL = "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"

# Linux Input Permission Rules
UDEV_RULE_PATH = Path("/etc/udev/rules.d/99-touch2key-uinput.rules")
UDEV_RULE_CONTENT = 'KERNEL=="uinput", SUBSYSTEM=="misc", OPTIONS+="static_node=uinput", TAG+="uaccess", GROUP="input", MODE="0660"\n'

def is_root():
    """Checks if the script is running with root/sudo privileges."""
    return os.geteuid() == 0

def download_adb():
    """Downloads and extracts Android platform-tools with rollback on failure."""
    print("[+] Ensuring ADB is available...")
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    platform_tools_dir = BIN_DIR / "platform-tools"
    adb_path = platform_tools_dir / "adb"  # Note: No .exe extension on Linux
    zip_path = BIN_DIR / "adb.zip"

    if adb_path.exists():
        print("[+] ADB already present.")
        return

    print("[+] Downloading ADB...")
    try:
        # Pre-cleanup
        if zip_path.exists(): os.remove(zip_path)
        if platform_tools_dir.exists(): shutil.rmtree(platform_tools_dir)

        response = requests.get(ADB_URL, stream=True)
        response.raise_for_status()

        with open(zip_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)

        print("[+] Extracting ADB...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(BIN_DIR)

        # CRITICAL LINUX FIX: The zipfile module strips execution permissions.
        # We must manually make adb executable (chmod +x)
        os.chmod(adb_path, 0o755)

        print("[+] ADB setup complete.")

    except Exception as e:
        print(f"\n[!] Error during ADB setup: {e}")
        if platform_tools_dir.exists():
            shutil.rmtree(platform_tools_dir)
        sys.exit(1)
    finally:
        if zip_path.exists():
            os.remove(zip_path)

def setup_uinput():
    """Configures udev rules to allow non-root access to /dev/uinput."""
    print("[+] Configuring /dev/uinput permissions...")

    # 1. Idempotency Check: Skip if the rule is already perfectly configured
    if UDEV_RULE_PATH.exists():
        try:
            with open(UDEV_RULE_PATH, 'r') as f:
                if f.read() == UDEV_RULE_CONTENT:
                    print("[+] udev rules are already configured. Skipping...")
                    return
        except PermissionError:
            pass # Needs root to read, will drop down to root check below

    # 2. Check for Sudo/Root
    if not is_root():
        print("[!] Setting up uinput permissions requires root access.")
        print("[+] Please re-run this setup script with 'sudo'.")
        sys.exit(1)

    # 3. Create the Rule
    print("[+] Writing udev rules...")
    try:
        with open(UDEV_RULE_PATH, 'w') as f:
            f.write(UDEV_RULE_CONTENT)
        
        # 4. Reload rules dynamically so the user DOES NOT have to reboot their PC
        print("[+] Reloading udev rules...")
        subprocess.run(["udevadm", "control", "--reload-rules"], check=True)
        subprocess.run(["udevadm", "trigger"], check=True)

        print("[+] Permissions applied successfully.")

    except Exception as e:
        print(f"[!] Failed to setup udev rules: {e}")
        sys.exit(1)

def setup_linux():
    print("--- Touch2Key Setup Wizard (Linux) ---")
    download_adb()
    setup_uinput()
    
    print("\n[+] Setup complete! You are ready to use Touch2Key.")
    print("[i] Note: If input mapping fails, ensure your user is in the 'input' group:")
    print("          Run: sudo usermod -aG input $USER")
    print("          (You will need to log out and log back in for group changes to take effect)")

if __name__ == "__main__":
    setup_linux()

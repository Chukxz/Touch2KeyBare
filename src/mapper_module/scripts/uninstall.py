import os
import shutil
import argparse
import subprocess
from pathlib import Path
from mapper_module.utils import (
    PROJECT_ROOT, SYSTEM, IMAGES_FOLDER, JSONS_FOLDER
)

BIN_DIR = PROJECT_ROOT / "bin"

def run():
    # Setup Argument Parser
    parser = argparse.ArgumentParser(description="Touch2Key Uninstaller")
    parser.add_argument(
        "--purge", 
        action="store_true", 
        help="Perform a total wipe, including saved JSON mappings and images."
    )
    args = parser.parse_args()

    print(f"--- Uninstalling Touch2Key ({SYSTEM}) ---")

    # 1. Platform Specific Driver/Rule Removal
    # (Must happen before deleting BIN_DIR)
    if SYSTEM == "Windows":
        installer_exe = BIN_DIR / "Interception" / "command line installer" / "install-interception.exe"
        if installer_exe.exists():
            print("[+] Uninstalling Interception driver...")
            try:
                subprocess.run([str(installer_exe), "/uninstall"], capture_output=True, check=True)
                print("[!] Please REBOOT your computer to complete driver removal.")
            except Exception as e:
                print(f"[!] Failed to uninstall driver: {e}")

    elif SYSTEM == "Linux":
        udev_rule = Path("/etc/udev/rules.d/99-touch2key-uinput.rules")
        if udev_rule.exists():
            print("[+] Removing udev rules...")
            if os.geteuid() == 0:
                try:
                    udev_rule.unlink()
                    subprocess.run(["udevadm", "control", "--reload-rules"], check=True)
                    print("[+] udev rules removed.")
                except Exception as e:
                    print(f"[!] Error: {e}")
            else:
                print("[!] Permission Denied: Run as 'sudo' to remove udev rules.")

    # 2. Selective Cleanup
    # We protect the user's data unless --purge is explicitly passed
    protected = {IMAGES_FOLDER.name, JSONS_FOLDER.name}
    
    print(f"[+] Cleaning up {PROJECT_ROOT}...")
    
    for item in PROJECT_ROOT.iterdir():
        # Do not delete the uninstaller script itself while it is running
        if item.name == Path(__file__).name:
            continue
            
        if args.purge or item.name not in protected:
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                print(f"    - Deleted: {item.name}")
            except Exception as e:
                print(f"    - Could not delete {item.name}: {e}")
        else:
            print(f"    - Preserved: {item.name}")

    if not args.purge:
        print("\n[+] Uninstall complete (Safe Mode).")
        print("[*] Your JSON mappings and images were preserved.")
        print("[*] Run with '--purge' to delete all user data.")
    else:
        print("\n[+] Purge complete. All files removed.")

if __name__ == "__main__":
    run()

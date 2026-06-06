import os
import shutil
import argparse
import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from mapper_module.utils import (
    PROJECT_ROOT, SYSTEM, IMAGES_FOLDER, JSONS_FOLDER
)

BIN_DIR = PROJECT_ROOT / "bin"

def confirm_uninstall(message):
    """Fallback-safe confirmation dialog."""
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        answer = messagebox.askyesno("Touch2Key Uninstall", message)
        root.destroy()
        return answer
    except Exception:
        # Fallback to CLI for headless/server environments
        return input(f"{message} (y/n): ").lower() == 'y'

def run():
    parser = argparse.ArgumentParser(description="Touch2Key Uninstaller")
    parser.add_argument("--purge", action="store_true", help="Delete JSON configs and images.")
    args = parser.parse_args()

    # --- Pre-flight Confirmation ---
    warning = "Are you sure you want to uninstall Touch2Key? This will remove system drivers/rules and all binaries."
    if not confirm_uninstall(warning):
        print("[!] Uninstallation cancelled by user.")
        return

    print(f"\n--- Uninstalling Touch2Key ({SYSTEM}) ---")

    # --- Platform Specific Driver/Rule Removal ---
    if SYSTEM == "Windows":
        installer_exe = BIN_DIR / "Interception" / "command line installer" / "install-interception.exe"
        if installer_exe.exists():
            print("[+] Uninstalling Interception driver...")
            try:
                subprocess.run([str(installer_exe), "/uninstall"], capture_output=True, check=True)
                print("[!] REBOOT REQUIRED: Please restart your computer to finish driver removal.")
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
                    print(f"[!] Error removing udev rules: {e}")
            else:
                print("[!] Permission Denied: Run as 'sudo' to remove udev rules.")

    # --- Full Binary & ADB Cleanup ---
    if BIN_DIR.exists():
        print(f"[+] Removing binary directory (ADB, tools, etc)...")
        try:
            shutil.rmtree(BIN_DIR)
            print("    - Binaries cleared.")
        except Exception as e:
            print(f"    - Could not delete binaries: {e}")

    # --- Selective Data Cleanup ---
    protected = {IMAGES_FOLDER.name, JSONS_FOLDER.name}
    
    print(f"[+] Cleaning up {PROJECT_ROOT}...")
    for item in PROJECT_ROOT.iterdir():
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
        print("[*] JSON mappings and images preserved in root.")
    else:
        print("\n[+] Purge complete. All files removed.")

if __name__ == "__main__":
    run()
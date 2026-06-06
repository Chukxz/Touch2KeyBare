import os
import sys
import shutil
import subprocess
from mapper_module.utils import PROJECT_ROOT, SYSTEM

BIN_DIR = PROJECT_ROOT / "bin"

def run():
    print(f"--- Uninstalling Touch2Key ({SYSTEM}) ---")
    
    # 1. Platform Specific Removal
    if SYSTEM == "Windows":
        installer_exe = BIN_DIR / "Interception" / "command line installer" / "install-interception.exe"
        if installer_exe.exists():
            print("[+] Uninstalling Interception driver...")
            subprocess.run([str(installer_exe), "/uninstall"], capture_output=True)
            print("[!] Please REBOOT your computer to fully remove the driver.")
            
    elif SYSTEM == "Linux":
        udev_rule = "/etc/udev/rules.d/99-touch2key-uinput.rules"
        if os.path.exists(udev_rule):
            print("[+] Removing udev rules...")
            if os.geteuid() == 0:
                os.remove(udev_rule)
                subprocess.run(["udevadm", "control", "--reload-rules"], check=True)
            else:
                print("[!] Permission Denied: Please run uninstall with 'sudo' to remove udev rules.")

    # 2. General Cleanup
    if BIN_DIR.exists():
        print("[+] Removing binary directory...")
        shutil.rmtree(BIN_DIR)
        
    print("[+] Uninstall complete. Note: You may still have configuration files in your home directory.")
    print("    (You may need to manually delete your settings if desired).")

if __name__ == "__main__":
    run()

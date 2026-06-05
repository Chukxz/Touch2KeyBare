import os
import subprocess
import ctypes
import sys
import shutil
import requests
import zipfile

from mapper_module.utils import PROJECT_ROOT

# Configuration
BIN_DIR = PROJECT_ROOT / "bin"
ADB_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
INTERCEPTION_EXE = BIN_DIR / "interception" / "install-interception.exe"

def is_admin():
    """Checks if the script is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def download_adb():
    """Downloads and extracts Android platform-tools."""
    print("[+] Ensuring ADB is available...")
    BIN_DIR.mkdir(exist_ok=True)
    adb_path = BIN_DIR / "platform-tools" / "adb.exe"
    
    if not adb_path.exists():
        zip_path = BIN_DIR / "adb.zip"
        response = requests.get(ADB_URL, stream=True)
        with open(zip_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(BIN_DIR)
        os.remove(zip_path)
        print("[+] ADB setup complete.")
    else:
        print("[+] ADB already present.")

def setup_driver():
    """Handles the one-time driver registration and returns True if a reboot is needed."""
    if not is_admin():
        print("[!] Driver registration requires Admin rights.")
        print("[+] Please re-run this setup script as Administrator.")
        sys.exit(1)

    print("[+] Registering Interception driver...")
    result = subprocess.run([str(INTERCEPTION_EXE), "/install"], capture_output=True)
    
    if result.returncode == 0:
        print("[+] Driver registered successfully!")
        return True  # True means a reboot is required
    else:
        print(f"[!] Failed to register driver: {result.stderr.decode()}")
        return False

def setup_windows():
    print("--- Touch2Key Setup Wizard ---")
    download_adb()
    
    # Track if the driver was actually installed during this run
    needs_reboot = setup_driver()

    if needs_reboot:
        print("\n" + "="*55)
        print("!!! SYSTEM RESTART REQUIRED !!!".center(55))
        print("="*55)
        print("The Interception driver has been installed.")
        print("Touch2Key will NOT be able to simulate mouse/keyboard")
        print("inputs until you restart your computer.")
        print("="*55 + "\n")
        
        choice = input("Would you like to restart your PC now? (y/n): ").strip().lower()
        if choice == 'y':
            print("[+] Initiating system restart in 5 seconds...")
            # Windows command to restart the PC with a 5-second delay and a custom message
            os.system('shutdown /r /t 5 /c "Touch2Key driver installation complete."')
        else:
            print("[+] Please remember to manually restart before running Touch2Key.")
    else:
        print("\n[+] Setup complete! You are ready to use Touch2Key.")

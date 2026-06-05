        
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

def setup_driver():
    """Handles the one-time driver registration."""
    if not is_admin():
        print("[!] Driver registration requires Admin rights.")
        print("[+] Please re-run this setup script as Administrator.")
        sys.exit(1)

    print("[+] Registering Interception driver...")
    # Adjust this path based on where you extract the Interception zip
    result = subprocess.run([str(INTERCEPTION_EXE), "/install"], capture_output=True)
    if result.returncode == 0:
        print("[+] Driver registered successfully! Please restart your PC.")
    else:
        print(f"[!] Failed to register driver: {result.stderr.decode()}")

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

def setup_windows():
    print("--- Touch2Key Setup Wizard ---")
    download_adb()
    
    # Only register driver if not already installed
    # (Optional: Add a registry check here to skip if already registered)
    setup_driver()
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

INTERCEPTION_API_URL = "https://api.github.com/repos/oblitum/Interception/releases/latest"

INTERCEPTION_EXE = BIN_DIR / "Interception" / "command line installer" / "install-interception.exe"

def is_admin():
    """Checks if the script is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def download_adb():
    """Downloads and extracts Android platform-tools with rollback on failure."""
    print("[+] Ensuring ADB is available...")
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    
    platform_tools_dir = BIN_DIR / "platform-tools"
    adb_path = platform_tools_dir / "adb.exe"
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
        response.raise_for_status() # Fails immediately on bad connection
        
        with open(zip_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)

        print("[+] Extracting ADB...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(BIN_DIR)
        print("[+] ADB setup complete.")

    except Exception as e:
        print(f"\n[!] Error during ADB setup: {e}")
        if platform_tools_dir.exists():
            shutil.rmtree(platform_tools_dir)
        sys.exit(1)
    finally:
        if zip_path.exists():
            os.remove(zip_path)

def download_interception():
    """Fetches and extracts the latest Interception release from GitHub."""
    print("[+] Ensuring Interception driver files are available...")
    
    # Interception zip structure usually extracts to a folder named "Interception"
    interception_dir = BIN_DIR / "Interception" 
    installer_exe = interception_dir / "command line installer" / "install-interception.exe"
    zip_path = BIN_DIR / "interception.zip"

    # If we already have the installer, skip the download
    if installer_exe.exists():
        print("[+] Interception files already present.")
        return

    print("[+] Querying GitHub for latest Interception release...")
    try:
        # Clean up from any previous failed attempts
        if zip_path.exists():
            os.remove(zip_path)
        if interception_dir.exists():
            shutil.rmtree(interception_dir)

        # Use GitHub API to get the latest release data
        api_response = requests.get(INTERCEPTION_API_URL)
        api_response.raise_for_status()
        
        release_data = api_response.json()
        
        # Find the zip file URL in the release assets
        download_url = None
        for asset in release_data.get("assets", []):
            if asset["name"].endswith(".zip"):
                download_url = asset["browser_download_url"]
                break
                
        if not download_url:
            raise ValueError("Could not find a .zip asset in the latest release.")

        # Download the zip
        print(f"[+] Downloading Interception ({release_data['tag_name']})...")
        zip_response = requests.get(download_url, stream=True)
        zip_response.raise_for_status()
        
        with open(zip_path, 'wb') as f:
            shutil.copyfileobj(zip_response.raw, f)

        # Extract the zip
        print("[+] Extracting Interception...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(BIN_DIR)

        print("[+] Interception download complete.")

    except Exception as e:
        print(f"\n[!] Error downloading Interception: {e}")
        if interception_dir.exists():
            shutil.rmtree(interception_dir)
        sys.exit(1)

    finally:
        if zip_path.exists():
            os.remove(zip_path)

def setup_driver():
    """Handles the one-time driver registration and returns True if a reboot is needed."""
    
    # 1. Check if it's already installed!
    try:
        import interception
        # If this imports successfully without throwing an error, the driver is likely active.
        # (Assuming the python wrapper is installed and detects the driver)
        print("[+] Interception driver is already installed and active.")
        return False # No reboot needed
    except ImportError:
        pass # Not installed or not active, proceed with installation

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
    download_interception()

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

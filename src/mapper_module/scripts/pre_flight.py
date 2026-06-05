import shutil
from pathlib import Path
from mapper_module import SYSTEM

def check_adb():
    """Verify ADB is available."""
    # Check system PATH or local bin folder
    if shutil.which("adb"):
        return True
    
    # Optional: check your custom bin/ directory
    bin_adb = Path(__file__).resolve().parent.parent.parent.parent / "bin" / "platform-tools" / "adb.exe"
    if bin_adb.exists():
        return True
        
    return False

def check_driver():
    """Verify system driver (Platform specific)."""
    if SYSTEM == "Windows":
        # Interception typically doesn't have a simple 'which' check.
        # We check for a common registry key or try a dummy call.
        try:
            import interception
            return True
        except ImportError:
            return False
    elif SYSTEM == "Linux":
        # Check if user has permission to read uinput
        return Path("/dev/uinput").exists()
    return False

def run():
    """Execute all checks. Returns False if any check fails."""
    checks = {
        "ADB": check_adb(),
        "Driver": check_driver()
    }
    
    failed = [name for name, status in checks.items() if not status]
    
    if failed:
        print(f"[!] Pre-flight failed: {', '.join(failed)} missing or unavailable.")
        print("[+] Please run 'touch2key-setup' to configure environment.")
        return False
        
    print("[+] Pre-flight checks passed.")
    return True

if __name__ == "__main__":
    run()
from __future__ import annotations
from mapper_module.utils import SYSTEM

# --- Single Instance Logic ---

def check_single_instance_windows(instance_name: str) -> tuple[bool, int | None]:
    """Uses a named Mutex to prevent duplicate instances on Windows."""
    import ctypes

    mutex_name = f"Global\\{instance_name}"
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return False, None
    return True, handle

def check_single_instance_linux(instance_name: str) -> tuple[bool, object | None]:
    """Uses a lockfile to prevent duplicate Linux instances."""
    import fcntl
    
    lock_file = f"/tmp/{instance_name}.lock"
    # 'a' mode creates the file if it doesn't exist
    handle = open(lock_file, "a") 
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True, handle
    except (IOError, OSError):
        return False, None

def check_single_instance(instance_name: str) -> tuple[bool, object | None]:
    """Wrapper to check if another instance is running."""
    if SYSTEM == "Windows":
        return check_single_instance_windows(instance_name)
    elif SYSTEM == "Linux":
        return check_single_instance_linux(instance_name)
    return False, None

# --- Platform Bridge ---

def get_platform():
    """
    Returns the platform-specific modules. 
    Imports are deferred inside the function to avoid circular imports.
    """
    if SYSTEM == "Windows":
        from .windows.bridge import InterceptionBridge
        from .windows.window import WindowManager
        from .windows.system import SystemConfig
        from .windows.mapping import Mapping
        return InterceptionBridge, WindowManager, SystemConfig, Mapping
        
    elif SYSTEM == "Linux":
        from .linux.bridge import UInputBridge as InterceptionBridge
        from .linux.window import WindowManager
        from .linux.system import SystemConfig
        from .linux.mapping import Mapping
        return InterceptionBridge, WindowManager, SystemConfig, Mapping
        
    else:
        raise RuntimeError(f"Unsupported platform: {SYSTEM}")

__all__ = ["check_single_instance", "get_platform"]
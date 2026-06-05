from mapper_module.utils import SYSTEM

# import fcntl
# import os

# def check_single_instance_linux(instance_name):
#     """Uses a lockfile to prevent duplicate Linux instances."""
#     lock_file = f"/tmp/{instance_name}.lock"
#     handle = open(lock_file, "w")
#     try:
#         fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
#         return True, handle
#     except (IOError, OSError):
#         return False, None


def check_single_instance(instance_name):
    """Create a unique mutex to prevent duplicate instances (Cross-Platform safe)."""
    if SYSTEM == "Windows":
        mutex_name = f"Global\\{instance_name}"
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        if ctypes.windll.kernel32.GetLastError() == 183:
            return False, None
        return True, handle
    elif SYSTEM == "Linux":
        # Fallback for Linux. Advanced implementation would use fcntl lockfiles.
        return True, None
    else:
        return False, None # Fallback for unsupported platforms.

def get_platform():
    if SYSTEM == "Windows":
        from .windows.bridge import InterceptionBridge
        from .windows.window import WindowManager
        from .windows.system import SystemConfig
        from .windows.mapping import Mapping
    elif SYSTEM == "Linux":
        from .linux.bridge import UInputBridge as InterceptionBridge
        from .linux.window import WindowManager
        from .linux.system import SystemConfig
        from .linux.mapping import Mapping
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
    
    return InterceptionBridge, WindowManager, SystemConfig, Mapping

__all__ = ["check_single_instance", "get_platform"]

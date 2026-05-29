import platform

def get_platform():
    system = platform.system()
    if system == "Windows":
        from .windows.bridge import InterceptionBridge
        from .windows.window import WindowManager
        from .windows.system import SystemConfig
        from .windows.mapping import Mapping
    elif system == "Linux":
        from .linux.bridge import UInputBridge as InterceptionBridge
        from .linux.window import WindowManager
        from .linux.system import SystemConfig
        from .linux.mapping import Mapping
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
    
    return InterceptionBridge, WindowManager, SystemConfig, Mapping

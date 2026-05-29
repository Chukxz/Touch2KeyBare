import ctypes
import psutil
from mapper_module.utils import NT_TIMER_RES

class SystemConfig:
    def set_dpi_awareness(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:   
                pass

    def set_timer_resolution(self):
        ctypes.windll.ntdll.NtSetTimerResolution(
            NT_TIMER_RES, 1, ctypes.byref(ctypes.c_ulong())
        )

    def set_high_priority(self, pid, label):
        try:
            p = psutil.Process(pid)
            p.nice(psutil.HIGH_PRIORITY_CLASS)
            p.cpu_affinity(list(range(psutil.cpu_count() or 1)))
            print(f"\n[SYSTEM] - {label} set to HIGH (Floating Affinity).")
        except Exception as e:
            print(f"\n[SYSTEM] - Warning: {e}.")
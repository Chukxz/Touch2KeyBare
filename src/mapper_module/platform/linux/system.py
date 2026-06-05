# # Internal cross-platform niceness helper for bridge health respawn
# def internal_set_high_priority(pid: int | None, label):
#     try:
#         p = psutil.Process(pid)
#         if platform.system() == "Windows":
#             p.nice(psutil.HIGH_PRIORITY_CLASS)
#         else:
#             p.nice(-10) # Safe Linux priority equivalent
#         p.cpu_affinity(list(range(psutil.cpu_count() or 1)))
    
#         print(f"\n[UTILITY] - {label} set to HIGH (Floating Affinity).")
#     except Exception as e:
#         print(f"\n[UTILITY] - Warning: {e}.")

from ..base import AbstractSystemConfig

class SystemConfig(AbstractSystemConfig):...
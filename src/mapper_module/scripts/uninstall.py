#!/usr/bin/env python3
"""
CLI-Only Driver, Rules, and Data Uninstaller.
Supports both Windows and Linux without GUI framework dependencies.
"""

from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

from mapper_module.utils import (
    BIN_DIR,
    DATA_FOLDER,
    PROJECT_ROOT,
    SYSTEM,
    UDEV_RULE_PATH,
)


def _is_admin() -> bool:
    """Checks for Administrator (Windows) or root (Linux) privileges."""
    if SYSTEM == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    return os.geteuid() == 0


def _request_elevation() -> None:
    """Requests elevation via Windows UAC or advises sudo on Linux."""
    if SYSTEM == "Windows":
        script = Path(__file__).resolve()
        params = " ".join(sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', os.getcwd(), 1
        )
    else:
        print("[!] Please run this script with 'sudo'.")


def _kill_adb() -> None:
    """Terminates active adb daemon processes."""
    print("[+] Checking for running ADB processes...")
    cmd = (
        ["taskkill", "/F", "/IM", "adb.exe", "/T"]
        if SYSTEM == "Windows"
        else ["pkill", "-f", "adb"]
    )
    try:
        subprocess.run(cmd, capture_output=True, check=False)
        print("[+] ADB cleanup finished.")
    except Exception as exc:
        print(f"[!] Note: Could not kill ADB (might not be running): {exc}")


def purge_data() -> None:
    """Deletes CLI data directory (settings.toml, jsons/, images/)."""
    if DATA_FOLDER.exists():
        shutil.rmtree(DATA_FOLDER, ignore_errors=True)
    print(f"    - User data purged ({DATA_FOLDER}).")


def purge_profs() -> None:
    """Deletes profiling files (.prof) in the project root."""
    deleted_count = 0
    for prof_file in PROJECT_ROOT.glob("*.prof"):
        prof_file.unlink(missing_ok=True)
        deleted_count += 1
    print(f"    - Profiling file(s) purged ({deleted_count} file(s) removed).")


def run() -> None:
    # 1. Elevation Check
    if not _is_admin():
        if SYSTEM == "Windows":
            print("[!] Administrator privileges required.")
            _request_elevation()
        else:
            print("[!] Root privileges required. Please execute with 'sudo'.")
        sys.exit(0)

    # 2. CLI Arguments
    parser = argparse.ArgumentParser(
        description="Driver and Rules Uninstaller (CLI Mode)"
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Delete data directory (images, jsons, settings.toml)",
    )
    parser.add_argument(
        "--purge-all",
        action="store_true",
        help="Delete data directory and root profiling file(s)",
    )
    parser.add_argument(
        "--no-restart", action="store_true", help="Skip system reboot prompt on Windows"
    )
    args = parser.parse_args()

    # 3. Confirmation
    if not args.yes:
        confirm = (
            input("Are you sure you want to uninstall drivers/rules and local binaries? (y/N): ")
            .strip()
            .lower()
        )
        if confirm != "y":
            print("[!] Aborted.")
            if SYSTEM == "Windows":
                input("\nPress Enter to exit...")
            return

    # 4. Kill ADB
    _kill_adb()

    # 5. OS-Specific Driver / Rules Removal
    needs_reboot = False
    if SYSTEM == "Windows":
        print("\n--- Uninstalling Interception Driver ---")
        installer_exe = (
            BIN_DIR
            / "Interception"
            / "command line installer"
            / "install-interception.exe"
        )
        if installer_exe.exists():
            res = subprocess.run([str(installer_exe), "/uninstall"], capture_output=True)
            if res.returncode == 0:
                needs_reboot = True
                print("[+] Interception driver uninstalled successfully.")
            else:
                print("[!] Driver uninstaller returned a non-zero code.")
        else:
            print("[!] Interception installer not found in bin/.")

    elif SYSTEM == "Linux":
        print("\n--- Removing Udev Rules ---")
        if UDEV_RULE_PATH.exists():
            UDEV_RULE_PATH.unlink(missing_ok=True)
            subprocess.run(["udevadm", "control", "--reload-rules"], check=False)
            subprocess.run(["udevadm", "trigger"], check=False)
            print("[+] Udev rules removed and subsystem reloaded.")
        else:
            print(f"[!] Udev rule file not found at {UDEV_RULE_PATH}.")

    # 6. Delete Binaries
    if BIN_DIR.exists():
        shutil.rmtree(BIN_DIR, ignore_errors=True)
        print("    - Local binaries deleted.")

    # 7. Purge Files
    if args.purge or args.purge_all:
        purge_data()

    if args.purge_all:
        purge_profs()

    print("\n[+] Uninstall complete.")

    # 8. Reboot or Exit
    if SYSTEM == "Windows":
        if needs_reboot and not args.no_restart:
            print("\n" + "=" * 55)
            print(" SYSTEM RESTART REQUIRED ".center(55, "="))
            print("=" * 55)
            choice = input("Restart PC now (Will restart in 5 seconds)? (y/N): ").strip().lower()
            if choice == "y":
                subprocess.run(
                    [
                        "shutdown",
                        "/r",
                        "/t",
                        "5",
                        "/c",
                        "Driver uninstallation complete.",
                    ]
                )
                return
            else:
                print("[!] Please remember to restart your computer to complete removal.")
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    run()

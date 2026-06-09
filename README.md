# Touch2Key

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OS: Windows](https://img.shields.io/badge/os-Windows-blue.svg)](https://www.microsoft.com/en-us/windows)
[![OS: Linux](https://img.shields.io/badge/os-Linux-yellow.svg)](https://www.linuxfoundation.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Touch2Key** is a high-performance, cross-platform input mapper designed to seamlessly translate touch interactions (via Android/ADB) into zero-latency keyboard and mouse inputs on your PC.

It is recommended to enable `Developer Options` on Android and `Wireless Debugging` (especially if you want to use WIFI - 5GHz recommended) and if there's a popup window grant permissions.

This input mapper can be used with `Sunshine/Moonlight` or `Artemis/Apollo` for full visual and auditory integration at which point we recommend disabling all inputs in `Sunshine` or `Apollo` to avoid conflicts with our mapper.

## Key Features
* **Platform Native Injection:** Windows (Interception driver) and Linux (evdev/uinput).
If you're on Linux ensure that your windowing system is using X11.

* **Zero-Latency:** Dedicated isolated background worker processes and background helper threads with heartbeat timers and real-time status logs.

* **Event Coalescing:** Dynamically aggregates high-frequency touch-drags.

* **Sophisticated and Responsive Plotting GUI**: Plotting supports advanced functions via clearly described and intuitive methods.

* **Camera Movement Support for Touchzones:** The user can decide to give selected touch zones a camera movement ability.

* **Handedness and Hot-Reloading:** Configuration or mapping sources (JSON files) can be reloaded at runtime and handedness (Mouse/WASD finger side) can be swapped at runtime with hot-reloading.

* **Anti-Cheat Safe:** Humanized dwell times and randomized click durations for strictly user-initiated actions. No custom bot scripts or cheating. A basic toggler is provided to ensure seamless normal or menu mode in-gaming by inspecting cursor visibility and using the game's/emulator's toggle button if any.

* **Automated Setup:** Interception download (Windows with admin) / Udev rules configuration (Linux with sudo) automated. ADB cross-platform download automated.

* **Targeted Audience:** Optimized for FPS and RPG style games.

* **Shareable Resources:** HUD Image files and mapping JSON files can be shared by simple copying and pasting and then using the plotter to validate and/or set the current HUD and/or JSON.

* **Automatic Program Detection:** Supported programs (eg. games or emulators), which are currently running are automatically detected and a selection is made as the automatic choice subject to user confirmation/override, else the user chooses the program of their choice.

## Installation
1. **Prerequisites:** Python 3.10+.
2. **Install:**
   ```bash
   git clone https://github.com/Chukxz/Touch2Key.git
   cd Touch2Key
   pip install .
3. **Setup:** Run setup (Usually requires an internet connection).


## Uninstallation
Because Touch2Key installs system-level drivers and kernel rules, **simply running `pip uninstall Touch2Key` is not sufficient.** You must use the included uninstaller.

| Action | Command | Description |
| :--- | :--- | :--- |
| **Standard** | `touch2key-uninstall` | Removes drivers/rules/binaries; preserves your custom mappings/images. |
| **Purge** | `touch2key-uninstall --purge` | Removes drivers/rules/binaries **AND** deletes all saved mappings/images. |

*(Note: Windows requires a system reboot after uninstallation to fully release the driver).*

## Command Line Interface (CLI)
| Command | Description |
| :--- | :--- |
| `touch2key` | Launches the main engine. |
| `touch2key-capture` | ADB screen capture. |
| `touch2key-plot` | Mapping visualizer. |
| `touch2key-preflight` | Diagnostic checks. |
| `touch2key-reset` | Resets configuration setttings.|
| `touch2key-select` | JSON selector.|
| `touch2key-setup` | OS configuration wizard. |
| `touch2key-show` | Displays full ADB executable path if found.|
| `touch2key-uninstall` | Safely removes drivers and binaries. |
| `touch2key-wireless` | Force ADB wireless connection. |

*(Note: Windows requires a system reboot after installation to fully load the driver).*

## Contributing
Please use `black` for formatting and `pytest` for unit testing (optional).

## License
MIT License.

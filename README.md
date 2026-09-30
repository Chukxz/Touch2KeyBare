# Touch2KeyBare

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OS: Windows](https://img.shields.io/badge/os-Windows-blue.svg)](https://www.microsoft.com/en-us/windows)
[![OS: Linux](https://img.shields.io/badge/os-Linux-yellow.svg)](https://www.linuxfoundation.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Touch2KeyBare** is a high-performance, cross-platform input mapper designed to seamlessly translate touch interactions (via Android/ADB) into zero-latency keyboard and mouse inputs on your PC.

This is the First Touch2Key Published Implementation with only CLI support + Basic GUI windows.
The second version with full GUI, CLI support and improved functionality, can be accessed [here](https://github.com/Chukxz/touch2key).

It is recommended to enable `Developer Options` on Android and `Wireless Debugging` (especially if you want to use WIFI - 5GHz recommended) and if there's a popup window grant permissions.

This input mapper can be used with `Sunshine/Moonlight` or `Apollo/Artemis` for full visual and auditory integration at which point we recommend disabling all inputs in `Sunshine` or `Apollo` to avoid conflicts with our mapper.

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

## Window Selection & Persistence
On startup, the engine launches an interactive Window Selector dialog that lists all active processes with their titles and class names. 

*   **Initial Binding:** Users must manually select their target emulator or game from the provided list. The engine then binds to this specific window ID.

*   **Persistent Tracking:** Once the initial selection is made, the engine maintains a robust link to that application. If the target window is lost—due to a crash or an application restart—the system uses the captured window class name to automatically re-acquire the most relevant (largest) visible window of the same type. This ensures that sessions are maintained seamlessly without requiring manual re-selection of the target window.


## Key Customization & Configuration
After selecting your target window, the engine will prompt you to configure your control keys to ensure the mapping matches your preferred layout.

*   **Custom Key Binding:** A dedicated capture dialog allows you to bind specific keys for core functions, such as the **Toggle** (for Camera/Menu mode) and **Sprint**.
*   **Automatic Persistence:** Once captured, these preferences are saved to your `settings.toml` file. 
*   **Default Handling:** The system will attempt to load existing configurations from your settings file automatically, but you are always given the option to re-bind keys or reset to defaults during the startup sequence.

## Connectivity & Resilience
* **Auto-Adaptive Input:** The engine automatically detects your Android device's specific touchscreen hardware and multi-touch capabilities upon startup, requiring no manual configuration of input drivers.
* **Wired & Wireless Support:** The connection is managed by a background daemon that supports both direct USB and wireless ADB. **Note:** Wireless mode typically requires an initial wired connection to toggle your device into TCP/IP mode (`adb tcpip 5555`) before it can be used wirelessly, unless your device is already configured in wireless mode. 
* **Self-Healing Stream:** If your connection drops—due to cable removal or wireless instability—the engine automatically detects the loss, pauses input mapping, and transparently resumes as soon as the device is available again, with no restart required.


## Installation

### Prerequisites
* Python 3.10+
* Android device with USB/Wireless Debugging enabled
* Linux users: X11 session with `sudo` access for `uinput`/`udev` rules

### Setup
* **Install: Remember to create a virtual environment on your machine by using the appropiate `venv` command and activating it (depending on your OS), after navigating to the `Touch2KeyBare` directory on your machine before running the `pip install .` command as it is the standard python practice to avoid package conflicts and ensure isolation.**

   ```bash
   git clone https://github.com/Chukxz/Touch2KeyBare.git
   cd Touch2KeyBare
   pip install .
* **Setup:** Run setup (Usually requires an internet connection).

*(Note: Windows requires a system reboot after installation to fully load the driver).*

## Uninstallation
Because Touch2KeyBare installs system-level drivers and kernel rules, **simply running `pip uninstall Touch2KeyBare` is not sufficient.** You should first run the included uninstaller before uninstalling via pip to avoid any issues or residual files.

| Action | Command | Description |
| :--- | :--- | :--- |
| **Standard** | `touch2keybare-uninstall` | Removes drivers/rules/binaries; preserves all user data. |
| **Purge** | `touch2keybare-uninstall --purge` | Removes drivers/rules/binaries **AND** deletes all user data — all saved jsons/images files and the settings toml file. |
| **Purge-All** | `touch2keybare-uninstall --purge-all` | Removes drivers/rules/binaries **AND** deletes all user and diagnostic data — all saved jsons/images files, the settings toml file **AND** the .prof (profiling) file. |
| **Skip Confirmation** | `touch2keybare-uninstall [--yes, -y]` | Skip confirmation prompt. |
| **Skip Reboot** | `touch2keybare-uninstall --no-restart` | Skip reboot prompt (Windows). |

*(Note: Windows requires a system reboot after uninstallation to fully release the driver).*

## Command Line Interface (CLI)
| Command | Description |
| :--- | :--- |
| `touch2keybare` | Launches the main engine. |
| `touch2keybare --profile` | Launches and also runs profiling. | 
| `touch2keybare-adb` | Displays full ADB executable path if found.|
| `touch2keybare-capture` | ADB screen capture. |
| `touch2keybare-plot` | Mapping visualizer. |
| `touch2keybare-preflight` | Diagnostic checks. |
| `touch2keybare-reset` | Resets configuration settings.|
| `touch2keybare-select` | JSON selector.|
| `touch2keybare-setup` | OS configuration wizard. |
| `touch2keybare-uninstall` | Safely removes drivers, rules and binaries. |
| `touch2keybare-uninstall --purge` | Uninstalls and removes jsons/images and the settings toml file. |
| `touch2keybare-uninstall --purge-all` | Purges and removes the .prof (profiling) file. |
| `touch2keybare-wireless` | Forces ADB wireless connection. |

## Contributing
Please use `black` for formatting (recommended), `pytest` for unit testing (optional), and `snakeviz` for visual view of the profile (optional).

Install these via running `pip install .[dev]` during installation.

To support editable mode run `pip install -e .[dev]` (add the `-e` flag) during installation, but note that contributions to the Touch2KeyBare's github repository would likely require permissions from the author(s).

## License
MIT License.
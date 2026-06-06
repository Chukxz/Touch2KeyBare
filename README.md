
# 🎮 Touch2Key

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OS: Windows](https://img.shields.io/badge/os-Windows-blue.svg)](#)
[![OS: Linux](https://img.shields.io/badge/os-Linux-yellow.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Touch2Key** is a high-performance, cross-platform input mapper designed to seamlessly translate touch interactions (via Android/ADB) into zero-latency keyboard and mouse inputs on your PC.

## ✨ Key Features
* **Platform Native Injection:** Windows (Interception driver) and Linux (evdev/uinput).
* **Zero-Latency:** Dedicated isolated background worker processes.
* **Event Coalescing:** Dynamically aggregates high-frequency touch-drags.
* **Anti-Cheat Safe:** Humanized dwell times and randomized click durations.

## 🚀 Installation
1. **Prerequisites:** Python 3.10+ and ADB.
2. **Install:**
   ```bash
   git clone [https://github.com/Chukxz/Touch2Key.git](https://github.com/Chukxz/Touch2Key.git)
   cd Touch2Key
   pip install .

## 🛠️ Command Line Interface (CLI)
| Command | Description |
| :--- | :--- |
| `touch2key` | Launches the main engine. |
| `touch2key-setup` | OS configuration wizard. |
| `touch2key-preflight`| Diagnostic checks. |
| `touch2key-capture` | ADB screen capture. |
| `touch2key-wireless` | Force ADB wireless connection. |
| `touch2key-plot` | Mapping visualizer. |

## 🧠 Architecture Overview
1. **Dispatcher:** Reads raw ADB touch data.
2. **Mapper:** Translates coordinates to strings.
3. **Bridge:** Routes traffic to background workers.
4. **Workers:** Handles hardware-level injection.

## 🤝 Contributing
Please use `black` for formatting and `pytest` for unit testing.

## 📝 License
MIT License.


# StartInfo Build Tool

[简体中文](README.md) | English

A dedicated Nuitka packaging script for StartInfo — one configuration file plus one script, supporting Windows / Linux / macOS.

## Usage

This project uses uv to manage its environment. Run the following from any directory inside the project:

```bash
uv run python tools/build/build.py
```

- Build parameters are set directly in `tools/build/build_config.json` (version number, icon, data directory, etc.), keeping the same workflow as editing the JSON by hand.
- Build artifacts are output to `tools/build/output/`, organized into directories by OS + architecture. The program itself lives in the `main.dist/` subdirectory:

  | Build machine | Artifact directory |
  |---|---|
  | Windows | `output/windows/main.dist/` |
  | Linux | `output/linux/main.dist/` |
  | macOS (Intel) | `output/macOS-intel/StartInfo.app` |
  | macOS (Apple Silicon) | `output/macOS-m/StartInfo.app` |

- **macOS artifacts are .app bundles**, placed directly in the platform directory (no `main.dist` wrapper). The executable and data directory are inside `StartInfo.app/Contents/MacOS/`: because qasync depends on pyobjc/Foundation on macOS, Nuitka requires `--mode=app`, so the script automatically switches to that mode and names the bundle after the product. Windows/Linux builds remain `--standalone` directory form.

## Environment

- The script automatically uses the project's own `.venv` virtual environment (Windows: `.venv\Scripts\python.exe`, Linux/macOS: `.venv/bin/python`) — the environment managed by uv. If `.venv` does not exist, it falls back to the system Python. To specify a different interpreter, set `python_executable` in the config.
- Nuitka must be installed in the current environment: `uv pip install nuitka`.
- **Windows + MSVC**: the full path to `vcvars64.bat` must be filled in under `msvc_path` in `build_config.json` (the script generates a temporary bat file that calls it to activate the compiler environment). To use gcc on Windows instead, change `compiler` to `gcc`.
- Linux/macOS require no MSVC configuration; Nuitka uses gcc/clang by default.

## Configuration Field Reference

| Field | Description |
|---|---|
| `main_script` | Entry script, relative to the project root |
| `file_version` / `product_version` | Version numbers, updated manually before a release |
| `packaging_type` | `directory` (default) for a single directory; `file` for single-file `--onefile` |
| `console_mode` | Windows console mode; `disable` for a windowless GUI |
| `plugin` | Nuitka plugins, e.g. `pyside6`; accepts a string or a list |
| `jobs` | Number of parallel compile jobs |
| `output_dir` | Optional; when empty, output defaults to `tools/build/output/<platform dir>/` (split automatically by build machine OS + architecture) |
| `compiler` | Compiler backend per platform; project standard: `windows: msvc`, `linux: gcc`, `macos: clang` (may also be written as a single string applied to all three platforms) |
| `msvc_path` | Path to vcvars64.bat on Windows |
| `extra_args` | Extra Nuitka arguments shared by all three platforms |
| `windows_extra_args` / `linux_extra_args` / `macos_extra_args` | Arguments appended only for the corresponding platform (icon, exe name, etc.) |

Relative paths (icon, data directory, etc.) are resolved relative to the project root.

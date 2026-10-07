# Running from Source

[简体中文](../development.md) | English

First, clone the repository:

```bash
git clone https://github.com/HuangTao313/StartInfo.git
cd StartInfo
```

Use uv to synchronize project dependencies:

```bash
uv sync
```

## Running

The source code entry points of StartInfo are `main.py` and `settings.py`.

You can run them directly according to your needs.

**Start the main application:**

```bash
uv run main.py
```

**Launch the settings page directly:**

```bash
uv run settings.py
```

The `core` directory contains the core functionality modules of StartInfo. It is an internal library developed specifically for this project and is not intended to run as an independent application.

Files inside the `core` directory are called indirectly by entry points such as `main.py` and `settings.py`.

**Running files inside the `core` directory directly is neither required nor recommended.**

## `core` Directory Structure

| Module | Responsibility |
| --- | --- |
| `core/base_lib.py` | Foundation: JSON I/O, application constants (title / version / startup shortcut path), runtime environment and network detection, single-instance lock and restart |
| `core/paths.py` | The single source of truth for the `data` directory and file paths |
| `core/logger.py` | Logging initialization (importing `core` registers the file log) |
| `core/config.py` | Config item definitions and the global `cfg` |
| `core/templates.py` | Template scanning, importing and activation |
| `core/startup.py` | Startup entry management |
| `core/updater.py` | Update checking, download and installation |
| `core/widgets/` | Widget system: `framework.py` (framework) + `widgets.py` (built-in widgets) |
| `core/ui/` | UI layer: `app.py` (application and theme), `dialogs.py` (dialogs), `ui_widgets.py` (controls), `settings_pages/` (settings pages) |

> `base_lib`, `paths`, `logger` and `templates` form the bottom layer:
> `base_lib → logger → config → templates → paths` is a one-way dependency chain.
> `templates` must remain a leaf (because `config` imports it at module top level), so do not merge it into other modules.

**Import convention:** outside the package, always use `from core.<module> import ...`, or use the
facade packages `from core.ui import ...` / `from core.widgets import ...`; modules inside the `core`
package use relative imports between each other.

```python
from core.base_lib import TITLE, VERSION, SingleInstance    # foundation
from core.config import cfg, qconfig                        # configuration
from core.widgets import WeatherWidget                      # widgets (single facade for framework + built-ins)
from core.ui import app_manager, dialog, BasicSettingsPage  # UI (dialogs / controls / settings pages)
```

## `data` Directory Structure

The `data` directory is organized by **who manages its files**, not by file format:

| Path | Contents | How the installer handles it |
| --- | --- | --- |
| `data/assets/` | Read-only resources packaged with the application: `api.json`, `emoji.json`, `current_version.json`, `qweather.db`, `xiaomi_weather.db`, `settings.ico`, `startinfo.ico`, plus the language files under `i18n/` | Overwrite directly |
| `data/config.json` | User configuration | **Must not overwrite** |
| `data/templates/` | Built-in templates + user-imported / user-edited templates | **Must not overwrite existing files** |
| `data/cache/` | Generated at runtime, safe to delete: `widgets_cache.db`, `version.json`, update download cache | No need to ship |
| `data/logs/` | Runtime logs | No need to ship |


# Command Line Arguments

StartInfo supports the following command-line arguments, which can be used for debugging, troubleshooting, and specific use cases.

Usage:

**Running from source:**

```bash
uv run main.py <argument>
```

**Compiled version:**

```powershell
StartInfo.exe <argument>
```

The following arguments work in both modes.

---

## `--settings`

Skip the main application flow and directly open the settings page.

This option can be used when the main application cannot start normally but the settings page still works.

Example:

```powershell
StartInfo.exe --settings
```

---

## `--debug`

Temporarily forces the log level of the current launch to `DEBUG`.

This option is intended for debugging and troubleshooting.

This parameter **does not modify the saved log level in settings**.

Without `--debug`, StartInfo will continue using the log level configured in the settings page.

Example:

```powershell
StartInfo.exe --debug
```

The current launch will use the `DEBUG` log level. The next normal launch will still use the previously configured log level.

`--debug` is not an entry-point argument and can be combined with other arguments.

Example:

```powershell
StartInfo.exe --settings --debug
```

## `--startup`

Used to indicate whether StartInfo was launched by the **Windows startup entry**.

This parameter is mainly added automatically by StartInfo's startup feature and usually does not need to be manually specified by users.

When the application starts, the startup count component checks whether the `--startup` parameter exists to determine whether the current launch was triggered by Windows startup, and records the corresponding statistics.

The actual startup entry format is similar to:

```powershell
StartInfo.exe --startup
```

> `--startup` is an internal-use parameter. In most cases, users do not need to manually add or modify it.


---

## Combining Arguments

StartInfo supports passing multiple command-line arguments at the same time.

Currently supported arguments:

```
--settings
--debug
--startup
```

Example:

```powershell
StartInfo.exe --settings --debug --startup
```

Argument handling logic:

- `--settings` is an entry-point argument and takes priority by opening the settings page.
- `--debug` only affects the log level of the current launch and can be combined with other arguments.
- `--startup` is handled independently by the startup count component and can coexist with other arguments.

Normal users usually do not need to manually combine multiple arguments.


---

## Template Files

StartInfo supports receiving a Jinja2 template file path as a command-line argument.

You can drag a template file directly onto the StartInfo executable.

Example:

```powershell
StartInfo.exe D:\example.j2
```

After startup, the application will detect the provided template file and ask whether to import and enable the template.

This feature is mainly designed to make it easier for users to quickly add custom templates.

If a template path and other command-line arguments are provided at the same time:

```powershell
StartInfo.exe --settings D:\example.j2
```

`--settings` takes priority. The application will directly open the settings page and will not start the template import process.


---

# Logging and Debugging

StartInfo uses Loguru for runtime logging.

The default log level is `WARNING`, so normal operation will not generate a large amount of regular runtime information.

Log files are kept for **3 days** by default, and expired logs are automatically cleaned up.

If you encounter unexpected behavior, launch StartInfo with the `--debug` parameter to enable more detailed DEBUG-level logging.

When reporting issues or submitting bug reports, please attach the relevant log files whenever possible.
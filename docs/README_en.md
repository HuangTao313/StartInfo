<div align="center">

<img src="images/startinfo.png" alt="StartInfo Logo" width="18%">

<h1>StartInfo</h1>

<p>A desktop information dashboard built with PySide6 and QFluentWidgets.</p>

[![Stars](https://img.shields.io/github/stars/HuangTao313/StartInfo?style=for-the-badge&color=orange&label=Stars)](https://github.com/HuangTao313/StartInfo)
[![License](https://img.shields.io/github/license/HuangTao313/StartInfo?style=for-the-badge&color=darkgreen&label=License)](LICENSE)
[![Downloads](https://img.shields.io/github/downloads/HuangTao313/StartInfo/total.svg?style=for-the-badge&color=green&label=Downloads)](https://github.com/HuangTao313/StartInfo/releases)
[![Latest Release](https://img.shields.io/github/v/release/HuangTao313/StartInfo?style=for-the-badge&label=Latest%20Release)](https://github.com/HuangTao313/StartInfo/releases)

</div>

<p align="center">
<a href="../README.md">简体中文</a> | English
</p>

> [!WARNING]
> **Low-frequency Maintenance Notice**
>
> Due to changes in the author's academic schedule, the time available for maintaining this project will be limited. Therefore, this project will enter a low-frequency maintenance state in the future.
>
> The project will continue to be maintained, but new features and version releases may mainly be developed during longer holidays.
>
> If you encounter bugs or have suggestions, feel free to submit an Issue. If you are willing and able to contribute, Pull Requests are also welcome.

> [!NOTE]
> **Project Scope**
>
> StartInfo is currently designed primarily for users in China.
> The application is not fully internationalized yet, and some features rely on China-based APIs and services.
>
> English documentation is provided for accessibility, but the user interface and some services may still be Chinese-oriented.

# Features

* Weather and air quality information
* Date, time, lunar calendar, 24 solar terms, and holidays
* On This Day in History
* Daily Luck
* Minecraft server information
* More features...

# Screenshots

<table>
  <tr>
    <td style="text-align: center;">Main Window(Dark Mode)</td>
    <td style="text-align: center;">Settings Window(Dark Mode)</td>
  </tr>
  <tr>
    <td><img src="docs/images/main-window.png" width="100%" /></td>
    <td><img src="docs/images/settings.png" width="100%" /></td>
  </tr>
</table>

# Download

Currently, Windows installer and portable versions are provided.

## Windows

**System Requirements:**

- Windows 10 or later
- 64-bit (x86_64) system only

**Version Types:**

- **Installer Version**: Install StartInfo using the installer. Recommended for most users.
- **Portable Version**: No installation required. Extract and run directly. Suitable for users who want to place the application in a specific directory or use it on portable devices.

Download the latest version:

- Installer: [StartInfo-win-x86_64-Setup.exe](https://github.com/HuangTao313/StartInfo/releases/latest/download/StartInfo-win-x86_64-Setup.exe)
- Portable: [StartInfo-win-x86_64-Portable.zip](https://github.com/HuangTao313/StartInfo/releases/latest/download/StartInfo-win-x86_64-Portable.zip)

> Download links always point to the corresponding files in the latest GitHub Release.
>
> macOS-related features have been adapted, but macOS builds are currently not provided.

# Running from Source

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

# Update Mechanism

StartInfo supports multiple update sources:

* GitHub (default)
* GitHub mirror

To avoid sending update requests too frequently, StartInfo locally caches version check results.

The default cache validity period is **10 minutes**. During the cache validity period, checking for updates again will not send another request to the server.

Therefore, if StartInfo has already checked for updates, users may need to wait until the cache expires before a newly released version can be detected.

This design reduces the load on update servers and prevents excessive update requests.


# QWeather Configuration

If you use QWeather as the weather data source, you need to configure your own API Host and API Key in the settings.

## Obtaining API Host and API Key

1. Visit the [QWeather Developer Platform](https://dev.qweather.com/) and register an account.
2. Create a project and obtain an API Key.
3. View your API Host in the developer console settings.

StartInfo requires both API Host and API Key to correctly request data from the QWeather API.


## Configuring in StartInfo

Open the StartInfo settings page and enter the following information in the weather-related settings:

- **API Host**: The Host provided by the QWeather developer console.
- **API Key**: The API Key generated by the QWeather developer console.

The API Host format is similar to:

```text
xxxxxxxx.re.qweatherapi.com
```

When entering the API Host, **do not include `https://` or `http://`**. StartInfo will automatically handle the request URL.

Enter the API Key exactly as provided by the developer console. Do not add quotation marks or any additional characters.

After configuration is complete, switch the weather data source to QWeather.

> Both the QWeather API Host and API Key are associated with your developer account. Please use your own API Host and API Key instead of using someone else's configuration.

If you do not want to use QWeather temporarily, you can switch to the Xiaomi Weather data source.


# Security Notice

Some API Keys appeared in the project's historical commits. These keys have now been fully reset and are no longer valid.

When using related APIs, please configure your own API Keys.

# AI-Assisted Development

AI-assisted programming (Vibe Coding) was used during the development of this project, including code writing, refactoring, debugging, and problem analysis.

The overall project design, feature planning, code review, and final maintenance are still handled by the author.

# Documentation

- [Template Customization Guide](docs/template-customization.md)
- [Widget Development Guide](docs/widget-development.md)

> StartInfo does not currently support a plugin system. All existing Widgets are built-in components and are located in [core/widgets.py](core/widgets.py).


# Dependencies

StartInfo mainly uses the following projects:

- [Python](https://www.python.org/)
- [PySide6](https://doc.qt.io/qtforpython-6/gettingstarted.html#getting-started)
- [PySide6-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets/tree/PySide6)
- [Loguru](https://github.com/Delgan/loguru)

## Acknowledgements

Thanks to the following projects and resources:

- [Class-Widgets](https://github.com/Class-Widgets/Class-Widgets) — Some design ideas were inspired by this project.
- [QWidgetSekai](https://github.com/Aegisir/QWidgetSekai) — The switch button in the settings page was ported from its [switch_button.py](https://github.com/Aegisir/QWidgetSekai/blob/main/pyqt_project/SwitchButton/src/switch_button.py). The original implementation was based on PyQt5 and has been migrated to PySide6.

## APIs and References

- [XiaomiWeather API](https://github.com/huanghui0906/API/blob/master/XiaomiWeather.md) — Reference documentation for the Xiaomi Weather API.


## Icon Resources

- [AppIcon Forge](https://github.com/zhangyu1818/appicon-forge) — Used for generating application icons.
- [Material Design Icons](https://github.com/google/material-design-icons) — Source of icons used in the main application.
- [Fluent UI System Icons](https://github.com/microsoft/fluentui-system-icons) — Source of icons used in the settings window.


## Contributors

Thanks to everyone who contributed to the development, testing, and feedback of StartInfo.

<p>
  <a href="https://github.com/HuangTao313">
    <img src="https://github.com/HuangTao313.png" width="60px" alt="HuangTao" style="border-radius: 50%;">
  </a>
  <a href="https://github.com/Yuuka-doesnt-know">
    <img src="https://github.com/Yuuka-doesnt-know.png" width="60px" alt="Yuuka-doesnt-know" style="border-radius: 50%;">
  </a>
</p>


# License

This project is open source under the GNU GPLv3.0 License.

For the full license text, please refer to the [LICENSE](LICENSE) file in the project root directory.

#

Copyright © 2023-2026 HuangTao313. Licensed under GPL-3.0.
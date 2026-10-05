# 从源码运行

首先克隆项目：

```bash
git clone https://github.com/HuangTao313/StartInfo.git
cd StartInfo
```

使用 uv 同步项目依赖：

```bash
uv sync
```

## 运行

StartInfo 的源码入口为 `main.py` 和 `settings.py`，可以根据需要直接运行。

**启动主程序：**

```bash
uv run main.py
```

**直接启动设置页面：**

```bash
uv run settings.py
```

`core` 目录为 StartInfo 的核心功能模块，是项目内部自制的核心库，不作为独立程序运行。

`core` 中的文件由 `main.py`、`settings.py` 等入口间接调用，**无需也不建议直接运行 `core` 目录中的文件**。

## core 目录结构

| 模块 | 职责 |
| --- | --- |
| `core/base_lib.py` | 底座：JSON 读写、应用常量（标题 / 版本 / 启动项路径）、运行环境与网络检测、单实例锁与程序重启 |
| `core/paths.py` | data 目录与文件路径的唯一定义处 |
| `core/logger.py` | 日志初始化（导入 `core` 即完成文件日志注册） |
| `core/config.py` | 配置项定义与全局 `cfg` |
| `core/templates.py` | 模板扫描、导入与启用 |
| `core/startup.py` | 开机启动项管理 |
| `core/updater.py` | 检查更新与下载安装 |
| `core/widgets/` | 组件系统：`framework.py` 框架 + `builtin.py` 内置组件 |
| `core/ui/` | 界面层：`app.py` 应用与主题、`dialogs.py` 弹窗、`ui_widgets.py` 控件、`settings_pages/` 设置页 |

> `base_lib`、`paths`、`logger`、`templates` 构成底层：`base_lib → logger → config → templates → paths`
> 是一条单向依赖链。`templates` 必须保持为叶子（`config` 在顶层导入它），因此不要把它并入其他模块。

**导入约定：** 包外统一使用 `from core.<模块> import ...`，或使用门面包
`from core.ui import ...` / `from core.widgets import ...`；`core` 包内部模块之间使用相对导入。

```python
from core.base_lib import TITLE, VERSION, SingleInstance   # 底座
from core.config import cfg, qconfig                       # 配置
from core.widgets import WeatherWidget                     # 组件（框架与内置组件统一出口）
from core.ui import app_manager, dialog, BasicSettingsPage  # 界面（弹窗 / 控件 / 设置页统一出口）
```

## data 目录结构

`data` 目录按「谁负责管这些文件」划分：

| 路径 | 内容 | 安装包如何处理 |
| --- | --- | --- |
| `data/assets/` | 随程序打包分发的只读资源：`api.json`、`emoji.json`、`current_version.json`、`qweather.db`、`xiaomi_weather.db`、`settings.ico`、`startinfo.ico`，以及 `i18n/` 下的多语言文件 | 直接覆盖 |
| `data/config.json` | 用户配置 | **不得覆盖** |
| `data/templates/` | 内置模板 + 用户导入/编辑的模板 | **不得覆盖已存在文件** |
| `data/cache/` | 运行时生成、可随时删除：`widgets_cache.db`、`version.json`、更新下载缓存 | 不需要分发 |
| `data/logs/` | 运行时生成的日志 | 不需要分发 |


# 启动参数

StartInfo 支持以下启动参数，可用于调试、故障排查以及特定场景下的功能调用。

启动参数的使用方式如下：

**源码运行：**

```bash
uv run main.py 参数
```

**已编译版本：**

```powershell
StartInfo.exe 参数
```

以下参数在两种运行方式下均有效。

---

## `--settings`

跳过主程序流程，直接启动设置页面。

当主程序无法正常启动，但设置页面仍可以正常运行时，可以使用此参数进入设置。

示例：

```powershell
StartInfo.exe --settings
```

---

## `--debug`

临时将本次启动的日志等级强制设置为 `DEBUG`，用于调试和问题排查。

该参数**不会修改设置中保存的日志等级**。不使用 `--debug` 启动时，程序仍会使用设置页面中保存的日志等级。

示例：

```powershell
StartInfo.exe --debug
```

本次启动会使用 `DEBUG` 日志等级；下次正常启动时，仍然使用设置页面中原本配置的日志等级。

`--debug` 不属于启动入口参数，可以与其他参数同时使用。

例如：

```powershell
StartInfo.exe --settings --debug
```

---

## `--startup`

用于标识 StartInfo 是否由**开机自启动项**启动。

该参数主要由 StartInfo 的开机启动功能自动添加，通常不需要用户手动指定。

程序启动时，开机次数组件会根据是否存在 `--startup` 参数判断当前启动是否属于开机自启动，并进行对应统计。

开机启动项实际使用形式类似：

```powershell
StartInfo.exe --startup
```

> `--startup` 属于内部用途参数，一般情况下无需手动添加或修改。

---

## 参数组合

StartInfo 支持同时传入多个启动参数。

当前支持的参数包括：

```
--settings
--debug
--startup
```

例如：

```powershell
StartInfo.exe --settings --debug --startup
```

参数处理逻辑如下：

- `--settings` 属于启动入口参数，会优先进入设置页面。
- `--debug` 只影响本次启动的日志等级，可以与其他参数同时使用。
- `--startup` 由开机次数组件独立处理，可以与其他参数同时存在。

普通用户通常无需手动组合多个参数。

---

## 模板文件

StartInfo 支持接收 Jinja2 模板文件路径作为启动参数。

可以将模板文件直接拖拽到 StartInfo 的程序图标上。

例如：

```powershell
StartInfo.exe D:\example.j2
```

程序启动后会识别传入的模板文件，并询问是否导入和启用该模板。

该功能主要用于方便用户快速添加自定义模板。

如果同时传入模板路径和其他启动参数：

```powershell
StartInfo.exe --settings D:\example.j2
```

则 `--settings` 优先处理，程序会直接进入设置页面，不会执行模板导入流程。

---

# 日志与调试

StartInfo 使用 Loguru 记录运行日志。

默认日志等级为 `WARNING`，因此正常运行时不会记录大量普通运行信息。

日志文件默认保留 **3 天**，过期日志会自动清理。

如果遇到程序运行异常，可以使用 `--debug` 参数启动程序，以记录更详细的 DEBUG 级别日志，并在反馈问题或提交 Issue 时附上相关日志。
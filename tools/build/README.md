# StartInfo 构建工具

StartInfo 专用的 Nuitka 打包脚本,一份配置 + 一个脚本,支持 Windows / Linux / macOS。

## 使用

本项目使用 uv 管理环境,在项目任意目录下执行:

```bash
uv run python tools/build/build.py
```

- 构建参数直接改 `tools/build/build_config.json`(版本号、图标、数据目录等),与原来填 JSON 的习惯一致。
- 产物输出到 `tools/build/output/` 下按系统+架构划分的目录中,程序在其中的 `main.dist/` 子目录里:

  | 构建机器 | 产物目录 |
  |---|---|
  | Windows | `output/windows/main.dist/` |
  | Linux | `output/linux/main.dist/` |
  | macOS (Intel) | `output/macOS-intel/StartInfo.app` |
  | macOS (Apple Silicon) | `output/macOS-m/StartInfo.app` |

- **macOS 产物为 .app bundle**,直接位于平台目录下(无 `main.dist` 包装层),可执行文件和数据目录在 `StartInfo.app/Contents/MacOS/` 里:因 qasync 在 macOS 依赖 pyobjc/Foundation,Nuitka 强制要求 `--mode=app`,脚本会自动改用该模式并以产品名命名 bundle;Windows/Linux 仍为 `--standalone` 目录形态。

## 环境

- 脚本自动使用项目自带的 `.venv` 虚拟环境(Windows: `.venv\Scripts\python.exe`,Linux/macOS: `.venv/bin/python`),即 `uv` 管理的环境;没有 `.venv` 时回退到系统 Python。如需指定其他解释器,在配置里填 `python_executable`。
- 需要在当前环境安装 nuitka:`uv pip install nuitka`。
- **Windows + MSVC**:需要在 `build_config.json` 的 `msvc_path` 里填写 `vcvars64.bat` 的完整路径(脚本会生成临时 bat 调用它激活编译环境)。Windows 上改用 gcc 时把 `compiler` 改为 `gcc`。
- Linux/macOS 无需 msvc 配置,Nuitka 默认使用 gcc/clang。

## 配置字段速查

| 字段 | 说明 |
|---|---|
| `main_script` | 入口脚本,相对项目根目录 |
| `file_version` / `product_version` | 版本号,发布前手动改 |
| `packaging_type` | `directory`(默认)单目录;`file` 单文件 `--onefile` |
| `console_mode` | Windows 控制台模式,`disable` 为无窗口 GUI |
| `plugin` | Nuitka 插件,如 `pyside6`,支持字符串或列表 |
| `jobs` | 编译并行数 |
| `output_dir` | 可选,不填时默认输出到 `tools/build/output/<平台目录>/`(按构建机器系统+架构自动划分) |
| `compiler` | 按平台的编译后端,项目标准:`windows: msvc`、`linux: gcc`、`macos: clang`(也可写成一个字符串统一三平台) |
| `msvc_path` | Windows 下 vcvars64.bat 路径 |
| `extra_args` | 三平台公共的 Nuitka 附加参数 |
| `windows_extra_args` / `linux_extra_args` / `macos_extra_args` | 仅对应平台追加的参数(图标、exe 名等) |

相对路径(图标、数据目录等)均相对项目根目录解析。

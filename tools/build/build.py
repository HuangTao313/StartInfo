# -*- coding: utf-8 -*-
"""StartInfo 专用 Nuitka 构建脚本(跨平台: Windows / Linux / macOS)

本项目使用 uv 管理环境,用法(在项目任意目录下均可):
    uv run python tools/build/build.py

配置:
    同目录下的 build_config.json,版本号等参数直接改 JSON。
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
CONFIG_PATH = SCRIPT_DIR / "build_config.json"

IS_WINDOWS = sys.platform == "win32"
PLATFORM_KEY = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")


def resolve_compiler(config):
    """编译后端: compiler 支持 dict(按平台)或 str(全平台统一)。

    平台标准: windows=msvc, linux=gcc, macos=clang(均为系统原生编译器)。
    """
    defaults = {"windows": "msvc", "linux": "gcc", "macos": "clang"}
    compiler = config.get("compiler", defaults)
    if isinstance(compiler, dict):
        compiler = compiler.get(PLATFORM_KEY, defaults[PLATFORM_KEY])
    return str(compiler).lower()


def load_config():
    if not CONFIG_PATH.exists():
        sys.exit(f"[ERROR] 未找到配置文件: {CONFIG_PATH}")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def resolve_python(config):
    """确定 Python 解释器: 配置指定 > 项目 .venv > 系统 python。"""
    override = config.get("python_executable")
    if isinstance(override, dict):
        override = override.get(PLATFORM_KEY)
    if override:
        exe = Path(override)
        if not exe.is_absolute():
            exe = PROJECT_ROOT / exe
        return str(exe)

    venv_python = PROJECT_ROOT / ".venv" / (
        "Scripts/python.exe" if IS_WINDOWS else "bin/python"
    )
    if venv_python.exists():
        print(f"[INFO] 使用项目虚拟环境: {venv_python}")
        return str(venv_python)

    fallback = "python" if IS_WINDOWS else "python3"
    print(f"[WARN] 未找到项目 .venv,回退到系统 {fallback}")
    return fallback


def build_env(python_path):
    """把解释器所在目录放到 PATH 最前面。"""
    env = os.environ.copy()
    env["PATH"] = str(Path(python_path).resolve().parent) + os.pathsep + env.get("PATH", "")
    return env


def check_nuitka(python_path, env):
    try:
        subprocess.run(
            [python_path, "-c", "import nuitka"],
            env=env, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit(f"[ERROR] 当前环境没有安装 nuitka,请先执行: uv pip install nuitka")


def _platform_extra_args(config):
    extra = list(config.get("extra_args", []))
    extra.extend(config.get(f"{PLATFORM_KEY}_extra_args", []))
    return extra


def build_nuitka_command(config, python_path):
    cmd = [python_path, "-m", "nuitka", "--standalone"]

    # console_mode 是 Windows 专属选项
    if IS_WINDOWS and config.get("console_mode"):
        cmd.append(f"--windows-console-mode={config['console_mode']}")

    if config.get("packaging_type") == "file":
        cmd.append("--onefile")

    if config.get("output_dir"):
        cmd.append(f"--output-dir={config['output_dir']}")

    cmd.extend([
        f"--main={config['main_script']}",
        f"--company-name={config['company_name']}",
        f"--product-name={config['product_name']}",
        f"--file-version={config['file_version']}",
        f"--product-version={config['product_version']}",
    ])

    compiler = resolve_compiler(config)
    if IS_WINDOWS:
        cmd.append("--mingw64" if compiler in ("gcc", "mingw", "mingw64") else "--msvc=latest")
    elif compiler == "clang":
        # Linux/macOS 上 gcc/clang 是系统默认,gcc 无需传参;clang 显式指定
        cmd.append("--clang")

    cmd.extend(["--lto=yes", f"--jobs={config.get('jobs', 16)}", "--show-progress"])

    plugin = config.get("plugin")
    if plugin:
        plugins = plugin if isinstance(plugin, list) else [plugin]
        cmd.extend(f"--enable-plugin={p}" for p in plugins)

    cmd.extend(_platform_extra_args(config))
    return cmd


def _quote_batch_arg(arg):
    s = str(arg)
    if " " in s and not s.startswith('"'):
        return f'"{s}"'
    return s


def run_msvc(cmd, config, env):
    """Windows + MSVC: 通过临时 bat 先 call vcvars64.bat 激活环境再编译。"""
    msvc_vcvars = config.get("msvc_path")
    if not msvc_vcvars:
        sys.exit("[ERROR] Windows 下使用 MSVC 需要在 build_config.json 里填写 msvc_path(vcvars64.bat 路径)")
    if not Path(msvc_vcvars).exists():
        sys.exit(f"[ERROR] MSVC 激活脚本不存在: {msvc_vcvars},请修改 build_config.json 的 msvc_path")

    pydir = str(Path(env["PATH"].split(os.pathsep)[0]))
    cmd_str = " ".join(_quote_batch_arg(a) for a in cmd)
    batch_content = "\r\n".join([
        "@echo off",
        f'set "PATH={pydir};%PATH%"',
        "echo [INFO] 正在设置 MSVC 编译环境...",
        f'call "{msvc_vcvars}"',
        "if %errorlevel% neq 0 (",
        "    echo [ERROR] MSVC 编译环境加载失败!",
        "    exit /b 1",
        ")",
        "echo [INFO] MSVC 环境就绪,开始 Nuitka 打包...",
        cmd_str,
    ])

    batch_path = Path(tempfile.gettempdir()) / f"_startinfo_build_{os.getpid()}.bat"
    try:
        batch_path.write_text(batch_content, encoding="gbk")
        print(f"[INFO] 执行 MSVC 编译包装脚本: {batch_path}")
        subprocess.run(["cmd", "/c", str(batch_path)], cwd=PROJECT_ROOT, check=True, env=env)
    except subprocess.CalledProcessError as e:
        sys.exit(f"[ERROR] 打包失败: {e}")
    finally:
        batch_path.unlink(missing_ok=True)


def run_build(cmd, config, env):
    print("Nuitka 命令:", " ".join(cmd))
    if IS_WINDOWS and resolve_compiler(config) not in ("gcc", "mingw", "mingw64"):
        run_msvc(cmd, config, env)
        return
    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True, env=env)
    except subprocess.CalledProcessError as e:
        sys.exit(f"[ERROR] 打包失败: {e}")


def main():
    config = load_config()
    python_path = resolve_python(config)
    env = build_env(python_path)
    check_nuitka(python_path, env)

    print(f"[INFO] 平台: {PLATFORM_KEY} | 编译器: {resolve_compiler(config)} | 输出目录: {config.get('output_dir', '当前目录')}")
    cmd = build_nuitka_command(config, python_path)
    run_build(cmd, config, env)
    print("[OK] Nuitka 打包成功完成!")


if __name__ == "__main__":
    main()

"""开机启动项管理（Windows 快捷方式 / macOS LaunchAgent / Linux XDG Autostart）。"""
import os
import plistlib
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from .base_lib import SHORTCUT_FILE_PATH, system
from .logger import log
from .paths import EXE_FILE_PATH, MAIN_PATH, WIN_STARTUP_FOLDER_PATH

# macOS 使用 LaunchAgent 实现当前用户登录后自动启动。
MACOS_LAUNCH_AGENT_LABEL = 'com.startinfo.launcher'
MACOS_LAUNCH_AGENTS_PATH = Path.home() / 'Library' / 'LaunchAgents'
MACOS_SHORTCUT_PATH = MACOS_LAUNCH_AGENTS_PATH / f'{MACOS_LAUNCH_AGENT_LABEL}.plist'

# Linux 使用 XDG Autostart 实现当前用户登录桌面后自动启动。
# Ubuntu/GNOME/KDE/XFCE 等主流桌面环境均支持该规范。
LINUX_AUTOSTART_FILE_NAME = 'com.startinfo.launcher.desktop'


def _get_xdg_config_home() -> Path:
    """获取 XDG 配置目录，优先使用 XDG_CONFIG_HOME。"""
    config_home = os.environ.get('XDG_CONFIG_HOME')
    if config_home:
        path = Path(config_home).expanduser()
        if path.is_absolute():
            return path
    return Path.home() / '.config'


LINUX_CONFIG_HOME = _get_xdg_config_home()
LINUX_AUTOSTART_FOLDER_PATH = LINUX_CONFIG_HOME / 'autostart'
LINUX_AUTOSTART_FILE_PATH = LINUX_AUTOSTART_FOLDER_PATH / LINUX_AUTOSTART_FILE_NAME


def _get_program_arguments() -> list[str]:
    """
    获取开机自启的启动命令（macOS / Linux 共用）。

    打包后直接启动当前可执行文件；开发环境则使用当前 Python 解释器
    启动项目根目录下的 main.py。这里使用 absolute() 而不是 resolve()，
    避免虚拟环境中的 python 被解析成系统解释器而丢失依赖。
    --startup 用于区分开机自启和手动启动。
    """
    if getattr(sys, 'frozen', False):
        return [str(Path(sys.executable).absolute()), '--startup']

    return [
        str(Path(sys.executable).absolute()),
        str((MAIN_PATH / 'main.py').absolute()),
        '--startup',
    ]


def _quote_linux_exec_argument(argument: str) -> str:
    """按 Desktop Entry 规范对 Exec 参数进行双引号转义。"""
    escaped = (
        argument
        .replace('\\', '\\\\')
        .replace('"', '\\"')
        .replace('%', '%%')
    )
    return f'"{escaped}"'


def _get_linux_desktop_entry_text() -> str:
    """生成 StartInfo 的 .desktop 文件文本内容。"""
    exec_line = ' '.join(
        _quote_linux_exec_argument(argument)
        for argument in _get_program_arguments()
    )
    desktop_entry_data = {
        'Type': 'Application',
        'Version': '1.0',
        'Name': 'StartInfo',
        'Comment': 'StartInfo startup launcher',
        'Exec': exec_line,
        'Path': str(MAIN_PATH.absolute()),
        'Terminal': 'false',
        'StartupNotify': 'false',
        'Hidden': 'false',
        'X-GNOME-Autostart-enabled': 'true',
    }
    lines = ['[Desktop Entry]']
    lines.extend(f'{key}={value}' for key, value in desktop_entry_data.items())
    return '\n'.join(lines) + '\n'


def _read_linux_desktop_entry(file_path: Path) -> dict[str, str]:
    """解析 .desktop 文件中的 [Desktop Entry] 配置项。"""
    desktop_entry_data: dict[str, str] = {}
    in_desktop_entry_section = False

    with file_path.open('r', encoding='utf-8') as file:
        for raw_line in file:
            line = raw_line.strip()
            if line.startswith('[') and line.endswith(']'):
                in_desktop_entry_section = (line == '[Desktop Entry]')
                continue

            if not in_desktop_entry_section or not line or line.startswith('#'):
                continue

            key, separator, value = line.partition('=')
            if separator:
                desktop_entry_data[key.strip()] = value.strip()

    return desktop_entry_data


# ---------------------------------------------------------------------------
# Windows：启动文件夹快捷方式
# ---------------------------------------------------------------------------

def _windows_exists() -> bool:
    if not WIN_STARTUP_FOLDER_PATH.exists():
        log.info(f'快捷方式不存在: {SHORTCUT_FILE_PATH}')
        return False

    from win32com.client import Dispatch
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(str(SHORTCUT_FILE_PATH))
    if shortcut.Targetpath == str(EXE_FILE_PATH):
        log.info(f'快捷方式已存在，且目标路径正确: {SHORTCUT_FILE_PATH}')
        return True

    log.info(f'快捷方式已存在，但目标路径不匹配: {SHORTCUT_FILE_PATH}')
    return False


def _windows_create() -> bool:
    from win32com.client import Dispatch
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(str(SHORTCUT_FILE_PATH))
    shortcut.Targetpath = str(EXE_FILE_PATH)
    shortcut.Arguments = '--startup'
    shortcut.WorkingDirectory = str(MAIN_PATH)
    shortcut.save()
    log.info(f'快捷方式已创建并移动到启动文件夹: {SHORTCUT_FILE_PATH}')
    return True


def _windows_remove() -> bool:
    if SHORTCUT_FILE_PATH.exists():
        SHORTCUT_FILE_PATH.unlink(missing_ok=True)
        log.info(f'快捷方式已删除: {SHORTCUT_FILE_PATH}')
    else:
        log.info(f'快捷方式不存在: {SHORTCUT_FILE_PATH}')
    return True


# ---------------------------------------------------------------------------
# macOS：LaunchAgent
# ---------------------------------------------------------------------------

def _macos_exists() -> bool:
    try:
        if not MACOS_SHORTCUT_PATH.is_file():
            log.info(f'macOS 开机启动项不存在: {MACOS_SHORTCUT_PATH}')
            return False

        with MACOS_SHORTCUT_PATH.open('rb') as file:
            launch_agent_data = plistlib.load(file)

        expected_data = {
            'Label': MACOS_LAUNCH_AGENT_LABEL,
            'ProgramArguments': _get_program_arguments(),
            'WorkingDirectory': str(MAIN_PATH.resolve()),
            'RunAtLoad': True,
        }
        configuration_is_correct = all(
            launch_agent_data.get(key) == value
            for key, value in expected_data.items()
        )

        if configuration_is_correct:
            log.info(
                f'macOS 开机启动项已存在，且配置正确: '
                f'{MACOS_SHORTCUT_PATH}'
            )
            return True

        log.info(
            f'macOS 开机启动项已存在，但配置不匹配: '
            f'{MACOS_SHORTCUT_PATH}'
        )
        return False

    except (OSError, plistlib.InvalidFileException, ValueError, TypeError) as e:
        log.error(f'检查 macOS 开机启动项失败: {e}')
        return False


def _macos_create() -> bool:
    MACOS_LAUNCH_AGENTS_PATH.mkdir(parents=True, exist_ok=True)
    launch_agent_data = {
        'Label': MACOS_LAUNCH_AGENT_LABEL,
        'ProgramArguments': _get_program_arguments(),
        'WorkingDirectory': str(MAIN_PATH.resolve()),
        'RunAtLoad': True,
        'KeepAlive': False,
        'ProcessType': 'Interactive',
        'LimitLoadToSessionType': 'Aqua',
    }

    # 先写入临时文件再替换，避免程序中断时留下不完整的 plist。
    temporary_path = MACOS_SHORTCUT_PATH.with_suffix('.plist.tmp')
    with temporary_path.open('wb') as file:
        plistlib.dump(launch_agent_data, file, sort_keys=False)
    temporary_path.replace(MACOS_SHORTCUT_PATH)

    log.info(f'macOS 开机启动项已创建: {MACOS_SHORTCUT_PATH}')
    return True


def _macos_remove() -> bool:
    if not MACOS_SHORTCUT_PATH.exists():
        log.info(f'macOS 开机启动项不存在: {MACOS_SHORTCUT_PATH}')
        return True

    # 如果 LaunchAgent 已在当前登录会话中加载，先尝试卸载。
    # 未加载时 launchctl 会返回非零状态，不影响删除 plist。
    launchctl_result = subprocess.run(
        [
            'launchctl',
            'bootout',
            f'gui/{os.getuid()}',
            str(MACOS_SHORTCUT_PATH),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if launchctl_result.returncode != 0:
        log.debug(
            'macOS LaunchAgent 当前未加载或无需卸载: '
            f'{launchctl_result.stderr.strip()}'
        )

    MACOS_SHORTCUT_PATH.unlink(missing_ok=True)
    log.info(f'macOS 开机启动项已删除: {MACOS_SHORTCUT_PATH}')
    return True


# ---------------------------------------------------------------------------
# Linux：XDG Autostart
# ---------------------------------------------------------------------------

def _linux_exists() -> bool:
    try:
        if not LINUX_AUTOSTART_FILE_PATH.is_file():
            log.info(f'Linux 开机启动项不存在: {LINUX_AUTOSTART_FILE_PATH}')
            return False

        desktop_entry_data = _read_linux_desktop_entry(LINUX_AUTOSTART_FILE_PATH)
        exec_line = ' '.join(
            _quote_linux_exec_argument(argument)
            for argument in _get_program_arguments()
        )
        expected_data = {
            'Type': 'Application',
            'Exec': exec_line,
            'Path': str(MAIN_PATH.absolute()),
            'Terminal': 'false',
            'Hidden': 'false',
            'X-GNOME-Autostart-enabled': 'true',
        }
        configuration_is_correct = all(
            desktop_entry_data.get(key) == value
            for key, value in expected_data.items()
        )

        if configuration_is_correct:
            log.info(
                f'Linux 开机启动项已存在，且配置正确: '
                f'{LINUX_AUTOSTART_FILE_PATH}'
            )
            return True

        log.info(
            f'Linux 开机启动项已存在，但配置不匹配: '
            f'{LINUX_AUTOSTART_FILE_PATH}'
        )
        return False

    except (OSError, UnicodeDecodeError) as e:
        log.error(f'检查 Linux 开机启动项失败: {e}')
        return False


def _linux_create() -> bool:
    LINUX_AUTOSTART_FOLDER_PATH.mkdir(parents=True, exist_ok=True)
    desktop_entry_text = _get_linux_desktop_entry_text()

    # 先写入临时文件再替换，避免程序中断时留下不完整的 .desktop。
    temporary_path = LINUX_AUTOSTART_FILE_PATH.with_suffix('.desktop.tmp')
    temporary_path.write_text(desktop_entry_text, encoding='utf-8')
    try:
        temporary_path.chmod(0o644)
    except OSError:
        pass
    temporary_path.replace(LINUX_AUTOSTART_FILE_PATH)

    log.info(f'Linux 开机启动项已创建: {LINUX_AUTOSTART_FILE_PATH}')
    return True


def _linux_remove() -> bool:
    if not LINUX_AUTOSTART_FILE_PATH.exists():
        log.info(f'Linux 开机启动项不存在: {LINUX_AUTOSTART_FILE_PATH}')
        return True

    LINUX_AUTOSTART_FILE_PATH.unlink(missing_ok=True)
    log.info(f'Linux 开机启动项已删除: {LINUX_AUTOSTART_FILE_PATH}')
    return True


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------

_HANDLERS: dict[str, tuple[Callable[[], bool], ...]] = {
    'Windows': (_windows_exists, _windows_create, _windows_remove),
    'Darwin': (_macos_exists, _macos_create, _macos_remove),
    'Linux': (_linux_exists, _linux_create, _linux_remove),
}


def _run_handler(action: str, index: int) -> bool:
    """按当前系统调用对应的实现函数，不支持的系统返回 False。"""
    handler = _HANDLERS.get(system)
    if handler is None:
        log.error(f'当前系统不支持{action}开机启动项: {system}')
        return False
    return handler[index]()


def create_shortcut() -> bool:
    """创建开机启动项。"""
    try:
        return _run_handler('创建', 1)
    except Exception as e:
        log.error(f'创建快捷方式失败: {str(e)}')
        return False


def is_shortcut_exist() -> bool:
    """检查开机启动项是否存在且配置正确。"""
    try:
        return _run_handler('检查', 0)
    except Exception as e:
        log.error(f'检查快捷方式失败: {e}')
        return False


def remove_shortcut() -> bool:
    """删除开机启动项。"""
    try:
        return _run_handler('删除', 2)
    except Exception as e:
        log.error(f'删除快捷方式时出错: {e}')
        return False
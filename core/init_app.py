import os
import plistlib
import subprocess
import sys
from pathlib import Path

from . import ht_lib as lib

# 日志
log = lib.log

# macOS 使用 LaunchAgent 实现当前用户登录后自动启动。
MACOS_LAUNCH_AGENT_LABEL = 'com.startinfo.launcher'
MACOS_LAUNCH_AGENTS_PATH = Path.home() / 'Library' / 'LaunchAgents'
MACOS_SHORTCUT_PATH = MACOS_LAUNCH_AGENTS_PATH / f'{MACOS_LAUNCH_AGENT_LABEL}.plist'


def _get_macos_program_arguments() -> list[str]:
    """
    获取 macOS LaunchAgent 的启动命令。

    打包后直接启动当前可执行文件；开发环境则使用当前 Python 解释器
    启动项目根目录下的 main.py。--startup 用于区分开机自启和手动启动。
    """
    if getattr(sys, 'frozen', False):
        return [str(Path(sys.executable).resolve()), '--startup']

    return [
        str(Path(sys.executable).resolve()),
        str((lib.MAIN_PATH / 'main.py').resolve()),
        '--startup',
    ]


def _get_macos_launch_agent_data() -> dict:
    """生成 StartInfo 的 macOS LaunchAgent 配置。"""
    return {
        'Label': MACOS_LAUNCH_AGENT_LABEL,
        'ProgramArguments': _get_macos_program_arguments(),
        'WorkingDirectory': str(lib.MAIN_PATH.resolve()),
        'RunAtLoad': True,
        'KeepAlive': False,
        'ProcessType': 'Interactive',
        'LimitLoadToSessionType': 'Aqua',
    }


# 创建快捷方式
def create_shortcut() -> bool:
    """
    创建快捷方式并移动到启动文件夹
    """
    try:
        # 如果系统是Windows
        if lib.system == 'Windows':
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(lib.SHORTCUT_PATH))
            shortcut.Targetpath = str(lib.EXE_PATH)
            shortcut.Arguments = '--startup'
            shortcut.WorkingDirectory = str(lib.MAIN_PATH)
            shortcut.save()
            log.info(f'快捷方式已创建并移动到启动文件夹: {lib.SHORTCUT_PATH}')
            return True

        # 如果系统是MacOS
        else:
            MACOS_LAUNCH_AGENTS_PATH.mkdir(parents=True, exist_ok=True)
            launch_agent_data = _get_macos_launch_agent_data()

            # 先写入临时文件再替换，避免程序中断时留下不完整的 plist。
            temporary_path = MACOS_SHORTCUT_PATH.with_suffix('.plist.tmp')
            with temporary_path.open('wb') as file:
                plistlib.dump(launch_agent_data, file, sort_keys=False)
            temporary_path.replace(MACOS_SHORTCUT_PATH)

            log.info(f'macOS 开机启动项已创建: {MACOS_SHORTCUT_PATH}')
            return True


    except Exception as e:
        log.error(f'创建快捷方式失败: {str(e)}')
        return False


# 检查开机启动项是否存在
def is_shortcut_exist() -> bool:
    """
    检测指定的 .exe 文件是否已经添加到开机启动项
    :return: 如果存在返回 True，否则返回 False
    """
    # 如果系统是Windows
    if lib.system == 'Windows':
        if lib.WIN_STARTUP_PATH.exists():
            # 检查快捷方式的目标路径是否与指定的目标路径一致
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(lib.SHORTCUT_PATH))
            if shortcut.Targetpath == str(lib.EXE_PATH):
                log.info(f'快捷方式已存在，且目标路径正确: {lib.SHORTCUT_PATH}')
                return True

            else:
                log.info(f'快捷方式已存在，但目标路径不匹配: {lib.SHORTCUT_PATH}')
                return False

        else:
            log.info(f'快捷方式不存在: {lib.SHORTCUT_PATH}')
            return False

    # 如果系统是MacOS
    else:
        try:
            if not MACOS_SHORTCUT_PATH.is_file():
                log.info(f'macOS 开机启动项不存在: {MACOS_SHORTCUT_PATH}')
                return False

            with MACOS_SHORTCUT_PATH.open('rb') as file:
                launch_agent_data = plistlib.load(file)

            expected_data = _get_macos_launch_agent_data()
            checked_keys = (
                'Label',
                'ProgramArguments',
                'WorkingDirectory',
                'RunAtLoad',
            )
            configuration_is_correct = all(
                launch_agent_data.get(key) == expected_data[key]
                for key in checked_keys
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

# 删除开机启动项
def remove_shortcut() -> bool:
    """
    删除开机启动项中的快捷方式
    """
    try:
        # 如果系统是Windows
        if lib.system == 'Windows':
            if lib.SHORTCUT_PATH.exists():
                lib.SHORTCUT_PATH.unlink(missing_ok = True)
                log.info(f'快捷方式已删除: {lib.SHORTCUT_PATH}')

            else:
                log.info(f'快捷方式不存在: {lib.SHORTCUT_PATH}')
            return True

        # 如果系统是MacOS
        else:
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

    except Exception as e:
        log.error(f'删除快捷方式时出错: {e}')
        return False
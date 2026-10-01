"""StartInfo 底座库：JSON 读写、应用常量、运行环境、进程生命周期。

这是 ``core`` 内部最底层、可被任意模块安全导入的模块。它只依赖两件事：

- :mod:`core.paths`   —— 纯路径常量，自身无依赖
- :mod:`core.logger`  —— 需要 ``config.log_level``，因此位于 config 之上

因此 ``base_lib → logger → config → templates → paths`` 是一条单向链，没有环。

.. warning::
   不要在本模块顶层导入 ``config`` 或 ``templates``，也不要把 ``paths`` /
   ``logger`` / ``templates`` 折进本模块：``config`` 在顶层导入
   ``templates.get_template_files``，``templates`` 必须保持为叶子，
   否则 ``config → templates → base_lib → logger → config`` 会立即成环。
"""

import atexit
import errno
import json
import os
import platform
import shlex
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Union

from .logger import log
from .paths import (CURRENT_VERSION_FILE_PATH, EXE_FILE_PATH, MAIN_PATH,
                    WIN_STARTUP_FOLDER_PATH)


# =============================================================================
# JSON 读写
# =============================================================================
def read_json(file_path: Union[str, Path]) -> dict:
    """读取单个 json 文件，失败时记录日志并返回空字典。"""
    path = Path(file_path)
    if not path.exists():
        log.error(f'文件不存在: {path}')
        return {}

    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)

    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log.error(f'解析文件 {path.name} 失败: {e}')
        return {}

    except Exception as e:
        log.error(f'读取文件 {path.name} 时发生未知错误: {e}')
        return {}


# =============================================================================
# 应用身份与静态常量
# =============================================================================
# 本地已安装版本记录（读取随程序分发的 current_version.json）
CURRENT_VERSION_JSON: dict = read_json(CURRENT_VERSION_FILE_PATH)
# 版本号
VERSION: str = CURRENT_VERSION_JSON.get('version', '版本号获取失败')

# 全局标题
TITLE: str = '开机速览'
# 单实例锁与系统级标识
APP_ID = 'StartInfo'

# 开机启动项快捷方式路径
SHORTCUT_FILE_PATH = WIN_STARTUP_FOLDER_PATH / f'{TITLE}.lnk'


# =============================================================================
# 运行环境与网络可用性
# =============================================================================
# 获取系统环境信息
system = platform.system()

# 网络检测结果缓存（模块级变量，所有导入方共享）
# 记录 (是否可用, 检测时刻)；带 TTL 避免长期缓存断网结果，
# 网络恢复后仍可重新检测
_is_internet_cache: tuple[bool, float] | None = None
_INTERNET_CACHE_TTL: float = 60.0  # 缓存有效秒数


def is_internet(timeout: float = 3.0) -> bool | float:
    """
    检测网络连通性（使用阿里云公共 DNS，自动缓存结果）

    - 第一次调用：执行网络检测并缓存结果
    - 缓存有效期（默认 60 秒）内：直接返回缓存结果（零开销）
    - 缓存过期后：重新检测，避免断网恢复后仍返回旧的失败结果
    - 所有导入本模块的文件共享同一个缓存状态

    :param timeout: 超时时间（秒），默认 3 秒
    :return: True 表示网络可用，False 表示不可用
    """
    global _is_internet_cache

    now = time.monotonic()
    if _is_internet_cache is None or now - _is_internet_cache[1] >= _INTERNET_CACHE_TTL:
        _is_internet_cache = (check_internet(timeout), now)

    return _is_internet_cache[0]


def check_internet(timeout: float) -> bool:
    """底层网络检测逻辑（使用阿里云 DNS）"""
    try:
        # 阿里云公共 DNS（首选）
        with socket.create_connection(('223.5.5.5', 53), timeout=timeout):
            return True
    except OSError:
        try:
            # 阿里云公共 DNS（备用）
            with socket.create_connection(('223.6.6.6', 53), timeout=timeout):
                return True
        except OSError:
            return False


# =============================================================================
# 单实例锁（禁止多开）
# =============================================================================
class SingleInstance:
    """跨平台单实例锁。"""

    def __init__(self):
        self._handle = None  # Windows 互斥体句柄
        self._fd = None      # POSIX 锁文件描述符

        if sys.platform == 'win32':
            self.is_first = self._acquire_win()
        else:
            self.is_first = self._acquire_posix()

        atexit.register(self.release)
        log.debug(f'多开检测: {"首次实例" if self.is_first else "已有实例在运行"}')

    @property
    def is_running(self) -> bool:
        """True 表示已有实例在运行。"""
        return not self.is_first

    def _acquire_win(self) -> bool:
        import ctypes
        from ctypes.wintypes import HANDLE, BOOL

        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = [ctypes.c_void_p, BOOL, ctypes.c_wchar_p]
        create_mutex.restype = HANDLE
        self._close_handle = kernel32.CloseHandle
        self._close_handle.argtypes = [HANDLE]

        self._handle = create_mutex(None, False, APP_ID)
        # 错误码必须紧跟 CreateMutexW 读取
        err = ctypes.get_last_error()
        if not self._handle:
            raise OSError(err, f'CreateMutexW 失败: {ctypes.FormatError(err)}')
        # 183 = ERROR_ALREADY_EXISTS，说明互斥体已存在，即已有实例
        return err != 183

    def _acquire_posix(self) -> bool:
        import fcntl

        # 文件名带 uid，避免临时目录下不同用户互相干扰
        path = os.path.join(tempfile.gettempdir(), f'{APP_ID}-{os.getuid()}.lock')
        self._fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError as e:
            os.close(self._fd)
            self._fd = None
            if e.errno not in (errno.EAGAIN, errno.EACCES):
                raise
            return False

    def release(self) -> None:
        """释放锁；进程退出时由 atexit 自动调用。可重复调用。"""
        if self._handle:
            self._close_handle(self._handle)
            self._handle = None
        if self._fd is not None:
            import fcntl
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None


# =============================================================================
# 重启
# =============================================================================
def restart_program(args: str = ""):
    """
    兼容互斥锁的强制重启
    :param args: 启动参数，例如 "--settings"。留空则默认启动主程序。
    """
    # 如果是Windows系统
    if system == 'Windows':
        # 1. 获取当前进程 PID
        current_pid = os.getpid()

        # 2. 构造命令
        # 注意：start "" "{EXE_FILE_PATH}" {args}
        # 如果 args 不为空，它会紧跟在路径后面
        # 例如：start "" "C:\path\to\main.exe" --settings

        # 我们加上一个判断，确保参数前面有个空格
        extra_args = f" {args}" if args else ""

        # 构造一行流命令
        # taskkill 强制杀掉当前 PID 确保文件锁/互斥锁释放
        # timeout 等待 1 秒给系统缓冲
        # start 重新拉起程序
        cmd = f'taskkill /f /pid {current_pid} & timeout /t 1 /nobreak & start "" "{EXE_FILE_PATH}"{extra_args}'

        # 破坏性操作：强制杀掉当前进程，记录后以后台静默方式执行 CMD 命令
        log.info(f'主程序即将重启 (PID={current_pid}, 参数="{args or "无"}")')
        subprocess.Popen(cmd, shell=True)

        # 4. 当前程序立即退出
        sys.exit()

    # MacOS打包环境
    else:
        current_pid = os.getpid()
        extra_args = shlex.split(args) if args else []
        # 保留虚拟环境中的解释器路径；resolve() 会把 .venv/bin/python
        # 解析为基础 Python，导致重启后找不到项目依赖。
        executable_path = Path(sys.executable).absolute()

        # Nuitka 的 macOS GUI 程序位于 xxx.app/Contents/MacOS/ 中。
        # 找到 .app 后使用 open 交给 Launch Services 正确拉起应用。
        app_path = next(
            (path for path in executable_path.parents if path.suffix == '.app'),
            None
        )
        if app_path:
            restart_command = ['/usr/bin/open', '-n', str(app_path)]
            if extra_args:
                restart_command.extend(['--args', *extra_args])
        elif getattr(sys, 'frozen', False) or '__compiled__' in globals():
            # 兼容 Nuitka/PyInstaller 生成的独立可执行文件。
            restart_command = [str(executable_path), *extra_args]
        else:
            # 开发环境中的 sys.executable 是 Python，需要明确启动 main.py。
            restart_command = [
                str(executable_path),
                str((MAIN_PATH / 'main.py').resolve()),
                *extra_args
            ]

        # 辅助进程等待当前程序退出后再启动新实例。等待时间设置上限，
        # 避免 Nuitka 外层进程暂未退出时一直阻塞重启。
        restart_script = '''
old_pid="$1"
shift
wait_count=0
while kill -0 "$old_pid" 2>/dev/null && [ "$wait_count" -lt 30 ]; do
    sleep 0.1
    wait_count=$((wait_count + 1))
done
exec "$@"
'''
        subprocess.Popen(
            [
                '/bin/sh',
                '-c',
                restart_script,
                'StartInfo-restart',
                str(current_pid),
                *restart_command
            ],
            cwd=str(MAIN_PATH),
            start_new_session=True,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        log.info(f'MacOS程序正在重启，启动参数: {args or "无"}')
        # Qt 的槽函数可能拦截 SystemExit，直接结束旧进程才能确保辅助进程继续。
        os._exit(0)


__all__ = [
    # JSON 读写
    'read_json',
    # 应用身份与静态常量
    'CURRENT_VERSION_JSON', 'VERSION', 'TITLE', 'APP_ID', 'SHORTCUT_FILE_PATH',
    # 运行环境与网络
    'system', 'is_internet', 'check_internet',
    # 进程生命周期
    'SingleInstance', 'restart_program',
]
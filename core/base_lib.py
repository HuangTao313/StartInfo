# =============================================================================
# 导入区
# =============================================================================
import atexit
import ctypes
import json
import os
import platform
import shlex
import shutil
import socket
import subprocess
import time
from sys import argv
from ctypes.wintypes import HANDLE, DWORD, BOOL
from typing import Union

from loguru import logger

from .config import cfg
from .paths import *


# 获取全局启动参数
global_argv = argv

# 获取系统环境信息
system = platform.system()

# 日志初始化 (建议放在这里，因为依赖 cfg.log_level)
log_level = 'DEBUG' if '--debug' in global_argv else cfg.log_level.value

logger.add(
    sink=LOG_FILE_PATH,
    enqueue=True,
    retention='3 days',
    encoding='utf-8',
    level=log_level,
    delay=True)
log = logger

# 读取单个json文件
def read_json(file_path: Union[str, Path]) -> dict:
    path = Path(file_path)
    if not path.exists():
        log.error(f'文件不存在: {path}')
        return {}

    try:
        # 使用 with open 配合 json.load，内存效率更高
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)

    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log.error(f'解析文件 {path.name} 失败: {e}')
        return {}

    except Exception as e:
        log.error(f'读取文件 {path.name} 时发生未知错误: {e}')
        return {}

# =============================================================================
# 基础配置 (不依赖 cfg 的常量)
# =============================================================================
CURRENT_VERSION_JSON = read_json(CURRENT_VERSION_PATH)
VERSION: str = CURRENT_VERSION_JSON.get('version', '版本号获取失败') # 版本号
TITLE: str = '开机速览'                         # 全局标题
SHORTCUT_PATH: Path = WIN_STARTUP_PATH / f'{TITLE}.lnk'  # 开机启动项路径

# 检查网络连接情况
# 模块级缓存变量（所有导入此模块的文件共享同一个缓存）
# 记录 (是否可用, 检测时刻)；带 TTL 避免长期缓存断网结果，
# 网络恢复后仍可重新检测
_is_internet_cache: tuple[bool, float] | None = None
_INTERNET_CACHE_TTL: float = 60.0  # 缓存有效秒数

def is_internet(timeout: float = 3.0) -> bool:
    """
    检测网络连通性（使用阿里云公共 DNS，自动缓存结果）

    - 第一次调用：执行网络检测并缓存结果
    - 缓存有效期（默认 60 秒）内：直接返回缓存结果（零开销）
    - 缓存过期后：重新检测，避免断网恢复后仍返回旧的失败结果
    - 所有导入 lib 的文件共享同一个缓存状态

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

# Windows下禁止多开
class WinSingleInstance:
    def __init__(self, name='Local\\StartInfo'):
        # 定义Windows API
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self._create_mutex = kernel32.CreateMutexW
        self._create_mutex.argtypes = [ctypes.c_void_p, BOOL, ctypes.c_wchar_p]
        self._create_mutex.restype = HANDLE

        self._close_handle = kernel32.CloseHandle
        self._close_handle.argtypes = [HANDLE]

        self._get_error = kernel32.GetLastError
        self._get_error.restype = DWORD

        # 创建互斥体
        self.handle = self._create_mutex(None, False, name)
        # 如果 GetLastError 返回 183 (ERROR_ALREADY_EXISTS)，说明互斥体已存在
        self.is_first = not (self.handle is None or self._get_error() == 183)

        # 自动清理 - 无论如何都注册清理，确保句柄被正确释放
        atexit.register(self._close_handle, self.handle)

    def __del__(self):
        """析构函数，确保互斥体被释放"""
        try:
            if hasattr(self, 'handle') and self.handle:
                self._close_handle(self.handle)
        except:
            pass

    @property
    def is_running(self):
        """返回检测结果：True表示已有实例运行"""
        return not self.is_first

# 模板路径与列表
def get_template_path() -> Path:
    """动态获取当前激活的模板路径（每次调用实时读取配置）。"""
    return TEMPLATE_FOLDER_PATH / cfg.template_file.value


def get_template_files() -> list:
    """扫描模板文件夹，获取所有 .j2 模板文件名"""
    if not TEMPLATE_FOLDER_PATH.exists():
        return ['default.j2']
    files = [
        p.name for p in TEMPLATE_FOLDER_PATH.glob('*.j2')
        if p.is_file() and p.name != 'birthday_wishes.j2'
    ]
    if not files:
        return ['default.j2']
    return files

# 导入模板
def import_template(template_file_path: Path) -> tuple[bool, str]:
    """
    导入模板文件

    :param template_file_path: 模板文件路径
    :return: (是否成功, 提示信息)
    """
    # 检查传入的模板文件是否存在
    if not template_file_path.exists():
        error_text = f'模版文件{template_file_path.name}不存在'
        log.error(error_text)
        return False, error_text

    # 自动创建模版文件夹(如果不存在)
    TEMPLATE_FOLDER_PATH.mkdir(parents=True, exist_ok=True)
    new_template_file_path = TEMPLATE_FOLDER_PATH / template_file_path.name

    # 如果模板已经导入，则提示用户
    if new_template_file_path.exists():
        warning_text = f'模版文件{template_file_path.name}已存在，请勿重复导入'
        log.warning(warning_text)
        return False, warning_text

    # 导入模板
    try:
        shutil.copy(template_file_path, new_template_file_path)
        info_text = f'模版文件已导入：{new_template_file_path.name}'
        log.info(info_text)
        return True, info_text
    except Exception as e:
        error_text = f'导入模版文件失败：{str(e)}'
        log.error(error_text)
        return False, error_text

# 启用模板
def activate_template(template_file_path: Path | str) -> tuple[bool, str]:
    """
    启用模板文件

    :param template_file_path: 模板文件路径（支持字符串或Path对象）
    :return: (是否成功, 提示信息)
    """
    # 参数校验
    if not template_file_path or not str(template_file_path).strip():
        error_text = '模板文件路径不能为空'
        log.error(error_text)
        return False, error_text

    # 统一转换为Path对象
    if isinstance(template_file_path, str):
        template_file_path = Path(template_file_path)
        if not template_file_path.is_absolute():
            template_file_path = TEMPLATE_FOLDER_PATH / template_file_path

    # 检查文件是否存在
    if not template_file_path.exists():
        error_text = f'模版文件{template_file_path.name}不存在'
        log.error(error_text)
        return False, error_text

    # 写入配置并启用模板
    try:
        # 使用 qconfig.set() 方法正确设置并保存配置项
        from .config import qconfig, cfg
        qconfig.set(cfg.template_file, template_file_path.name, save=True)
        info_text = f'已启用模版文件{template_file_path.name}'
        log.info(info_text)
        return True, info_text

    except Exception as e:
        error_text = f'启用模版文件失败：{str(e)}'
        log.error(error_text)
        return False, error_text

# 重启
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
        # 注意：start "" "{EXE_PATH}" {args}
        # 如果 args 不为空，它会紧跟在路径后面
        # 例如：start "" "C:\path\to\main.exe" --settings

        # 我们加上一个判断，确保参数前面有个空格
        extra_args = f" {args}" if args else ""

        # 构造一行流命令
        # taskkill 强制杀掉当前 PID 确保文件锁/互斥锁释放
        # timeout 等待 1 秒给系统缓冲
        # start 重新拉起程序
        cmd = f'taskkill /f /pid {current_pid} & timeout /t 1 /nobreak & start "" "{EXE_PATH}"{extra_args}'

        # 3. 以后台静默方式执行 CMD 命令
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
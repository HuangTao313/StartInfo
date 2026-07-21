# =============================================================================
# 导入区
# =============================================================================
import atexit
import ctypes
import json
import os
import platform
import shutil
import socket
import subprocess
from ctypes.wintypes import HANDLE, DWORD, BOOL
from typing import Any, Dict
from typing import Union

from loguru import logger

from .config import cfg
from .paths import *

# 涉及 cfg 的必须留在后面
TEMPLATE_PATH = TEMPLATE_FOLDER_PATH / cfg.template_file.value
WEATHER_DATA_EXPIRE_TIME: int = cfg.weather_interval.value * 60

# 日志初始化 (建议放在这里，因为依赖 cfg.log_level)
logger.add(LOG_PATH, rotation='1 day', retention='3 days', encoding='utf-8', level=cfg.log_level.value)
log = logger

# 获取全局启动参数
global_argv = sys.argv

# 获取系统环境信息
system = platform.system()

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
TITLE: str = f'开机速览({VERSION})'                         # 全局标题
SHORTCUT_NAME: str = '开机速览'                             # 开机启动项名称
SHORTCUT_PATH: Path = WIN_STARTUP_PATH / f'{SHORTCUT_NAME}.lnk'  # 开机启动项路径

# 检查网络连接情况
# 模块级缓存变量（所有导入此模块的文件共享同一个缓存）
_is_internet_cache = None

def is_internet(timeout: float = 3.0) -> bool:
    """
    检测网络连通性（使用阿里云公共 DNS，自动缓存结果）

    - 第一次调用：执行网络检测并缓存结果
    - 后续调用：直接返回缓存结果（零开销）
    - 所有导入 lib 的文件共享同一个缓存状态

    :param timeout: 超时时间（秒），默认 3 秒
    :return: True 表示网络可用，False 表示不可用
    """
    global _is_internet_cache

    if _is_internet_cache is None:
        _is_internet_cache = check_internet(timeout)

    return _is_internet_cache


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

# 读写data.json
class JsonHandler:

    def __init__(self):
        """初始化处理器，使用预定义的JSON_PATH路径"""
        self.file_path = DATA_FILE_PATH  # 保持Path对象类型
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        """安全加载JSON数据（自动创建空文件）"""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                log.error(f'加载JSON失败: {e}')
                # 备份损坏的文件
                backup_path = self.file_path.with_suffix('.json.backup')
                try:
                    shutil.copy2(self.file_path, backup_path)
                    log.warning(f'已备份损坏的JSON文件到: {backup_path}')
                except Exception as backup_error:
                    log.error(f'备份失败: {backup_error}')
                # 返回默认结构而不是空字典
                return {
                    'General': {
                        'is_first_startup': True,
                        'data_reset_times': 0,
                        'startup_times': 1,
                        'last_birthday_date': '',  # 记录上次显示生日祝福的日期
                    },
                    'Data': {
                        'date': {},
                        'weather': {},
                        'other': {}
                    },
                    'Easter_egg': {
                        'name': '',
                        'is_get': False,
                        'get_date': ''
                    }
                }
        return {}

    def read(self, *keys: str) -> Any:
        """
        安全嵌套读取
        :param keys: 多级键路径（如 'user', 'name'）
        :return: 值或None
        """
        current = self.data
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    def write(self, *keys: str, value: Any):
        """
        安全嵌套写入（自动创建路径）
        :param keys: 多级键路径（如 'user', 'name'）
        :param value: 要写入的值
        """
        current = self.data
        for key in keys[:-1]:
            current = current.setdefault(key, {})
        current[keys[-1]] = value
        self._save()

    def update(self, *keys: str, update_dict: Dict):
        """
        字典合并更新
        :param keys: 多级键路径（如 'settings'）
        :param update_dict: 要合并的字典
        """
        current = self.data
        for key in keys[:-1]:  # 处理除最后一个键外的所有键
            # 检查当前层级的值是否为字典类型，如果不是则重置为空字典
            if not isinstance(current, dict):
                current = {}
            # 确保当前路径下的值是字典类型
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        # 处理最后一个键
        final_key = keys[-1]
        if not isinstance(current, dict):
            current = {}

        # 检查update_dict是否为字典类型
        if not isinstance(update_dict, dict):
            log.warning(f'update_dict should be a dict, got {type(update_dict)}')
            update_dict = {}

        # 确保目标位置是字典类型，然后更新
        if final_key not in current or not isinstance(current[final_key], dict):
            current[final_key] = {}

        current[final_key].update(update_dict)
        self._save()



    def _save(self):
        """保存数据到文件（自动创建目录）"""
        # 检查数据完整性，避免保存不完整的数据
        required_keys = ['General', 'Data', 'Easter_egg']
        if not all(key in self.data for key in required_keys):
            missing_keys = [key for key in required_keys if key not in self.data]
            log.error(f'数据不完整，缺少必要的键: {missing_keys}，拒绝保存以避免覆盖原有数据')
            # 如果原文件存在，不要覆盖它
            if self.file_path.exists():
                log.warning('保留原有文件，不进行保存')
                return
            else:
                # 如果文件不存在但数据不完整，仍然保存（初始化场景）
                log.warning('文件不存在但数据不完整，仍然保存用于初始化')

        # 使用pathlib创建目录
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def batch_update(self):
        """
        批量更新（单线程优化版）
        用法：
        with handler.batch_update():
            handler.write('key', 'value')
            handler.update('section', {'new': 'data'})
        """
        return self._BatchContext(self)

    class _BatchContext:
        def __init__(self, handler):
            self.handler = handler
            self.original_data = handler.data.copy()  # 仅浅拷贝

        def __enter__(self):
            self.handler.data = self.original_data.copy()
            return self.handler

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.handler.data = self.original_data  # 回滚
            else:
                self.handler._save()  # 保存

# 初始化data.json读写
file = JsonHandler()

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

# # 加密
# def encrypt(plaintext) -> str:
#     """加密字符串"""
#     cipher = AES.new(KEY.encode(), AES.MODE_CBC)
#     ciphertext = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
#     return base64.b64encode(cipher.iv + ciphertext).decode('utf-8')
#
# # 解密
# def decrypt(ciphertext) -> str:
#     try:
#         if not ciphertext:
#             return ''
#
#         data = base64.b64decode(ciphertext)
#         if len(data) < AES.block_size:
#             raise ValueError('加密数据长度不足')
#
#         iv = data[:AES.block_size]
#         cipher = AES.new(KEY.encode(), AES.MODE_CBC, iv)
#         plaintext = unpad(cipher.decrypt(data[AES.block_size:]), AES.block_size)
#         return plaintext.decode('utf-8')
#
#     except Exception as e:
#         log.error(f'解密失败: {str(e)}, 数据: {ciphertext}')
#         return ciphertext  # 返回默认值而不是抛出异常


# 次数自增函数
def times(mode: str) -> int | None:
    try:
        if mode == 'reset':
            file.write('General', 'startup_times', value = 1)

        elif mode == 'read':
            return file.read('General', 'startup_times')

        elif mode == 'add':
            new_times = file.read('General', 'startup_times')
            file.write('General', 'startup_times', value = new_times + 1)

    except Exception as e:
        log.error(f'次数自增函数错误: {str(e)}')

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
def restart_program(args: str = ''):
    """
    重启当前程序

    开发环境:
        使用当前 Python 解释器重新启动 main.py

    打包环境:
        Windows 下通过独立 cmd 进程重新启动 exe，
        避免当前进程退出导致启动命令被中断。
    """

    # 开发环境
    if not getattr(sys, 'frozen', False):
        log.debug('尝试在开发环境重启，此功能未完善')
        subprocess.Popen(
            'uv run main.py',
            shell=True,
            cwd=str(MAIN_PATH),
        )
        sys.exit()

    # Windows 打包环境
    elif system == 'Windows':
        current_pid = os.getpid()
        # 拼接启动参数
        extra_args = f' {args}' if args else ''
        # 结束旧进程 -> 等待资源释放 -> 启动新进程
        cmd = (
            f'taskkill /f /pid {current_pid} '
            f'& timeout /t 1 /nobreak '
            f'& start "" "{sys.executable}"{extra_args}'
        )

        # 独立执行，避免随当前进程退出
        subprocess.Popen(
            cmd,
            shell=True,
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP |
                subprocess.CREATE_NO_WINDOW
            )
        )

        sys.exit()

    # MacOS打包环境
    else:
        log.warning('暂不支持MacOS系统，请自行重启')
        sys.exit()

# 重试装饰器
# def async_retry_on_value(fail_value='获取失败'):
#     """
#     专门适配 aiohttp 异步函数的重试装饰器
#     """
#     retries = 2
#     delay = 1
#
#     def decorator(func):
#         @wraps(func)
#         async def wrapper(*args, **kwargs):
#             attempt = 0
#             # 这里的 result 初始值可以设为你预期的失败值
#             result = fail_value
#
#             while attempt < retries:
#                 # 执行异步网络请求
#                 result = await func(*args, **kwargs)
#
#                 # 判断逻辑：如果是字典且包含数据，或者不是失败字符串
#                 if result != fail_value:
#                     return result
#
#                 attempt += 1
#                 log.warning(f'⚠️ {func.__name__} 请求异常，正在进行第 {attempt} 次异步重试...')
#
#                 if attempt < retries:
#                     # 使用异步等待，确保 UI 不卡顿
#                     await asyncio.sleep(delay)
#
#             log.error(f'❌ {func.__name__} 在 {retries} 次重试后最终失败。')
#             return result
#
#         return wrapper
#
#     return decorator

# # =============================================================================
# # 全局异步上下文管理器
# # =============================================================================
# class AsyncSessionManager:
#     '''
#     全局异步会话管理器，用于共享 aiohttp.ClientSession
#     减少连接创建开销，提升异步网络请求性能
#     '''
#     _instance = None
#     _session = None
#     _initialized = False
#
#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#         return cls._instance
#
#     async def __aenter__(self):
#         '''异步上下文管理器入口，创建共享的 ClientSession'''
#         if not self._initialized or self._session is None or self._session.closed:
#             import aiohttp
#             self._session = aiohttp.ClientSession()
#             self._initialized = True
#             log.debug('已创建全局共享的 aiohttp.ClientSession')
#         return self._session
#
#     async def __aexit__(self, exc_type, exc_val, exc_tb):
#         '''异步上下文管理器出口，不关闭 session 以保持全局共享'''
#         # 不关闭 session，保持全局共享
#         # 只在程序退出时通过 close() 方法手动关闭
#         pass
#
#     @property
#     def session(self):
#         '''获取当前的 ClientSession 实例'''
#         if not self._initialized or self._session is None or self._session.closed:
#             raise RuntimeError('ClientSession 未初始化或已关闭，请使用 async with 语句')
#         return self._session
#
#     async def close(self):
#         '''手动关闭会话（用于清理）'''
#         if self._session and not self._session.closed:
#             await self._session.close()
#             self._initialized = False
#
# # 创建全局实例
# async_session = AsyncSessionManager()
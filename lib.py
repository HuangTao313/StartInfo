import socket
import sys
import json
import ctypes
import atexit
import base64
from ctypes.wintypes import HANDLE, DWORD, BOOL
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from pathlib import Path
from loguru import logger
from typing import Any, Dict

# 获取文件路径
MAIN_PATH = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent

# === 数据文件路径 ===
JSON_PATH = MAIN_PATH / 'data' / 'json' / 'data.json'            # data.json的路径
API_PATH = MAIN_PATH / 'data' / 'json' / 'api.json'              # api_key.json的路径
EMOJI_PATH = MAIN_PATH / 'data' / 'json' / 'emoji.json'          # emoji文件路径
TEMPLATE_FOLDER_PATH = MAIN_PATH / 'data' / 'template'           # 模板文件夹路径
CHANGELOG_PATH = MAIN_PATH / 'data' / 'changelog.txt'            # 更新日志路径
# DOWNLOAD_PATH = MAIN_PATH / 'data' / 'download'                  # 下载文件夹

# === 日志文件路径 ===
LOG_PATH = MAIN_PATH / 'data' / 'log' / 'log.log'       # log.log的路径

# === 可执行文件路径 ===
EXE_PATH = MAIN_PATH / 'main.exe'                       # main.exe的路径
SETTINGS_PATH = MAIN_PATH / 'settings.exe'              # settings.exe的路径
# ARIA2_PATH = MAIN_PATH / 'data' / 'aria2' / 'aria2c.exe'
UNINS_PATH = MAIN_PATH / 'unins000.exe'                 # 卸载程序的路径

# === 应用配置 ===
VERSION = 'V20260124-Beta'                                   # 版本号
TITLE = f'开机速览({VERSION})'                          # 全局标题
SHORTCUT_NAME = '开机速览2.1.5'                         # 开机启动项名称
# RELEASE_TIME = 1769247459                               # 发布时间(时间戳)
WEATHER_DATA_EXPIRE_TIME = 1800                         # 天气数据过期时间(单位：秒)

# === 系统路径 ===
STARTUP_PATH = Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'  # 获取当前用户的启动文件夹路径
SHORTCUT_PATH = STARTUP_PATH / f'{SHORTCUT_NAME}.lnk'   # 开机启动项路径

# === 安全配置 ===
KEY = "387856766_2174509658_Ht."                        # 密钥

# 初始化日志管理器
logger.add(LOG_PATH, rotation='1 day', retention='3 days', encoding='utf-8')
log = logger

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
        with socket.create_connection(("223.5.5.5", 53), timeout=timeout):
            return True
    except OSError:
        try:
            # 阿里云公共 DNS（备用）
            with socket.create_connection(("223.6.6.6", 53), timeout=timeout):
                return True
        except OSError:
            return False

# 读写data.json
class JsonHandler:

    def __init__(self):
        """初始化处理器，使用预定义的JSON_PATH路径"""
        self.file_path = JSON_PATH  # 保持Path对象类型
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        """安全加载JSON数据（自动创建空文件）"""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载JSON失败: {e}")
        return {}

    def read(self, *keys: str) -> Any:
        """
        安全嵌套读取
        :param keys: 多级键路径（如 "user", "name"）
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
        :param keys: 多级键路径（如 "user", "name"）
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
        :param keys: 多级键路径（如 "settings"）
        :param update_dict: 要合并的字典
        """
        current = self.data
        for key in keys:
            current = current.setdefault(key, {})
        current.update(update_dict)
        self._save()

    def _save(self):
        """保存数据到文件（自动创建目录）"""
        # 使用pathlib创建目录
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def batch_update(self):
        """
        批量更新（单线程优化版）
        用法：
        with handler.batch_update():
            handler.write("key", "value")
            handler.update("section", {"new": "data"})
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

# 读取单个json文件
def read_json(file_path) -> dict:
    """安全读取 JSON 文件"""
    try:
        path = Path(file_path)
        if not path.exists():
            log.error(f"文件不存在: {file_path}")
            return {}

        content = path.read_text(encoding='utf-8')
        return json.loads(content)

    except json.JSONDecodeError as e:
        log.error(f"JSON 格式错误: {e}")
        return {}
    except FileNotFoundError:
        log.error(f"文件未找到: {file_path}")
        return {}
    except UnicodeDecodeError:
        log.error(f"文件编码错误: {file_path}")
        return {}

# def read(section, option):
#     path = CACHE_PATH
#     if not path.exists():
#         return None
#     conf = configparser.ConfigParser(interpolation=None)
#     conf.read(path, encoding='utf-8')
#     return conf[section][option] if conf.has_section(section) and conf.has_option(section, option) else None
#
# def write(section, option, value=''):
#     path = CACHE_PATH
#     path.parent.mkdir(parents=True, exist_ok=True)
#     conf = configparser.ConfigParser(interpolation=None)
#     if path.exists():
#         conf.read(path, encoding='utf-8')
#     if not conf.has_section(section):
#         conf.add_section(section)
#     conf[section][option] = value
#     with open(path, 'w', encoding='utf-8') as f:
#         conf.write(f)

# 初始化data.json读写
file = JsonHandler()
# 当前模板文件路径
TEMPLATE_PATH = TEMPLATE_FOLDER_PATH / file.read('General', 'template_file')

# 加密
def encrypt(plaintext) -> str:
    """加密字符串"""
    cipher = AES.new(KEY.encode(), AES.MODE_CBC)
    ciphertext = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
    return base64.b64encode(cipher.iv + ciphertext).decode('utf-8')

# 解密
def decrypt(ciphertext) -> str:
    try:
        if not ciphertext:
            return ""

        data = base64.b64decode(ciphertext)
        if len(data) < AES.block_size:
            raise ValueError("加密数据长度不足")

        iv = data[:AES.block_size]
        cipher = AES.new(KEY.encode(), AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(data[AES.block_size:]), AES.block_size)
        return plaintext.decode('utf-8')

    except Exception as e:
        log.error(f"解密失败: {e}, 数据: {ciphertext}")
        return ""  # 返回默认值而不是抛出异常


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
        log.error(f"次数自增函数错误: {e}")

# # 检查缓存文件
# def check_cache() -> bool:
#     # 只检查cache.ini是否存在（不再检查holidays.json）
#     if cache_path.exists:
#         # 检查cache.ini文件的完整性（原逻辑完全保留）
#         i, i_2 = 0, 0
#         options_states, holidays_states = [], []
#         # Options
#         while i < 6:
#             if read('Options', Options[i]) != None:
#                 options_states.append(True)
#             else:
#                 options_states.append(False)
#             i += 1
#         # Data
#         while i_2 < 3:
#             if read('Data', Data[i_2]) != None:
#                 holidays_states.append(True)
#             else:
#                 holidays_states.append(False)
#             i_2 += 1
#         # 检查
#         if False in options_states or False in holidays_states:
#             return False
#         else:
#             return True
#     else:
#         return False

# 禁止多开
class SingleInstance:
    def __init__(self, name="Local\\MyAppMutex_12345678"):
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
        self.is_first = not (self.handle is None or self._get_error() == 183)

        # 自动清理
        if self.is_first:
            atexit.register(self._close_handle, self.handle)

    @property
    def is_running(self):
        """返回检测结果：True表示已有实例运行"""
        return not self.is_first


# if __name__ == '__main__':
    # # 使用示例
    # KEY = "387856766_2174509658_Ht."  # 您自己的密钥（建议至少16字节）
    # text = "8aa148f399f3fc0a87166becddb0b3b4"
    #
    # encrypted = encrypt(text)
    # decrypted = decrypt(encrypted)
    #
    # print("原始文本:", text)
    # print("加密后:", encrypted)
    # print("解密后:", decrypted)
    # print(EXE_PATH)
    #
    # print(read_json(API_PATH))
    # print(is_internet())
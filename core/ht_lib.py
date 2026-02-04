# =============================================================================
# 导入区
# =============================================================================
import socket
import sys
import json
import ctypes
import atexit
import base64
import shutil
from ctypes.wintypes import HANDLE, DWORD, BOOL
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from pathlib import Path
from loguru import logger
from typing import Any, Dict

# =============================================================================
# 防重复导入保护（Nuitka 兼容）
# =============================================================================
if "core" in sys.modules and hasattr(sys.modules["core"], "lib"):
    # 防止重复导入导致状态混乱
    sys.modules[__name__] = sys.modules["core.lib"]

# =============================================================================
# 路径与初始化函数
# =============================================================================
def get_main_path() -> Path:
    """智能判断主程序目录"""
    if getattr(sys, 'frozen', False):
        # 打包后：exe 所在目录就是主目录
        path = Path(sys.executable).parent
    else:
        # 开发时：可能是 ht_lib.py 所在目录（core/），也可能是主脚本目录
        path = Path(__file__).parent.resolve()

    # 如果路径以 'core' 结尾，说明我们在 core/ 里，要退回上一级
    if path.name == "core":
        path = path.parent

    return path

MAIN_PATH: Path = get_main_path()

# =============================================================================
# 日志系统初始化
# =============================================================================
LOG_PATH: Path = MAIN_PATH / 'data' / 'log' / 'log.log'  # log.log 的路径
logger.add(LOG_PATH, rotation='1 day', retention='3 days', encoding='utf-8')
log = logger

# =============================================================================
# 工具函数
# =============================================================================
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

# =============================================================================
# 数据文件路径
# =============================================================================
JSON_PATH: Path = MAIN_PATH / 'data' / 'json' / 'data.json'              # data.json 的路径
API_PATH: Path = MAIN_PATH / 'data' / 'json' / 'api.json'                # api_key.json 的路径
EMOJI_PATH: Path = MAIN_PATH / 'data' / 'json' / 'emoji.json'            # emoji 文件路径
TEMPLATE_FOLDER_PATH: Path = MAIN_PATH / 'data' / 'template'             # 模板文件夹路径
CURRENT_VERSION_PATH: Path = MAIN_PATH / 'data' / 'json' / 'current_version.json'  # 本地版本文件路径
CURRENT_VERSION_JSON: dict = read_json(CURRENT_VERSION_PATH)

# =============================================================================
# 可执行文件路径
# =============================================================================
EXE_PATH: Path = MAIN_PATH / 'main.exe'          # main.exe 的路径
SETTINGS_PATH: Path = MAIN_PATH / 'settings.exe' # settings.exe 的路径
UNINS_PATH: Path = MAIN_PATH / 'unins000.exe'    # 卸载程序的路径

# =============================================================================
# 应用配置
# =============================================================================
VERSION: str = CURRENT_VERSION_JSON.get('version', '版本号获取失败')  # 版本号
TITLE: str = f'开机速览({VERSION})'                                 # 全局标题
SHORTCUT_NAME: str = f'开机速览{VERSION}'                            # 开机启动项名称
WEATHER_DATA_EXPIRE_TIME: int = 1800                                # 天气数据过期时间(单位：秒)

# =============================================================================
# 系统路径
# =============================================================================
STARTUP_PATH: Path = (
    Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' /
    'Start Menu' / 'Programs' / 'Startup'
)  # 获取当前用户的启动文件夹路径
SHORTCUT_PATH: Path = STARTUP_PATH / f'{SHORTCUT_NAME}.lnk'  # 开机启动项路径
DOWNLOAD_PATH: Path = MAIN_PATH / 'data' / 'download'    # 下载缓存路径

# =============================================================================
# 安全配置
# =============================================================================
KEY: str = "387856766_2174509658_Ht."  # 密钥

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
                log.error(f"加载JSON失败: {e}")
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
            log.warning(f"update_dict should be a dict, got {type(update_dict)}")
            update_dict = {}

        # 确保目标位置是字典类型，然后更新
        if final_key not in current or not isinstance(current[final_key], dict):
            current[final_key] = {}

        current[final_key].update(update_dict)
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

# 初始化data.json读写
file = JsonHandler()
# 当前模板文件路径
TEMPLATE_PATH = TEMPLATE_FOLDER_PATH / file.read('General', 'template_file')

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
        log.error(f"解密失败: {str(e)}, 数据: {ciphertext}")
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
        log.error(f"次数自增函数错误: {str(e)}")

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
        error_text = "模板文件路径不能为空"
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
        file.write('General', 'template_file', value=template_file_path.name)
        info_text = f'已启用模版文件{template_file_path.name}'
        log.info(info_text)
        return True, info_text
    except Exception as e:
        error_text = f'启用模版文件失败：{str(e)}'
        log.error(error_text)
        return False, error_text

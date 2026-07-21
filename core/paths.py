import sys
from pathlib import Path

# =============================================================================
# 路径获取函数
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
    if path.name == 'core':
        path = path.parent

    return path

# =============================================================================
# 核心目录定义 (不依赖任何外部配置)
# =============================================================================
# 主目录
MAIN_PATH: Path = get_main_path()
# 数据文件夹目录
DATA_FOLDER_PATH = MAIN_PATH / 'data'
# 数据库目录
DB_FOLDER_PATH = DATA_FOLDER_PATH / 'db'
# JSON 配置文件夹
JSON_PATH: Path = DATA_FOLDER_PATH / 'json'
# 模板文件夹路径
TEMPLATE_FOLDER_PATH: Path = DATA_FOLDER_PATH / 'templates'
# 日志文件夹路径
LOG_FOLDER_PATH: Path = DATA_FOLDER_PATH / 'logs'
# 下载缓存路径
DOWNLOAD_PATH: Path = DATA_FOLDER_PATH / 'download'

# =============================================================================
# 具体文件路径
# =============================================================================
LOG_PATH: Path = LOG_FOLDER_PATH / 'log.log'               # log.log 的路径
DATA_FILE_PATH: Path = JSON_PATH / 'data.json'             # data.json 的路径
CONFIG_FILE_PATH: Path = JSON_PATH / 'config.json'         # 配置文件路径
API_FILE_PATH: Path = JSON_PATH / 'api.json'                    # api_key.json 的路径
EMOJI_PATH: Path = JSON_PATH / 'emoji.json'                # emoji 文件路径
CURRENT_VERSION_PATH: Path = JSON_PATH / 'current_version.json'  # 本地版本文件路径

# 可执行文件路径
EXE_PATH: Path = MAIN_PATH / 'StartInfo.exe'                    # main.exe 的路径
UNINS_PATH: Path = MAIN_PATH / 'unins000.exe'              # 卸载程序的路径

# =============================================================================
# 系统路径
# =============================================================================
WIN_STARTUP_PATH: Path = (
    Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' /
    'Start Menu' / 'Programs' / 'Startup'
)  # 获取当前用户的启动文件夹路径
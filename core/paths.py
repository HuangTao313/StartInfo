"""data 目录与文件路径的唯一定义处。

data/ 磁盘布局：

    data/config.json    用户配置（只存在于用户机器上，安装包不得覆盖）
    data/templates/     模板：内置模板 + 用户导入/编辑的模板（写入，安装包不得覆盖）
    data/assets/        随程序打包分发的只读资源（安装包整体覆盖）
      ├── api.json / emoji.json / current_version.json
      ├── qweather.db / xiaomi_weather.db
      ├── settings.ico / startinfo.ico
      └── i18n/*.qm     多语言文件（随语言数量增长，单独一层）
    data/cache/         运行时生成、可随时删除：widgets_cache.db / version.json / 下载缓存
    data/logs/          日志（每次启动生成一个文件）

划分依据是「谁负责管这些文件」，而不是文件格式：

    assets   -> 安装包分发并可直接覆盖
    config/templates -> 用户可改，安装包必须跳过已存在文件
    cache/logs -> 程序自己生成，删了不影响

命名规则：目录一律 ``*_FOLDER_PATH``，文件一律 ``*_FILE_PATH``。
本模块不依赖项目内任何其他模块，可被任意模块安全导入。
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime


# =============================================================================
# 路径获取函数
# =============================================================================
def get_main_path() -> Path:
    """智能判断主程序目录"""
    if getattr(sys, 'frozen', False):
        # 打包后：exe 所在目录就是主目录
        path = Path(sys.executable).parent

    else:
        # 开发时：本项目内调用者位于 core/ 内
        path = Path(__file__).parent.resolve()

    # 如果路径以 'core' 结尾，说明我们在 core/ 里，要退回上一级
    if path.name == 'core':
        path = path.parent

    return path


# =============================================================================
# 目录定义 (不依赖任何外部配置)
# =============================================================================
# 主目录
MAIN_PATH: Path = get_main_path()
# 数据文件夹目录
DATA_FOLDER_PATH: Path = MAIN_PATH / 'data'
# 随程序分发的只读资源目录（由安装包整体覆盖分发）
ASSETS_FOLDER_PATH: Path = DATA_FOLDER_PATH / 'assets'
# 多语言文件目录（随语言数量增长，单独一层）
I18N_FOLDER_PATH: Path = ASSETS_FOLDER_PATH / 'i18n'
# 模板文件夹路径（用户可导入/编辑，因此不放进 assets）
TEMPLATE_FOLDER_PATH: Path = DATA_FOLDER_PATH / 'templates'
# 日志文件夹路径
LOG_FOLDER_PATH: Path = DATA_FOLDER_PATH / 'logs'
# 缓存目录
CACHE_FOLDER_PATH: Path = DATA_FOLDER_PATH / 'cache'


# =============================================================================
# 数据文件路径
# =============================================================================
# 日志文件路径（按启动时刻命名，一次启动一个文件）
LOG_FILE_PATH: Path = LOG_FOLDER_PATH / f'{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.log'

# 用户配置文件（唯一会被程序写入并经用户修改的文件）
CONFIG_FILE_PATH: Path = DATA_FOLDER_PATH / 'config.json'
# 远程版本缓存（检查更新时写入）
VERSION_CACHE_FILE_PATH: Path = CACHE_FOLDER_PATH / 'version.json'
# 本地已安装版本记录（随程序分发）
CURRENT_VERSION_FILE_PATH: Path = ASSETS_FOLDER_PATH / 'current_version.json'
# API 配置（随程序分发）
API_FILE_PATH: Path = ASSETS_FOLDER_PATH / 'api.json'
# emoji 资源（随程序分发）
EMOJI_FILE_PATH: Path = ASSETS_FOLDER_PATH / 'emoji.json'

# 组件缓存数据库（运行时生成）
WIDGET_CACHE_FILE_PATH: Path = CACHE_FOLDER_PATH / 'widgets_cache.db'
# 各天气数据源的城市查询库（随程序分发，按数据源名取用）
WEATHER_DB_FILE_PATHS: dict[str, Path] = {
    'qweather': ASSETS_FOLDER_PATH / 'qweather.db',
    'xiaomi_weather': ASSETS_FOLDER_PATH / 'xiaomi_weather.db',
}


# =============================================================================
# 资源文件路径
# =============================================================================
# 设置窗口图标
SETTINGS_ICON_FILE_PATH: Path = ASSETS_FOLDER_PATH / 'settings.ico'
# 应用图标
LOGO_ICON_FILE_PATH: Path = ASSETS_FOLDER_PATH / 'startinfo.ico'
# QFluentWidgets 中文翻译文件
TRANSLATION_FILE_PATH: Path = I18N_FOLDER_PATH / 'qfw' / 'qfluentwidgets.zh_CN.qm'


# =============================================================================
# 可执行文件与系统路径
# =============================================================================
# 可执行文件路径
EXE_FILE_PATH: Path = MAIN_PATH / 'StartInfo.exe'
# 卸载程序路径
UNINSTALLER_FILE_PATH: Path = MAIN_PATH / 'unins000.exe'
# 当前用户的启动文件夹路径
WIN_STARTUP_FOLDER_PATH: Path = (
    Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' /
    'Start Menu' / 'Programs' / 'Startup'
)


# =============================================================================
# 旧版配置迁移
# =============================================================================
# 只迁移 config.json 这一个文件，理由：
#   - 它是唯一「只存在于用户机器上、不会随安装包分发」的文件，
#     不搬就会让老用户的配置静默重置；
#   - 其余资源文件由安装包整体分发到新位置（且必须用新版覆盖，否则会退回旧数据）；
#   - 缓存文件（widgets_cache.db / version.json / 下载缓存）可重新生成，无需迁移。
# config.json 在历史上只有一处旧位置。
_LEGACY_CONFIG_FILE_PATHS: tuple[Path, ...] = (
    DATA_FOLDER_PATH / 'json' / 'config.json',
)


def migrate_legacy_config() -> Path | None:
    """把旧版位置里的用户配置搬到当前位置。

    必须在读取任何数据文件之前调用（``core/__init__.py`` 已完成此事，
    早于 ``config`` 的 ``qconfig.load``）。

    若当前位置已有配置文件，直接返回 None——绝不覆盖用户现有配置。
    旧位置残留的其他资源文件不做处理，由安装包分发的新版文件接管。

    :return: 迁移后的配置文件路径；无需迁移或迁移失败时返回 None
    """
    if CONFIG_FILE_PATH.exists():
        return None

    for old_path in _LEGACY_CONFIG_FILE_PATHS:
        try:
            if not old_path.is_file():
                continue
            CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_path), str(CONFIG_FILE_PATH))
            return CONFIG_FILE_PATH
        except OSError:
            continue

    return None
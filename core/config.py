"""应用配置：验证器、配置项定义与全局 cfg 实例。

本模块只依赖 paths 与 templates，**不依赖 core.logger**：
logger.py 需要读取本模块的 ``cfg.log_level``，因此本模块只能用 loguru 的
原始 ``logger`` 单例（与 ``core.logger.log`` 是同一对象），不能反向导入它。
"""

from loguru import logger
from qfluentwidgets import (QConfig, OptionsConfigItem, OptionsValidator,
                            ColorConfigItem, ConfigItem, BoolValidator,
                            qconfig, ConfigValidator)
from datetime import datetime

from . import paths
from .i18n import get_available_languages
from .templates import get_template_files

log = logger


# ===========================================================================
# 验证器
# ===========================================================================

class StringValidator(ConfigValidator):
    """字符串验证器"""

    def __init__(self, default: str = ''):
        self._default = default

    def validate(self, value):
        return isinstance(value, str)

    def correct(self, value):
        if isinstance(value, str):
            return value
        return self._default


class IntRangeValidator(ConfigValidator):
    """整数范围验证器。"""

    def __init__(self, min_val: int = 0, max_val: float = float('inf'),
                 default_val: int = None):
        self.min_val = min_val
        self.max_val = max_val
        self.default_val = default_val if default_val is not None else min_val

    def validate(self, value):
        return isinstance(value, int) and self.min_val <= value <= self.max_val

    def correct(self, value: object) -> int:
        try:
            val = int(value)
        except (ValueError, TypeError):
            return self.default_val
        return int(max(self.min_val, min(val, self.max_val)))


class ListValidator(ConfigValidator):
    """列表验证器。"""

    def __init__(self, default: list = None):
        if default is None:
            default = []
        self._default = default

    def validate(self, value):
        return isinstance(value, list)

    def correct(self, value):
        if isinstance(value, list):
            return value
        return self._default


class DictValidator(ConfigValidator):
    """字典验证器。"""

    def __init__(self, default: dict | None = None):
        # 拷贝存储，避免多个验证器实例共享同一可变默认值
        self._default = dict(default) if default else {}

    def validate(self, value):
        return isinstance(value, dict)

    def correct(self, value):
        if isinstance(value, dict):
            return value
        return dict(self._default)


class CityDictValidator(DictValidator):
    """城市信息字典验证器：校验 {数据源: 城市名/城市ID} 格式的字典。

    correct 时以默认值铺底，保证每个数据源的键都存在，
    避免配置缺键时组件按当前数据源取值抛 KeyError。
    """

    def validate(self, value):
        return isinstance(value, dict) and len(value) > 0

    def correct(self, value):
        result = dict(self._default)
        if isinstance(value, dict):
            result.update(value)
        return result


class DateDictValidator(DictValidator):
    """日期信息字典验证器：值格式 {名称: 'YYYY-MM-DD'}"""

    @staticmethod
    def normalize(value) -> dict:
        """规范化日期字典：旧版 'YYYYMMDD' 迁移为 'YYYY-MM-DD'，无法解析的条目丢弃"""
        result = {}
        if not isinstance(value, dict):
            return result
        for key, date in value.items():
            if not isinstance(date, str):
                continue
            for fmt in ('%Y-%m-%d', '%Y%m%d'):
                try:
                    result[key] = datetime.strptime(date, fmt).strftime('%Y-%m-%d')
                    break
                except ValueError:
                    continue
        return result

    def correct(self, value):
        return self.normalize(value)

class DynamicOptionsValidator(ConfigValidator):
    """支持动态选项列表的验证器。

    选项列表通过 options_getter 在运行时动态获取，因此每次读取都能拿到
    磁盘上的最新模板列表。首次成功获取后缓存，避免重复扫描目录；
    需要重新扫描时调用 :meth:`invalidate`。
    """

    def __init__(self, options_getter):
        self._options_getter = options_getter
        self._options = None  # 首次成功获取后缓存

    @property
    def options(self) -> list:
        """兼容 OptionsConfigItem.options 的读取。"""
        return self.get_options()

    def get_options(self) -> list:
        if self._options is None:
            options = self._options_getter() or []
            if options:
                self._options = options
        return self._options or []

    def invalidate(self) -> None:
        """清除缓存的选项列表，下次读取时重新扫描获取。"""
        self._options = None

    def validate(self, value):
        if not isinstance(value, str):
            return False
        current_options = self.get_options()
        if not current_options:
            return len(value) > 0
        return value in current_options

    def correct(self, value):
        current_options = self.get_options()
        if not current_options:
            return value
        if value in current_options:
            return value
        # 配置的模板可能已被外部删除：优先回退默认模板，其次第一个可用模板
        fallback = 'default.j2' if 'default.j2' in current_options else current_options[0]
        log.warning(f'模板 {value} 不存在，已回退到 {fallback}')
        return fallback


# ===========================================================================
# 配置类
# ===========================================================================

class StartInfoConfig(QConfig):
    # =========================== General ===========================
    # 自动关闭弹窗
    auto_close_switch = ConfigItem('General', 'auto_close_switch', True, BoolValidator())
    auto_close_time = ConfigItem(
        'General', 'auto_close_time', 60,
        IntRangeValidator(min_val=30, max_val=300, default_val=60)
    )

    # 关闭设置窗口后的行为
    close_settings_action = OptionsConfigItem(
        'General', 'close_settings_action', 'restart',
        OptionsValidator(['restart', 'exit'])
    )
    # 语言（languages.json 为随程序分发的只读资源，导入时读取一次即可）
    # dynamic 表示跟随系统语言，由 AppManager._apply_language 解析为具体语言
    language = OptionsConfigItem(
        'General', 'language', 'dynamic',
        OptionsValidator(['dynamic'] + get_available_languages()),
        restart=True
    )
    # 更新源
    update_source = OptionsConfigItem(
        'General', 'update_source', 'github',
        OptionsValidator(['github', 'github_mirror'])
    )

    # 日志等级
    LOG_LEVELS = ['DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
    log_level = OptionsConfigItem('General', 'log_level', 'WARNING', OptionsValidator(LOG_LEVELS))

    # =========================== 个性化 ===========================
    # 主题
    theme = OptionsConfigItem(
        'Appearance', 'theme', 'dynamic',
        OptionsValidator(['light', 'dark', 'dynamic'])
    )
    # 主题色模式
    theme_color_mode = OptionsConfigItem(
        'Appearance', 'theme_color_mode', 'dynamic',
        OptionsValidator(['dynamic', 'custom'])
    )
    # 主题色
    theme_color = ColorConfigItem('Appearance', 'theme_color', '#0078d4')
    # 云母效果
    mica_effect_switch = ConfigItem('Appearance', 'mica_effect_switch', True, BoolValidator())
    # 模板
    template_file = OptionsConfigItem(
        'Appearance', 'template_file', 'default.j2',
        DynamicOptionsValidator(get_template_files)
    )

    # =========================== 日期和时间 ===========================
    datetime_switch = ConfigItem('DateTimeWidget', 'switch', True, BoolValidator())
    lunar_date_switch = ConfigItem('DateTimeWidget', 'lunar_date_switch', False, BoolValidator())
    solar_term_switch = ConfigItem('DateTimeWidget', 'solar_term_switch', False, BoolValidator())
    holiday_switch = ConfigItem('DateTimeWidget', 'holiday_switch', True, BoolValidator())
    other_date_switch = ConfigItem('DateTimeWidget', 'other_date_switch', False, BoolValidator())

    # =========================== 天气 ===========================
    # 城市信息默认值（按天气数据源分别存储）
    DEFAULT_CITY_NAMES = {'qweather': '北京', 'xiaomi_weather': '北京'}
    DEFAULT_CITY_IDS = {'qweather': '101010100', 'xiaomi_weather': '101010100'}

    weather_switch = ConfigItem('WeatherWidget', 'switch', False, BoolValidator())
    city_name = ConfigItem(
        'WeatherWidget', 'city_name', DEFAULT_CITY_NAMES,
        CityDictValidator(DEFAULT_CITY_NAMES)
    )
    city_id = ConfigItem(
        'WeatherWidget', 'city_id', DEFAULT_CITY_IDS,
        CityDictValidator(DEFAULT_CITY_IDS)
    )
    qweather_api_host = ConfigItem('WeatherWidget', 'qweather_api_host', '' ,StringValidator())
    qweather_api_key = ConfigItem('WeatherWidget', 'qweather_api_key', '', StringValidator())
    weather_data_refresh_interval = ConfigItem(
        'WeatherWidget', 'data_refresh_interval', 30,
        IntRangeValidator(min_val=15, max_val=60, default_val=30)
    )
    weather_source = OptionsConfigItem(
        'WeatherWidget', 'source', 'xiaomi_weather',
        OptionsValidator(['xiaomi_weather', 'qweather'])
    )

    # =========================== 倒数日 ===========================
    countdown_switch = ConfigItem('CountdownDayWidget', 'switch', False, BoolValidator())
    countdown_name = ConfigItem('CountdownDayWidget', 'name', '', StringValidator())
    countdown_date = ConfigItem('CountdownDayWidget', 'date', '', StringValidator())
    countdown_days_dict = ConfigItem('CountdownDayWidget', 'countdown_days_dict', {}, DateDictValidator())

    # =========================== 生日祝福 ===========================
    birthday_wishes_switch = ConfigItem('BirthdayWishesWidget', 'switch', False, BoolValidator())
    birthday_dict = ConfigItem('BirthdayWishesWidget', 'birthdays_dict', {}, DateDictValidator())

    # =========================== MC服务器检测 ===========================
    mc_server_info_switch = ConfigItem(
        'MCServerInfoWidget', 'switch', False, BoolValidator(),
    )
    mc_server_name = ConfigItem(
        'MCServerInfoWidget', 'server_name', '',
        StringValidator()
    )
    mc_server_ip = ConfigItem(
        'MCServerInfoWidget', 'server_ip', '',
        StringValidator()
    )
    mc_server_port = ConfigItem(
        'MCServerInfoWidget', 'server_port', '25565',
        StringValidator(default='25565')
    )
    mc_server_friends_list = ConfigItem(
        'MCServerInfoWidget', 'friends_list', [],
        ListValidator(default=[])
    )
    mc_server_data_refresh_interval = ConfigItem(
        'MCServerInfoWidget', 'data_refresh_interval', 60,
        IntRangeValidator(min_val=5, max_val=3600, default_val=60)
    )

    # =========================== 每日一言 ===========================
    words_switch = ConfigItem('EveryDayWordsWidget', 'switch', True, BoolValidator())
    words_source = OptionsConfigItem(
        'EveryDayWordsWidget', 'source', 'hitokoto',
        OptionsValidator(['hitokoto', 'iciba'])
    )

    # =========================== GitHub仓库信息 ===========================
    github_repo_switch = ConfigItem('GitHubRepoInfoWidget', 'switch', False, BoolValidator())
    github_repo_owner = ConfigItem('GitHubRepoInfoWidget', 'repo_owner', '', StringValidator())
    github_repo_name = ConfigItem('GitHubRepoInfoWidget', 'repo_name', '', StringValidator())
    github_repo_data_refresh_interval = ConfigItem(
        'GitHubRepoInfoWidget', 'data_refresh_interval', 1,
        IntRangeValidator(min_val=1, max_val=24, default_val=1)
    )

    # =========================== InformationSwitch (组件开关) ===========================
    greeting_switch = ConfigItem('OtherWidgetsSwitch', 'greeting_widget', True, BoolValidator())
    startup_times_switch = ConfigItem('OtherWidgetsSwitch', 'startup_times_widget', True, BoolValidator())
    historical_switch = ConfigItem('OtherWidgetsSwitch', 'historical_widget', False, BoolValidator())
    daily_character_switch = ConfigItem(
        'OtherWidgetsSwitch', 'daily_character_widget', False, BoolValidator()
    )

cfg = StartInfoConfig()
qconfig.load(paths.CONFIG_FILE_PATH, cfg)

# ===========================================================================
# 配置写入统一日志
# qfluentwidgets 的所有设置卡片（含 qconfig.set / cfg.set）都经由 QConfig.set
# 落盘，补丁这一个方法即可覆盖全部写路径。只记字段路径、不记值，
# 避免 API Key、Token 等敏感数据进入日志。
# ===========================================================================
_orig_config_set = QConfig.set


def _logged_config_set(self, item, value, save=True, copy=True):
    # 与原始实现保持一致：值未变化时跳过，避免写日志噪声
    if getattr(item, 'value', object()) == value:
        return _orig_config_set(self, item, value, save=save, copy=copy)

    log.debug(f'配置项变更: {item.key} (save={save})')
    return _orig_config_set(self, item, value, save=save, copy=copy)


QConfig.set = _logged_config_set

__all__ = [
    'cfg', 'qconfig', 'StartInfoConfig',
    'StringValidator', 'IntRangeValidator', 'DynamicOptionsValidator',
    'CityDictValidator',
]
from qfluentwidgets import (QConfig, OptionsConfigItem, OptionsValidator,
                            ColorConfigItem, ColorValidator,
                            ConfigItem, BoolValidator, qconfig, ConfigValidator)
from . import paths as lib


# ===========================================================================
# 验证器
# ===========================================================================

class StringValidator(ConfigValidator):
    """非空字符串验证器"""
    def __init__(self, default: str = "未知"):
        self._default = default

    def validate(self, value):
        return isinstance(value, str) and len(value) > 0

    def correct(self, value):
        if isinstance(value, str) and len(value) > 0:
            return value
        return self._default


class IntRangeValidator(ConfigValidator):
    """整数范围验证器"""
    def __init__(self, min_val: int = 0, max_val: float = float('inf'), default_val: int = None):
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


class DynamicOptionsValidator(ConfigValidator):
    """支持动态选项列表的验证器。

    选项列表通过 options_getter 在运行时动态获取。
    构造时不调用 getter：config.py 类体执行期间 ht_lib 可能尚未完成加载
    （ht_lib 在顶层 import 本模块的 cfg），立即调用会触发循环导入。
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
        return value if value in current_options else current_options[0]


# ===========================================================================
# 辅助函数
# ===========================================================================

def _get_template_files() -> list:
    """延迟导入 ht_lib 的 get_template_files，避免 config ↔ ht_lib 循环依赖。

    ht_lib 在模块顶层 import 本模块的 cfg，因此本模块不能在顶层直接
    import ht_lib；改为在调用时导入。若 ht_lib 仍在加载中（构造验证器
    时触发的调用），返回空列表，配置项使用默认值即可。
    """
    try:
        from .ht_lib import get_template_files
        return get_template_files()
    except ImportError:
        return []


# ===========================================================================
# 配置类
# ===========================================================================

class MyConfig(QConfig):
    # =========================== General ===========================

    # 模板
    template_file = OptionsConfigItem(
        'General', 'template_file', 'default.j2',
        DynamicOptionsValidator(_get_template_files),
    )

    # 主题
    theme = OptionsConfigItem(
        'General', 'theme', 'dynamic',
        OptionsValidator(['light', 'dark', 'dynamic']),
    )
    use_win_theme_color = ConfigItem('General', 'use_win_theme_color', True, BoolValidator())
    theme_color = ColorConfigItem('General', 'theme_color', '#ff009faa', ColorValidator(default='#ff009faa'))

    # 自动关闭弹窗
    auto_close_switch = ConfigItem('General', 'auto_close_switch', False, BoolValidator())
    auto_close_time = ConfigItem('General', 'auto_close_time', 60, IntRangeValidator(min_val=30, max_val=300, default_val=60))

    # 关闭设置窗口后的行为
    close_settings_action = OptionsConfigItem(
        'General', 'close_settings_action', 'restart',
        OptionsValidator(['restart', 'exit']),
    )

    # 日志等级
    LOG_LEVELS = ['DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
    log_level = OptionsConfigItem('General', 'log_level', 'WARNING', OptionsValidator(LOG_LEVELS))

    # =========================== 日期和时间 ===========================
    datetime_switch = ConfigItem('DateTime', 'switch', True, BoolValidator())
    lunar_date_switch = ConfigItem('DateTime', 'lunar_date_switch', False, BoolValidator())
    solar_term_switch = ConfigItem('DateTime', 'solar_term_switch', False, BoolValidator())
    holiday_switch = ConfigItem('DateTime', 'holiday_switch', True, BoolValidator())
    other_date_switch = ConfigItem('DateTime', 'other_date_switch', False, BoolValidator())

    # =========================== 天气 ===========================
    weather_switch = ConfigItem('Weather', 'switch', False, BoolValidator())
    city_name = ConfigItem('Weather', 'city_name', '北京市', StringValidator(default='北京市'))
    city_id = ConfigItem('Weather', 'city_id', {'qweather': '101010100', 'xiaomi_weather': '101010100'})
    weather_interval = ConfigItem('Weather', 'interval', 30, IntRangeValidator(min_val=15, max_val=60, default_val=30))
    weather_source = OptionsConfigItem(
        'Weather', 'source', 'xiaomi_weather',
        OptionsValidator(['xiaomi_weather', 'qweather'])
    )
    qweather_api_key = ConfigItem('Weather', 'qweather_api_key', '', StringValidator(default=''))

    # =========================== 倒数日 ===========================
    countdown_switch = ConfigItem('Countdown', 'switch', False, BoolValidator())
    countdown_name = ConfigItem('Countdown', 'name', '', StringValidator(default=''))
    countdown_date = ConfigItem('Countdown', 'date', '', StringValidator(default=''))

    # =========================== 生日祝福 ===========================
    birthday_wishes_switch = ConfigItem('BirthdayWishes', 'switch', False, BoolValidator())
    birthday_dict = ConfigItem('BirthdayWishes', 'birthday_dict', {'黄桃': '20100403'})

    # =========================== MC服务器检测 ===========================
    minecraft_server_checker_switch = ConfigItem('MinecraftJavaServerChecker', 'switch', False, BoolValidator())
    minecraft_server_name = ConfigItem('MinecraftJavaServerChecker', 'server_name', '', StringValidator(default=''))
    minecraft_server_ip = ConfigItem('MinecraftJavaServerChecker', 'server_ip', '', StringValidator(default=''))
    minecraft_server_port = ConfigItem('MinecraftJavaServerChecker', 'server_port', '25565', StringValidator(default='25565'))
    minecraft_server_friends_list = ConfigItem('MinecraftJavaServerChecker', 'friends_list', [])
    minecraft_server_data_refresh_interval = ConfigItem('MinecraftJavaServerChecker', 'data_refresh_interval', 60, IntRangeValidator(min_val=5, default_val=60))

    # =========================== 每日一言 ===========================
    words_switch = ConfigItem('EveryDayWords', 'switch', True, BoolValidator())
    words_source = OptionsConfigItem(
        'EveryDayWords', 'source', 'hitokoto',
        OptionsValidator(['hitokoto', 'iciba'])
    )

    # =========================== InformationSwitch (组件开关) ===========================
    greeting_switch = ConfigItem('InformationSwitch', 'greeting', True, BoolValidator())
    startup_times_switch = ConfigItem('InformationSwitch', 'startup_times', True, BoolValidator())
    historical_switch = ConfigItem('InformationSwitch', 'historical', False, BoolValidator())
    daily_character_switch = ConfigItem('InformationSwitch', 'daily_character', False, BoolValidator())

cfg = MyConfig()
qconfig.load(lib.CONFIG_FILE_PATH, cfg)

__all__ = ['cfg', 'qconfig', 'MyConfig']

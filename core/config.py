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


class DynamicOptionsValidator(OptionsValidator):
    """支持动态选项列表的验证器"""
    def __init__(self, options_getter):
        self._options_getter = options_getter
        super().__init__(options_getter())

    def get_options(self):
        return self._options_getter()

    def validate(self, value):
        if not isinstance(value, str):
            return False
        current_options = self.get_options()
        if not current_options:
            return len(value) > 0
        return value in current_options


# ===========================================================================
# 辅助函数
# ===========================================================================

def get_template_files() -> list:
    """扫描模板文件夹，获取所有 .j2 模板文件名"""
    if not lib.TEMPLATE_FOLDER_PATH.exists():
        return ['default.j2']
    files = [
        p.name for p in lib.TEMPLATE_FOLDER_PATH.glob('*.j2')
        if p.is_file() and p.name != 'birthday_wishes.j2'
    ]
    if not files:
        return ['default.j2']
    return files


# ===========================================================================
# 配置类
# ===========================================================================

class MyConfig(QConfig):
    # =========================== General ===========================

    # 模板
    template_file = OptionsConfigItem(
        'General', 'template_file', 'default.j2',
        DynamicOptionsValidator(get_template_files),
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

    # =========================== 倒数日 ===========================

    countdown_switch = ConfigItem('Countdown', 'switch', False, BoolValidator())
    countdown_name = ConfigItem('Countdown', 'name', '', StringValidator(default=''))
    countdown_date = ConfigItem('Countdown', 'date', '', StringValidator(default=''))

    # =========================== 天气&空气质量 ===========================

    weather_switch = ConfigItem('Weather', 'switch', False, BoolValidator())
    city_name = ConfigItem('Weather', 'city_name', '北京市', StringValidator(default='北京市'))
    city_id = ConfigItem('Weather', 'city_id', '101010100', StringValidator(default='101010100'))
    weather_interval = ConfigItem('Weather', 'interval', 30, IntRangeValidator(min_val=15, max_val=60, default_val=30))

    air_quality_switch = ConfigItem('AirQuality', 'switch', False, BoolValidator())
    air_quality_interval = ConfigItem('AirQuality', 'interval', 120, IntRangeValidator(min_val=15, max_val=240, default_val=120))

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
        'EveryDayWords', 'words_source', 'hitokoto',
        OptionsValidator(['hitokoto', 'iciba']),
    )

    # =========================== InformationSwitch (组件开关) ===========================

    greeting_switch = ConfigItem('InformationSwitch', 'greeting', True, BoolValidator())
    startup_times_switch = ConfigItem('InformationSwitch', 'startup_times', True, BoolValidator())
    datetime_switch = ConfigItem('InformationSwitch', 'datetime', True, BoolValidator())
    holiday_solar_term_switch = ConfigItem('InformationSwitch', 'holiday_solar_term', True, BoolValidator())
    historical_switch = ConfigItem('InformationSwitch', 'historical', True, BoolValidator())


cfg = MyConfig()
qconfig.load(lib.CONFIG_FILE_PATH, cfg)

__all__ = ['cfg', 'qconfig', 'MyConfig']

from qfluentwidgets import (QConfig, OptionsConfigItem, OptionsValidator,ColorConfigItem,ColorValidator,
                            ConfigItem, BoolValidator, Theme, qconfig, EnumSerializer, ConfigValidator)
from . import ht_lib as lib


class StringValidator(ConfigValidator):
    def validate(self, value):
        """验证值是否为非空字符串"""
        return isinstance(value, str) and len(value) > 0

    def correct(self, value):
        """修正值：如果不是有效字符串，返回默认值；否则返回原值"""
        if isinstance(value, str) and len(value) > 0:
            return value
        return "未知"  # 默认值


class IntRangeValidator(ConfigValidator):
    def __init__(self, min_val: int = 0, max_val: float = float('inf'), default_val: int = None):
        """
        :param min_val: 最小值，默认 0
        :param max_val: 最大值，默认正无穷（即不设上限）
        """
        self.min_val = min_val
        self.max_val = max_val
        # 如果不传默认值，修正时回到最小值
        self.default_val = default_val if default_val is not None else min_val

    def validate(self, value):
        return isinstance(value, int) and self.min_val <= value <= self.max_val

    def correct(self, value):
        try:
            val = int(value)
        except (ValueError, TypeError):
            return self.default_val

        # 即使 max_val 是无穷大，min(val, inf) 依然等于 val，逻辑完美通杀
        return int(max(self.min_val, min(val, self.max_val)))

class DynamicOptionsValidator(OptionsValidator):
    """支持动态选项列表的验证器"""
    def __init__(self, options_getter):
        """
        :param options_getter: 一个函数，返回选项列表
        """
        self._options_getter = options_getter
        # 初始化时调用一次父类的初始化，传入初始选项
        super().__init__(options_getter())

    def get_options(self):
        """动态获取选项列表"""
        return self._options_getter()

    def validate(self, value):
        """验证值是否在选项列表中"""
        if not isinstance(value, str):
            return False
        # 如果选项列表为空，只验证是否为字符串
        current_options = self.get_options()
        if not current_options:
            return len(value) > 0
        return value in current_options

class MyConfig(QConfig):
    # ===== General部分 =====
    # 模板
    @staticmethod
    def get_template_files() -> list:
        """
        扫描模板文件夹，动态获取所有 .j2 结尾的模板文件名
        :return: 模板文件名列表，若为空则返回保底默认值
        """
        # 1. 确保文件夹存在，不存在就返回默认
        if not lib.TEMPLATE_FOLDER_PATH.exists():
            return ["default.j2"]

        # 2. 扫描所有 .j2 文件，不包含 birthday_wishes.j2
        files = [
            p.name for p in lib.TEMPLATE_FOLDER_PATH.glob("*.j2")
            if p.is_file() and p.name != 'birthday_wishes.j2'
        ]

        # 3. 关键：QFW 的 OptionsConfigItem 严禁返回空列表
        # 如果没找到任何文件，手动塞一个默认值进去
        if not files:
            return ["default.j2"]

        return files

    template_file = OptionsConfigItem('General', 'template_file', 'default.j2', DynamicOptionsValidator(get_template_files))

    # 主题
    theme = OptionsConfigItem(
        "General", "theme", 'dynamic',
        OptionsValidator(["light", "dark", "dynamic"]),
        # restart=True  # 建议开启，因为切换主题通常需要重启窗口来彻底刷新 UI
    )

    # 使用系统主题色
    use_win_theme_color = ConfigItem('General', 'use_win_theme_color', True, BoolValidator())

    # 主题色
    theme_color = ColorConfigItem("General", "theme_color", '#ff009faa',ColorValidator(default='#ff009faa'))
    # 倒数日功能
    countdown_switch = ConfigItem('Countdown', 'switch', False, BoolValidator())
    countdown_text = ConfigItem('Countdown', 'text', '',StringValidator())
    countdown_date = ConfigItem('Countdown', 'date', '', StringValidator())

    # 自动关闭
    auto_close_switch = ConfigItem('General', 'auto_close_switch', False, BoolValidator())
    # 自动关闭时间(单位：秒，范围：30~300秒)
    auto_close_time = ConfigItem('General', 'auto_close_time', 60, IntRangeValidator(min_val=30, max_val=300, default_val=60))
    # 关闭设置窗口后的行为
    close_settings_action = OptionsConfigItem('General', 'close_settings_action', 'restart', OptionsValidator(['restart', 'exit']))

    # ===== Weather部分 =====
    weather_switch = ConfigItem('Weather', 'switch', True, BoolValidator())
    city_name = ConfigItem('Weather', 'city_name', '北京市',StringValidator())
    city_id = ConfigItem('Weather', 'city_id', '101010100',StringValidator())
    # 天气数据更新间隔(单位：分钟，范围：15~60分钟)
    weather_interval = ConfigItem('Weather', 'interval', 30, IntRangeValidator(min_val=15, max_val=60, default_val=30))

    # ===== BirthdayWishes部分 =====
    birthday_wishes_switch = ConfigItem('BirthdayWishes', 'switch', False, BoolValidator())
    birthday_dict = ConfigItem('BirthdayWishes', 'birthday_dict', {'黄桃': '20100403'})

    # ===== Minecraft Java Server Checker部分 =====
    minecraft_server_checker_switch = ConfigItem('MinecraftJavaServerChecker', 'switch', False, BoolValidator())
    minecraft_server_name = ConfigItem('MinecraftJavaServerChecker', 'server_name', '', StringValidator())
    minecraft_server_ip = ConfigItem('MinecraftJavaServerChecker', 'server_ip', '', StringValidator())
    minecraft_server_data_refresh_interval = ConfigItem('MinecraftJavaServerChecker', 'data_refresh_interval', 60, IntRangeValidator(min_val=5, default_val=60))
    minecraft_server_port = ConfigItem('MinecraftJavaServerChecker', 'server_port', '25565', StringValidator())
    minecraft_server_friends_list = ConfigItem('MinecraftJavaServerChecker', 'friends_list', [])

    # ===== 信息开关部分 =====
    greeting_switch = ConfigItem('InformationSwitch', 'greeting', True, BoolValidator())
    datetime_switch = ConfigItem('InformationSwitch', 'datetime', True, BoolValidator())
    historical_switch = ConfigItem('InformationSwitch', 'historical', True, BoolValidator())
    words_switch = ConfigItem('InformationSwitch', 'words', True, BoolValidator())
    startup_times_switch = ConfigItem('InformationSwitch', 'startup_times', True, BoolValidator())

    # ===== 调试 =====
    # 日志等级列表
    log_level_list = ['DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
    log_level = OptionsConfigItem('General', 'log_level', 'WARNING', OptionsValidator(log_level_list))
    # 禁用旧版设置
    ban_old_settings = ConfigItem('General', 'ban_old_settings', False, BoolValidator())

cfg = MyConfig()
# 建议加上路径，确保它生成在你项目的 data 目录下
qconfig.load(lib.CONFIG_FILE_PATH, cfg)

# 导出 qconfig 和 cfg，方便其他模块使用
__all__ = ['cfg', 'qconfig', 'MyConfig']

# 添加调试日志，检查配置项是否正确加载
# lib.log.info(f'配置加载：city_name 类型 = {type(cfg.city_name)}, 值 = {cfg.city_name.value if hasattr(cfg.city_name, "value") else cfg.city_name}')
# lib.log.info(f'配置加载：city_id 类型 = {type(cfg.city_id)}, 值 = {cfg.city_id.value if hasattr(cfg.city_id, "value") else cfg.city_id}')
# lib.log.info(f'配置加载：birthday_wishes_switch 类型 = {type(cfg.birthday_wishes_switch)}, 值 = {cfg.birthday_wishes_switch.value if hasattr(cfg.birthday_wishes_switch, "value") else cfg.birthday_wishes_switch}')
# lib.log.info(f'配置加载：birthday_dict 类型 = {type(cfg.birthday_dict)}, 值 = {cfg.birthday_dict.value if hasattr(cfg.birthday_dict, "value") else cfg.birthday_dict}')
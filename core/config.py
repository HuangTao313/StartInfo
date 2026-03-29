from qfluentwidgets import (QConfig, OptionsConfigItem, OptionsValidator,ColorConfigItem,
                            ConfigItem, BoolValidator, Theme, qconfig, EnumSerializer, ConfigValidator)
from . import ht_lib as lib

# 配置文件路径

# 模板文件
# template_files = [p.name for p in lib.TEMPLATE_FOLDER_PATH.glob("*.j2") if p.is_file()]

class StringValidator(ConfigValidator):
    def validate(self, value):
        """验证值是否为非空字符串"""
        return isinstance(value, str) and len(value) > 0

    def correct(self, value):
        """修正值：如果不是有效字符串，返回默认值；否则返回原值"""
        if isinstance(value, str) and len(value) > 0:
            return value
        return "北京市"  # 默认值

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
    def get_template_files():
        """动态获取模板文件列表"""
        return [p.name for p in lib.TEMPLATE_FOLDER_PATH.glob("*.j2") if p.is_file()]

    template_file = OptionsConfigItem('General', 'template_file', 'default.j2', DynamicOptionsValidator(get_template_files))

    # 主题
    theme = OptionsConfigItem(
        "General", "theme", 'dynamic',
        OptionsValidator(["light", "dark", "dynamic"]),
        # restart=True  # 建议开启，因为切换主题通常需要重启窗口来彻底刷新 UI
    )

    # 主题色
    # theme_color = ColorConfigItem("General", "theme_color", ColorConfigItem())
    # 倒数日功能
    countdown = ConfigItem('General', 'countdown', False, BoolValidator())

    startup = ConfigItem("General", "startup", False, BoolValidator())

    # ===== Weather部分 =====
    city_name = ConfigItem('Weather', 'city_name', '北京市',StringValidator())
    city_id = ConfigItem('Weather', 'city_id', '101010100',StringValidator())

    # ===== BirthdayWishes部分 =====
    birthday_wishes = ConfigItem('BirthdayWishes', 'birthday_wishes', False, BoolValidator())
    birthday_dict = ConfigItem('BirthdayWishes', 'birthday_dict', {'黄桃': '20100403'})

cfg = MyConfig()
# 建议加上路径，确保它生成在你项目的 data 目录下
qconfig.load(lib.CONFIG_FILE_PATH, cfg)

# 导出 qconfig 和 cfg，方便其他模块使用
__all__ = ['cfg', 'qconfig', 'MyConfig']

# 添加调试日志，检查配置项是否正确加载
lib.log.info(f'配置加载：city_name 类型 = {type(cfg.city_name)}, 值 = {cfg.city_name.value if hasattr(cfg.city_name, "value") else cfg.city_name}')
lib.log.info(f'配置加载：city_id 类型 = {type(cfg.city_id)}, 值 = {cfg.city_id.value if hasattr(cfg.city_id, "value") else cfg.city_id}')
lib.log.info(f'配置加载：birthday_wishes 类型 = {type(cfg.birthday_wishes)}, 值 = {cfg.birthday_wishes.value if hasattr(cfg.birthday_wishes, "value") else cfg.birthday_wishes}')
lib.log.info(f'配置加载：birthday_dict 类型 = {type(cfg.birthday_dict)}, 值 = {cfg.birthday_dict.value if hasattr(cfg.birthday_dict, "value") else cfg.birthday_dict}')
"""组件系统门面包：组件框架 + 内置组件。

- :mod:`core.widgets.framework` —— 组件框架（基类 / 缓存 / 注册表）
- :mod:`core.widgets.builtin`   —— StartInfo 内置组件，全部集中在这一个文件内

包外请统一使用本门面包，例如：

    from core.widgets import WeatherWidget, NetworkWidgetBase, register

注意：导入本包会连带导入内置组件（读取 ``api.json`` / ``emoji.json``、
导入 lunar_python 等），这是「框架与内置组件打包在一起」的既定取舍。
"""

from .framework import (APIConfig, CacheManager, ExtNetworkWidgetBase,
                        LocalWidgetBase, NetworkWidgetBase, WidgetInfo,
                        register, registered_widgets)
from .widgets import (BirthdayWidget, CountDownDayWidget, DailyCharacterWidget,
                      DailyWordsWidget, DateTimeWidget, GitHubRepoInfoWidget,
                      GreetingWidget, MCServerError, MCServerInfoWidget,
                      StartupTimesWidget, TodayInHistoryWidget, WeatherWidget,
                      global_date)

__all__ = [
    # 框架
    'APIConfig', 'CacheManager', 'ExtNetworkWidgetBase', 'LocalWidgetBase',
    'NetworkWidgetBase', 'WidgetInfo', 'register', 'registered_widgets',
    # 内置组件
    'BirthdayWidget', 'CountDownDayWidget', 'DailyCharacterWidget',
    'DailyWordsWidget', 'DateTimeWidget', 'GitHubRepoInfoWidget',
    'GreetingWidget', 'MCServerError', 'MCServerInfoWidget',
    'StartupTimesWidget', 'TodayInHistoryWidget', 'WeatherWidget',
    'global_date',
]
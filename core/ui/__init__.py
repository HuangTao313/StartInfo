"""界面层门面包。

- :mod:`core.ui.app`       —— QApplication / qasync 事件循环 / 主题管理
- :mod:`core.ui.dialogs`   —— 应用级弹窗、通知与更新下载框
- :mod:`core.ui.controls`  —— 可复用设置卡片与编辑框
- :mod:`core.ui.settings_pages` —— 设置窗口的三个页面

包外请使用本门面包，例如::

    from core.ui import app_manager, dialog, Notify, BasicSettingsPage

包内模块之间请使用相对导入（``from .dialogs import ...``），
不要写 ``from core import ui``，避免门面包半初始化。
导入顺序即依赖顺序：app → dialogs → controls → 页面。
"""

from .app import AppManager, app_manager, get_theme_color, tr
from .dialogs import dialog, error_dialog, file_dialog, main_window
from .ui_widgets import (BaseSettingPage, BirthdayEditBox, BirthdayTableDelegate,
                         CalendarSettingCard, CitySearchBox, ExpandGroupCard,
                         ExtSwitchSettingCard, ListEditingBox, TextSettingCard,
                         Notify, UpdateDownloadBox, action)
from .switch_button import IndicatorPosition, SwitchButton
from .settings_pages import (AboutSettingsPage, AppearanceSettingsPage,
                             BasicSettingsPage)
from ..i18n import (get_system_language, get_available_languages,
                    get_language_names)

__all__ = [
    # app
    'AppManager', 'app_manager', 'get_theme_color', 'tr',
    # i18n
    'get_system_language', 'get_available_languages', 'get_language_names',
    # dialogs
    'Notify', 'UpdateDownloadBox', 'action', 'dialog', 'error_dialog',
    'file_dialog', 'main_window',
    # controls
    'BaseSettingPage', 'BirthdayEditBox', 'BirthdayTableDelegate',
    'CalendarSettingCard', 'CitySearchBox', 'ExpandGroupCard',
    'ExtSwitchSettingCard', 'ListEditingBox', 'TextSettingCard',
    # switch button
    'IndicatorPosition', 'SwitchButton',
    # 设置页
    'BasicSettingsPage', 'AppearanceSettingsPage', 'AboutSettingsPage',
]
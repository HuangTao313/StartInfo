"""界面层门面包。

- :mod:`core.ui.app`            —— QApplication / qasync 事件循环 / 主题管理
- :mod:`core.ui.dialogs`        —— 应用级弹窗（dialog / main_window / error_dialog / file_dialog）
- :mod:`core.ui.ui_widgets`     —— 设置页基底、城市搜索与更新弹窗、通知/异步操作工具
- :mod:`core.ui.setting_cards`  —— 设置卡片与编辑框
- :mod:`core.ui.switch_button`  —— 自定义开关按钮
- :mod:`core.ui.settings_pages` —— 设置窗口的三个页面

包外请使用本门面包，例如::

    from core.ui import app_manager, dialog, Notify, BasicSettingsPage

包内模块之间请使用相对导入（``from .dialogs import ...``），
不要写 ``from core import ui``，避免门面包半初始化。
导入顺序即依赖顺序：app → dialogs → ui_widgets → setting_cards → 页面。
"""

from .app import AppManager, app_manager, get_theme_color, tr
from .dialogs import dialog, error_dialog, file_dialog, main_window
from .settings_pages import (AboutSettingsPage, AppearanceSettingsPage,
                             BasicSettingsPage)
from .switch_button import IndicatorPosition, SwitchButton
from .ui_widgets import (BaseSettingPage, CitySearchBox, Notify,
                         UpdateDownloadBox, action)
from .setting_cards import (DateTableDelegate, DateTableEditBox,
                            DateTableEditSettingCard, EditingSettingCardBase,
                            ExpandGroupCard, ExtSwitchSettingCard, ListEditingBox,
                            ListEditingSettingCard, TextSettingCard)
from ..i18n import (get_system_language, get_available_languages,
                    get_language_names)

__all__ = [
    # app
    'AppManager', 'app_manager', 'get_theme_color', 'tr',
    # i18n
    'get_system_language', 'get_available_languages', 'get_language_names',
    # dialogs
    'dialog', 'error_dialog', 'file_dialog', 'main_window',
    # ui_widgets
    'BaseSettingPage', 'CitySearchBox', 'Notify', 'UpdateDownloadBox', 'action',
    # setting_cards
    'DateTableDelegate', 'DateTableEditBox', 'DateTableEditSettingCard',
    'EditingSettingCardBase', 'ExpandGroupCard', 'ExtSwitchSettingCard',
    'ListEditingBox', 'ListEditingSettingCard', 'TextSettingCard',
    # switch button
    'IndicatorPosition', 'SwitchButton',
    # 设置页
    'BasicSettingsPage', 'AppearanceSettingsPage', 'AboutSettingsPage',
]
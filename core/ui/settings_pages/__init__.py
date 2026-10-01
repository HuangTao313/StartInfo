"""设置窗口的页面集合。

- :mod:`core.ui.settings_pages.basic`      —— 基本设置
- :mod:`core.ui.settings_pages.appearance` —— 个性化
- :mod:`core.ui.settings_pages.about`      —— 关于

页面依赖 ``core.ui`` 的 app / dialogs / controls，必须晚于它们导入；
``core/ui/__init__.py`` 已保证这一顺序。

包外推荐直接用上层门面包（一段式）：``from core.ui import BasicSettingsPage``；
需要直接引用本包时使用 ``from core.ui.settings_pages import BasicSettingsPage``。
"""

from .basic import BasicSettingsPage
from .appearance import AppearanceSettingsPage
from .about import AboutSettingsPage

__all__ = ['AboutSettingsPage', 'AppearanceSettingsPage', 'BasicSettingsPage']

"""新版设置窗口入口。"""
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from qfluentwidgets import FluentWindow, FluentIcon

import sys
import core.ht_lib as lib
import core.ui as ui
from core.view.about_settings_page import AboutSettingsPage
from core.view.basic_settings_page import BasicSettingsPage
from core.view.custom_settings_page import CustomSettingsPage
from core.view.ui_widgets import Notify
from core.config import cfg

# 常量
SETTINGS_ICON = lib.DATA_FOLDER_PATH / 'icons' / 'settings.ico'


class SettingsWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('开机速览-设置')
        self.resize(1000, 800)
        self.setMinimumSize(800, 600)
        self._center()
        if SETTINGS_ICON.exists():
            self.setWindowIcon(QIcon(str(SETTINGS_ICON)))

        self.addSubInterface(BasicSettingsPage(self), FluentIcon.SETTING, '基本设置')
        self.addSubInterface(CustomSettingsPage(self), FluentIcon.BRUSH, '个性化')
        self.addSubInterface(AboutSettingsPage(self), FluentIcon.INFO, '关于')

        # 系统兼容性警告
        if lib.system != 'Windows':
            Notify.warning(content='当前系统暂不支持某些功能', parent=self)

    def _center(self):
        screen = ui.app_manager.get_app().primaryScreen()
        geo = screen.availableGeometry()
        x = (geo.width() - self.width()) // 2
        y = (geo.height() - self.height()) // 2
        self.move(x, y)


def start_settings():
    w = SettingsWindow()
    w.setAttribute(Qt.WA_DeleteOnClose)
    w.show()

    loop = ui.app_manager.get_loop()
    w.destroyed.connect(loop.quit)

    with loop:
        loop.run_forever()

    if cfg.close_settings_action.value == 'restart':
        from core.ht_lib import restart_program
        restart_program()

    else:
        sys.exit()


if __name__ == '__main__':
    start_settings()

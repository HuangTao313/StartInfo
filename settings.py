"""新版设置窗口入口。"""
import sys

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from qfluentwidgets import FluentWindow, FluentIcon, NavigationItemPosition, SplashScreen

import core.base_lib as lib
import core.ui as ui
from core.config import cfg
from core.view.about_settings_page import AboutSettingsPage
from core.view.basic_settings_page import BasicSettingsPage
from core.view.custom_settings_page import CustomSettingsPage

# 图标
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

        # 云母效果FluentWindow在Windows11默认启用，如果未启用云母效果，则禁用
        if not cfg.mica_effect_switch.value:
            self.set_mica_enabled(False)

        # 1. 创建启动页面
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(96, 96))

        # 2. 在创建其他子页面前先显示主界面
        self.show()

        # 3.创建子界面
        self.addSubInterface(BasicSettingsPage(self), FluentIcon.SETTING, '基本设置')
        self.addSubInterface(CustomSettingsPage(self), FluentIcon.BRUSH, '个性化')
        self.addSubInterface(AboutSettingsPage(self), FluentIcon.INFO, '关于',NavigationItemPosition.BOTTOM)

        # 4. 隐藏启动页面
        self.splashScreen.finish()

    def set_mica_enabled(self, enabled: bool):
        self.setMicaEffectEnabled(enabled)

    def _center(self):
        screen = ui.app_manager.get_app().primaryScreen()
        geo = screen.availableGeometry()
        x = (geo.width() - self.width()) // 2
        y = (geo.height() - self.height()) // 2
        self.move(x, y)


def start_settings():
    app = ui.app_manager.get_app()
    w = SettingsWindow()
    w.show()
    loop = ui.app_manager.get_loop()
    with loop:
        loop.run_forever()

    if cfg.close_settings_action.value == 'restart':
        from core.base_lib import restart_program
        restart_program()

    else:
        sys.exit()


if __name__ == '__main__':
    start_settings()
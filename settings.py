"""新版设置窗口入口。"""
import sys

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from qfluentwidgets import FluentWindow, FluentIcon, NavigationItemPosition, SplashScreen

import core.ui as ui
from core.base_lib import restart_program, system
from core.config import cfg
from core.paths import SETTINGS_ICON_FILE_PATH
from core.ui import AboutSettingsPage, AppearanceSettingsPage, BasicSettingsPage

# 图标
SETTINGS_ICON = SETTINGS_ICON_FILE_PATH

class SettingsWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr('开机速览-设置'))
        self.resize(1000, 800)
        self.setMinimumSize(800, 600)
        self._center()
        if SETTINGS_ICON.exists():
            self.setWindowIcon(QIcon(str(SETTINGS_ICON)))

        # 云母效果仅支持 Windows 11
        # 未启用或系统不支持时，关闭云母效果
        if not cfg.mica_effect_switch.value or system != 'Windows':
            self.set_mica_enabled(False)

            if system != 'Windows':
                # 非 Windows 平台不支持云母效果，锁定开关为关闭状态
                cfg.set(cfg.mica_effect_switch, False, save=True)

        # 1. 创建启动页面
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(64, 64))

        # 2. 在创建其他子页面前先显示主界面
        self.show()

        # 3.创建子界面
        self.addSubInterface(BasicSettingsPage(self), FluentIcon.SETTING, self.tr('基本设置'))
        self.addSubInterface(AppearanceSettingsPage(self), FluentIcon.BRUSH, self.tr('个性化'))
        self.addSubInterface(AboutSettingsPage(self), FluentIcon.INFO, self.tr('关于'),NavigationItemPosition.BOTTOM)

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
    ui.app_manager.init_app()
    window = SettingsWindow()
    window.show()
    loop = ui.app_manager.get_loop()
    with loop:
        loop.run_forever()

    if cfg.close_settings_action.value == 'restart':
        restart_program()

    else:
        sys.exit()


if __name__ == '__main__':
    start_settings()
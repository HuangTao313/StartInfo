import sys
from pathlib import Path
from PySide6.QtGui import QIcon
from qfluentwidgets import FluentWindow, FluentIcon
from core.load_ui import *
from core.config import cfg
import core.ht_lib as lib

# 定义常量
SETTINGS_ICON = lib.DATA_FOLDER_PATH / 'icons' / 'settings.ico'

# 添加项目根目录到路径，确保能正确导入 core 包
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import core.ui as ui

class NewSettings(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("开机速览-设置")
        self.resize(1000, 800)
        # 如果你希望窗口启动时出现在屏幕正中间，可以加上这行
        self.center()
        self.setMinimumSize(800, 600)  # 设置最小尺寸，防止用户缩得太小导致UI崩坏
        if SETTINGS_ICON.exists():
            self.setWindowIcon(QIcon(str(SETTINGS_ICON)))

        self.basic_settings_page = BasicStettingsPage(self)
        self.addSubInterface(self.basic_settings_page, FluentIcon.SETTING, '基本设置')

        self.custom_settings_page = CustomSettingsPage(self)
        self.addSubInterface(self.custom_settings_page, FluentIcon.BRUSH, '个性化')

        self.about_settings_page = AboutSettingsWidgets(self)
        self.addSubInterface(self.about_settings_page, FluentIcon.INFO, '关于')


    def center(self):
        # 获取主屏幕对象
        screen = ui.app_manager.get_app().primaryScreen()
        # 获取屏幕的可视区域（排除了任务栏占据的空间）
        screen_geometry = screen.availableGeometry()

        # 计算居中坐标：(屏幕宽 - 窗口宽) / 2
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2

        # 移动窗口到计算出的位置
        self.move(x, y)

def start_new_settings() -> None:
    ui.app_manager.init_app()
    app = ui.app_manager.get_app()
    w = NewSettings()
    w.show()
    app.exec()
    # 如果用户选择关闭设置窗口后重启到主程序
    if cfg.close_settings_action.value == 'restart':
        lib.restart_program()


if __name__ == '__main__':
   start_new_settings()
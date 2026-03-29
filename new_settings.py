import sys
from pathlib import Path
# from PySide6.QtWidgets import QApplication, QWidget
# from PySide6.QtGui import QIcon
from qfluentwidgets import FluentWindow, FluentIcon
from load_ui import *

# 添加项目根目录到路径，确保能正确导入 core 包
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import core.ui as ui

class Demo(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("开机速览-设置")
        # self.setWindowIcon(QIcon(FluentIcon.SETTING))

        # self.test_ui = TestWidget(self)
        # self.addSubInterface(self.test_ui, FluentIcon.RINGER, '测试')

        self.basic_settings_page = BasicStettingsPage(self)
        self.addSubInterface(self.basic_settings_page, FluentIcon.SETTING, '基本设置')

        self.custom_page = CustomSettingsPage(self)
        self.addSubInterface(self.custom_page, FluentIcon.BRUSH, '个性化')

def start_new_settings() -> None:
    ui.app_manager.init_app()
    app = ui.app_manager.get_app()
    w = Demo()
    w.show()
    app.exec()

if __name__ == '__main__':
   start_new_settings()
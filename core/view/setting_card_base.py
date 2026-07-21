"""设置页面基底 —— 所有设置页面继承此类。"""

from PySide6.QtWidgets import QWidget
from qfluentwidgets import ScrollArea, ExpandLayout


class BaseSettingPage(ScrollArea):
    """ScrollArea 壳子：透明背景 + 底盘 + ExpandLayout。"""

    def __init__(self, parent=None, object_name=''):
        super().__init__(parent=parent)
        self.enableTransparentBackground()

        self.scrollWidget = QWidget()
        self.scrollWidget.setObjectName('scrollWidget')
        self.scrollWidget.setStyleSheet('background: transparent;')

        self.expandLayout = ExpandLayout(self.scrollWidget)

        if object_name:
            self.setObjectName(object_name)

    def finalise(self):
        """所有卡片创建完毕后调用，将底盘装入滚动区域。"""
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

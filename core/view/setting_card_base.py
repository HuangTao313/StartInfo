"""设置页面基底 —— 所有设置页面继承此类。"""

from PySide6.QtWidgets import QWidget, QHBoxLayout
from qfluentwidgets import ScrollArea, ExpandLayout


class BaseSettingPage(ScrollArea):
    """ScrollArea 壳子：透明背景 + 底盘 + ExpandLayout（内容水平居中）。"""

    def __init__(self, parent=None, object_name=''):
        super().__init__(parent=parent)
        self.enableTransparentBackground()

        self.scrollWidget = QWidget()
        self.scrollWidget.setObjectName('scrollWidget')
        self.scrollWidget.setStyleSheet('background: transparent;')

        # 内容容器：承载卡片，限制宽度区间，在滚动视口中水平居中
        self.contentWidget = QWidget(self.scrollWidget)
        self.contentWidget.setObjectName('contentWidget')
        self.contentWidget.setStyleSheet('background: transparent;')
        # 窗口最大化后内容保持该宽度并居中，两侧留白；
        # 最小宽度保证卡片正常展开（不依赖卡片的 sizeHint）
        self.contentWidget.setMinimumWidth(800)
        self.contentWidget.setMaximumWidth(1000)

        self.expandLayout = ExpandLayout(self.contentWidget)

        # 外层水平布局：内容容器拉伸占满视口（受 min/max 约束），
        # 超宽时容器停在 1000 并居中
        outer_layout = QHBoxLayout(self.scrollWidget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(self.contentWidget, 1)

        if object_name:
            self.setObjectName(object_name)

    def finalise(self):
        """所有卡片创建完毕后调用，将底盘装入滚动区域。"""
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
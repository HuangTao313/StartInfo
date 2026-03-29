from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import (ScrollArea, ExpandLayout, SettingCardGroup,CalendarPicker,
                            SwitchSettingCard, ComboBoxSettingCard, FluentIcon as FIF, PushSettingCard)
from core.config import cfg  # 导入刚才写的管家


class BasicSettingsWidget(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # 1. 开启透明背景（ScrollArea 层面）
        self.enableTransparentBackground()

        # 2. 创建唯一的底盘并设置透明
        self.scrollWidget = QWidget()
        self.scrollWidget.setObjectName("scrollWidget")  # 给底盘起个名
        self.scrollWidget.setStyleSheet("background: transparent;")  # 这里的 QWidget 尽量精准

        # 3. 设置布局（绑定到底盘上）
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # ---------------------------------------------------------
        # 注意！下面不要再写 self.scrollWidget = QWidget() 了
        # ---------------------------------------------------------

        # 4. 创建组并添加卡片
        self.generalGroup = SettingCardGroup("基本设置", self.scrollWidget)

        # 3. 手敲一个开关卡片（绑定到大脑）
        # 开机自启
        self.startupCard = SwitchSettingCard(
            FIF.POWER_BUTTON,
            "开机自启",
            "是否开机启动",
            configItem=cfg.startup,
            parent=self.generalGroup
        )

        # 选择城市
        self.cityCard = PushSettingCard(
            text="选择城市",
            icon=FIF.CLOUD,
            title="城市",
            content="获取天气的城市"
        )
        # 启用倒数日功能
        self.countdownCard = SwitchSettingCard(
            icon=FIF.CALENDAR,
            title='启用倒数日功能',
            content='在主程序显示：“距离xxx还有xx天”',
            configItem=cfg.countdown,
        )

        # 设置倒数日日期
        self.cd_date = CalendarPicker(self)

        # 4. 把卡片塞进组，把组塞进页面
        self.generalGroup.addSettingCard(self.startupCard)
        self.generalGroup.addSettingCard(self.cityCard)
        self.generalGroup.addSettingCard(self.countdownCard)
        self.generalGroup.addSettingCard(self.cd_date)
        self.expandLayout.addWidget(self.generalGroup)

        # 最后把底盘装进滚动区域
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName("basic_settings_page")

        # 绑定信号与槽
        cfg.startup.valueChanged.connect(self.onStartupChanged)

    def onStartupChanged(self, is_enabled: bool):
        if is_enabled:
            # self.add_to_startup()
            print(">>> 已添加开机启动项")
        else:
            # self.remove_from_startup()
            print(">>> 已删除开机启动项")

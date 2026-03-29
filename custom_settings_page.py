from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import (ScrollArea, ExpandLayout, SettingCardGroup, ColorSettingCard,
                            SwitchSettingCard, ComboBoxSettingCard, FluentIcon as FIF, PushSettingCard)
import os
import core.config as config # 导入刚才写的管家
import core.ui as ui
import core.ht_lib as lib

cfg = config.cfg

class CustomSettingsWidgets(ScrollArea):
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
        self.generalGroup = SettingCardGroup("个性化", self.scrollWidget)

        # 3. 手敲一个开关卡片（绑定到大脑）
        # 主题
        self.themeCard = ComboBoxSettingCard(
            configItem=cfg.theme,  # 绑定你刚改好的字符串配置项
            icon=FIF.BRUSH,  # 使用画笔图标更贴切
            title="主题",
            content="调整软件的外观颜色",
            # 这里的中文顺序必须严格对应 config.py 里的 ["light", "dark", "dynamic"]
            # 索引 0: 浅色 -> light
            # 索引 1: 深色 -> dark
            # 索引 2: 跟随系统 -> dynamic
            texts=['浅色主题', '深色主题', '跟随系统'],
            parent=self.generalGroup
        )

        # # 主题色
        # self.themeColorCard = ColorSettingCard(
        #     configItem=cfg.theme_color,
        #     icon=FIF.COLOR_SWATCH,
        #     title="主题色",
        #     content="调整软件主题色",
        #     parent=self.generalGroup
        # )

        # 模版
        template_files = [p.name for p in lib.TEMPLATE_FOLDER_PATH.glob("*.j2") if p.is_file()]
        self.templateCard = ComboBoxSettingCard(
            configItem=cfg.template_file,
            icon=FIF.LABEL,
            title='模板',
            content='选择主程序使用的模板',
            texts=template_files,
            parent=self.generalGroup
        )

        # 导入模板
        self.import_templateCard = PushSettingCard(
            text="导入模板",
            icon=FIF.DOWNLOAD,
            title="导入模板",
            content="导入Jinja2模板"
        )

        # 打开模板自定义文档
        self.open_template_docCard = PushSettingCard(
            text="模板自定义文档",
            icon=FIF.DICTIONARY,
            title="模板自定义文档",
            content="DIY自己的模板"
        )

        # 4. 把卡片塞进组，把组塞进页面
        self.generalGroup.addSettingCard(self.themeCard)
        self.generalGroup.addSettingCard(self.templateCard)
        self.generalGroup.addSettingCard(self.import_templateCard)
        self.generalGroup.addSettingCard(self.open_template_docCard)
        self.expandLayout.addWidget(self.generalGroup)


        # 最后把底盘装进滚动区域
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName("custom_settings_page")

        # 绑定信号
        cfg.theme.valueChanged.connect(self.onThemeChanged)
        self.import_templateCard.clicked.connect(self.onImportTemplateClicked)
        self.open_template_docCard.clicked.connect(self.open_template_doc)

    # 定义槽
    def onThemeChanged(self, theme_type: str):
        ui.app_manager.refresh_theme(theme_type)

    def onImportTemplateClicked(self):
        print('导入模板')

    def open_template_doc(self):
        os.startfile(str(lib.TEMPLATE_FOLDER_PATH / '模板自定义文档.md'),)
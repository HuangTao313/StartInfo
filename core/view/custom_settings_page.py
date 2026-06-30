from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from qfluentwidgets import (ScrollArea, ExpandLayout, SettingCardGroup, ColorSettingCard,
                            SwitchSettingCard, ComboBoxSettingCard, FluentIcon as FIF, PushSettingCard,
                            PrimaryPushSettingCard, InfoBar, InfoBarPosition)  # === 新增：引入 ExpandGroupSettingCard (手风琴组件) ===
import os
from ..config import cfg
from .. import ui
from .. import ht_lib as lib
from .ui_widgets import Notify, ZhSwitchSettingCard


class CustomSettingsWidgets(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # 1. 开启透明背景（ScrollArea 层面）
        self.enableTransparentBackground()

        # 2. 创建唯一的底盘并设置透明
        self.scrollWidget = QWidget()
        self.scrollWidget.setObjectName('scrollWidget')  # 给底盘起个名
        self.scrollWidget.setStyleSheet('background: transparent;')  # 这里的 QWidget 尽量精准

        # 3. 设置布局（绑定到底盘上）
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # ---------------------------------------------------------
        # 注意！下面不要再写 self.scrollWidget = QWidget() 了
        # ---------------------------------------------------------

        # 4. 创建组并添加卡片
        # ===== 主题 =====
        self.themeGroup = SettingCardGroup('主题', self.scrollWidget)

        # 主题
        self.themeCard = ComboBoxSettingCard(
            configItem=cfg.theme,  # 绑定你刚改好的字符串配置项
            icon=FIF.CONSTRACT,  # 使用画笔图标更贴切
            title='主题',
            content='调整软件的外观颜色',
            # 这里的中文顺序必须严格对应 config.py 里的 ['light', 'dark', 'dynamic']
            # 索引 0: 浅色 -> light
            # 索引 1: 深色 -> dark
            # 索引 2: 跟随系统 -> dynamic
            texts=['浅色主题', '深色主题', '跟随系统'],
            parent=self.themeGroup
        )

        # 使用系统主题色
        self.useWinThemeColor = ZhSwitchSettingCard(
            configItem=cfg.use_win_theme_color,
            icon=FIF.PALETTE,
            title='使用系统主题色',
            content='使用系统主题色',
            parent=self.themeGroup
        )

        # 主题色
        self.themeColorCard = ColorSettingCard(
            configItem=cfg.theme_color,
            icon=FIF.PALETTE,
            title='主题色',
            content='自定义程序主题色，调整前请先关闭【使用系统主题色】',
            parent=self.themeGroup
        )

        # 如果使用系统主题色，则禁用自定义主题色
        self.themeColorCard.setEnabled(not cfg.use_win_theme_color.value)

        # 添加进组
        self.themeGroup.addSettingCard(self.themeCard)
        self.themeGroup.addSettingCard(self.useWinThemeColor)
        self.themeGroup.addSettingCard(self.themeColorCard)
        self.expandLayout.addWidget(self.themeGroup)

        # ===== 模板 =====
        self.templatelGroup = SettingCardGroup('模板', self.scrollWidget)
        template_files = cfg.get_template_files()
        self.templateCard = ComboBoxSettingCard(
            configItem=cfg.template_file,
            icon=FIF.LABEL,
            title='模板',
            content='选择主程序使用的模板',
            texts=template_files,
            parent=self.templatelGroup
        )

        # 导入模板
        self.import_templateCard = PushSettingCard(
            text='导入模板',
            icon=FIF.DOWNLOAD,
            title='导入模板',
            content='导入Jinja2模板',
            parent=self.templatelGroup
        )

        # 刷新模板列表
        self.refresh_templateCard = PrimaryPushSettingCard(
            text='刷新模板列表',
            icon=FIF.SYNC,
            title='刷新模板列表',
            content='刷新模板列表',
            parent=self.templatelGroup
        )

        # 打开模板文件夹
        self.open_template_folderCard = PrimaryPushSettingCard(
            text='打开模板文件夹',
            icon=FIF.FOLDER,
            title='打开模板文件夹',
            content='打开模板文件夹',
            parent=self.templatelGroup
        )

        # 打开模板自定义文档
        self.open_template_docCard = PrimaryPushSettingCard(
            text='模板自定义文档',
            icon=FIF.DICTIONARY,
            title='模板自定义文档',
            content='DIY自己的模板',
            parent=self.templatelGroup
        )

        # 4. 把卡片塞进组，把组塞进页面

        self.templatelGroup.addSettingCard(self.templateCard)
        self.templatelGroup.addSettingCard(self.import_templateCard)
        self.templatelGroup.addSettingCard(self.refresh_templateCard)
        self.templatelGroup.addSettingCard(self.open_template_folderCard)
        self.templatelGroup.addSettingCard(self.open_template_docCard)
        self.expandLayout.addWidget(self.templatelGroup)

        # 最后把底盘装进滚动区域
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName('custom_settings_page')

        # 绑定信号
        cfg.theme.valueChanged.connect(self.onThemeChanged)
        cfg.use_win_theme_color.valueChanged.connect(self.onUseWinThemeColorChanged)
        cfg.theme_color.valueChanged.connect(self.onThemeColorChanged)
        self.import_templateCard.clicked.connect(self.onImportTemplateClicked)
        self.refresh_templateCard.clicked.connect(self.onRefreshTemplateClicked)
        self.open_template_folderCard.clicked.connect(self.onOpenTemplateFolderClicked)
        self.open_template_docCard.clicked.connect(self.open_template_doc)

    # 定义槽函数
    # 主题改变
    def onThemeChanged(self, theme_type: str):
        ui.app_manager.refresh_theme(theme_type)

    # 使用系统主题色
    def onUseWinThemeColorChanged(self):
        if cfg.use_win_theme_color.value:
            theme_color = ui.get_real_windows_accent_color()
            if theme_color:
                ui.app_manager.refresh_theme_color(theme_color)

        else:
            ui.app_manager.refresh_theme_color(cfg.theme_color.value)

        self.themeColorCard.setEnabled(not cfg.use_win_theme_color.value)


    # 主题色改变
    def onThemeColorChanged(self, theme_color: str):
        if not cfg.use_win_theme_color.value:
            ui.app_manager.refresh_theme_color(theme_color)

        else:
            Notify.warning(content='请先关闭【使用系统主题色】', parent=self)

    # 导入模板
    def onImportTemplateClicked(self):
        template_file_path: Path = ui.file_dialog("选择模版文件", "", "jinja2模板文件 (*.j2)")
        # 如果文件路径不为空
        if template_file_path is not None:
            # 尝试导入模板
            is_success, text = lib.import_template(template_file_path)
            # 如果导入成功
            if is_success:
                # 弹出成功信息
                Notify.success(title='模板导入成功', content=f'已成功导入模板：{template_file_path.name}', parent=self)
                self.onRefreshTemplateClicked()

    # 刷新模板列表
    @staticmethod
    def update_combobox_options(card: ComboBoxSettingCard, new_texts: list):
        """
        手动更新 ComboBoxSettingCard 的选项列表
        :param card: 你的 templateCard 实例
        :param new_texts: 新的显示文字列表 (e.g., ["default.j2", "new.j2"])
        """
        # 保存旧选项
        old_options = cfg.template_file.value
        # 1. 获取最新的配置项选项 (也就是从你刚写的 get_template_files 获取的列表)
        # 因为 ConfigItem 会在调用时动态触发 validator 里的 get_options
        new_options = card.configItem.validator.get_options()

        # 2. 清除旧内容
        card.comboBox.clear()
        card.optionToText.clear()

        # 3. 重新建立映射并添加选项
        card.optionToText = {o: t for o, t in zip(new_options, new_texts)}
        for text, option in zip(new_texts, new_options):
            card.comboBox.addItem(text, userData=option)

        # 4. 恢复当前选中的值 (防止刷新后跳回第一个)
        if old_options in card.optionToText:
            card.comboBox.setCurrentText(card.optionToText[old_options])

    def onRefreshTemplateClicked(self):
        # 1. 获取最新文件列表
        templates_list = cfg.get_template_files()

        # 2. 调用上面的更新函数
        # 假设你的显示文字和配置值是一样的，都传 templates_list
        self.update_combobox_options(self.templateCard, templates_list)

        # 3. 顺手弹个封装好的消息提醒（刚才封装的 Notify 类派上用场了）
        Notify.success(f"已刷新模板列表，发现 {len(templates_list)} 个文件", parent=self)

    # 打开模板文件夹
    def onOpenTemplateFolderClicked(self):
        os.startfile(lib.TEMPLATE_FOLDER_PATH)

    # 打开模板自定义文档
    def open_template_doc(self):
        os.startfile(str(lib.TEMPLATE_FOLDER_PATH / '模板自定义文档.md'),)
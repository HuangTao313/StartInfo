"""个性化设置页面。"""

import os

from qfluentwidgets import (ColorSettingCard, ComboBoxSettingCard,
                            FluentIcon as FIF, OptionsSettingCard,
                            PrimaryPushSettingCard, PushSettingCard,
                            RadioButton, SettingCardGroup, HyperlinkCard)

from .setting_card_base import BaseSettingPage
from .ui_widgets import Notify, ExtSwitchSettingCard
from .. import base_lib as lib
from .. import ui
from ..config import cfg


class CustomSettingsPage(BaseSettingPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent, object_name='custom_settings_page')

        self.parent_window = parent

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # ── 主题 ──
        self.themeGroup = SettingCardGroup('主题', self.scrollWidget)

        self.themeCard = ComboBoxSettingCard(
            configItem=cfg.theme, icon=FIF.CONSTRACT, title='主题',
            content='调整软件的外观颜色',
            texts=['浅色主题', '深色主题', '跟随系统'],
            parent=self.themeGroup,
        )

        self.useWinThemeColor = ExtSwitchSettingCard(
            icon=FIF.PALETTE, title='使用系统主题色',
            content='使用系统主题色', config_item=cfg.use_win_theme_color,
            parent=self.themeGroup,
        )

        self.themeColorCard = ColorSettingCard(
            configItem=cfg.theme_color, icon=FIF.PALETTE,
            title='主题色', content='自定义程序主题色，调整前请先关闭【使用系统主题色】',
            parent=self.themeGroup,
        )
        self.themeColorCard.setEnabled(not cfg.use_win_theme_color.value)

        self.micaEffectSwitchCard = ExtSwitchSettingCard(
            icon=FIF.TRANSPARENT, title='云母效果', content='窗口和表面显示半透明(仅支持Windows11)',
            config_item=cfg.mica_effect_switch, parent=self.themeGroup,
        )
        # 非Windows系统云母效果开关默认锁定
        if lib.system != 'Windows':
            self.micaEffectSwitchCard.setEnabled(False)

        self.themeGroup.addSettingCards([
            self.themeCard,
            self.useWinThemeColor,
            self.themeColorCard,
            self.micaEffectSwitchCard,
        ])
        self.expandLayout.addWidget(self.themeGroup)

        # ── 模板 ──
        self.templateGroup = SettingCardGroup('模板', self.scrollWidget)

        template_files = lib.get_template_files()
        self.templateCard = OptionsSettingCard(
            configItem=cfg.template_file, icon=FIF.LABEL, title='模板',
            content='选择主界面使用的模板', texts=template_files,
            parent=self.templateGroup,
        )

        self.importTemplateCard = PushSettingCard(
            text='导入模板', icon=FIF.DOWNLOAD,
            title='导入模板', content='导入Jinja2模板',
            parent=self.templateGroup,
        )

        self.refreshTemplateCard = PrimaryPushSettingCard(
            text='刷新模板列表', icon=FIF.SYNC,
            title='刷新模板列表', content='刷新模板列表',
            parent=self.templateGroup,
        )

        self.openTemplateFolderCard = PrimaryPushSettingCard(
            text='打开模板文件夹', icon=FIF.FOLDER,
            title='打开模板文件夹', content='打开模板文件夹',
            parent=self.templateGroup,
        )

        self.openTemplateDocCard = HyperlinkCard(
            icon=FIF.DICTIONARY, title='模板自定义文档',
            content='打开模板自定义文档',
            url='https://github.com/HuangTao313/StartInfo/blob/main/docs/template-customization.md',
            text='打开', parent=self.templateGroup,
        )

        self.templateGroup.addSettingCards([
            self.templateCard,
            self.importTemplateCard,
            self.refreshTemplateCard,
            self.openTemplateFolderCard,
            self.openTemplateDocCard,
        ])
        self.expandLayout.addWidget(self.templateGroup)
        self.finalise()

    def _connect_signals(self):
        """连接信号与槽。"""
        cfg.theme.valueChanged.connect(self._onThemeChanged)
        cfg.use_win_theme_color.valueChanged.connect(self._onUseWinThemeColorChanged)
        cfg.theme_color.valueChanged.connect(self._onThemeColorChanged)
        cfg.mica_effect_switch.valueChanged.connect(self.parent_window.set_mica_enabled)
        self.importTemplateCard.clicked.connect(self._onImportTemplateClicked)
        self.refreshTemplateCard.clicked.connect(self._onRefreshTemplateClicked)
        self.openTemplateFolderCard.clicked.connect(self._onOpenTemplateFolderClicked)

    # ------------------------------------------------------------------
    # 主题
    # ------------------------------------------------------------------

    def _onThemeChanged(self, theme_type: str):
        ui.app_manager.refresh_theme(theme_type)

    def _onUseWinThemeColorChanged(self):
        if cfg.use_win_theme_color.value:
            theme_color = ui.get_real_windows_accent_color()
            if theme_color:
                ui.app_manager.refresh_theme_color(theme_color)
        else:
            ui.app_manager.refresh_theme_color(cfg.theme_color.value)
        self.themeColorCard.setEnabled(not cfg.use_win_theme_color.value)

    def _onThemeColorChanged(self, theme_color: str):
        if not cfg.use_win_theme_color.value:
            ui.app_manager.refresh_theme_color(theme_color)
        else:
            Notify.warning(content='请先关闭【使用系统主题色】', parent=self)

    # ------------------------------------------------------------------
    # 模板
    # ------------------------------------------------------------------

    def _onImportTemplateClicked(self):
        template_file_path = ui.file_dialog('选择模版文件', '', 'jinja2模板文件 (*.j2)')
        if template_file_path is not None:
            is_success, text = lib.import_template(template_file_path)
            if is_success:
                Notify.success(title='模板导入成功',
                               content=f'已成功导入模板：{template_file_path.name}',
                               parent=self)
                self._onRefreshTemplateClicked()

    # @staticmethod
    # def _update_combobox_options(card: ComboBoxSettingCard, new_texts: list):
    #     old_options = cfg.template_file.value
    #     new_options = card.configItem.validator.get_options()
    #     card.comboBox.clear()
    #     card.optionToText.clear()
    #     card.optionToText = {o: t for o, t in zip(new_options, new_texts)}
    #     for text, option in zip(new_texts, new_options):
    #         card.comboBox.addItem(text, userData=option)
    #     if old_options in card.optionToText:
    #         card.comboBox.setCurrentText(card.optionToText[old_options])

    @staticmethod
    def _update_options_setting_card(card: OptionsSettingCard, new_texts: list):
        """刷新模板选项按钮列表（模板文件变更后重建单选按钮）。

        OptionsSettingCard 展开时重建按钮会与展开动画/高度计算冲突，
        因此先强制收起并复位高度，避免刷新后显示异常。
        """
        old_value = cfg.template_file.value
        config_name = card.configName

        # 展开状态下重建单选按钮会导致高度计算异常，先收起并停掉动画
        card.setExpand(False)
        card.expandAni.stop()
        card.setFixedHeight(card.card.height())

        # 清除验证器缓存，保证 configItem.options 与最新文件列表一致
        card.configItem.validator.invalidate()

        # 移除旧的单选按钮
        for button in card.buttonGroup.buttons():
            card.buttonGroup.removeButton(button)
            card.viewLayout.removeWidget(button)
            button.deleteLater()

        # 依据最新模板列表重建按钮，文本与选项值均为模板文件名
        for text in new_texts:
            button = RadioButton(text, card.view)
            card.buttonGroup.addButton(button)
            card.viewLayout.addWidget(button)
            button.setProperty(config_name, text)

        card._adjustViewSize()

        # 保留原选中项；若原模板已不存在则回退到第一个
        value = old_value if old_value in new_texts else new_texts[0]
        card.setValue(value)

        # setValue 内部 choiceLabel.adjustSize() 会压缩标签固有高度，
        # 重新激活头部布局，让标签恢复垂直拉伸（避免收起时文本上移）
        card.card.hBoxLayout.invalidate()
        card.card.hBoxLayout.activate()

    def _onRefreshTemplateClicked(self):
        templates_list = lib.get_template_files()
        self._update_options_setting_card(self.templateCard, templates_list)
        Notify.success(f'已刷新模板列表，发现 {len(templates_list)} 个文件', parent=self)

    def _onOpenTemplateFolderClicked(self):
        os.startfile(lib.TEMPLATE_FOLDER_PATH)
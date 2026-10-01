"""个性化设置页面。"""

import os

from qfluentwidgets import (ColorSettingCard, ComboBoxSettingCard,
                            FluentIcon as FIF, OptionsSettingCard,
                            PrimaryPushSettingCard, PushSettingCard,
                            RadioButton, SettingCardGroup, HyperlinkCard, qconfig)

from ...base_lib import system
from ...config import cfg
from ...paths import TEMPLATE_FOLDER_PATH
from ...templates import get_template_files, import_template
from ..app import app_manager, get_theme_color
from ..controls import BaseSettingPage, ExtSwitchSettingCard
from ..dialogs import Notify, file_dialog


class AppearanceSettingsPage(BaseSettingPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent, object_name='appearance_settings_page')

        self.parent_window = parent

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # ── 主题 ──
        self.themeGroup = SettingCardGroup(self.tr('主题'), self.contentWidget)

        self.themeCard = ComboBoxSettingCard(
            configItem=cfg.theme, icon=FIF.CONSTRACT, title=self.tr('主题'),
            content=self.tr('调整软件的外观颜色'),
            texts=[self.tr('浅色主题'), self.tr('深色主题'), self.tr('跟随系统')],
            parent=self.themeGroup
        )

        self.themeColorModeCard = ComboBoxSettingCard(
            icon=FIF.PALETTE, title=self.tr('主题色'),
            content=self.tr('跟随系统或自定义'), configItem=cfg.theme_color_mode,
            texts=[self.tr('跟随系统'), self.tr('自定义')],
            parent=self.themeGroup
        )

        # Linux下由于发行版众多，无法做到获取系统主题色，因而禁用这个功能，强制自定义主题色
        if system == 'Linux':
            # 如果配置文件已修改为跟随系统，改回自定义模式
            if cfg.theme_color_mode.value == 'dynamic':
                qconfig.set(cfg.theme_color_mode, 'custom', save=True)

            self.themeColorModeCard.setEnabled(False)

        self.themeColorCard = ColorSettingCard(
            configItem=cfg.theme_color, icon=FIF.PALETTE,
            title=self.tr('自定义主题色'), content=self.tr('自定义程序主题色'),
            parent=self.themeGroup
        )
        # 仅在主题色模式为「自定义」时显示该卡片
        self.themeColorCard.setVisible(cfg.theme_color_mode.value == 'custom')

        self.micaEffectSwitchCard = ExtSwitchSettingCard(
            icon=FIF.TRANSPARENT, title=self.tr('云母效果'),
            content=self.tr('窗口和表面显示半透明(仅支持Windows11)'),
            config_item=cfg.mica_effect_switch, parent=self.themeGroup
        )
        # 非Windows系统云母效果开关默认锁定
        if system != 'Windows':
            self.micaEffectSwitchCard.setEnabled(False)

        self.themeGroup.addSettingCards([
            self.themeCard,
            self.themeColorModeCard,
            self.themeColorCard,
            self.micaEffectSwitchCard
        ])
        self.expandLayout.addWidget(self.themeGroup)

        # ── 模板 ──
        self.templateGroup = SettingCardGroup(self.tr('模板'), self.contentWidget)

        template_files = get_template_files()
        self.templateCard = OptionsSettingCard(
            configItem=cfg.template_file, icon=FIF.LABEL, title=self.tr('模板'),
            content=self.tr('选择主界面使用的模板'), texts=template_files,
            parent=self.templateGroup
        )

        self.importTemplateCard = PushSettingCard(
            text=self.tr('导入模板'), icon=FIF.DOWNLOAD,
            title=self.tr('导入模板'), content=self.tr('导入Jinja2模板'),
            parent=self.templateGroup
        )

        self.refreshTemplateCard = PrimaryPushSettingCard(
            text=self.tr('刷新模板列表'), icon=FIF.SYNC,
            title=self.tr('刷新模板列表'), content=self.tr('刷新模板列表'),
            parent=self.templateGroup
        )

        self.openTemplateFolderCard = PrimaryPushSettingCard(
            text=self.tr('打开模板文件夹'), icon=FIF.FOLDER,
            title=self.tr('打开模板文件夹'), content=self.tr('打开模板文件夹'),
            parent=self.templateGroup
        )

        self.openTemplateDocCard = HyperlinkCard(
            icon=FIF.DICTIONARY, title=self.tr('模板自定义文档'),
            content=self.tr('打开模板自定义文档'),
            url='https://github.com/HuangTao313/StartInfo/blob/main/docs/template-customization.md',
            text=self.tr('打开'), parent=self.templateGroup
        )

        self.templateGroup.addSettingCards([
            self.templateCard,
            self.importTemplateCard,
            self.refreshTemplateCard,
            self.openTemplateFolderCard,
            self.openTemplateDocCard
        ])
        self.expandLayout.addWidget(self.templateGroup)
        self.finalise()

    def _connect_signals(self):
        """连接信号与槽。"""
        cfg.theme.valueChanged.connect(self._onThemeChanged)
        cfg.theme_color_mode.valueChanged.connect(self._onThemeColorModeChanged)
        cfg.theme_color.valueChanged.connect(self._onThemeColorChanged)
        cfg.mica_effect_switch.valueChanged.connect(self.parent_window.set_mica_enabled)
        self.importTemplateCard.clicked.connect(self._onImportTemplateClicked)
        self.refreshTemplateCard.clicked.connect(self._onRefreshTemplateClicked)
        self.openTemplateFolderCard.clicked.connect(self._onOpenTemplateFolderClicked)

    # ------------------------------------------------------------------
    # 主题
    # ------------------------------------------------------------------

    @staticmethod
    def _onThemeChanged(theme_type: str):
        app_manager.refresh_theme(theme_type)

    def _onThemeColorModeChanged(self):
        if cfg.theme_color_mode.value == 'dynamic':
            theme_color = get_theme_color()
            if theme_color:
                app_manager.refresh_theme_color(theme_color)
        else:
            app_manager.refresh_theme_color(cfg.theme_color.value)
        self.themeColorCard.setVisible(cfg.theme_color_mode.value == 'custom')
        self.themeGroup.adjustSize()

    def _onThemeColorChanged(self, theme_color: str):
        if cfg.theme_color_mode.value != 'dynamic':
            app_manager.refresh_theme_color(theme_color)
        else:
            Notify.warning(content=self.tr('请先将【主题色】切换为自定义'), parent=self)

    # ------------------------------------------------------------------
    # 模板
    # ------------------------------------------------------------------

    def _onImportTemplateClicked(self):
        template_file_path = file_dialog(
            self.tr('选择模版文件'), '', self.tr('jinja2模板文件 (*.j2)'))
        if template_file_path is not None:
            is_success, result_message = import_template(template_file_path)
            if is_success:
                Notify.success(title=self.tr('模板导入成功'),
                               content=self.tr('已成功导入模板：{name}').format(
                                   name=template_file_path.name),
                               parent=self)
                self._onRefreshTemplateClicked()

            else:
                Notify.error(result_message, parent=self)


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
        templates_list = get_template_files()
        self._update_options_setting_card(self.templateCard, templates_list)
        Notify.success(
            self.tr('已刷新模板列表，发现 {count} 个文件').format(count=len(templates_list)),
            parent=self)

    @staticmethod
    def _onOpenTemplateFolderClicked():
        os.startfile(TEMPLATE_FOLDER_PATH)
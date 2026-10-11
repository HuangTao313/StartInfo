"""基本设置页面。"""

import shutil

from qfluentwidgets import (ComboBoxSettingCard, FluentIcon as FIF,
                            PrimaryPushSettingCard, SettingCardGroup,
                            MessageBox)

from ...base_lib import restart_program, open_target
from ...config import cfg
from ...i18n import get_language_names
from ...logger import log
from ...paths import CACHE_FOLDER_PATH, LOG_FOLDER_PATH
from ...startup import create_shortcut, is_shortcut_exist, remove_shortcut
from ..app import app_manager
from ..ui_widgets import BaseSettingPage, Notify
from ..setting_cards import NumberSettingCard, ExtSwitchSettingCard


class BasicSettingsPage(BaseSettingPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent, object_name='basic_settings_page')

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # ── 基本设置 ──
        self.generalGroup = SettingCardGroup(self.tr('基本设置'), self.contentWidget)

        self.startupCard = ExtSwitchSettingCard(
            FIF.POWER_BUTTON, self.tr('开机自启'), self.tr('是否开机启动'),
            config_item=None, parent=self.generalGroup
        )
        self.startupCard.setChecked(is_shortcut_exist())

        self.autoCloseCard = ExtSwitchSettingCard(
            FIF.CLOSE, self.tr('主窗口自动关闭'),
            self.tr('主窗口在一段后自动关闭，程序结束运行'),
            config_item=cfg.auto_close_switch, parent=self.generalGroup
        )

        self.autoCloseTimeCard = NumberSettingCard(
            config_item=cfg.auto_close_time, icon=FIF.STOP_WATCH,
            title=self.tr('自动关闭时间(单位：秒/s)'),
            content=self.tr('主窗口自动关闭时间(范围：30~300秒，默认60秒)'),
            min_value=30, max_value=300,
            parent=self.generalGroup
        )

        self.closeSettingsActionCard = ComboBoxSettingCard(
            texts=[self.tr('重启到主程序'), self.tr('直接退出')], icon=FIF.CLOSE,
            title=self.tr('关闭设置窗口后的行为'), content=self.tr('重启到主程序或直接退出'),
            configItem=cfg.close_settings_action, parent=self.generalGroup
        )

        # 顺序须与 cfg.language 的 options 一致：dynamic 在前，其余按 languages.json 键序
        languages = [self.tr('跟随系统')] + get_language_names()
        self.languageCard = ComboBoxSettingCard(
            texts=languages, icon=FIF.LANGUAGE,
            title=self.tr('语言'), content=self.tr('切换程序的显示语言'),
            configItem=cfg.language, parent=self.generalGroup
        )

        self.generalGroup.addSettingCards([
            self.startupCard,
            self.autoCloseCard,
            self.autoCloseTimeCard,
            self.closeSettingsActionCard,
            self.languageCard
        ])
        self.expandLayout.addWidget(self.generalGroup)

        # ── 调试 ──
        self.debugGroup = SettingCardGroup(self.tr('调试'), self.contentWidget)

        self.deleteCaCheCard = PrimaryPushSettingCard(
            icon=FIF.DELETE, title=self.tr('删除缓存'),
            content=self.tr('删除程序在运行中产生的缓存数据'), text=self.tr('立即删除'),
            parent=self.debugGroup
        )

        self.logLevelCard = ComboBoxSettingCard(
            icon=FIF.ALIGNMENT, title=self.tr('日志等级'),
            content=self.tr('调整程序的日志等级，重启后生效'),
            texts=cfg.LOG_LEVELS, configItem=cfg.log_level, parent=self.debugGroup
        )

        self.openLogFolderCard = PrimaryPushSettingCard(
            text=self.tr('打开日志文件夹'), icon=FIF.FOLDER,
            title=self.tr('打开日志文件夹'), content=self.tr('打开程序日志文件夹'),
            parent=self.debugGroup
        )

        self.debugGroup.addSettingCards([
            self.deleteCaCheCard,
            self.logLevelCard,
            self.openLogFolderCard
        ])
        self.expandLayout.addWidget(self.debugGroup)

        self.finalise()

    def _connect_signals(self):
        """连接信号与槽。"""
        self.startupCard.checkedChanged.connect(self._onStartupChanged)
        self.deleteCaCheCard.clicked.connect(self._onDeleteCaCheClicked)
        cfg.language.valueChanged.connect(self._onLanguageChanged)
        self.openLogFolderCard.clicked.connect(self._onOpenLogFolderClicked)

    # ------------------------------------------------------------------
    # 槽函数
    # ------------------------------------------------------------------

    def _onLanguageChanged(self, language: str):
        """语言卡片选择后（qfw 卡片已自动保存配置）热重载翻译器。

        配置值不同但实际生效语言相同（如系统为 zh_CN 时在「跟随系统」
        与「简体中文」间切换）时不重载、不提示。
        实际语言变化时，已打开窗口的文案在构造时已固化，不会随翻译器
        刷新，询问用户是否立即重启以完全应用新语言。
        """
        previous = app_manager.current_language
        resolved = app_manager.switch_language(language)
        if resolved is None:
            Notify.error(self.tr('语言切换失败，请查看日志'), parent=self)
            return

        if resolved == previous:
            return

        self.box = MessageBox(self.tr('切换语言'), self.tr('语言将在重启后完全生效，是否立即重启？'), self)
        self.box.yesButton.setText(self.tr('立即重启'))
        self.box.cancelButton.setText(self.tr('稍后重启'))
        if self.box.exec():
            restart_program('--settings')

    def _onStartupChanged(self, is_enabled: bool):
        if is_enabled:
            if create_shortcut():
                Notify.success(content=self.tr('已添加开机启动项'), parent=self)
            else:
                Notify.error(content=self.tr('添加开机启动项失败，请查看日志'), parent=self)
        else:
            if remove_shortcut():
                Notify.success(content=self.tr('已删除开机启动项'), parent=self)
            else:
                Notify.error(content=self.tr('删除开机启动项失败，请查看日志'), parent=self)

    def _onOpenLogFolderClicked(self) -> None:
        if LOG_FOLDER_PATH.exists():
            open_target(LOG_FOLDER_PATH)
            Notify.success(self.tr('已打开日志文件夹'), parent=self)

        else:
            Notify.error(self.tr('日志文件夹不存在'), parent=self)

    def _onDeleteCaCheClicked(self) -> bool | None:
        if CACHE_FOLDER_PATH.exists():
            shutil.rmtree(CACHE_FOLDER_PATH)

            # 复位初始化标记，使后续缓存写入能在下次 init_db 时重建目录与表
            from ...widgets import CacheManager
            CacheManager.reset()
            log.info('已删除缓存')
            Notify.success(self.tr('已删除缓存'), parent=self)
            return True

        else:
            Notify.info(content=self.tr('未发现缓存'), parent=self)
            return None
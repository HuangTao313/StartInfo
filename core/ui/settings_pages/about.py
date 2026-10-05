"""关于页面。"""

import os
import shutil
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QWidget
from qasync import asyncSlot
from qfluentwidgets import (BodyLabel, ComboBoxSettingCard, FluentIcon as FIF,
                            HyperlinkCard, MessageBox, PrimaryPushSettingCard,
                            SettingCardGroup, TitleLabel,SubtitleLabel, StrongBodyLabel,
                            TextBrowser)

from ...base_lib import CURRENT_VERSION_JSON, VERSION
from ...config import cfg
from ...logger import log
from ...paths import DATA_FOLDER_PATH, LOGO_ICON_FILE_PATH, UNINSTALLER_FILE_PATH
from ...updater import check_update_logic
from ..controls import BaseSettingPage
from ..dialogs import Notify, UpdateDownloadBox

# 常量
LOGO_ICON_PATH = LOGO_ICON_FILE_PATH

class ChangelogBrowser(TextBrowser):
    """高度随内容与宽度自适应的文本框。"""

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setPlainText(text)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._updateHeight()  # 先按初始宽度估一次，避免首帧占位过大

    def _updateHeight(self):
        doc = self.document()
        doc.setTextWidth(self.viewport().width())
        h = int(doc.size().height()) + 3  # 少量余量，防止末行被截断
        if self.height() != h:  # 防止 setFixedHeight 再触发 resizeEvent 死循环
            self.setFixedHeight(h)

    def showEvent(self, e):
        super().showEvent(e)
        self._updateHeight()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._updateHeight()

class AboutSettingsPage(BaseSettingPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent, object_name='about_settings_page')

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # ── 关于 ──
        self.aboutGroup = SettingCardGroup(self.tr('关于'), self.contentWidget)

        # 图标（居中）
        if LOGO_ICON_PATH.exists():
            self.image_label = SubtitleLabel()
            pixmap = QPixmap(LOGO_ICON_PATH)
            self.image_label.setPixmap(pixmap)
            self.image_label.setFixedSize(pixmap.size())
            self._add_centered_widget(self.image_label)

        # 标题（居中）。tr() 必须传字面量，lupdate 无法提取变量；
        # 文案需与 base_lib.TITLE 保持一致
        self._add_centered_widget(TitleLabel(self.tr('开机速览')))

        # 简单介绍(居中)
        self._add_centered_widget(StrongBodyLabel(self.tr('一款基于 PySide6 与 QFluentWidgets 开发的桌面信息聚合工具，通过模块化组件在开机后快速展示各类实用信息。')))
        self._add_centered_widget(StrongBodyLabel(self.tr('本项目采用 GNU GPLv3.0 许可证开源')))

        # 与下方设置项之间的间距
        self._add_spacer(20)

        # 更新日志
        changelog_text = self.tr(
            '版本号：{version}\n'
            '发布日期：{release_date}\n\n'
            '更新日志：\n'
            '{changelog}'
        ).format(
            version=VERSION,
            release_date=CURRENT_VERSION_JSON.get('release_date', self.tr('获取失败')),
            changelog=CURRENT_VERSION_JSON.get('changelog', self.tr('获取失败')),
        )

        # ExpandLayout 按子件当前高度排布，须先 adjustSize 拿到内容高度
        self.changelogTitle = SubtitleLabel(self.tr('更新日志'))
        # SubtitleLabel 默认 DemiBold，此处取消加粗（保留 20px 字号）
        font = self.changelogTitle.font()
        font.setWeight(QFont.Normal)
        self.changelogTitle.setFont(font)
        self.changelogTitle.adjustSize()

        self.changelogCard = ChangelogBrowser(changelog_text, self.scrollWidget)

        # 检查更新
        self.checkUpdateCard = PrimaryPushSettingCard(
            text=self.tr('检查更新'), icon=FIF.UPDATE,
            title=self.tr('检查更新(当前版本号：{VERSION})').format(VERSION=VERSION),
            content=self.tr('检查新版本并下载'), parent=self.aboutGroup
        )

        # 更新源
        self.updateSourceCard = ComboBoxSettingCard(
            icon=FIF.CLOUD_DOWNLOAD, title=self.tr('更新源'),
            content=self.tr('选择更新源：GitHub、GitHub镜像站'),
            texts=['GitHub', self.tr('GitHub镜像站')],
            configItem=cfg.update_source, parent=self.aboutGroup
        )

        # 项目GitHub仓库
        self.githubCard = HyperlinkCard(
            icon=FIF.GITHUB, title=self.tr('此项目的GitHub仓库'),
            content=self.tr('打开此项目的GitHub仓库'),
            url='https://github.com/HuangTao313/StartInfo',
            text=self.tr('打开'), parent=self.aboutGroup
        )

        # 卸载
        self.uninstallCard = PrimaryPushSettingCard(
            text=self.tr('卸载'), icon=FIF.DELETE, title=self.tr('卸载'),
            content=self.tr('卸载本程序'), parent=self.aboutGroup
        )

        self.aboutGroup.addSettingCards([
            self.checkUpdateCard,
            self.updateSourceCard,
            self.githubCard,
            self.uninstallCard,
        ])
        # 小标题与上方卡片、下方日志卡片之间留出间距
        self._add_spacer(14)
        self.aboutGroup.addSettingCard(self.changelogTitle)
        self._add_spacer(6)
        self.aboutGroup.addSettingCard(self.changelogCard)
        self.expandLayout.addWidget(self.aboutGroup)
        self.finalise()

    def _connect_signals(self):
        """连接信号与槽。"""
        self.checkUpdateCard.clicked.connect(self.onUpdateClicked)
        self.uninstallCard.clicked.connect(self.onUninstallClicked)

    def _add_centered_widget(self, widget):
        """把非卡片 widget 水平居中添加进 aboutGroup。"""
        container = QWidget(self.aboutGroup)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        layout.addWidget(widget)
        layout.addStretch(1)
        # ExpandLayout 按子项当前高度排布，显式固定高度避免内容被下一项盖住
        container.setFixedHeight(widget.sizeHint().height())
        self.aboutGroup.addSettingCard(container)

    def _add_spacer(self, height: int):
        """在 aboutGroup 中插入一段垂直空白。"""
        spacer = QWidget(self.aboutGroup)
        spacer.setFixedHeight(height)
        self.aboutGroup.addSettingCard(spacer)

    # ------------------------------------------------------------------
    # 槽函数
    # ------------------------------------------------------------------

    @asyncSlot()
    async def onUpdateClicked(self):
        self.checkUpdateCard.setEnabled(False)
        try:
            update_available, new_version_data, error_msg = await check_update_logic()
            if error_msg:
                Notify.error(title=self.tr('检查更新失败'), content=error_msg, parent=self)
            elif update_available:
                box = UpdateDownloadBox(new_version_data, self)
                self._updateBox = box  # 持有引用，防止被垃圾回收
                box.show()  # 非模态：qasync 下 exec() 会阻塞事件循环，导致下载进度无法刷新
            else:
                Notify.info(content=self.tr('当前已经是最新版本'), parent=self)
        finally:
            self.checkUpdateCard.setEnabled(True)

    def onUninstallClicked(self):
        self.box = MessageBox(self.tr('卸载确认'), self.tr('确定要卸载本程序吗？'), self)
        self.box.yesButton.setText(self.tr('确定'))
        self.box.cancelButton.setText(self.tr('取消'))
        if self.box.exec():
            if UNINSTALLER_FILE_PATH.exists():
                try:
                    log.remove()
                    shutil.rmtree(DATA_FOLDER_PATH)
                except Exception as e:
                    log.error(f'设置-删除data文件夹失败: {e}')
                try:
                    os.startfile(UNINSTALLER_FILE_PATH)
                    sys.exit()
                except Exception as e:
                    log.error(f'设置-启动卸载程序失败: {e}')
                    Notify.error(
                        content=self.tr('启动卸载程序失败: {error}').format(error=e),
                        parent=self)
            else:
                log.warning('设置-未找到卸载程序')
                Notify.warning(content=self.tr('未找到卸载程序'), parent=self)
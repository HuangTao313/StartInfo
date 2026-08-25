"""关于页面。"""

import os
import shutil
import sys

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QWidget
from qasync import asyncSlot
from qfluentwidgets import (BodyLabel, ComboBoxSettingCard, FluentIcon as FIF,
                            HyperlinkCard, MessageBox, PrimaryPushSettingCard,
                            SettingCardGroup, TitleLabel,SubtitleLabel, StrongBodyLabel)

from .setting_card_base import BaseSettingPage
from .. import base_lib as lib
from ..config import cfg
from ..updater import check_update_logic, run_update_process

# 常量
LOGO_ICON_PATH = lib.DATA_FOLDER_PATH / 'icons' / 'startinfo.ico'
IS_LOGO_EXIST = LOGO_ICON_PATH.exists()


class AboutSettingsPage(BaseSettingPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent, object_name='about_settings_page')

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # ── 关于 ──
        self.aboutGroup = SettingCardGroup('关于', self.contentWidget)

        # 图标（居中）
        if IS_LOGO_EXIST:
            self.image_label = SubtitleLabel()
            pixmap = QPixmap(LOGO_ICON_PATH)
            self.image_label.setPixmap(pixmap)
            self.image_label.setFixedSize(pixmap.size())
            self._add_centered_widget(self.image_label)

        # 标题（居中）
        self._add_centered_widget(TitleLabel(lib.TITLE))

        # 小标题(居中)
        self._add_centered_widget(SubtitleLabel('StartInfo'))
        self._add_centered_widget(SubtitleLabel('本项目采用 GNU GPLv3.0 许可证开源'))

        # 简单介绍(居中)
        self._add_centered_widget(StrongBodyLabel('一款基于 PySide6 与 QFluentWidgets 开发的桌面信息聚合工具，通过模块化组件在开机后快速展示各类实用信息。'))


        # 与下方设置项之间的间距
        self._add_spacer(20)

        # 更新日志
        changelog_text = (
            f'版本号：{lib.VERSION}\n'
            f'发布日期：{lib.CURRENT_VERSION_JSON.get('release_date', '获取失败')}\n\n'
            f'更新日志：\n{lib.CURRENT_VERSION_JSON.get('changelog', '获取失败')}'
        )

        self.changelog = BodyLabel(changelog_text, self.scrollWidget)
        self.changelog.setWordWrap(True)
        self.changelog.adjustSize()

        # 检查更新
        self.checkUpdateCard = PrimaryPushSettingCard(
            text='检查更新', icon=FIF.UPDATE, title='检查更新',
            content='检查新版本并下载', parent=self.aboutGroup,
        )

        # 更新源
        self.updateSourceCard = ComboBoxSettingCard(
            icon=FIF.CLOUD_DOWNLOAD, title='更新源',
            content='选择更新源：GitHub、GitHub镜像站',
            texts=['GitHub', 'GitHub镜像站'],
            configItem=cfg.update_source, parent=self.aboutGroup,
        )

        # 项目GitHub仓库
        self.githubCard = HyperlinkCard(
            icon=FIF.GITHUB, title='此项目的GitHub仓库',
            content='打开此项目的GitHub仓库',
            url='https://github.com/HuangTao313/StartInfo',
            text='打开', parent=self.aboutGroup,
        )

        # 卸载
        self.uninstallCard = PrimaryPushSettingCard(
            text='卸载', icon=FIF.DELETE, title='卸载',
            content='卸载本程序', parent=self.aboutGroup,
        )

        self.aboutGroup.addSettingCards([
            self.checkUpdateCard,
            self.updateSourceCard,
            self.githubCard,
            self.uninstallCard,
            self.changelog,
        ])
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
            # 用户主动检查时强制刷新版本文件，避免用到旧更新源的缓存数据
            update_available, new_version_data, error_msg = await check_update_logic(force_refresh=True)
            if error_msg:
                from .ui_widgets import Notify
                Notify.error(title='检查更新失败', content=error_msg, parent=self)
            elif update_available:
                content = (
                    f'版本号：{new_version_data.get('version', '获取失败')}\n'
                    f'发布日期：{new_version_data.get('release_date', '获取失败')}\n'
                    f'更新日志：\n{new_version_data.get('changelog', '暂无更新日志')}'
                )
                box = MessageBox('发现新版本', content, self)
                box.yesButton.setText('立即更新')
                box.cancelButton.setText('取消更新')
                if box.exec():
                    lib.log.info('>>> 准备接入更新流程...')
                    self.window().close()
                    run_update_process(new_version_data)
            else:
                from .ui_widgets import Notify
                Notify.info(content='当前已经是最新版本', parent=self)
        finally:
            self.checkUpdateCard.setEnabled(True)

    def onUninstallClicked(self):
        box = MessageBox('卸载确认', '确定要卸载本程序吗？', self)
        box.yesButton.setText('确定')
        box.cancelButton.setText('取消')
        if box.exec():
            if lib.UNINS_PATH.exists():
                try:
                    lib.log.remove()
                    shutil.rmtree(lib.DATA_FOLDER_PATH)
                except Exception as e:
                    lib.log.error(f'设置-删除data文件夹失败: {e}')
                try:
                    os.startfile(lib.UNINS_PATH)
                    sys.exit()
                except Exception as e:
                    lib.log.error(f'设置-启动卸载程序失败: {e}')
                    from .ui_widgets import Notify
                    Notify.error(content=f'启动卸载程序失败: {e}', parent=self)
            else:
                lib.log.warning('设置-未找到卸载程序')
                from .ui_widgets import Notify
                Notify.warning(content='未找到卸载程序', parent=self)
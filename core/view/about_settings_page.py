"""关于页面。"""

import os
import shutil
import sys

from PySide6.QtGui import QPixmap
from qasync import asyncSlot
from qfluentwidgets import (SubtitleLabel, BodyLabel, SettingCardGroup,
                            FluentIcon as FIF, PrimaryPushSettingCard, MessageBox,
                            ComboBoxSettingCard)

from .setting_card_base import BaseSettingPage
from .. import base_lib as lib
from ..config import cfg
from ..updater import check_update_logic, run_update_process

# 常量
LOGO_ICON_PATH = lib.DATA_FOLDER_PATH / 'icons' / 'information.ico'
IS_LOGO_EXIST = LOGO_ICON_PATH.exists()


class AboutSettingsPage(BaseSettingPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent, object_name='about_settings_page')

        self.aboutGroup = SettingCardGroup('关于', self.scrollWidget)

        # 图标
        if IS_LOGO_EXIST:
            self.image_label = SubtitleLabel(self.scrollWidget)
            pixmap = QPixmap(LOGO_ICON_PATH)
            self.image_label.setPixmap(pixmap)
            self.image_label.setFixedSize(pixmap.size())
            self._add_widget(self.image_label)

        # 标题
        self._add_widget(SubtitleLabel(lib.TITLE, self.scrollWidget))

        # 更新日志
        changelog_text = (
            f'版本号：{lib.VERSION}\n'
            f'发布日期：{lib.CURRENT_VERSION_JSON.get('release_date', '获取失败')}\n\n'
            f'更新日志：\n{lib.CURRENT_VERSION_JSON.get('changelog', '获取失败')}'
        )

        changelog = BodyLabel(changelog_text, self.scrollWidget)
        changelog.setWordWrap(True)
        changelog.adjustSize()
        self._add_widget(changelog)

        # 检查更新
        self.checkUpdateCard = PrimaryPushSettingCard(
            text='检查更新', icon=FIF.UPDATE, title='检查更新',
            content='检查新版本并下载', parent=self.aboutGroup,
        )
        self.checkUpdateCard.clicked.connect(self.onUpdateClicked)

        # 更新源
        self.updateSourceCard = ComboBoxSettingCard(
            icon=FIF.CLOUD_DOWNLOAD, title='更新源', content='选择更新源：阿里云OSS、GitHub、GitHub镜像站',
            texts=['阿里云OSS', 'GitHub(未启用)', 'GitHub镜像站(未启用)'], configItem=cfg.update_source, parent=self.aboutGroup,
        )

        # 卸载
        self.uninstallCard = PrimaryPushSettingCard(
            text='卸载', icon=FIF.DELETE, title='卸载',
            content='卸载本程序', parent=self.aboutGroup,
        )
        self.uninstallCard.clicked.connect(self.onUninstallClicked)

        self.aboutGroup.addSettingCard(self.checkUpdateCard)
        self.aboutGroup.addSettingCard(self.updateSourceCard)
        self.aboutGroup.addSettingCard(self.uninstallCard)
        self.expandLayout.addWidget(self.aboutGroup)
        self.finalise()

    def _add_widget(self, widget):
        """把非卡片 widget 添加到 aboutGroup。"""
        self.aboutGroup.addSettingCard(widget)

    # ------------------------------------------------------------------
    # 槽函数
    # ------------------------------------------------------------------

    @asyncSlot()
    async def onUpdateClicked(self):
        self.checkUpdateCard.setEnabled(False)
        try:
            update_available, new_version_data, error_msg = await check_update_logic()
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
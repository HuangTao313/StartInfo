import os
import sys
import shutil
from operator import is_

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap
from qfluentwidgets import (ScrollArea, ExpandLayout, SubtitleLabel, BodyLabel, SettingCardGroup, FluentIcon as FIF,
                            PrimaryPushSettingCard, MessageBox)  # === 新增：引入 ExpandGroupSettingCard (手风琴组件) ===

from ..updater import check_update_logic, run_update_process
from .. import ht_lib as lib
from .ui_widgets import Notify


# 定义常量
LOGO_ICON_PATH = lib.DATA_FOLDER_PATH / 'icons' / 'information.ico'
is_logo_exist = LOGO_ICON_PATH.exists()

class AboutSettingsWidgets(ScrollArea):
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
        # ===== 关于 =====
        self.aboutGroup = SettingCardGroup('关于', self.scrollWidget)

        if is_logo_exist:
            self.image_label = SubtitleLabel(self.scrollWidget)
            # 1. 加载原图
            pixmap = QPixmap(LOGO_ICON_PATH)
            self.image_label.setPixmap(pixmap)

            # 强制 Label 的大小等于图片的原始大小
            self.image_label.setFixedSize(pixmap.size())

        # 标题
        self.title = SubtitleLabel(lib.TITLE, self.scrollWidget)
        # 1. 准备文本
        self.text = f"发布日期：{lib.CURRENT_VERSION_JSON.get('release_date', '获取失败')}\n\n更新日志：\n{lib.CURRENT_VERSION_JSON.get('changelog', '获取失败')}"

        # 2. 创建 BodyLabel 而不是 TextBrowser
        self.changelog = BodyLabel(self.text, self.scrollWidget)

        # 3. 核心设置：允许换行
        self.changelog.setWordWrap(True)

        # 4. 样式：取消背景和边框（QFW 的 Label 默认就是透明的）
        # 关键：让 Label 自动根据内容调整大小
        self.changelog.adjustSize()

        # 检查更新
        self.checkUpdateCard = PrimaryPushSettingCard(
            text='检查更新',
            icon=FIF.UPDATE,
            title='检查更新',
            content='检查新版本并下载',
            parent=self.aboutGroup
        )

        # 卸载
        self.uninstallCard = PrimaryPushSettingCard(
            text='卸载',
            icon=FIF.DELETE,
            title='卸载',
            content='卸载本程序',
            parent=self.aboutGroup
        )

        if is_logo_exist:
            self.aboutGroup.addSettingCard(self.image_label)

        self.aboutGroup.addSettingCard(self.title)
        self.aboutGroup.addSettingCard(self.changelog)
        self.aboutGroup.addSettingCard(self.checkUpdateCard)
        self.aboutGroup.addSettingCard(self.uninstallCard)
        self.expandLayout.addWidget(self.aboutGroup)

        # 最后把底盘装进滚动区域
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName('about_settings_page')

        # 连接信号与槽
        self.checkUpdateCard.clicked.connect(self.onUpdateClicked)
        self.uninstallCard.clicked.connect(self.onUninstallClicked)

    # 定义槽函数
    def onUpdateClicked(self):
        # 用一个变量接收，方便看清楚
        update_available, new_version_data = check_update_logic()

        if update_available:
            # 1. 提取数据（注意 key 要和字典里的一致）
            version = new_version_data.get('version', '获取失败')
            # 根据你刚才发的 Log，key 是 'release_date'
            release_date = new_version_data.get('release_date', '获取失败')
            changelog = new_version_data.get('changelog', '暂无更新日志')

            # 2. 构建文案（使用多行字符串更清晰）
            content = (
                f"版本号：{version}\n"
                f"发布日期：{release_date}\n"
                f"更新日志：\n{changelog}"
            )

            # 3. 弹出对话框
            box = MessageBox('发现新版本', content, self)
            box.yesButton.setText('立即更新')
            box.cancelButton.setText('取消更新')

            if box.exec():
                lib.log.info('>>> 准备接入更新流程...')
                # 关闭设置窗口，然后启动更新流程
                self.window().close()
                run_update_process(new_version_data)
        else:
            Notify.info(content='当前已经是最新版本', parent=self)

    def onUninstallClicked(self):
        box = MessageBox('卸载确认', '确定要卸载本程序吗？', self)
        # 2. 自定义按钮文本
        box.yesButton.setText('确定')
        box.cancelButton.setText('取消')

        # 3. 显示并处理结果
        if box.exec():
            # 启动卸载程序
            if lib.UNINS_PATH.exists():
                # 删除data文件夹
                try:
                    lib.log.remove()
                    shutil.rmtree(lib.DATA_FOLDER_PATH)
                    print(f'设置-已删除日志和模板文件夹')
                except Exception as e:
                    lib.log.error(f'设置-删除data文件夹失败: {e}')
                    Notify.error(content=f'删除日志和模板文件夹失败: {e}', parent=self)

                try:
                    os.startfile(lib.UNINS_PATH)
                    lib.log.info('设置-已启动卸载程序')
                    sys.exit()

                except Exception as e:
                    lib.log.error(f'设置-启动卸载程序失败: {e}')
                    Notify.error(content=f'启动卸载程序失败: {e}', parent=self)

            else:
                lib.log.warning('设置-未找到卸载程序')
                Notify.warning(content='未找到卸载程序', parent=self)
        else:
            lib.log.info('设置-取消卸载')
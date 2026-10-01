"""core.ui 弹窗、通知与更新下载框。

应用级对话框（dialog / main_window / error_dialog / file_dialog）、
Toast 通知（Notify）以及更新包下载框。
"""

import asyncio
import functools
import os
import re
import time
from pathlib import Path
from typing import List

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog
from qasync import asyncSlot
from qfluentwidgets import MessageBoxBase, SubtitleLabel, BodyLabel, InfoBar, InfoBarPosition, ProgressBar, Dialog

from ..base_lib import TITLE, restart_program, system
from ..logger import log
from ..paths import LOG_FILE_PATH
from ..updater import GITHUB_RELEASES_URL, perform_update_async
from .app import app_manager, tr


def _setup_auto_close(dialog_instance: Dialog, seconds: int | bool) -> None:
    """
    为对话框设置自动关闭定时器；seconds 为 False 或 <=0 时禁用

    :param dialog_instance: 目标对话框
    :param seconds: 倒计时秒数 (int) 或 禁用状态 (False)
    """
    if seconds is not False and seconds > 0:
        # 定时器必须挂到对话框下方：无父对象且无持有时会被 GC，导致定时器永不触发
        auto_close_timer = QTimer(dialog_instance)
        auto_close_timer.setSingleShot(True)
        auto_close_timer.timeout.connect(dialog_instance.accept)
        auto_close_timer.start(seconds * 1000)

def dialog(title: str, content: str, buttons: List[str] = None, timeout: int | bool = False) -> bool:
    """
    安全的消息框函数 - 使用单例 QApplication

    :param title: 弹窗标题
    :param content: 弹窗内容
    :param buttons: 按钮列表 (默认 ['确定'])
    :param timeout: 自动关闭秒数 (int) 或 禁用状态 (False, 默认)
    :return: True if confirmed, False otherwise
    """
    app_manager.get_app()

    # 默认按钮延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
    if buttons is None:
        buttons = [tr('确定')]

    # 创建对话框
    dialog = Dialog(title, content, None)
    # 设置按钮
    long = len(buttons)
    if long == 1:
        # 单按钮 - 确认
        dialog.yesButton.setText(buttons[0])
        dialog.cancelButton.hide()
        dialog.buttonLayout.insertStretch(1)

    elif long == 2:
        # 双按钮
        dialog.yesButton.setText(buttons[0])
        dialog.cancelButton.setText(buttons[1])

    else:
        raise ValueError('按钮列表长度不能超过 2')

    # 自动关闭（仅在 timeout 为正数时生效）
    _setup_auto_close(dialog, timeout)

    # 显示对话框并返回结果
    result = dialog.exec()
    return bool(result)

# 文件选择对话框
def file_dialog(title: str, directory: str = '', filter: str = None) -> Path | None:
    """
    文件选择对话框 - 使用单例 QApplication

    :param title: 对话框标题
    :param directory: 初始目录
    :param filter: 文件过滤器
    :return: 选中的文件路径，如果没有选择则返回 None
    """
    app_manager.get_app()

    # 默认过滤器延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
    if filter is None:
        filter = tr('All Files (*)')

    # 解包 QFileDialog.getOpenFileName 的返回值
    file_path_str, _ = QFileDialog.getOpenFileName(
        parent=None,  # 使用无父窗口
        caption=title,
        dir=directory,
        filter=filter
    )

    # 如果用户未选择文件（取消操作），返回 None
    if not file_path_str:
        return None

    # 将字符串转换为 Path 对象并返回
    return Path(file_path_str)

# 报错弹窗
def error_dialog(text: str) -> None:
    yn = dialog(tr('程序运行时发生错误╥﹏╥...'), text, [tr('重启'), tr('打开日志文件')])
    if yn:
        # 重启
        restart_program()

    # 打开日志文件
    elif not yn:
        try:
            if LOG_FILE_PATH.exists():
                os.startfile(LOG_FILE_PATH.parent)
                os.startfile(LOG_FILE_PATH)
                log.info(f'已打开日志文件：{LOG_FILE_PATH}')

            else:
                log.error(f'打开日志文件失败 - 日志文件不存在：{LOG_FILE_PATH}')
                dialog(tr('打开日志文件失败╥﹏╥...'),
                       tr('日志文件不存在：{path}').format(path=LOG_FILE_PATH))

        except Exception as e:
            log.error(f'打开日志文件失败：{e}')
            dialog(tr('打开日志文件失败╥﹏╥...'), f'{e}')

# ========== 主窗口 - 稳定版（支持禁用自动关闭） ==========
def main_window(text: str, auto_close_seconds: int = 60) -> bool:
    """
    主窗口函数
    :param text: 渲染后的文本
    :param auto_close_seconds: 倒计时秒数 (int) 或 禁用状态 (False)
    """
    app_manager.get_app()

    # 1. 清理文本首尾空行
    clean_text = text.strip()

    # 创建对话框
    dialog_instance = Dialog(TITLE, clean_text, None)
    dialog_instance.yesButton.setText(tr('确定'))
    dialog_instance.cancelButton.setText(tr('设置'))

    # 2. 禁止抖动逻辑
    dialog_instance.adjustSize()
    dialog_instance.setFixedSize(dialog_instance.width(), dialog_instance.height())
    dialog_instance.contentLabel.setAlignment(Qt.AlignTop | Qt.AlignLeft)

    # 3. 动态时间更新逻辑 (保持开启)
    # 定时器挂到对话框下方，避免局部变量被 GC 后时钟停止刷新
    timer = QTimer(dialog_instance)

    def update_time():
        new_time = time.strftime('%H:%M:%S', time.localtime())
        current_display_text = dialog_instance.contentLabel.text()
        new_content = re.sub(r'\d{2}:\d{2}:\d{2}', new_time, current_display_text)
        dialog_instance.contentLabel.setText(new_content)

    timer.timeout.connect(update_time)
    timer.start(1000)
    dialog_instance.finished.connect(timer.stop)

    # 4. 自动关闭功能
    # 只有当 auto_close_seconds 不是 False 且 大于 0 时才启动定时器
    _setup_auto_close(dialog_instance, auto_close_seconds)

    # 显示对话框并返回结果
    result = dialog_instance.exec()
    return bool(result)


class Notify:
    """弹窗提醒工具类"""

    @staticmethod
    def info(content: str, title: str = None, duration: int = 2000, parent=None):
        """显示普通信息提示"""
        # 默认标题延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
        if title is None:
            title = tr('提示')
        # 如果调用时没传 parent，尝试从 AppManager 获取主窗口（假设你存了）
        # 或者在调用时手动传 self
        InfoBar.info(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=parent
        )

    @staticmethod
    def success(content: str, title: str = None, duration: int = 2000, parent=None):
        """显示成功绿条弹窗"""
        # 默认标题延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
        if title is None:
            title = tr('成功')
        # 如果调用时没传 parent，尝试从 AppManager 获取主窗口（假设你存了）
        # 或者在调用时手动传 self
        InfoBar.success(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=parent
        )

    @staticmethod
    def warning(content: str, title: str = None, duration: int = 5000, parent=None):
        """显示橙色警告弹窗"""
        # 默认标题延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
        if title is None:
            title = tr('警告')
        InfoBar.warning(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=parent
        )

    @staticmethod
    def error(content: str, title: str = None, duration: int = 5000, parent=None):
        """显示错误红条弹窗"""
        # 默认标题延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
        if title is None:
            title = tr('错误')
        InfoBar.error(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=parent
        )

def action(success_msg: str = '', fail_msg: str = None):
    """装饰器：自动包装异步方法 → asyncSlot → InfoBar 反馈。

    用法：
        @action('天气数据已更新', '获取失败')
        async def on_refresh_weather(self):
            w = WeatherWidget()
            return await w.get_data_async()

        方法返回值非空 → 显示 success_msg
        返回 None      → 静默（表示无需操作，不弹任何提示）
        返回 False     → 显示 fail_msg
        抛出异常       → 显示异常信息

    也适用于同步方法：
        @action('删除成功')
        def on_delete(self):
            shutil.rmtree(path)
            return True
    """
    def deco(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 默认失败提示延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
            _fail_msg = tr('操作失败') if fail_msg is None else fail_msg
            try:
                result = func(self, *args, **kwargs)
                # 如果是协程，await
                if hasattr(result, '__await__'):
                    result = await result
                if result:
                    InfoBar.success(title=success_msg, content='', parent=self,
                                    position=InfoBarPosition.TOP,
                                    duration=2000)
                elif result is None:
                    # 返回 None 表示无需操作（如数据源未变更），静默处理
                    pass
                else:
                    InfoBar.error(title=_fail_msg, content='', parent=self,
                                  position=InfoBarPosition.TOP,
                                  duration=2000)
                return result

            except Exception as e:
                log.error(f'设置-操作失败: {e}')
                InfoBar.error(title=str(e), content='', parent=self,
                              position=InfoBarPosition.TOP,
                              duration=3000)
        return asyncSlot()(wrapper)
    return deco

def _format_size(size: int) -> str:
    """把字节数格式化为易读的 B/KB/MB 文本。"""
    if size < 1024:
        return f'{size}B'
    if size < 1024 * 1024:
        return f'{size / 1024:.1f}KB'
    return f'{size / (1024 * 1024):.1f}MB'


class UpdateDownloadBox(MessageBoxBase):
    """检查更新确认 + 下载进度弹窗。

    - 初始显示新版本信息与「立即更新/取消更新」按钮。
    - Windows：点击「立即更新」后清除文案，切换为下载进度条，异步下载安装包。
    - 非 Windows：点击「立即更新」跳转 GitHub Releases 页面并关闭弹窗。
    """

    def __init__(self, update_info: dict, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self._last_percent = -1

        # ── 初始：新版本信息 ──
        self.titleLabel = SubtitleLabel(self.tr('发现新版本'))
        self.contentLabel = BodyLabel(
            self.tr('版本号：{version}\n'
                    '发布日期：{release_date}\n'
                    '更新日志：\n'
                    '{changelog}').format(
                version=update_info.get('version', self.tr('获取失败')),
                release_date=update_info.get('release_date', self.tr('获取失败')),
                changelog=update_info.get('changelog', self.tr('暂无更新日志')),
            ),
            self,
        )
        self.contentLabel.setWordWrap(True)

        # ── 下载进度（初始隐藏）──
        self.progressLabel = BodyLabel(self.tr('正在下载新版本安装包：0%'), self)
        self.progressBar = ProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.contentLabel)
        self.viewLayout.addWidget(self.progressLabel)
        self.viewLayout.addWidget(self.progressBar)

        self.yesButton.setText(self.tr('立即更新'))
        self.cancelButton.setText(self.tr('取消更新'))
        self.widget.setMinimumWidth(480)

        self.progressLabel.hide()
        self.progressBar.hide()

        # 基类的按钮连接的是名称混淆的私有方法，这里断开后接管点击
        self.yesButton.clicked.disconnect()
        self.cancelButton.clicked.disconnect()
        self.yesButton.clicked.connect(self._onYesClicked)
        self.cancelButton.clicked.connect(self._onCancelClicked)

    def _onYesClicked(self, checked: bool = False):
        if system != 'Windows':
            # 非 Windows：跳转到 GitHub 最新构建的 Releases 页面
            QDesktopServices.openUrl(QUrl(GITHUB_RELEASES_URL))
            self.accept()
            return

        # Windows：清除文案，切换为下载进度视图
        self._switch_to_download_view()
        asyncio.ensure_future(self._download_and_install())

    def _onCancelClicked(self, checked: bool = False):
        self.reject()

    def _switch_to_download_view(self):
        """清除文案，切换为下载进度视图。"""
        self.titleLabel.setText(self.tr('正在更新'))
        self.contentLabel.hide()
        self.progressLabel.setText(self.tr('正在下载新版本安装包：0%'))
        self.progressLabel.show()
        self.progressBar.show()
        self.yesButton.hide()
        self.cancelButton.hide()

    async def _download_and_install(self):
        try:
            success, error_msg = await perform_update_async(
                self.update_info, progress_callback=self._on_download_progress)
        except Exception as e:
            log.error(f'更新器-更新过程异常: {e}')
            success, error_msg = False, self.tr('更新过程发生异常：{error}').format(error=e)

        if not success:
            self._show_download_error(error_msg)

    def _on_download_progress(self, downloaded: int, total: int):
        if total > 0:
            percent = min(100, int(downloaded / total * 100))
            # 整数百分比去重，避免 ProgressBar 动画频繁重启导致卡顿
            if percent != self._last_percent:
                self._last_percent = percent
                self.progressBar.setValue(percent)
            self.progressLabel.setText(
                self.tr('正在下载新版本安装包：{percent}% ({downloaded} / {total})').format(
                    percent=percent,
                    downloaded=_format_size(downloaded),
                    total=_format_size(total)))
        else:
            self.progressLabel.setText(
                self.tr('正在下载新版本安装包：{downloaded}').format(
                    downloaded=_format_size(downloaded)))

    def _show_download_error(self, error_msg: str):
        self.titleLabel.setText(self.tr('下载失败'))
        self.progressLabel.setText(error_msg)
        self.progressBar.error()  # 进度条置为错误状态（红色）
        self.cancelButton.setText(self.tr('关闭'))
        self.cancelButton.show()
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

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFileDialog

from qfluentwidgets import Dialog

from ..base_lib import TITLE, restart_program
from ..logger import log
from ..paths import LOG_FILE_PATH




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
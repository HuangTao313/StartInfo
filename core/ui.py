# coding:utf-8
import sys
import os
from PySide6.QtWidgets import QApplication, QFileDialog
from qfluentwidgets import Dialog, Theme, setTheme
import platform
from typing import List
from . import ht_lib as lib

class AppManager:
    """单例管理 QApplication 和主题"""
    _instance = None
    _app = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppManager, cls).__new__(cls)
            cls._app = None
        return cls._instance

    def init_app(self):
        """初始化 QApplication (只调用一次)"""
        if self._app is None:
            self._app = QApplication(sys.argv)
            # 获取系统主题
            self._system_theme = self._get_system_theme()
            setTheme(self._system_theme)
        return self._app

    def _get_system_theme(self) -> Theme:
        """获取系统主题 (深色/浅色)"""
        if platform.system() != "Windows":
            return Theme.LIGHT  # 非 Windows 系统默认浅色

        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return Theme.LIGHT if value == 1 else Theme.DARK
        except Exception as e:
            print(f"获取系统主题失败: {e}")
            return Theme.DARK

    def get_app(self) -> QApplication:
        """获取 QApplication 实例 (确保已初始化)"""
        if self._app is None:
            self.init_app()
        return self._app

    def quit(self):
        """退出应用程序 (由主程序调用)"""
        if self._app:
            self._app.quit()
            self._app = None


# 全局 AppManager 实例
app_manager = AppManager()


def dialog(title: str, content: str, buttons: List[str] = ['确定']) -> bool:
    """
    安全的消息框函数 - 使用单例 QApplication

    :param title: 弹窗标题
    :param content: 弹窗内容
    :param buttons: 按钮列表 (默认 ['确定'])
    :return: True if confirmed, False otherwise
    """
    app_manager.get_app()

    # 创建对话框
    dialog = Dialog(title, content, None)
    # 设置按钮
    long = len(buttons)
    if long == 1:
        # 单按钮-确认
        dialog.yesButton.setText(buttons[0])
        dialog.cancelButton.hide()
        dialog.buttonLayout.insertStretch(1)
    elif long == 2:
        # 双按钮
        dialog.yesButton.setText(buttons[0])
        dialog.cancelButton.setText(buttons[1])
    else:
        raise ValueError("按钮列表长度不能超过2")

    # 显示对话框并返回结果
    result = dialog.exec()
    return result

def file_dialog(title: str, directory: str = "", filter: str = "All Files (*)") -> str | None:
    """
    文件选择对话框 - 使用单例 QApplication

    :param title: 对话框标题
    :param directory: 初始目录
    :param filter: 文件过滤器
    :return: 选中的文件路径，如果没有选择则返回None
    """
    app_manager.get_app()

    file_path, _ = QFileDialog.getOpenFileName(
        parent=None,  # 使用无父窗口
        caption=title,
        dir=directory,
        filter=filter
    )

    # 如果用户未选择文件（取消操作），返回None
    return file_path if file_path else None


# 报错弹窗
def error_dialog(text: str) -> None:
    yn = dialog("程序运行时发生错误╥﹏╥...", text, ['确定', '打开日志文件'])
    if not yn:
        try:
            if lib.LOG_PATH.exists():
                os.startfile(lib.LOG_PATH.parent)
                os.startfile(lib.LOG_PATH)
                lib.log.info(f'已打开日志文件: {lib.LOG_PATH}')

            else:
                lib.log.error(f'打开日志文件失败-日志文件不存在: {lib.LOG_PATH}')
                dialog("打开日志文件失败╥﹏╥...", f"日志文件不存在: {lib.LOG_PATH}")

        except Exception as e:
            lib.log.error(f'打开日志文件失败: {e}')
            dialog("打开日志文件失败╥﹏╥...", f"{e}")
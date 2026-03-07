import sys
import os
import platform
from PySide6.QtWidgets import QApplication, QFileDialog, QVBoxLayout, QHBoxLayout
from qfluentwidgets import Dialog, Theme, setTheme, ListWidget, PushButton, PrimaryPushButton
from typing import List
from pathlib import Path
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
            # 应用用户选择的主题
            self._apply_theme()
        return self._app

    def _apply_theme(self):
        """应用用户选择的主题"""
        theme_mode = lib.file.read('General', 'theme') or 'dynamic'

        if theme_mode == 'light':
            setTheme(Theme.LIGHT)
        elif theme_mode == 'dark':
            setTheme(Theme.DARK)
        else:  # 'dynamic' 或其他值，跟随系统
            setTheme(self._get_system_theme())

    @staticmethod
    def refresh_theme(theme_mode: str = None):
        """
        刷新主题

        :param theme_mode: 主题模式 ('light'/'dark'/'dynamic')，不传则从数据文件读取
        """
        if theme_mode is None:
            theme_mode = lib.file.read('General', 'theme') or 'dynamic'

        if theme_mode == 'light':
            setTheme(Theme.LIGHT)
        elif theme_mode == 'dark':
            setTheme(Theme.DARK)
        else:  # 'dynamic' 或其他值，跟随系统
            # 获取系统主题
            if platform.system() != "Windows":
                setTheme(Theme.LIGHT)  # 非 Windows 系统默认浅色
            else:
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                         r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    winreg.CloseKey(key)
                    setTheme(Theme.LIGHT if value == 1 else Theme.DARK)
                except Exception as e:
                    lib.log.error(f"获取系统主题失败：{e}")
                    setTheme(Theme.DARK)

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
            lib.log.error(f"获取系统主题失败：{e}")
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
        # 单按钮 - 确认
        dialog.yesButton.setText(buttons[0])
        dialog.cancelButton.hide()
        dialog.buttonLayout.insertStretch(1)
    elif long == 2:
        # 双按钮
        dialog.yesButton.setText(buttons[0])
        dialog.cancelButton.setText(buttons[1])
    else:
        raise ValueError("按钮列表长度不能超过 2")

    # 显示对话框并返回结果
    result = dialog.exec()
    return result

# 文件选择对话框
def file_dialog(title: str, directory: str = "", filter: str = "All Files (*)") -> Path | None:
    """
    文件选择对话框 - 使用单例 QApplication

    :param title: 对话框标题
    :param directory: 初始目录
    :param filter: 文件过滤器
    :return: 选中的文件路径，如果没有选择则返回 None
    """
    app_manager.get_app()

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
    yn = dialog("程序运行时发生错误╥﹏╥...", text, ['确定', '打开日志文件'])
    if not yn:
        try:
            if lib.LOG_PATH.exists():
                os.startfile(lib.LOG_PATH.parent)
                os.startfile(lib.LOG_PATH)
                lib.log.info(f'已打开日志文件：{lib.LOG_PATH}')

            else:
                lib.log.error(f'打开日志文件失败 - 日志文件不存在：{lib.LOG_PATH}')
                dialog("打开日志文件失败╥﹏╥...", f"日志文件不存在：{lib.LOG_PATH}")

        except Exception as e:
            lib.log.error(f'打开日志文件失败：{e}')
            dialog("打开日志文件失败╥﹏╥...", f"{e}")


# ========== 选项选择对话框 (ChoiceBox) ==========

class _ChoiceBox(Dialog):
    """使用 QFluentWidgets 实现的选项选择对话框"""

    def __init__(self, title: str, message: str, options: list[str], parent=None):
        # 使用 Dialog 默认的标题和消息
        super().__init__(title, message, parent)

        self.options = options
        self.selected_option = None

        # 移除原有的按钮
        self.yesButton.hide()
        self.cancelButton.hide()

        # 重新创建 UI
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        # 获取内容布局
        content_layout = self.vBoxLayout

        # 设置布局间距 - 减小间距让列表更靠上
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 创建 ListWidget - 使用 QFluentWidgets 默认样式
        self.list_widget = ListWidget()
        self.list_widget.setMinimumHeight(150)
        self.list_widget.setMaximumHeight(350)

        # 添加列表项
        for option in self.options:
            self.list_widget.addItem(option)

        # 双击事件
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)

        # 选中事件
        self.list_widget.currentItemChanged.connect(self._on_current_item_changed)

        content_layout.addWidget(self.list_widget)

        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(20, 15, 20, 20)

        # 确定按钮（高亮样式）
        self.ok_button = PrimaryPushButton("确定")
        self.ok_button.setMinimumWidth(100)
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.ok_button.setEnabled(False)  # 初始禁用，选中选项后启用

        # 取消按钮（普通样式）
        self.cancel_button = PushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)

        # 添加按钮到布局
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        content_layout.addLayout(button_layout)

        # 设置窗口大小 - 更宽更高
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)
        
        # 窗口居中显示
        self.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _on_item_double_clicked(self, item):
        """双击选项事件"""
        self.selected_option = item.text()
        self.accept()

    def _on_current_item_changed(self, current, previous):
        """选中项变化事件"""
        # 有选中项时启用确定按钮
        self.ok_button.setEnabled(current is not None)

    def _on_ok_clicked(self):
        """点击确定按钮事件"""
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_option = current_item.text()
            self.accept()

    def get_result(self) -> str | None:
        """获取用户选择的选项"""
        return self.selected_option


def choicebox(title: str, message: str, options: list[str]) -> str | None:
    """
    显示选项选择对话框（列表样式）

    :param title: 对话框标题
    :param message: 提示信息（可选）
    :param options: 选项列表
    :return: 用户选择的选项，如果取消则返回 None
    """
    # 确保 QApplication 已初始化
    app = app_manager.get_app()

    # 创建对话框
    dialog = _ChoiceBox(title, message, options)

    # 显示对话框
    result = dialog.exec()

    # 返回结果
    if result == Dialog.Accepted:
        return dialog.get_result()
    else:
        return None


# ========== 下拉框选择对话框 (ComboBox) ==========

class _ComboBoxDialog(Dialog):
    """使用 QFluentWidgets 实现的下拉框选择对话框"""

    def __init__(self, title: str, message: str, options: list[str], parent=None):
        # 使用 Dialog 默认的标题和消息
        super().__init__(title, message, parent)

        self.options = options
        self.selected_option = None

        # 移除原有的按钮
        self.yesButton.hide()
        self.cancelButton.hide()

        # 重新创建 UI
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        # 获取内容布局
        content_layout = self.vBoxLayout

        # 设置布局间距
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 创建 ComboBox - 使用 QFluentWidgets 默认样式
        from qfluentwidgets import ComboBox as FluentComboBox
        self.combo_box = FluentComboBox()
        self.combo_box.addItems(self.options)
        self.combo_box.setMinimumWidth(250)
        self.combo_box.setMinimumHeight(40)

        content_layout.addWidget(self.combo_box)

        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(20, 15, 20, 20)

        # 确定按钮（高亮样式）
        self.ok_button = PrimaryPushButton("确定")
        self.ok_button.setMinimumWidth(100)
        self.ok_button.clicked.connect(self._on_ok_clicked)

        # 取消按钮（普通样式）
        self.cancel_button = PushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)

        # 添加按钮到布局
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        content_layout.addLayout(button_layout)

        # 设置窗口大小
        self.setMinimumWidth(600)
        self.setMinimumHeight(200)
        
        # 窗口居中显示
        self.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _on_ok_clicked(self):
        """点击确定按钮事件"""
        self.selected_option = self.combo_box.currentText()
        self.accept()

    def get_result(self) -> str | None:
        """获取用户选择的选项"""
        return self.selected_option


def combobox(title: str, message: str = "", options: list[str] = None) -> str | None:
    """
    显示选项选择对话框（下拉框样式）

    :param title: 对话框标题
    :param message: 提示信息（可选）
    :param options: 选项列表
    :return: 用户选择的选项，如果取消则返回 None
    """
    # 确保 QApplication 已初始化
    app = app_manager.get_app()

    # 处理默认参数
    if options is None:
        options = []
    
    # 如果 message 为 None，设为空字符串
    if message is None:
        message = ""

    # 创建对话框
    dialog = _ComboBoxDialog(title, message, options)

    # 显示对话框
    result = dialog.exec()

    # 返回结果
    if result == Dialog.Accepted:
        return dialog.get_result()
    else:
        return None


# ========== 主窗口 - 支持动态时间更新 ==========
def main_window(text: str, auto_close_seconds: int = 60) -> bool:
    """
    主窗口函数 - 支持动态时间更新

    :param text: 窗口显示内容（模板渲染后的文本）
    :param auto_close_seconds: 自动关闭时间（秒），默认 60 秒，设为 0 则不自动关闭
    :return: True if confirmed, False otherwise
    """
    import time
    import re
    from PySide6.QtCore import QTimer

    app_manager.get_app()

    # 创建对话框
    dialog_instance = Dialog(lib.TITLE, text, None)
    dialog_instance.yesButton.setText("确定")
    dialog_instance.cancelButton.setText("设置")

    # 动态时间更新（默认开启）
    timer = QTimer()

    def update_time():
        """定时器回调：更新时间"""
        new_time = time.strftime("%H:%M:%S", time.localtime())
        # 用正则替换文本中的时间（HH:MM:SS 格式）
        new_content = re.sub(r'\d{2}:\d{2}:\d{2}', new_time, text)
        dialog_instance.contentLabel.setText(new_content)

    # 启动定时器（每秒更新一次）
    timer.timeout.connect(update_time)
    timer.start(1000)

    # 对话框关闭时停止定时器
    dialog_instance.finished.connect(timer.stop)

    # 自动关闭功能
    if auto_close_seconds > 0:
        auto_close_timer = QTimer()
        auto_close_timer.setSingleShot(True)  # 只触发一次

        def auto_close():
            """自动关闭对话框"""
            dialog_instance.accept()

        auto_close_timer.timeout.connect(auto_close)
        auto_close_timer.start(auto_close_seconds * 1000)  # 转换为毫秒

        # 对话框手动关闭时停止自动关闭定时器
        dialog_instance.finished.connect(auto_close_timer.stop)

    # 显示对话框并返回结果
    result = dialog_instance.exec()
    return result
import sys
import os
import time
import re
import asyncio
from PySide6.QtCore import QTimer, Qt, QLocale
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout
from qfluentwidgets import Dialog, Theme, setTheme, ListWidget, PushButton, PrimaryPushButton,setThemeColor, FluentTranslator
from typing import List
from pathlib import Path
from qasync import QEventLoop
from . import ht_lib as lib
from .config import cfg


class AppManager:
    _instance = None
    _app = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppManager, cls).__new__(cls)
            cls._app = None
        return cls._instance

    def init_app(self):
        if self._app is None:
            self._app = QApplication(sys.argv)
            # 1.创建 qasync 的事件循环
            self._loop = QEventLoop(self._app)
            # 2. 将其设置为全局的 asyncio 事件循环
            asyncio.set_event_loop(self._loop)

            # 创建翻译器实例，生命周期必须和 app 相同
            translator = FluentTranslator(QLocale(QLocale.Chinese, QLocale.China))
            self._app.installTranslator(translator)

            self._apply_theme()
        return self._app

    def _apply_theme(self):
        """根据 cfg 的值初始化主题"""
        # 直接读取你 config.py 里的当前值
        theme_mode = cfg.theme.value
        theme_color_mode = cfg.theme_color.value if not cfg.use_win_theme_color.value else get_real_windows_accent_color()
        self.refresh_theme(theme_mode)
        self.refresh_theme_color(theme_color_mode)

    @staticmethod
    def refresh_theme(theme_mode: str):
        """
        刷新全局主题
        """
        if theme_mode == 'light':
            setTheme(Theme.LIGHT)
        elif theme_mode == 'dark':
            setTheme(Theme.DARK)
        else:
            # QFluentWidgets 完美支持 Theme.AUTO，它会自动看系统设置
            setTheme(Theme.AUTO)

    @staticmethod
    def refresh_theme_color(color_value):
        """
        刷新全局主题色
        color_value 可以是 QColor, '#ff0000', 或者 Qt.blue
        """
        # 注意：qfw 的 setThemeColor 内部会自动处理 qconfig 和 updateStyleSheet
        # 我们只需要确保传入的是有效的颜色
        setThemeColor(color_value, save=True)

    def get_app(self) -> QApplication:
            if self._app is None:
                self.init_app()
            return self._app

    def get_loop(self) -> QEventLoop:
        if self._app is None:
            self.init_app()
        return self._loop

# 全局 AppManager 实例
app_manager = AppManager()

def get_real_windows_accent_color():
    """
    直接从注册表读取 Windows 10/11 的实时主题色
    """
    # try:
    #     # 1. 定位到 DWM (Desktop Window Manager) 的注册表路径
    #     registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    #     key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\DWM")
    #
    #     # 2. 读取 AccentColor (DWORD格式)
    #     # 注册表存的是 AABBGGRR 格式
    #     value, _ = winreg.QueryValueEx(key, "AccentColor")
    #     winreg.CloseKey(key)
    #
    #     # 3. 核心转换逻辑：将 AABBGGRR 转为 #RRGGBB
    #     # value 是一个 32 位的整数
    #     # 我们通过位运算提取 R, G, B
    #     r = value & 0xff
    #     g = (value >> 8) & 0xff
    #     b = (value >> 16) & 0xff
    #
    #     return f"#{r:02x}{g:02x}{b:02x}".upper().lower()
    # except Exception:
    return "#009faa"  # 读取失败时的保底蓝色

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
    yn = dialog("程序运行时发生错误╥﹏╥...", text, ['重启', '打开日志文件'])
    if yn:
        # 重启
        lib.restart_program()

    # 打开日志文件
    elif not yn:
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

    else:
        lib.log.info('用户取消了操作，程序退出')
        sys.exit()

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
    dialog_instance = Dialog(lib.TITLE, clean_text, None)
    dialog_instance.yesButton.setText("确定")
    dialog_instance.cancelButton.setText("设置")

    # 2. 禁止抖动逻辑
    dialog_instance.adjustSize()
    dialog_instance.setFixedSize(dialog_instance.width(), dialog_instance.height())
    dialog_instance.contentLabel.setAlignment(Qt.AlignTop | Qt.AlignLeft)

    # 3. 动态时间更新逻辑 (保持开启)
    timer = QTimer()

    def update_time():
        new_time = time.strftime("%H:%M:%S", time.localtime())
        current_display_text = dialog_instance.contentLabel.text()
        new_content = re.sub(r'\d{2}:\d{2}:\d{2}', new_time, current_display_text)
        dialog_instance.contentLabel.setText(new_content)

    timer.timeout.connect(update_time)
    timer.start(1000)
    dialog_instance.finished.connect(timer.stop)

    # 4. 自动关闭功能 - 核心逻辑修改
    # 只有当 auto_close_seconds 不是 False 且 大于 0 时才启动定时器
    if auto_close_seconds is not False and auto_close_seconds > 0:
        auto_close_timer = QTimer()
        auto_close_timer.setSingleShot(True)

        def auto_close():
            """自动关闭对话框"""
            dialog_instance.accept()

        auto_close_timer.timeout.connect(auto_close)
        auto_close_timer.start(auto_close_seconds * 1000)

        # 确保手动关闭时也销毁这个定时器
        dialog_instance.finished.connect(auto_close_timer.stop)
    else:
        # 如果是 False，这里什么都不做，窗口将一直保持开启直到手动点击
        pass

    # 显示对话框并返回结果
    result = dialog_instance.exec()
    return result
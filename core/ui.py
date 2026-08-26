import asyncio
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtCore import QTranslator
from qasync import QEventLoop
from qfluentwidgets import Dialog, Theme, setTheme, setThemeColor

from . import base_lib as lib
from .config import cfg

# 日志
log = lib.log

# 翻译文件
TRANSLATION_FILE_PATH = str(lib.DATA_FOLDER_PATH / 'i18n' / 'qfluentwidgets.zh_CN.qm')

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
            log.debug('QApplication初始化')
            # 1.创建 qasync 的事件循环
            self._loop = QEventLoop(self._app)
            # 2. 将其设置为全局的 asyncio 事件循环
            asyncio.set_event_loop(self._loop)
            log.debug('将QT事件循环设置为全局 asyncio 事件循环')

            # 设置全局语言为中文
            self.translator = QTranslator()
            self.translator.load(TRANSLATION_FILE_PATH)
            self._app.installTranslator(self.translator)
            log.debug('设置语言为中文')

            self._apply_theme()
            log.debug('初始化主题')
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
        # init_app 自带惰性守卫并总是返回 _app，直接委托即可
        return self.init_app()

    def get_loop(self) -> QEventLoop:
        self.get_app()
        return self._loop

# 全局 AppManager 实例
app_manager = AppManager()

def get_real_windows_accent_color() -> str:
    """获取系统的主题色"""
    try:
        # 如果系统是Windows
        if lib.system == 'Windows':
            import winreg
            # 1. 定位到 DWM (Desktop Window Manager) 的注册表路径
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r'Software\Microsoft\Windows\DWM')

            # 2. 读取 AccentColor (DWORD格式)
            # 注册表存的是 AABBGGRR 格式
            value, _ = winreg.QueryValueEx(key, 'AccentColor')
            winreg.CloseKey(key)

            # 3. 核心转换逻辑：将 AABBGGRR 转为 #RRGGBB
            # value 是一个 32 位的整数
            # 我们通过位运算提取 R, G, B
            r = value & 0xff
            g = (value >> 8) & 0xff
            b = (value >> 16) & 0xff

            return f'#{r:02x}{g:02x}{b:02x}'.upper().lower()

        # 如果系统是MacOS，读取系统当前强调色
        elif lib.system == 'Darwin':
            script = '''
ObjC.import("AppKit");
var color = $.NSColor.controlAccentColor.colorUsingColorSpace(
    $.NSColorSpace.sRGBColorSpace
);
[color.redComponent, color.greenComponent, color.blueComponent].join(",");
'''
            result = subprocess.run(
                ['osascript', '-l', 'JavaScript', '-e', script],
                capture_output=True,
                text=True,
                timeout=3,
                check=True
            )
            components = [float(value) for value in result.stdout.strip().split(',')]
            if len(components) != 3:
                raise ValueError(f'无法解析MacOS强调色: {result.stdout!r}')

            r, g, b = (
                max(0, min(255, round(component * 255)))
                for component in components
            )
            return f'#{r:02x}{g:02x}{b:02x}'

        return '#0078d4'

    except Exception:
        return '#0078d4'  # 读取失败时的保底蓝色

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

def dialog(title: str, content: str, buttons: List[str] = ['确定'], timeout: int | bool = False) -> bool:
    """
    安全的消息框函数 - 使用单例 QApplication

    :param title: 弹窗标题
    :param content: 弹窗内容
    :param buttons: 按钮列表 (默认 ['确定'])
    :param timeout: 自动关闭秒数 (int) 或 禁用状态 (False, 默认)
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
        raise ValueError('按钮列表长度不能超过 2')

    # 自动关闭（仅在 timeout 为正数时生效）
    _setup_auto_close(dialog, timeout)

    # 显示对话框并返回结果
    result = dialog.exec()
    return bool(result)

# 文件选择对话框
def file_dialog(title: str, directory: str = '', filter: str = 'All Files (*)') -> Path | None:
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
    yn = dialog('程序运行时发生错误╥﹏╥...', text, ['重启', '打开日志文件'])
    if yn:
        # 重启
        lib.restart_program()

    # 打开日志文件
    elif not yn:
        try:
            if lib.LOG_FILE_PATH.exists():
                os.startfile(lib.LOG_FILE_PATH.parent)
                os.startfile(lib.LOG_FILE_PATH)
                log.info(f'已打开日志文件：{lib.LOG_FILE_PATH}')

            else:
                log.error(f'打开日志文件失败 - 日志文件不存在：{lib.LOG_FILE_PATH}')
                dialog('打开日志文件失败╥﹏╥...', f'日志文件不存在：{lib.LOG_FILE_PATH}')

        except Exception as e:
            log.error(f'打开日志文件失败：{e}')
            dialog('打开日志文件失败╥﹏╥...', f'{e}')

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
    dialog_instance.yesButton.setText('确定')
    dialog_instance.cancelButton.setText('设置')

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

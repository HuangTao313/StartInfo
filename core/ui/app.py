import asyncio
import subprocess
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QCoreApplication
from qasync import QEventLoop
from qfluentwidgets import Theme, setTheme, setThemeColor

from ..base_lib import system
from ..config import cfg
from ..i18n import (DEFAULT_LANGUAGE, get_available_languages,
                    get_language_files)
from ..logger import log
from ..paths import I18N_FOLDER_PATH

# 模块级 tr() 使用的翻译上下文，**必须保持为空字符串**。
# lupdate 把裸 tr() 调用（无论位于模块级、嵌套函数，还是类的方法/静态方法中）
# 一律归入「空上下文」，因此运行时只有用空上下文查找才能命中 .qm 里的译文。
# 若这里写成任意具名上下文（如 'StartInfo'），lupdate 生成的条目仍然存在，
# 但运行时永远查不到，会静默退回原文。
# 类内部的 self.tr() 由 Qt 与 lupdate 统一以「类名」作为上下文，不走这里。
GLOBAL_TR_CONTEXT = ''

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
            # 3.设置语言
            self._translators: list[QTranslator] = []
            self._apply_language()
            # 4.应用主题
            self._apply_theme()

        return self._app

    def _apply_theme(self):
        """根据 cfg 的值初始化主题"""
        theme = cfg.theme.value
        theme_color = cfg.theme_color.value if cfg.theme_color_mode.value != 'dynamic' else get_theme_color()
        self.refresh_theme(theme)
        log.debug(f'初始化主题：{theme}')
        self.refresh_theme_color(theme_color)
        log.debug(f'初始化主题色：{theme_color}')

    @staticmethod
    def refresh_theme(theme: str):
        """
        刷新全局主题
        """
        if theme == 'light':
            setTheme(Theme.LIGHT)
        elif theme == 'dark':
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

    def _apply_language(self, language: str = None) -> None:
        """初始化/切换语言：卸载旧翻译器后按 languages.json 的 files 顺序加载。

        Qt 的多个翻译器按安装逆序查询，后安装的优先命中——files 里排在
        后面的 startinfo 语言包会覆盖排在前面的 qfw 语言包中的同源文案
        （如 qfw 的开关状态「开/关」替换为「打开/关闭」）。
        """
        if language is None:
            language = cfg.language.value

        # 语言不在清单中（配置文件被手改/清单变更）时回退默认语言
        if language not in get_available_languages():
            log.warning(f'语言 {language} 不在语言包清单中，回退默认语言 {DEFAULT_LANGUAGE}')
            language = DEFAULT_LANGUAGE

        for old_translator in self._translators:
            self._app.removeTranslator(old_translator)
        self._translators.clear()

        for file_path in get_language_files(language):
            qm_path = I18N_FOLDER_PATH / file_path
            translator = QTranslator(self._app)
            if translator.load(str(qm_path)):
                self._app.installTranslator(translator)
                self._translators.append(translator)
                log.debug(f'已加载语言包: {qm_path.name}')
            else:
                log.warning(f'语言包加载失败，已跳过: {qm_path}')

        log.debug(f'当前语言: {language}')

    def switch_language(self, language: str) -> bool:
        """切换语言：保存配置并重载翻译器。返回是否成功。

        已打开的窗口不会随翻译器重载而刷新（文案在构造时已固化），
        完全生效需要重启程序。
        """
        if language not in get_available_languages():
            log.warning(f'切换语言失败，{language} 不在语言包清单中')
            return False

        # 值相同则不写入，避免 valueChanged 信号再次触发语言重载
        if language != cfg.language.value:
            cfg.set(cfg.language, language, save=True)
        else:
            # 本方法由卡片的 valueChanged 信号链触发时，qconfig.set 尚未
            # 执行到 save()；若此后弹窗选择立即重启，sys.exit() 的
            # SystemExit 会中断信号链跳过 save()，导致配置未落盘
            cfg.save()

        self._apply_language(language)
        return True

    def get_app(self) -> QApplication:
        # init_app 自带惰性守卫并总是返回 _app，直接委托即可
        return self.init_app()

    def get_loop(self) -> QEventLoop:
        self.get_app()
        return self._loop

# 全局 AppManager 实例
app_manager = AppManager()

def tr(text: str) -> str:
    """模块级翻译入口，由 :class:`AppManager` 提供。

    等价于 ``self.tr()``，供没有 ``self`` 的用户可见文案使用
    （模块级函数、模块级代码、非 QObject 的普通类）：:

        from .app import tr
        ui.dialog(tr('发生错误'))

    类内部请继续使用 ``self.tr()``，不要为了调用本函数而引入 QObject。
    """
    return QCoreApplication.translate(GLOBAL_TR_CONTEXT, text)


def get_theme_color() -> str:
    """获取系统的主题色"""
    try:
        # 如果系统是Windows
        if system == 'Windows':
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
        elif system == 'Darwin':
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
        return '#0078d4'
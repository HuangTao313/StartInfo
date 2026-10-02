"""i18n 底层模块：系统语言检测与语言包清单读取。

依赖链上的位置：``paths`` 之上、``base_lib`` 之下。**不得在模块顶层
导入 base_lib**（否则 ``config → i18n → base_lib → logger → config``
会立即成环），需要 base_lib 工具时在函数体内延迟导入。
"""

from typing import Any

from PySide6.QtCore import QLocale

from .paths import LANGUAGES_FILE_PATH

# 项目默认语言（无法获取系统语言、或系统语言不在语言包内时的兜底）
DEFAULT_LANGUAGE = 'zh_CN'

# languages.json 的解析结果缓存（随程序分发的只读资源，运行时不变）
_languages_data: dict | None = None


def _load_languages() -> dict:
    """读取并缓存 languages.json（语言代码 → name/version/files）"""
    global _languages_data
    if _languages_data is None:
        # 延迟导入：模块顶层导入会让 config → i18n → base_lib → logger
        # → config 成环；首次调用时各模块均已初始化完毕，无此问题
        from .base_lib import read_json

        _languages_data = read_json(LANGUAGES_FILE_PATH)
    return _languages_data


def get_system_language() -> str:
    """跨平台获取系统当前语言，如 'zh_CN'；无法获取时回退项目默认语言。

    QLocale 由 Qt 处理各平台差异（Windows 注册表 / macOS 系统偏好 /
    Linux 环境变量），name() 返回的格式正好与语言包键一致。
    """
    language = QLocale.system().name()
    if not language or language == 'C':
        return DEFAULT_LANGUAGE
    return language


def get_available_languages() -> list[str]:
    """获取本地可用语言列表（languages.json 第一层键），如 ['zh_CN', 'en_US']"""
    return list(_load_languages().keys())


def get_language_files(code: str) -> list[str]:
    """获取指定语言的 qm 文件列表（相对 i18n 目录，按 languages.json 的 files 顺序）。

    files 排在后面的语言包后安装，Qt 按安装逆序查询翻译，因此后加载的
    startinfo 语言包可以覆盖先加载的 qfw 语言包中的同源文案（如开关状态）。
    """
    info = _load_languages().get(code)
    if isinstance(info, dict):
        return list(info.get('files', []))
    return []


def get_language_names() -> list[Any | None]:
    """获取每种语言的 name 字段列表，如 ['简体中文', 'English']"""
    names = []
    for code, info in _load_languages().items():
        if isinstance(info, dict) and 'name' in info:
            names.append(info['name'])
        else:
            # 该语言缺 name 字段或条目格式异常时，用语言代码兜底
            names.append(code)
    return names
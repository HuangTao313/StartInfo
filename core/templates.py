"""模板文件的扫描、导入与启用。

本模块顶层**只依赖 paths 与 loguru**，不导入 config：
config.py 需要在顶层导入 :func:`get_template_files` 作为配置项的可选项来源，
顶层不反向依赖 config 才能彻底消除 config ↔ templates 的循环导入。
需要 cfg / qconfig 的两个函数在函数内部延迟导入。

loguru 的 ``logger`` 是全局单例，这里的 ``log`` 与 ``core.logger.log`` 是同一对象。
"""

import shutil
from pathlib import Path

from loguru import logger

from .paths import TEMPLATE_FOLDER_PATH

log = logger


def get_template_files() -> list:
    """扫描模板文件夹，获取所有 .j2 模板文件名

    生日专用模板 ``birthday_wishes.j2`` 由程序内部按需加载，不作为用户可选项。
    """
    if not TEMPLATE_FOLDER_PATH.exists():
        return ['default.j2']
    files = [
        p.name for p in TEMPLATE_FOLDER_PATH.glob('*.j2')
        if p.is_file() and p.name != 'birthday_wishes.j2'
    ]
    if not files:
        return ['default.j2']
    return files


def get_template_path() -> Path:
    """动态获取当前激活的模板路径（每次调用实时读取配置）。"""
    from .config import cfg
    return TEMPLATE_FOLDER_PATH / cfg.template_file.value


def import_template(template_file_path: Path) -> tuple[bool, str]:
    """
    导入模板文件

    :param template_file_path: 模板文件路径
    :return: (是否成功, 提示信息)
    """
    # 检查传入的模板文件是否存在
    if not template_file_path.exists():
        error_text = f'模版文件{template_file_path.name}不存在'
        log.error(error_text)
        return False, error_text

    # 自动创建模版文件夹(如果不存在)
    TEMPLATE_FOLDER_PATH.mkdir(parents=True, exist_ok=True)
    new_template_file_path = TEMPLATE_FOLDER_PATH / template_file_path.name

    # 如果模板已经导入，则提示用户
    if new_template_file_path.exists():
        warning_text = f'模版文件{template_file_path.name}已存在，请勿重复导入'
        log.warning(warning_text)
        return False, warning_text

    # 导入模板
    try:
        shutil.copy(template_file_path, new_template_file_path)
        info_text = f'模版文件已导入：{new_template_file_path.name}'
        log.info(info_text)
        return True, info_text

    except Exception as e:
        error_text = f'导入模版文件失败：{str(e)}'
        log.error(error_text)
        return False, error_text


def activate_template(template_file_path: Path | str) -> tuple[bool, str]:
    """
    启用模板文件

    :param template_file_path: 模板文件路径（支持字符串或Path对象）
    :return: (是否成功, 提示信息)
    """
    # 参数校验
    if not template_file_path or not str(template_file_path).strip():
        error_text = '模板文件路径不能为空'
        log.error(error_text)
        return False, error_text

    # 统一转换为Path对象
    if isinstance(template_file_path, str):
        template_file_path = Path(template_file_path)
        if not template_file_path.is_absolute():
            template_file_path = TEMPLATE_FOLDER_PATH / template_file_path

    # 检查文件是否存在
    if not template_file_path.exists():
        error_text = f'模版文件{template_file_path.name}不存在'
        log.error(error_text)
        return False, error_text

    # 写入配置并启用模板
    try:
        # 使用 qconfig.set() 方法正确设置并保存配置项
        from .config import qconfig, cfg
        qconfig.set(cfg.template_file, template_file_path.name, save=True)
        info_text = f'已启用模版文件{template_file_path.name}'
        log.info(info_text)
        return True, info_text

    except Exception as e:
        error_text = f'启用模版文件失败：{str(e)}'
        log.error(error_text)
        return False, error_text
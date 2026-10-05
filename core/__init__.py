"""StartInfo 内部核心库（项目专用，不作为独立程序运行）。

导入约定
--------
- 包外（main.py / settings.py / 未来入口）：``from core.<module> import ...``，
  或使用门面包 ``from core.ui import ...`` / ``from core.widgets import ...``。
- core 包内部模块之间使用相对导入（``.logger``、``..config``），
  不要写回环到门面包的绝对导入。

本模块承担两件启动期工作，顺序不可调换：

1. **旧版配置迁移**：必须在任何数据文件被读取之前完成，
   否则旧的 ``data/json/config.json`` 会被无视，用户配置等于丢失。
   这里早于 ``config`` 的 ``qconfig.load``。
   只迁移 config.json——资源文件由安装包分发，缓存文件可重新生成。
2. **初始化文件日志**：导入 logger 完成 loguru sink 注册，
   使「导入 core 即已有文件日志」成为稳定约定（沿用原 ``base_lib`` 的启动副作用）。
"""

from . import paths

# 迁移结果先收集，等 logger 就绪后再记录日志
_migrated_config = paths.migrate_legacy_config()

from . import logger  # noqa: E402, F401  初始化文件日志（必须在迁移之后）

if _migrated_config:
    from .logger import log

    log.info(f'用户配置已迁移到新位置: {_migrated_config}')
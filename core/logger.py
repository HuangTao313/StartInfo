"""日志初始化。

loguru 的 ``logger`` 是全局单例，项目内所有模块的 ``log`` 都指向它。

本模块在导入时就注册文件 sink，而 ``core/__init__.py`` 会导入本模块，
因此「任何 ``from core.X import ...`` 之后都已有文件日志」是稳定约定。
"""

import sys

from loguru import logger

# 别名必须先于 config 导入创建：config → i18n 的语言清单读取会经
# 延迟导入回到 base_lib → logger，此时本模块处于半初始化状态，
# 只有 log 已存在才能安全完成这条回路
log = logger

from .config import cfg
from .paths import CONFIG_FILE_PATH, LOG_FILE_PATH

# 日志初始化依赖 cfg.log_level，因此必须在 config 之后导入
# --debug 只影响本次启动，不写回配置
log_level = 'DEBUG' if '--debug' in sys.argv else cfg.log_level.value

logger.add(
    sink=LOG_FILE_PATH,
    enqueue=True,
    retention='3 days',
    encoding='utf-8',
    level=log_level,
    delay=True)

# 配置文件在导入 config 模块时已加载（qconfig.load 早于本文件 sink 初始化），
# 故在此补记，保证启动阶段的配置文件加载行为也在日志中可追踪
log.debug(f'加载配置文件: {CONFIG_FILE_PATH}')
log.debug('配置文件加载完成')
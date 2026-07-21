"""设置页面辅助工具：@action 装饰器 + 信号槽简化。"""

import functools

from qasync import asyncSlot
from qfluentwidgets import InfoBar, InfoBarPosition

from .. import ht_lib as lib


def action(success_msg: str = '', fail_msg: str = '操作失败'):
    """装饰器：自动包装异步方法 → asyncSlot → InfoBar 反馈。

    用法：
        @action('天气数据已更新', '获取失败')
        async def on_refresh_weather(self):
            w = WeatherWidget()
            return await w.get_data_async()

        方法返回值非空 → 显示 success_msg
        返回空/None  → 显示 fail_msg
        抛出异常     → 显示异常信息

    也适用于同步方法：
        @action('删除成功')
        def on_delete(self):
            shutil.rmtree(path)
            return True
    """
    def deco(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                result = func(self, *args, **kwargs)
                # 如果是协程，await
                if hasattr(result, '__await__'):
                    result = await result
                if result:
                    InfoBar.success(title=success_msg, content='', parent=self,
                                    position=InfoBarPosition.TOP_RIGHT,
                                    duration=2000)
                else:
                    InfoBar.error(title=fail_msg, content='', parent=self,
                                  position=InfoBarPosition.TOP_RIGHT,
                                  duration=2000)
                return result
            except Exception as e:
                lib.log.error(f'设置-操作失败: {e}')
                InfoBar.error(title=str(e), content='', parent=self,
                              position=InfoBarPosition.TOP_RIGHT,
                              duration=3000)
        return asyncSlot()(wrapper)
    return deco

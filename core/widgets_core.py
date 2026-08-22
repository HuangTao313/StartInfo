"""
组件框架 —— WidgetBase / LocalWidgetBase / NetworkWidgetBase

核心理念：
    子类声明意图（WIDGET_NAME / NEED_CACHE / LOCAL_INTERVAL），
    框架通过 get_data() 模板方法自动编排'读缓存 → 判断过期 → 重新获取 → 写回缓存'。

使用示例：

    class MyWeather(NetworkWidgetBase):
        WIDGET_NAME = '天气'
        NEED_CACHE = True
        LOCAL_INTERVAL = '1h'
        API_URL = 'https://api.weather.com/v1'

        def _parse_data(self, data: dict) -> dict:
            return {'temp': data['current']['temp']}

    w = MyWeather()
    w.get_data()                     # 自动走缓存
    w.get_data(force_refresh=True)   # 强制刷新
    await w.get_data_async()         # 异步版（默认短连接，用完即关）
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, TypedDict

import httpx

from .base_lib import log, is_internet
from .paths import DB_FOLDER_PATH
from .config import ConfigItem


# =============================================================================
# 缓存管理层
# =============================================================================

class CacheManager:
    """组件缓存 SQLite 持久化层（widget_name + cache_key 二级键）。"""

    DB_PATH = DB_FOLDER_PATH / 'widgets_cache.db'
    _initialized = False

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @classmethod
    def _ensure_db_dir(cls) -> None:
        cls.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        return sqlite3.connect(str(cls.DB_PATH))

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    @classmethod
    def init_db(cls) -> bool:
        """初始化数据库和表结构。幂等，可重复调用。"""
        if cls._initialized:
            return True
        try:
            cls._ensure_db_dir()
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS widgets_cache (
                    widget_name TEXT,
                    cache_key   TEXT,
                    cached_data TEXT,
                    updated_at  REAL,
                    PRIMARY KEY (widget_name, cache_key)
                )
            ''')
            conn.commit()
            conn.close()
            cls._initialized = True
            log.success(f'[CacheManager] 数据库已在 {cls.DB_PATH} 初始化')
            return True

        except Exception as exc:
            log.error(f'[CacheManager] 数据库初始化失败: {exc}')
            return False

    @classmethod
    def save_cache(
        cls, widget_name: str, data: dict, cache_key: str = 'default',
    ) -> bool:
        """写入 / 更新缓存。"""
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()
            json_str = json.dumps(data, ensure_ascii=False)
            cursor.execute('''
                INSERT OR REPLACE INTO widgets_cache
                    (widget_name, cache_key, cached_data, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (widget_name, cache_key, json_str, time.time()))
            conn.commit()
            conn.close()
            log.info(f'[CacheManager] [{widget_name}:{cache_key}] 缓存写入成功')
            return True

        except Exception as exc:
            log.error(f'[CacheManager] [{widget_name}:{cache_key}] 写入失败: {exc}')
            return False

    @classmethod
    def read_cache(
        cls, widget_name: str, cache_key: str = 'default',
    ) -> tuple[dict, float] | None:
        """读取缓存，返回 (data_dict, updated_at_timestamp) 或 None。"""
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT cached_data, updated_at
                FROM widgets_cache
                WHERE widget_name = ? AND cache_key = ?
            ''', (widget_name, cache_key))
            row = cursor.fetchone()
            conn.close()
            if row:
                return json.loads(row[0]), row[1]
            return None

        except Exception as exc:
            log.error(f'[CacheManager] [{widget_name}:{cache_key}] 读取失败: {exc}')
            return None

    @classmethod
    def clear_cache(cls, widget_name: str, cache_key: str | None = None) -> bool:
        """清理缓存。cache_key=None 时删除该组件全部缓存。"""
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()
            if cache_key is not None:
                cursor.execute(
                    'DELETE FROM widgets_cache WHERE widget_name = ? AND cache_key = ?',
                    (widget_name, cache_key),
                )
                log.info(f'[CacheManager] 已清空 [{widget_name}:{cache_key}] 缓存')
            else:
                cursor.execute(
                    'DELETE FROM widgets_cache WHERE widget_name = ?',
                    (widget_name,),
                )
                log.info(f'[CacheManager] 已清空 [{widget_name}] 全部缓存')
            conn.commit()
            conn.close()
            return True

        except Exception as exc:
            log.error(f'[CacheManager] 删除缓存失败: {exc}')
            return False

    # ------------------------------------------------------------------
    # JSON 路径辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_path(json_path: str) -> str:
        """将 'weather.temp' 转为 '$.'weather'.'temp''，适配 SQLite JSON 路径语法。"""
        json_path = json_path.strip()
        if json_path.startswith('$'):
            return json_path
        parts = json_path.split('.')
        return '$.' + '.'.join(f'{p}' for p in parts)

    # ------------------------------------------------------------------
    # SQLite 原生 JSON 路径读写（json_extract / json_set / json_remove）
    # ------------------------------------------------------------------

    @classmethod
    def read_path(cls, widget_name: str, cache_key: str, json_path: str
                  ) -> tuple[Any, float] | None:
        """按 JSON 路径读取子树。返回 (value, timestamp) 或 None。

        json_path 支持点分写法：'weather.temp' → '$.'weather'.'temp''。
        SQL 层直接用 json_extract()，不把整条记录反序列化到 Python。
        """
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()
            sql_path = cls._normalize_path(json_path)
            cursor.execute(
                'SELECT json_extract(cached_data, ?), updated_at '
                'FROM widgets_cache WHERE widget_name = ? AND cache_key = ?',
                (sql_path, widget_name, cache_key),
            )
            row = cursor.fetchone()
            conn.close()
            if row is None or row[0] is None:
                return None
            value = row[0]
            # 对象/数组返回值是 JSON 字符串，反序列化回 Python
            if isinstance(value, str) and value.strip()[:1] in ('{', '['):
                value = json.loads(value)
            return value, row[1]

        except Exception as exc:
            log.error(
                f'[CacheManager] 路径读取 [{widget_name}:{cache_key}::{json_path}] 失败: {exc}'
            )
            return None

    @classmethod
    def update_path(cls, widget_name: str, cache_key: str, json_path: str,
                    value: Any) -> bool:
        """局部更新缓存中的某个 JSON 路径。不影响同级其他数据；记录不存在时自动创建。

        SQL 层：INSERT OR IGNORE (空对象占位) → json_set(cached_data, path, json(value))。
        """
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()
            now = time.time()
            sql_path = cls._normalize_path(json_path)
            json_value = json.dumps(value, ensure_ascii=False)
            cursor.execute(
                'INSERT OR IGNORE INTO widgets_cache '
                '(widget_name, cache_key, cached_data, updated_at) '
                'VALUES (?, ?, ?, ?)',
                (widget_name, cache_key, '{}', now),
            )
            cursor.execute(
                'UPDATE widgets_cache '
                'SET cached_data = json_set(cached_data, ?, json(?)), '
                '    updated_at = ? '
                'WHERE widget_name = ? AND cache_key = ?',
                (sql_path, json_value, now, widget_name, cache_key),
            )
            conn.commit()
            conn.close()
            log.info(f'[CacheManager] [{widget_name}:{cache_key}::{json_path}] 路径更新成功')
            return True

        except Exception as exc:
            log.error(f'[CacheManager] 路径更新失败: {exc}')
            return False

    @classmethod
    def remove_path(cls, widget_name: str, cache_key: str, json_path: str) -> bool:
        """删除缓存中指定 JSON 路径的子树。SQL 层用 json_remove()。"""
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()
            sql_path = cls._normalize_path(json_path)
            now = time.time()
            cursor.execute(
                'UPDATE widgets_cache '
                'SET cached_data = json_remove(cached_data, ?), '
                '    updated_at = ? '
                'WHERE widget_name = ? AND cache_key = ?',
                (sql_path, now, widget_name, cache_key),
            )
            conn.commit()
            conn.close()
            log.info(f'[CacheManager] [{widget_name}:{cache_key}::{json_path}] 路径删除成功')
            return True

        except Exception as exc:
            log.error(f'[CacheManager] 路径删除失败: {exc}')
            return False


# =============================================================================
# 时间间隔解析
# =============================================================================

_INTERVAL_UNITS: dict[str, int] = {
    's': 1,
    'm': 60,
    'h': 3600,
    'd': 86400,
}


def _parse_interval(interval: str) -> float:
    """将 '1s'/'5m'/'2h'/'1d' 解析为秒数；纯数字字符串直接按秒处理。"""
    interval = str(interval).strip()
    if not interval:
        return 0.0

    # 纯数字
    if interval.isdigit():
        return float(interval)

    # 带单位
    unit = interval[-1].lower()
    number = interval[:-1]
    if unit in _INTERVAL_UNITS and number.replace('.', '', 1).isdigit():
        return float(number) * _INTERVAL_UNITS[unit]

    # 无法解析 → 默认 1 秒
    log.warning(f'[Interval] 无法解析 "{interval}"，使用默认 1s')
    return 1.0


# =============================================================================
# 组件注册表
# =============================================================================

@dataclass
class WidgetInfo:
    """组件注册信息"""
    cls: type                            # 组件类
    switch: ConfigItem                   # 启用开关
    template_key: str | None = None      # 注入模板的开关变量名(None=不注入)
    extra_template_keys: dict[str, ConfigItem] | None = None  # 子开关：模板变量名→配置项


# 全局组件注册表，@register 装饰器按定义顺序写入
registered_widgets: list[WidgetInfo] = []


def register(switch: ConfigItem, template_key: str | None = None,
             extra_template_keys: dict[str, ConfigItem] | None = None):
    """组件注册装饰器：在组件定义处声明启用开关与模板开关变量名

    用法:
        @register(cfg.words_switch, 'words_switch')
        class DailyWordsWidget(ExtNetworkWidgetBase):
            ...

        # 组件内部有子开关时，用 extra_template_keys 声明需要注入模板的子开关
        @register(cfg.datetime_switch, 'datetime_switch',
                  extra_template_keys={'holiday_switch': cfg.holiday_switch})
        class DateTimeWidget(LocalWidgetBase):
            ...

    main.py 遍历 registered_widgets 构建启用组件列表并注入模板开关状态，
    新增组件无需再修改 main.py。
    """
    def deco(cls):
        registered_widgets.append(WidgetInfo(cls, switch, template_key,
                                             extra_template_keys))
        return cls
    return deco


# =============================================================================
# 基类
# =============================================================================

class WidgetBase:
    """组件基类 —— 提供缓存模板方法。

    子类覆写点：
        _fetch_data()        → 同步获取数据，返回 dict
        _fetch_data_async()  → 异步获取数据，返回 dict

    配置属性（类变量，子类覆写）：
        WIDGET_NAME:    str   = 'StartInfo组件'   # 组件标识
        NEED_CACHE:     bool  = False             # 是否启用缓存
        LOCAL_INTERVAL: str   = '1s'              # 缓存有效期，如 '1h' / '5m' / '0'(永不过期)
    """

    WIDGET_NAME: str = 'StartInfo组件'
    NEED_CACHE: bool = False
    LOCAL_INTERVAL: str = '1s'

    def __init__(self) -> None:
        # 确保数据库已初始化（幂等）
        self._skip_cache_flag = False
        CacheManager.init_db()

    # ------------------------------------------------------------------
    # 缓存辅助（开发者可直接调用，但通常不需要）
    # ------------------------------------------------------------------

    def _read_cache(self, cache_key: str = 'default') -> tuple[dict, float] | None:
        return CacheManager.read_cache(self.WIDGET_NAME, cache_key)

    def _save_cache(self, data: dict, cache_key: str = 'default') -> bool:
        return CacheManager.save_cache(self.WIDGET_NAME, data, cache_key)

    def _clear_cache(self, cache_key: str | None = None) -> bool:
        return CacheManager.clear_cache(self.WIDGET_NAME, cache_key)

    # ------------------------------------------------------------------
    # 路径级缓存访问（透传 CacheManager 的 SQLite JSON 原生方法）
    # ------------------------------------------------------------------

    def _read_cache_path(self, json_path: str, cache_key: str = 'default'
                         ) -> tuple[Any, float] | None:
        """按 JSON 路径读取缓存子树。"""
        return CacheManager.read_path(self.WIDGET_NAME, cache_key, json_path)

    def _read_cache_value(self, path: str, default: object = 1) -> Any:
        """读取缓存路径的值，不存在时返回默认值"""
        cached = self._read_cache_path(path)
        return cached[0] if cached is not None else default

    def _update_cache_path(self, json_path: str, value: Any,
                           cache_key: str = 'default') -> bool:
        """局部更新缓存中指定 JSON 路径的值。"""
        return CacheManager.update_path(self.WIDGET_NAME, cache_key, json_path, value)

    def _remove_cache_path(self, json_path: str, cache_key: str = 'default') -> bool:
        """删除缓存中指定 JSON 路径的子树。"""
        return CacheManager.remove_path(self.WIDGET_NAME, cache_key, json_path)

    # ------------------------------------------------------------------
    # 缓存控制
    # ------------------------------------------------------------------

    def skip_cache(self) -> None:
        """标记本次获取的数据不应被缓存。

        在 _fetch_data / _parse_data 中遇到失败数据时调用此方法，
        框架会跳过本次缓存写入，下次调用时仍然重新获取。
        """
        self._skip_cache_flag = True

    # ------------------------------------------------------------------
    # 缓存有效性判断
    # ------------------------------------------------------------------

    def _is_cache_valid(self, timestamp: float) -> bool:
        """根据 LOCAL_INTERVAL 判断指定时间戳的缓存是否仍有效。"""
        if not self.NEED_CACHE:
            return False
        interval = _parse_interval(self.LOCAL_INTERVAL)
        if interval <= 0:
            # interval=0 表示「永不过期」
            return True

        # 日级缓存（'1d'）按自然日对齐：跨天即过期。
        # 若按滚动窗口（24h），昨天 21 点开机、今天 8 点开机仍会命中
        # 昨天的生日/每日一言等日级数据；'2d' 等更长间隔仍走滚动窗口。
        if interval == 86400:
            return time.strftime('%Y%m%d', time.localtime(timestamp)) \
                == time.strftime('%Y%m%d')

        return (time.time() - timestamp) < interval

    # ------------------------------------------------------------------
    # 公共入口：同步获取
    # ------------------------------------------------------------------

    def get_data(
        self, *, force_refresh: bool = False, cache_key: str = 'default',
    ) -> dict:
        """获取组件数据（自动处理缓存）。

        流程：
            1. NEED_CACHE=False → 直接调 _fetch_data() 返回
            2. NEED_CACHE=True  → 读缓存 → 有效则返回 → 无效则调 _fetch_data() 并写入
            3. force_refresh=True → 跳过缓存判断，强制重新获取

        Args:
            force_refresh: 强制刷新，跳过缓存。
            cache_key:     缓存层级标识，同一组件可维护多个独立缓存。
        """
        if not self.NEED_CACHE:
            return self._fetch_data()

        if not force_refresh:
            cached = self._read_cache(cache_key)
            if cached is not None:
                data, timestamp = cached
                if self._is_cache_valid(timestamp):
                    log.info(f'[{self.WIDGET_NAME}] 缓存命中 (key={cache_key})')
                    return data

        log.info(f'[{self.WIDGET_NAME}] 缓存未命中，重新获取 (key={cache_key})')
        data = self._fetch_data()
        if not self._skip_cache_flag:
            self._save_cache(data, cache_key)

        self._skip_cache_flag = False
        return data

    # ------------------------------------------------------------------
    # 公共入口：异步获取
    # ------------------------------------------------------------------

    async def get_data_async(
        self, *, force_refresh: bool = False, cache_key: str = 'default',
    ) -> dict:
        """异步版 get_data()，流程相同。"""
        if not self.NEED_CACHE:
            return await self._fetch_data_async()

        if not force_refresh:
            cached = self._read_cache(cache_key)
            if cached is not None:
                data, timestamp = cached
                if self._is_cache_valid(timestamp):
                    log.info(f'[{self.WIDGET_NAME}] 缓存命中 (key={cache_key}, async)')
                    return data

        log.info(f'[{self.WIDGET_NAME}] 缓存未命中，重新获取 (key={cache_key}, async)')
        data = await self._fetch_data_async()
        if not self._skip_cache_flag:
            self._save_cache(data, cache_key)
        self._skip_cache_flag = False
        return data

    # ------------------------------------------------------------------
    # 子类覆写点
    # ------------------------------------------------------------------

    def _fetch_data(self) -> dict:
        """同步获取原始数据。子类必须覆写。"""
        raise NotImplementedError(
            f'{self.__class__.__name__} 必须覆写 _fetch_data()'
        )

    async def _fetch_data_async(self) -> dict:
        """异步获取原始数据。默认回退到同步 _fetch_data()。"""
        return self._fetch_data()


# =============================================================================
# 本地组件基类
# =============================================================================

class LocalWidgetBase(WidgetBase):
    """本地组件基类 —— 数据不依赖网络。"""

    def _fetch_data(self) -> dict:
        raise NotImplementedError(
            f'{self.__class__.__name__} 必须覆写 _fetch_data()'
        )

    async def _fetch_data_async(self) -> dict:
        return self._fetch_data()


# =============================================================================
# 联网组件基类
# =============================================================================

class NetworkWidgetBase(WidgetBase):
    """联网组件基类 —— 封装 httpx 同步/异步请求。

    子类覆写点：
        _parse_data(raw_data: dict) → dict   # 解析 API 返回的 JSON

    类变量（子类直接覆写，和 API_URL 同级）：
        PARAMS:   dict | None = None      # 请求参数字典
        HEADERS:  dict | None = None      # 请求头字典
        RETRY_COUNT: int = 2              # 失败后重试次数（总共请求 count+1 次）
        RETRY_DELAY: float = 1.0          # 重试间隔（秒）
        REQUEST_TIMEOUT: float = 5.0      # 单次请求超时时间（秒）
    """

    API_URL: str = ''
    PARAMS: dict[str, str] | None = None
    HEADERS: dict[str, str] | None = None
    RETRY_COUNT: int = 2
    RETRY_DELAY: float = 1.0
    REQUEST_TIMEOUT: float = 5.0

    def __init__(self) -> None:
        super().__init__()
        self._async_client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # 子类覆写点：解析
    # ------------------------------------------------------------------

    def _parse_data(self, raw_data: dict) -> dict:
        """解析 API 返回的原始 JSON。子类必须覆写。"""
        raise NotImplementedError(
            f'{self.__class__.__name__} 必须覆写 _parse_data()'
        )

    # ------------------------------------------------------------------
    # 同步请求
    # ------------------------------------------------------------------

    def _sync_request(self) -> dict | None:
        """发出同步 GET 请求并返回解析后的数据。"""
        # 检查是否联网
        if not is_internet():
            log.error(f'当前未联网，联网组件 [{self.WIDGET_NAME}] 无法获取数据')
            return None

        if not self.API_URL:
            msg = f'联网组件 [{self.WIDGET_NAME}] 未配置 API_URL'
            log.error(msg)
            raise ValueError(msg)

        total_attempts = self.RETRY_COUNT + 1
        for attempt in range(total_attempts):
            try:
                with httpx.Client(timeout=self.REQUEST_TIMEOUT, follow_redirects=True) as client:
                    response = client.get(
                        self.API_URL,
                        params=self.PARAMS,
                        headers=self.HEADERS,
                    )
                    response.raise_for_status()
                    return self._parse_data(response.json())

            except httpx.HTTPError as exc:
                # last_exc = exc
                if attempt < total_attempts - 1:
                    log.warning(
                        f'[{self.WIDGET_NAME}] 请求失败（{attempt+1}/{total_attempts}），'
                        f'{self.RETRY_DELAY}s 后重试: {exc}'
                    )
                    time.sleep(self.RETRY_DELAY)

                else:
                    msg = f'组件 [{self.WIDGET_NAME}] 获取数据失败（已重试 {self.RETRY_COUNT} 次）'
                    log.error(f'{msg}: {exc}')
                    raise ConnectionError(msg) from exc

            except Exception as exc:
                msg = f'组件 [{self.WIDGET_NAME}] 发生未知错误'
                log.error(f'{msg}: {exc}')
                raise RuntimeError(msg) from exc

    # ------------------------------------------------------------------
    # 异步请求
    # ------------------------------------------------------------------

    async def _async_request(self) -> dict | None:
        """短连接异步 GET 请求。每次调用创建临时 AsyncClient，请求结束自动关闭。

        适合大多数组件（小时/天级刷新），无需手动管理连接。
        """
        # 检查是否联网
        if not is_internet():
            log.error(f'当前未联网，联网组件 [{self.WIDGET_NAME}] 无法获取数据')
            return None

        if not self.API_URL:
            msg = f'联网组件 [{self.WIDGET_NAME}] 未配置 API_URL'
            log.error(msg)
            raise ValueError(msg)

        total_attempts = self.RETRY_COUNT + 1
        for attempt in range(total_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT, follow_redirects=True) as client:
                    response = await client.get(
                        self.API_URL,
                        params=self.PARAMS,
                        headers=self.HEADERS,
                    )
                    response.raise_for_status()
                    return self._parse_data(response.json())

            except httpx.HTTPError as exc:
                if attempt < total_attempts - 1:
                    log.warning(
                        f'[{self.WIDGET_NAME}] 请求失败（{attempt+1}/{total_attempts}），'
                        f'{self.RETRY_DELAY}s 后重试: {exc}'
                    )
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    msg = f'组件 [{self.WIDGET_NAME}] 获取数据失败（已重试 {self.RETRY_COUNT} 次）'
                    log.error(f'{msg}: {exc}')
                    raise ConnectionError(msg) from exc

            except Exception as exc:
                msg = f'组件 [{self.WIDGET_NAME}] 发生未知错误'
                log.error(f'{msg}: {exc}')
                raise RuntimeError(msg) from exc

    # ------------------------------------------------------------------
    # 框架入口（覆写父类）
    # ------------------------------------------------------------------

    def _fetch_data(self) -> dict:
        return self._sync_request()

    async def _fetch_data_async(self) -> dict:
        return await self._async_request()

# 适用于高级联网组件的API定义标准
class APIConfig(TypedDict, total=False):
    url: str
    params: dict[str, Any] | None
    headers: dict[str, Any] | None
    parse_func: str

class ExtNetworkWidgetBase(WidgetBase):
    """支持多数据源、多 API 的高级联网组件基类"""
    # 数据源 → API名称 → API配置
    API_DATA: dict[str, dict[str, APIConfig]] | None = None

    # 用于决定当前使用哪个数据源
    CONFIG_ITEM: ConfigItem | None = None

    RETRY_COUNT: int = 2
    RETRY_DELAY: float = 1.0
    REQUEST_TIMEOUT: float = 5.0

    # --------------------------------------------------------------
    # 当前数据源
    # --------------------------------------------------------------
    @property
    def DATA_SOURCE(self) -> str:
        if self.CONFIG_ITEM is None:
            raise AttributeError(f'组件 [{self.WIDGET_NAME}] 未配置 CONFIG_ITEM')

        return self.CONFIG_ITEM.value

    @property
    def CURRENT_API_DATA(self) -> dict[str, APIConfig]:
        """获取当前数据源的全部 API 配置"""
        if self.API_DATA is None:
            log.error(f'组件 [{self.WIDGET_NAME}] 的 API_DATA 为空')
            raise AttributeError('API_DATA is None')

        data = self.API_DATA.get(self.DATA_SOURCE)
        if data is None:
            log.error(f'组件 [{self.WIDGET_NAME}]不存在数据源 [{self.DATA_SOURCE}]')
            raise KeyError(f'Unknown API source: {self.DATA_SOURCE}')

        return data

    # --------------------------------------------------------------
    # 初始化
    # --------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__()
        self._async_client: httpx.AsyncClient | None = None
        # 最近一次获取失败的用户可读错误信息（成功或未触发获取时为空字符串）
        self.last_error: str = ''

    # --------------------------------------------------------------
    # 单个 API —— 同步
    # --------------------------------------------------------------

    def _request_api(
        self,
        api_name: str,
        api_config: APIConfig,
    ) -> dict | None:
        """同步请求一个 API 并解析结果"""
        url = api_config.get('url')

        if not url:
            msg = f'组件 [{self.WIDGET_NAME}] API [{api_name}] 未配置 url'
            log.error(msg)
            raise ValueError(msg)

        total_attempts = self.RETRY_COUNT + 1

        for attempt in range(total_attempts):
            try:
                with httpx.Client(timeout=self.REQUEST_TIMEOUT, follow_redirects=True) as client:
                    response = client.get(
                        url,
                        params=api_config.get('params'),
                        headers=api_config.get('headers'),
                    )
                    response.raise_for_status()
                    raw_data = response.json()

                    # 获取解析函数名称
                    func_name = api_config.get('parse_func')

                    if func_name is None:
                        return raw_data

                    # 根据字符串获取实例方法
                    parse_func = getattr(self, func_name)
                    return parse_func(raw_data)

            except httpx.HTTPError as exc:
                if attempt < total_attempts - 1:
                    log.error(
                        f'[{self.WIDGET_NAME}] '
                        f'API [{api_name}] 请求失败 '
                        f'({attempt + 1}/{total_attempts})，'
                        f'{self.RETRY_DELAY}s 后重试: {exc}'
                    )

                    time.sleep(self.RETRY_DELAY)

                else:
                    msg = (f'组件 [{self.WIDGET_NAME}] API [{api_name}] 获取数据失败')
                    log.error(f'{msg}: {exc}')
                    raise ConnectionError(f'{msg}: {exc}') from exc

            except Exception as exc:
                msg = (f'组件 [{self.WIDGET_NAME}] API [{api_name}] 发生未知错误')
                log.error(f'{msg}: {exc}')
                raise RuntimeError(f'{msg}: {exc}') from exc

        return None

    # --------------------------------------------------------------
    # 单个 API —— 异步
    # --------------------------------------------------------------

    async def _request_api_async(
        self,
        api_name: str,
        api_config: APIConfig,
    ) -> dict | None:
        """异步请求一个 API 并解析结果"""
        url = api_config.get('url')

        if not url:
            raise ValueError(
                f'组件 [{self.WIDGET_NAME}] '
                f'API [{api_name}] 未配置 url'
            )

        total_attempts = self.RETRY_COUNT + 1
        for attempt in range(total_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT, follow_redirects=True) as client:
                    response = await client.get(
                        url,
                        params=api_config.get('params'),
                        headers=api_config.get('headers'),
                    )

                    response.raise_for_status()
                    raw_data = response.json()
                    func_name = api_config.get('parse_func')

                    if func_name is None:
                        return raw_data

                    parse_func = getattr(self, func_name)

                    return parse_func(raw_data)

            except httpx.HTTPError as exc:
                if attempt < total_attempts - 1:
                    log.warning(
                        f'[{self.WIDGET_NAME}] '
                        f'API [{api_name}] 请求失败 '
                        f'({attempt + 1}/{total_attempts})，'
                        f'{self.RETRY_DELAY}s 后重试: {exc}'
                    )

                    await asyncio.sleep(self.RETRY_DELAY)

                else:
                    msg = f'组件 [{self.WIDGET_NAME}] API [{api_name}] 获取数据失败'
                    log.error(f'{msg}: {exc}')
                    raise ConnectionError(f'{msg}: {exc}') from exc

            except Exception as exc:
                msg = f'组件 [{self.WIDGET_NAME}] API [{api_name}] 发生未知错误'
                log.error(f'{msg}: {exc}')
                raise RuntimeError(f'{msg}: {exc}') from exc

        return None

    # --------------------------------------------------------------
    # API 调度 —— 同步
    # --------------------------------------------------------------
    def _dispatch_requests(self) -> dict | None:
        """同步调度当前数据源的全部 API"""
        # 检查是否联网
        if not is_internet():
            self.last_error = '当前未联网，无法获取数据'
            log.error(f'当前未联网，联网组件 [{self.WIDGET_NAME}] 无法获取数据')
            return None

        result = {}
        errors = []

        for api_name, api_config in self.CURRENT_API_DATA.items():
            try:
                data = self._request_api(api_name, api_config)
                if data:
                    result.update(data)
                else:
                    # 请求成功但解析函数返回空，视为解析失败
                    errors.append(f'{api_name}: 数据解析失败')
                    log.error(f'[{self.WIDGET_NAME}] API [{api_name}] 解析失败')
            except Exception as e:
                # 单个 API 失败不影响其他 API 的数据
                errors.append(str(e))
                log.error(f'[{self.WIDGET_NAME}] API [{api_name}] 获取失败: {e}')

        # 任一 API 失败时不缓存部分结果，下次启动重新获取全部
        if errors:
            self.last_error = '；'.join(errors)
            self.skip_cache()

        # 记录本次缓存对应的数据源，供 get_cached_source() 判断切换
        if result:
            result['source'] = self.DATA_SOURCE

        return result

    # --------------------------------------------------------------
    # API 调度 —— 异步
    # --------------------------------------------------------------
    async def _dispatch_requests_async(self) -> dict | None:
        """异步并发调度当前数据源的全部 API"""
        # 检查是否联网
        if not is_internet():
            self.last_error = '当前未联网，无法获取数据'
            log.error(f'当前未联网，联网组件 [{self.WIDGET_NAME}] 无法获取数据')
            return None

        tasks = [
            self._request_api_async(api_name, api_config)
            for api_name, api_config
            in self.CURRENT_API_DATA.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        result = {}
        errors = []

        for data in results:
            if isinstance(data, Exception):
                # 单个 API 失败不影响其他 API 的数据
                errors.append(str(data))
                log.error(f'[{self.WIDGET_NAME}] API 获取失败: {data}')
            elif data:
                result.update(data)
            else:
                # 请求成功但解析函数返回空，视为解析失败
                errors.append('数据解析失败')
                log.error(f'[{self.WIDGET_NAME}] API 解析失败')

        # 任一 API 失败时不缓存部分结果，下次启动重新获取全部
        if errors:
            self.last_error = '；'.join(errors)
            self.skip_cache()

        # 记录本次缓存对应的数据源，供 get_cached_source() 判断切换
        if result:
            result['source'] = self.DATA_SOURCE

        return result

    # --------------------------------------------------------------
    # 框架入口
    # --------------------------------------------------------------
    def _fetch_data(self) -> dict:
        return self._dispatch_requests()

    async def _fetch_data_async(self) -> dict:
        return await self._dispatch_requests_async()

    # --------------------------------------------------------------
    # 缓存相关
    # --------------------------------------------------------------
    def get_cached_source(self) -> str | None:
        """获取已缓存内容的数据源名称(无缓存时返回 None)"""
        cached = self._read_cache_path('source')
        return cached[0] if cached is not None else None
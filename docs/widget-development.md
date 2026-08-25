# 组件系统开发文档

> 版本：2.0 · 适用：StartInfo 组件框架（基类 `core/widgets_core.py`，内置组件 `core/widgets.py`）

---

## 目录

- [架构总览](#架构总览)
- [快速开始](#快速开始)
  - [本地组件](#1-本地组件)
  - [联网组件](#2-联网组件)
- [缓存系统](#缓存系统)
  - [基本配置](#基本配置)
  - [多缓存键](#多缓存键)
  - [JSON 路径读写](#json-路径读写)
  - [过期策略详解](#过期策略详解)
- [异步模式](#异步模式)
- [API 参考](#api-参考)
  - [LocalWidgetBase](#localwidgetbase)
  - [NetworkWidgetBase](#networkwidgetbase)
  - [ExtNetworkWidgetBase](#extnetworkwidgetbase)
  - [register 装饰器](#register-装饰器)
  - [CacheManager](#cachemanager)
- [从旧版迁移](#从旧版迁移)
- [FAQ](#faq)

---

## 架构总览

```
LocalWidgetBase                     ← 组件根基类（get_data() / get_data_async() 模板方法）
│                                     子类只需声明 WIDGET_NAME / NEED_CACHE / LOCAL_INTERVAL
│                                     并覆写 _fetch_data()
│
├── NetworkWidgetBase               ← 单 API 联网组件，封装 httpx 请求
│     ├─ _sync_request()            ← 同步 GET（httpx.Client）
│     └─ _async_request()           ← 异步 GET（httpx.AsyncClient，短连接用完即关）
│
└── ExtNetworkWidgetBase            ← 多数据源/多 API 联网组件
      API_DATA 定义可用数据源，按 CONFIG_ITEM 切换（单数据源可省略），
      并发请求当前数据源的全部 API
```

**核心原则：** 子类声明意图（`WIDGET_NAME` / `NEED_CACHE` / `LOCAL_INTERVAL`），框架自动编排"读缓存 → 判断过期 → 重新获取 → 写回缓存"。

> 说明：原 `WidgetBase` 与 `LocalWidgetBase` 已合并为同一个 `LocalWidgetBase`，所有组件（本地 / 联网 / 多数据源）统一继承它。

内置组件（`core/widgets.py`）通过 `@register` 装饰器注册到组件注册表，`main.py` 遍历 `registered_widgets` 构建启用组件列表并注入模板，新增组件无需再修改 `main.py`（见 [register 装饰器](#register-装饰器)）。

---

## 快速开始

### 1. 本地组件

```python
from datetime import datetime

from .widgets_core import LocalWidgetBase


class GreetingWidget(LocalWidgetBase):
    WIDGET_NAME    = "问候语"
    NEED_CACHE     = False

    def _fetch_data(self) -> dict:
        hour = datetime.now().hour
        greeting = ("早上好" if 6 <= hour < 11 else
                    "中午好" if 11 <= hour < 12 else
                    "下午好" if 12 <= hour < 18 else
                    "晚上好")
        return {"greeting": greeting}
```

调用：

```python
w = GreetingWidget()
data = w.get_data()
data = w.get_data(force_refresh=True)  # 跳过缓存
await w.get_data_async()                # 异步调用
```

### 2. 联网组件

```python
from .widgets_core import NetworkWidgetBase


class HitokotoWidget(NetworkWidgetBase):
    WIDGET_NAME    = "一言"
    NEED_CACHE     = True
    LOCAL_INTERVAL = "1d"          # 一天只请求一次
    API_URL        = "https://v1.hitokoto.cn/"

    def _parse_data(self, raw: dict) -> dict:
        return {
            "hitokoto": raw.get("hitokoto", ""),
            "from":     raw.get("from", ""),
            "from_who": raw.get("from_who", ""),
        }
```

调用：

```python
h = HitokotoWidget()
data = h.get_data()
# 当天再次调用直接返回缓存，不发网络请求
```

---

## 缓存系统

### 基本配置

组件上声明三个类变量即可：

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `WIDGET_NAME` | `str` | `"StartInfo组件"` | 组件唯一标识，用于数据库主键 |
| `NEED_CACHE` | `bool` | `False` | 是否启用缓存 |
| `LOCAL_INTERVAL` | `str` | `"1s"` | 缓存有效期，支持 `"1s"` `"5m"` `"2h"` `"1d"` |

### 多缓存键

同一组件可管理多个独立缓存，使用 `cache_key` 区分：

```python
# 可以从 API 返回中提取不同部分，分别缓存
class WeatherWidget(NetworkWidgetBase):
    def _fetch_data(self) -> dict:
        raw = self._sync_request()
        self._save_cache(raw.get("weather", {}), cache_key="weather")
        self._save_cache(raw.get("aqi", {}),     cache_key="aqi")
        return raw

    def get_weather(self):
        return self.get_data(cache_key="weather")

    def get_aqi(self):
        return self.get_data(cache_key="aqi")
```

### JSON 路径读写

利用 SQLite 原生的 `json_extract` / `json_set` / `json_remove`，支持按路径操作缓存，不缓存整个 dict 到 Python 内存。

```python
# 路径写法：点分，如 "weather.temp" 或 "$.weather.temp"
value, ts = widget._read_cache_path("weather.temp")
widget._update_cache_path("weather.temp", 30)
widget._remove_cache_path("weather")
```

**优势：** 更新一个叶子节点时，SQL 层面只写一行，不需要把整个 dict 读出 → Python 改 → 重新写入。

### 过期策略详解

| `NEED_CACHE` | `LOCAL_INTERVAL` | 行为 |
|:---:|:---:|---|
| `False` | 任意 | 每次调用 `get_data()` 直接执行 `_fetch_data()` |
| `True` | `"1h"` | 缓存写入后 1 小时内返回缓存，过期后重新获取 |
| `True` | `"0"` 或 `"0s"` | 缓存永不过期，写入后永远返回缓存（除非 `force_refresh=True`） |
| `True` | `"1d"` | 按自然日对齐，跨天即过期（避免昨天 21 点写入、今天 8 点仍命中的问题） |

`force_refresh=True` 在任何情况下都跳过缓存判断，强制 `_fetch_data()`。

### 跳过缓存

当数据获取失败（网络超时、API 返回错误）时，不应该把错误数据写入缓存。在 `_parse_data` 或 `_fetch_data` 中调用 `self.skip_cache()` 即可：

```python
class WeatherWidget(NetworkWidgetBase):
    def _parse_data(self, raw_data: dict) -> dict:
        now = raw_data.get('now')
        if not now:
            self.skip_cache()       # 失败数据不缓存
            return {}
        return {...}
```

调用 `skip_cache()` 后，本次 `get_data()` 只返回数据但不写入数据库，下次调用仍然会重新获取。

---

## 异步模式

`get_data_async()` 走短连接异步请求：每次调用创建临时 `httpx.AsyncClient`，请求结束自动关闭，无需手动管理连接。

```python
async def _async_request(self) -> dict:
    async with httpx.AsyncClient(timeout=5.0) as client:
        ...
```

- 零心智负担，适合绝大多数组件（小时/天级刷新）
- 同步（`get_data()`）与异步（`get_data_async()`）共享同一套缓存逻辑，可混用

`ExtNetworkWidgetBase` 的异步调度使用 `asyncio.gather` 并发请求当前数据源下的全部 API。

---

## 解析函数约定

联网组件的解析函数（`NetworkWidgetBase._parse_data` / `ExtNetworkWidgetBase` 中由 `parse_func` 指定的 `_parse_xxx`）遵循以下约定，保证失败时不会丢失整块数据、也不会把坏数据写进缓存：

1. **永不抛异常**：解析函数是"全函数"。异常会沿 `_sync_request` / `_request_api` 一路抛到 `main.py`，导致整个组件数据被丢弃。
2. **取值一律用 `.get()`**：
   - 可选字段：`.get(key, 默认值)`（默认值通常为 `''`）。
   - 必需字段：`.get(key)` 判空（不填默认值时缺省为 `None`），缺失 → `self.skip_cache()` + `return None`。
   - 嵌套 ≥2 层、或同一字段要取多次时，先抽成局部变量，不要写长链式 `.get()`（如 `data.get('a',{}).get('b',{}).get('c','')`）；单层且只取一次的字段直接内联。
   - 带单位/后缀的可选字段用基类提供的 `self._fmt(value, suffix)` 拼接：值为 `None` 时返回空串，避免渲染出 `None℃`。
3. **失败返回 `None` + `skip_cache()`**：`None` 不会写入缓存；`main.py` 会跳过 `None` 结果，模板引擎对缺失变量只是不显示、不会报错。`ExtNetworkWidgetBase` 会把返回 `None` 的 API 记为解析失败（计入 `last_error`），其他 API 的数据不受影响。

```python
def _parse_weather(self, raw_data: dict) -> dict | None:
    now = raw_data.get('now')
    if not now:                      # 必需字段缺失
        self.skip_cache()
        return None

    weather = now.get('text')        # 多处使用 → 提前取出
    return {
        'weather': weather,
        # 单层且只取一次 → 内联；缺失由 _fmt 兜底为空串
        'temperature': self._fmt(now.get('temp'), '℃'),
        'humidity': self._fmt(now.get('humidity'), '%'),
    }
```

---

## API 参考

### LocalWidgetBase

所有组件的根基类（原 `WidgetBase` 与 `LocalWidgetBase` 已合并）。

**类变量（子类覆写）：**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `WIDGET_NAME` | `str` | `"StartInfo组件"` | 组件标识，数据库主键的一部分 |
| `NEED_CACHE` | `bool` | `False` | 是否启用缓存 |
| `LOCAL_INTERVAL` | `str` | `"1s"` | 缓存有效期 |

**公共方法：**

| 方法 | 返回 | 说明 |
|------|------|------|
| `get_data(*, force_refresh=False, cache_key="default")` | `dict` | 同步获取数据，自动处理缓存 |
| `get_data_async(*, force_refresh=False, cache_key="default")` | `dict` | 异步获取数据，自动处理缓存 |
| `skip_cache()` | `None` | 标记本次获取的数据不写入缓存 |

**缓存辅助方法（通常不需要直接调用）：**

| 方法 | 返回 | 说明 |
|------|------|------|
| `_read_cache(cache_key)` | `(dict, float) \| None` | 读整条缓存 + 时间戳 |
| `_save_cache(data, cache_key)` | `bool` | 写入整条缓存 |
| `_clear_cache(cache_key)` | `bool` | 删除缓存 |
| `_read_cache_path(json_path, cache_key)` | `(Any, float) \| None` | 读路径节点 + 时间戳 |
| `_read_cache_value(path, default)` | `Any` | 读取缓存路径的值，不存在时返回默认值 |
| `_update_cache_path(json_path, value, cache_key)` | `bool` | 局部更新路径值 |
| `_remove_cache_path(json_path, cache_key)` | `bool` | 删除路径子树 |

**子类覆写点：**

| 方法 | 返回 | 说明 |
|------|------|------|
| `_fetch_data()` | `dict` | 同步获取原始数据（必须覆写） |
| `_fetch_data_async()` | `dict` | 异步获取（默认回退到同步 `_fetch_data()`） |

### NetworkWidgetBase

继承 `LocalWidgetBase`，封装单 API 的 httpx 同步/异步请求。

**额外类变量：**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `API_URL` | `str` | `""` | API 地址（必须设置） |
| `PARAMS` | `dict \| None` | `None` | 请求参数字典 |
| `HEADERS` | `dict \| None` | `None` | 请求头字典 |
| `RETRY_COUNT` | `int` | `2` | 失败后重试次数（总共请求 count+1 次） |
| `RETRY_DELAY` | `float` | `1.0` | 重试间隔（秒） |
| `REQUEST_TIMEOUT` | `float` | `5.0` | 单次请求超时时间（秒） |

**子类覆写点：**

| 方法 | 返回 | 说明 |
|------|------|------|
| `_parse_data(raw_data)` | `dict` | 解析 API 返回的 JSON（必须覆写） |

**内部方法：**

| 方法 | 返回 | 说明 |
|------|------|------|
| `_sync_request()` | `dict` | 同步 GET（`httpx.Client`） |
| `_async_request()` | `dict` | 异步 GET（`httpx.AsyncClient`，短连接用完即关） |

`_fetch_data()` / `_fetch_data_async()` 已分别接入 `_sync_request()` / `_async_request()`，子类无需覆写。

### ExtNetworkWidgetBase

继承 `LocalWidgetBase`（原 `MultiSourceWidgetBase`，重命名为"数据源 → 多 API"结构）。用于同一组件有多个数据源可选、每个数据源又包含多个 API 的场景（如天气组件支持 qweather / xiaomi_weather 两个数据源，qweather 下又分天气、空气质量两个 API）；也支持只有一个数据源、包含多个 API 的组件，此时无需绑定 `CONFIG_ITEM`。

**类变量：**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `API_DATA` | `dict[str, dict[str, APIConfig]] \| None` | `None` | 数据源 → API名称 → API 配置（必须覆写） |
| `CONFIG_ITEM` | `ConfigItem \| None` | `None` | 数据源切换配置项（多数据源必须绑定；单数据源可省略，自动取唯一数据源） |
| `RETRY_COUNT` | `int` | `2` | 单个 API 失败后重试次数（总共请求 count+1 次） |
| `RETRY_DELAY` | `float` | `1.0` | 重试间隔（秒） |
| `REQUEST_TIMEOUT` | `float` | `5.0` | 单次请求超时时间（秒） |

`APIConfig` 字段（`TypedDict`，均可选）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | `str` | API 地址 |
| `params` | `dict \| None` | 请求参数字典 |
| `headers` | `dict \| None` | 请求头字典 |
| `parse_func` | `str` | 解析函数名（字符串，对应子类方法） |

**只读属性（由 API_DATA + CONFIG_ITEM 自动推导）：**

| 属性 | 说明 |
|------|------|
| `DATA_SOURCE` | 当前选中的数据源名称（`CONFIG_ITEM.value`；未绑定且仅一个数据源时自动取该数据源） |
| `CURRENT_API_DATA` | 当前数据源的全部 API 配置 |

**实例属性：**

| 属性 | 说明 |
|------|------|
| `last_error` | 最近一次获取失败的用户可读错误信息（成功时为空字符串） |

**子类覆写点：**

- 为每个 API 写一个解析方法，方法名与 `APIConfig.parse_func` 对应
- 解析方法接收 API 原始 JSON，返回 `dict`；返回 `None` 视为解析失败

**公共方法：**

| 方法 | 返回 | 说明 |
|------|------|------|
| `get_cached_source()` | `str \| None` | 读取已缓存数据来自哪个数据源（无缓存时返回 None） |

**使用示例：**

```python
class DailyWordsWidget(ExtNetworkWidgetBase):
    WIDGET_NAME    = 'EveryDayWords'
    NEED_CACHE     = True
    LOCAL_INTERVAL = '1d'
    CONFIG_ITEM    = cfg.words_source            # OptionsConfigItem，选项如 ['iciba', 'hitokoto']
    API_DATA = {
        'iciba': {
            'words': {
                'url': 'https://open.iciba.com/dsapi/',
                'parse_func': '_parse_iciba',
            },
        },
        'hitokoto': {
            'words': {
                'url': 'https://v1.hitokoto.cn/',
                'parse_func': '_parse_hitokoto',
            },
        },
    }

    def _parse_iciba(self, raw_data: dict) -> dict | None:
        return {'words_primary': raw_data.get('note', '')}

    def _parse_hitokoto(self, raw_data: dict) -> dict | None:
        return {'words_primary': raw_data.get('hitokoto', '')}
```

调用方式与普通联网组件一致：`widget.get_data()` / `await widget.get_data_async()`。调度时并发请求当前数据源下的全部 API 并把结果合并为一个字典；解析结果会自动附带 `source` 字段记录数据源名称。

**注意：**
- 单数据源组件无需绑定 `CONFIG_ITEM`：当 `CONFIG_ITEM` 为 `None` 且 `API_DATA` 只有一个数据源时，基类会自动使用该唯一数据源；数据源多于一个且未绑定 `CONFIG_ITEM` 时会报错。
- 任一 API 失败时，本次结果不会写入缓存（自动 `skip_cache()`），下次启动会重新获取全部。
- 缓存中存有 `source` 字段，切换数据源后旧的缓存不会自动失效——如需切换后强制刷新，调用 `get_data(force_refresh=True)` 或先 `clear_cache()`。

### register 装饰器

内置组件通过 `@register` 注册到全局组件注册表，无需修改 `main.py`：

```python
from .widgets_core import register

@register(cfg.words_switch, 'words_switch')
class DailyWordsWidget(ExtNetworkWidgetBase):
    ...
```

签名：

| 参数 | 类型 | 说明 |
|------|------|------|
| `switch` | `ConfigItem` | 组件启用开关 |
| `template_key` | `str \| None` | 注入模板的开关变量名（None=不注入） |
| `extra_template_keys` | `dict[str, ConfigItem] \| None` | 组件内部子开关：模板变量名 → 配置项 |

### CacheManager

进阶使用，通常不需要直接调用。所有方法均通过 `LocalWidgetBase` 的封装调用。

| 类方法 | 说明 |
|--------|------|
| `init_db()` | 初始化数据库（幂等，`LocalWidgetBase.__init__` 已调用） |
| `read_path(w, ck, path)` | `json_extract` 路径读取 |
| `update_path(w, ck, path, value)` | `json_set` 路径写入 |
| `remove_path(w, ck, path)` | `json_remove` 路径删除 |

详情见 [JSON 路径读写](#json-路径读写) 章节。

---

## 从旧版迁移

旧版 `core/get_data.py` 使用独立函数 + `format_data_to_json` / `format_data_to_jinja2` 手动管理缓存。迁移至组件框架后的变化：

| | 旧版 | 新版 |
|---|---|---|
| 数据获取 | 每个模块一个独立函数 | 一个类，覆写 `_fetch_data` |
| 网络请求 | 手动 `aiohttp` + session 管理 | 框架封装 `httpx`，自动处理 |
| 缓存 | 手动 `data.json` 读写 | SQLite 自动缓存，按 cache_key / 路径管理 |
| 异常处理 | 每函数写 `try/except/return False` | 框架统一抛出，调用方决定如何处理 |
| 类型安全 | 返回 `dict \| bool`（易忘判假） | 返回 `dict`，失败则抛异常 |

迁移步骤：

1. 新建组件类，继承 `LocalWidgetBase`（本地）或 `NetworkWidgetBase` / `ExtNetworkWidgetBase`（联网）
2. 从原函数的业务逻辑中提取数据获取/解析代码放入 `_fetch_data` / `_parse_data` 或 `parse_func` 指定的解析方法
3. 配置 `NEED_CACHE` 和 `LOCAL_INTERVAL`
4. 调用方统一用 `widget.get_data()` / `await widget.get_data_async()`

> 旧版组件基类分为 `WidgetBase` 与 `LocalWidgetBase` 两个类，现已在重构中合并为 `LocalWidgetBase`，迁移时统一继承即可。

---

## FAQ

**Q：缓存数据库文件在哪？**

`data/db/widgets_cache.db`。`CacheManager.init_db()` 在 `LocalWidgetBase.__init__()` 中自动调用（幂等）。

**Q：组件缓存和用户配置是什么关系？**

两者独立。组件缓存（`widgets_cache.db`）按组件管理运行时数据；用户配置由 `cfg`（qfluentwidgets 配置系统，持久化在 `data/json/config.json`）管理，组件通过 `CONFIG_ITEM` 等配置项引用。

**Q：组件怎么获取 API Key？**

框架不强制 key 管理方式。`NetworkWidgetBase` 子类设置 `PARAMS`，`ExtNetworkWidgetBase` 子类在 `API_DATA` 的 `params` 中配置：

```python
class MyWidget(NetworkWidgetBase):
    PARAMS = {"key": cfg.my_api_key.value}
```

**Q：异步方法兼容 PySide6 + qasync 吗？**

完全兼容。`ui.py` 中将全局事件循环设置为 `QEventLoop`，`httpx.AsyncClient` 底层走标准 asyncio 接口，对 qasync 透明。

**Q：同一个组件可以同时有同步和异步调用吗？**

可以。`get_data()` 用于同步上下文，`get_data_async()` 用于异步上下文，两者共享同一套缓存。不推荐混用，但技术上可行。

**Q：怎么配置自动重试？**

设置 `RETRY_COUNT` 和 `RETRY_DELAY` 类变量：

```python
class MyWidget(NetworkWidgetBase):
    RETRY_COUNT = 3      # 失败后重试 3 次（总共请求 4 次）
    RETRY_DELAY = 2.0    # 每次重试间隔 2 秒
```

- 只重试 `httpx.HTTPError`（网络/HTTP 错误），不重试代码 bug（`Exception`）
- 默认 `RETRY_COUNT=2`（共 3 次尝试），`RETRY_DELAY=1.0` 秒
- 同步重试用 `time.sleep`，异步重试用 `asyncio.sleep`，都不阻塞各自的事件循环
- `_sync_request` / `_async_request` / `_request_api` / `_request_api_async` 均享有重试逻辑

---

> 文档版本 2.0 · 维护者：HuangTao · 最后更新：2026-08-25

# Widget Development Guide

> Version: 2.0 · Applies to: the StartInfo widget framework (framework `core/widgets/framework.py`, built-in widgets `core/widgets/builtin.py`)


> StartInfo does not currently support a plugin system; all existing Widgets are built-in widgets, located uniformly in [core/widgets/builtin.py](../../core/widgets/builtin.py).

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
  - [1. Local Widgets](#1-local-widgets)
  - [2. Network Widgets](#2-network-widgets)
- [Cache System](#cache-system)
  - [Basic Configuration](#basic-configuration)
  - [Multiple Cache Keys](#multiple-cache-keys)
  - [JSON Path Read/Write](#json-path-readwrite)
  - [Expiration Strategy in Detail](#expiration-strategy-in-detail)
- [Async Mode](#async-mode)
- [API Reference](#api-reference)
  - [LocalWidgetBase](#localwidgetbase)
  - [NetworkWidgetBase](#networkwidgetbase)
  - [ExtNetworkWidgetBase](#extnetworkwidgetbase)
  - [register Decorator](#register-decorator)
  - [CacheManager](#cachemanager)
- [Migrating from the Legacy Version](#migrating-from-the-legacy-version)
- [FAQ](#faq)

---

## Architecture Overview

```
LocalWidgetBase                     ← Widget root base class (get_data() / get_data_async() template methods)
│                                     subclasses only need to declare WIDGET_NAME / NEED_CACHE / LOCAL_INTERVAL
│                                     and override _fetch_data()
│
├── NetworkWidgetBase               ← single-API network widget, wrapping httpx requests
│     ├─ _sync_request()            ← synchronous GET (httpx.Client)
│     └─ _async_request()           ← asynchronous GET (httpx.AsyncClient, short-lived connection closed when done)
│
└── ExtNetworkWidgetBase            ← multi-data-source / multi-API network widget
      API_DATA defines the available data sources, switched by CONFIG_ITEM (can be omitted for a single data source),
      concurrently requests all APIs of the current data source
```

**Core principle:** subclasses declare their intent (`WIDGET_NAME` / `NEED_CACHE` / `LOCAL_INTERVAL`), and the framework automatically orchestrates "read cache → check expiration → fetch again → write back to cache".

> Note: the former `WidgetBase` and `LocalWidgetBase` have been merged into the same `LocalWidgetBase`, which all widgets (local / network / multi-data-source) inherit from.

Built-in widgets (`core/widgets/builtin.py`) are registered into the widget registry through the `@register` decorator. `main.py` iterates over `registered_widgets` to build the list of enabled widgets and inject them into templates, so adding a new widget no longer requires modifying `main.py` (see [register Decorator](#register-decorator)).

`core.widgets` is the facade package of the widget system: the framework lives in `core/widgets/framework.py`, and built-in widgets are all written in `core/widgets/builtin.py`. **Outside the package, always import through the facade package**:

```python
from core.widgets import LocalWidgetBase, NetworkWidgetBase, ExtNetworkWidgetBase, register
```

New built-in widgets are simply appended to `core/widgets/builtin.py` and use in-package relative imports (such as `from .framework import ...`).

---

## Quick Start

### 1. Local Widgets

```python
from datetime import datetime

from core.widgets import LocalWidgetBase


class GreetingWidget(LocalWidgetBase):
    WIDGET_NAME    = "Greeting"
    NEED_CACHE     = False

    def _fetch_data(self) -> dict:
        hour = datetime.now().hour
        greeting = ("Good morning" if 6 <= hour < 11 else
                    "Good noon" if 11 <= hour < 12 else
                    "Good afternoon" if 12 <= hour < 18 else
                    "Good evening")
        return {"greeting": greeting}
```

Calling it:

```python
w = GreetingWidget()
data = w.get_data()
data = w.get_data(force_refresh=True)  # skip the cache
await w.get_data_async()                # asynchronous call
```

### 2. Network Widgets

```python
from core.widgets import NetworkWidgetBase


class HitokotoWidget(NetworkWidgetBase):
    WIDGET_NAME    = "Hitokoto"
    NEED_CACHE     = True
    LOCAL_INTERVAL = "1d"          # only request once per day
    API_URL        = "https://v1.hitokoto.cn/"

    def _parse_data(self, raw: dict) -> dict:
        return {
            "hitokoto": raw.get("hitokoto", ""),
            "from":     raw.get("from", ""),
            "from_who": raw.get("from_who", ""),
        }
```

Calling it:

```python
h = HitokotoWidget()
data = h.get_data()
# calling again on the same day returns the cache directly, with no network request
```

---

## Cache System

### Basic Configuration

Simply declare three class variables on the widget:

| Attribute | Type | Default | Description |
|------|------|--------|------|
| `WIDGET_NAME` | `str` | `"StartInfo组件"` | Unique widget identifier, used as the database primary key |
| `NEED_CACHE` | `bool` | `False` | Whether to enable caching |
| `LOCAL_INTERVAL` | `str` | `"1s"` | Cache validity period; supports `"1s"` `"5m"` `"2h"` `"1d"` |

### Multiple Cache Keys

A single widget can manage multiple independent caches, distinguished by `cache_key`:

```python
# different parts can be extracted from the API response and cached separately
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

### JSON Path Read/Write

Leveraging SQLite's native `json_extract` / `json_set` / `json_remove`, this supports operating on the cache by path, without caching the whole dict in Python memory.

```python
# path syntax: dot-separated, such as "weather.temp" or "$.weather.temp"
value, ts = widget._read_cache_path("weather.temp")
widget._update_cache_path("weather.temp", 30)
widget._remove_cache_path("weather")
```

**Advantage:** when updating a single leaf node, only one row is written at the SQL level; there is no need to read the whole dict out → modify it in Python → write it back.

### Expiration Strategy in Detail

| `NEED_CACHE` | `LOCAL_INTERVAL` | Behavior |
|:---:|:---:|---|
| `False` | any | every call to `get_data()` directly executes `_fetch_data()` |
| `True` | `"1h"` | the cache is returned within 1 hour after being written, and data is fetched again after it expires |
| `True` | `"0"` or `"0s"` | the cache never expires; once written it is always returned (unless `force_refresh=True`) |
| `True` | `"1d"` | aligned to calendar days, expiring as soon as the day changes (avoiding the problem of data written at 21:00 yesterday still being a hit at 8:00 today) |

`force_refresh=True` skips the cache check in every case and forces `_fetch_data()`.

### Skipping the Cache

When data retrieval fails (network timeout, API returning an error), the erroneous data should not be written to the cache. Simply call `self.skip_cache()` in `_parse_data` or `_fetch_data`:

```python
class WeatherWidget(NetworkWidgetBase):
    def _parse_data(self, raw_data: dict) -> dict:
        now = raw_data.get('now')
        if not now:
            self.skip_cache()       # do not cache failed data
            return {}
        return {...}
```

After `skip_cache()` is called, the current `get_data()` still returns the data but does not write it to the database, and the next call will fetch it again.

---

## Async Mode

`get_data_async()` uses short-lived asynchronous requests: each call creates a temporary `httpx.AsyncClient`, which is closed automatically when the request finishes, so there is no need to manage connections manually.

```python
async def _async_request(self) -> dict:
    async with httpx.AsyncClient(timeout=5.0) as client:
        ...
```

- Zero mental overhead, suitable for the vast majority of widgets (hourly/daily refresh)
- Synchronous (`get_data()`) and asynchronous (`get_data_async()`) calls share the same cache logic and can be mixed

`ExtNetworkWidgetBase` uses `asyncio.gather` in its asynchronous scheduling to concurrently request all APIs under the current data source.

---

## Parsing Function Conventions

The parsing functions of network widgets (`NetworkWidgetBase._parse_data` / the `_parse_xxx` specified by `parse_func` in `ExtNetworkWidgetBase`) follow the conventions below, ensuring that a failure neither loses the whole block of data nor writes bad data into the cache:

1. **Never raise exceptions**: a parsing function is a "total function". An exception would propagate along `_sync_request` / `_request_api` all the way up to `main.py`, causing the entire widget's data to be discarded.
2. **Always use `.get()` to read values**:
   - Optional fields: `.get(key, default)` (the default is usually `''`).
   - Required fields: check `.get(key)` for emptiness (when no default is given, the value defaults to `None`); if it is missing → `self.skip_cache()` + `return None`.
   - For nesting of 2 or more levels, or when the same field is read multiple times, extract it into a local variable first rather than writing a long chain of `.get()` (such as `data.get('a',{}).get('b',{}).get('c','')`); for single-level fields read only once, inline them directly.
   - For optional fields with a unit/suffix, concatenate with `self._fmt(value, suffix)` provided by the base class: when the value is `None` it returns an empty string, avoiding rendering `None℃`.
3. **On failure, return `None` + `skip_cache()`**: `None` is not written to the cache; `main.py` skips `None` results, and the template engine simply does not display missing variables rather than raising an error. `ExtNetworkWidgetBase` records an API that returns `None` as a parse failure (counted in `last_error`), without affecting the data of other APIs.

```python
def _parse_weather(self, raw_data: dict) -> dict | None:
    now = raw_data.get('now')
    if not now:                      # required field missing
        self.skip_cache()
        return None

    weather = now.get('text')        # used in several places → extract early
    return {
        'weather': weather,
        # single level, read only once → inline; a missing value falls back to an empty string via _fmt
        'temperature': self._fmt(now.get('temp'), '℃'),
        'humidity': self._fmt(now.get('humidity'), '%'),
    }
```

---

## API Reference

### LocalWidgetBase

The root base class of all widgets (the former `WidgetBase` and `LocalWidgetBase` have been merged).

**Class variables (overridden by subclasses):**

| Attribute | Type | Default | Description |
|------|------|--------|------|
| `WIDGET_NAME` | `str` | `"StartInfo组件"` | Widget identifier, part of the database primary key |
| `NEED_CACHE` | `bool` | `False` | Whether to enable caching |
| `LOCAL_INTERVAL` | `str` | `"1s"` | Cache validity period |

**Public methods:**

| Method | Returns | Description |
|------|------|------|
| `get_data(*, force_refresh=False, cache_key="default")` | `dict` | Retrieve data synchronously, handling the cache automatically |
| `get_data_async(*, force_refresh=False, cache_key="default")` | `dict` | Retrieve data asynchronously, handling the cache automatically |
| `skip_cache()` | `None` | Mark the data retrieved this time as not to be written to the cache |

**Cache helper methods (usually not called directly):**

| Method | Returns | Description |
|------|------|------|
| `_read_cache(cache_key)` | `(dict, float) \| None` | Read the whole cache entry + timestamp |
| `_save_cache(data, cache_key)` | `bool` | Write the whole cache entry |
| `_clear_cache(cache_key)` | `bool` | Delete the cache |
| `_read_cache_path(json_path, cache_key)` | `(Any, float) \| None` | Read a path node + timestamp |
| `_read_cache_value(path, default)` | `Any` | Read the value at a cache path, returning the default when it does not exist |
| `_update_cache_path(json_path, value, cache_key)` | `bool` | Partially update the value at a path |
| `_remove_cache_path(json_path, cache_key)` | `bool` | Delete a path subtree |

**Subclass override points:**

| Method | Returns | Description |
|------|------|------|
| `_fetch_data()` | `dict` | Retrieve raw data synchronously (must be overridden) |
| `_fetch_data_async()` | `dict` | Retrieve data asynchronously (falls back to the synchronous `_fetch_data()` by default) |

### NetworkWidgetBase

Inherits from `LocalWidgetBase` and wraps httpx synchronous/asynchronous requests for a single API.

**Additional class variables:**

| Attribute | Type | Default | Description |
|------|------|--------|------|
| `API_URL` | `str` | `""` | API address (must be set) |
| `PARAMS` | `dict \| None` | `None` | Request parameter dictionary |
| `HEADERS` | `dict \| None` | `None` | Request header dictionary |
| `RETRY_COUNT` | `int` | `2` | Number of retries after a failure (count+1 requests in total) |
| `RETRY_DELAY` | `float` | `1.0` | Retry interval (seconds) |
| `REQUEST_TIMEOUT` | `float` | `5.0` | Timeout for a single request (seconds) |

**Subclass override points:**

| Method | Returns | Description |
|------|------|------|
| `_parse_data(raw_data)` | `dict` | Parse the JSON returned by the API (must be overridden) |

**Internal methods:**

| Method | Returns | Description |
|------|------|------|
| `_sync_request()` | `dict` | Synchronous GET (`httpx.Client`) |
| `_async_request()` | `dict` | Asynchronous GET (`httpx.AsyncClient`, short-lived connection closed when done) |

`_fetch_data()` / `_fetch_data_async()` are already wired to `_sync_request()` / `_async_request()` respectively, so subclasses do not need to override them.

### ExtNetworkWidgetBase

Inherits from `LocalWidgetBase` (formerly `MultiSourceWidgetBase`, renamed to the "data source → multiple APIs" structure). It is used for scenarios where the same widget has multiple selectable data sources and each data source contains multiple APIs (for example, the weather widget supports the two data sources qweather / xiaomi_weather, and qweather is further divided into the two APIs weather and air quality); it also supports widgets with only one data source containing multiple APIs, in which case there is no need to bind `CONFIG_ITEM`.

**Class variables:**

| Attribute | Type | Default | Description |
|------|------|--------|------|
| `API_DATA` | `dict[str, dict[str, APIConfig]] \| None` | `None` | Data source → API name → API configuration (must be overridden) |
| `CONFIG_ITEM` | `ConfigItem \| None` | `None` | Data source switching config item (must be bound when there are multiple data sources; can be omitted for a single data source, in which case the only data source is used automatically) |
| `RETRY_COUNT` | `int` | `2` | Number of retries after a single API fails (count+1 requests in total) |
| `RETRY_DELAY` | `float` | `1.0` | Retry interval (seconds) |
| `REQUEST_TIMEOUT` | `float` | `5.0` | Timeout for a single request (seconds) |

`APIConfig` fields (`TypedDict`, all optional):

| Field | Type | Description |
|------|------|------|
| `url` | `str` | API address |
| `params` | `dict \| None` | Request parameter dictionary |
| `headers` | `dict \| None` | Request header dictionary |
| `parse_func` | `str` | Parsing function name (a string, corresponding to a subclass method) |

**Read-only properties (derived automatically from API_DATA + CONFIG_ITEM):**

| Attribute | Description |
|------|------|
| `DATA_SOURCE` | Name of the currently selected data source (`CONFIG_ITEM.value`; when unbound and there is only one data source, that data source is used automatically) |
| `CURRENT_API_DATA` | All API configurations of the current data source |

**Instance attributes:**

| Attribute | Description |
|------|------|
| `last_error` | User-readable error message of the most recent failed retrieval (an empty string on success) |

**Subclass override points:**

- Write one parsing method for each API, with a method name corresponding to `APIConfig.parse_func`
- The parsing method receives the raw JSON of the API and returns a `dict`; returning `None` is treated as a parse failure

**Public methods:**

| Method | Returns | Description |
|------|------|------|
| `get_cached_source()` | `str \| None` | Read which data source the cached data came from (returns None when there is no cache) |

**Usage example:**

```python
class DailyWordsWidget(ExtNetworkWidgetBase):
    WIDGET_NAME    = 'EveryDayWords'
    NEED_CACHE     = True
    LOCAL_INTERVAL = '1d'
    CONFIG_ITEM    = cfg.words_source            # OptionsConfigItem, with options such as ['iciba', 'hitokoto']
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

The calling convention is the same as for ordinary network widgets: `widget.get_data()` / `await widget.get_data_async()`. During scheduling, all APIs under the current data source are requested concurrently and their results are merged into a single dictionary; the parsed result automatically carries a `source` field recording the data source name.

**Notes:**
- A single-data-source widget does not need to bind `CONFIG_ITEM`: when `CONFIG_ITEM` is `None` and `API_DATA` has only one data source, the base class automatically uses that only data source; when there is more than one data source and `CONFIG_ITEM` is not bound, an error is raised.
- When any API fails, the result of the current run is not written to the cache (an automatic `skip_cache()`), and everything is fetched again on the next launch.
- The cache contains a `source` field, so old cache entries do not automatically become invalid after switching data sources — if you need to force a refresh after switching, call `get_data(force_refresh=True)` or call `clear_cache()` first.

### register Decorator

Built-in widgets are registered into the global widget registry through `@register`, without modifying `main.py`:

```python
from core.widgets import register

@register(cfg.words_switch, 'words_switch')
class DailyWordsWidget(ExtNetworkWidgetBase):
    ...
```

Signature:

| Parameter | Type | Description |
|------|------|------|
| `switch` | `ConfigItem` | Widget enable switch |
| `template_key` | `str \| None` | Name of the switch variable injected into the template (None = do not inject) |
| `extra_template_keys` | `dict[str, ConfigItem] \| None` | Intra-widget sub-switches: template variable name → config item |

### CacheManager

Advanced usage; usually there is no need to call these directly. All methods are invoked through the wrappers on `LocalWidgetBase`.

| Class method | Description |
|--------|------|
| `init_db()` | Initialize the database (idempotent; already called by `LocalWidgetBase.__init__`) |
| `read_path(w, ck, path)` | `json_extract` path read |
| `update_path(w, ck, path, value)` | `json_set` path write |
| `remove_path(w, ck, path)` | `json_remove` path delete |

For details, see the [JSON Path Read/Write](#json-path-readwrite) section.

---

## Migrating from the Legacy Version

The legacy `core/get_data.py` used standalone functions plus `format_data_to_json` / `format_data_to_jinja2` to manage the cache manually. The changes after migrating to the widget framework:

| | Legacy | New |
|---|---|---|
| Data retrieval | One standalone function per module | One class, overriding `_fetch_data` |
| Network requests | Manual `aiohttp` + session management | The framework wraps `httpx` and handles it automatically |
| Cache | Manual `data.json` reads and writes | Automatic SQLite caching, managed by cache_key / path |
| Exception handling | Every function writes `try/except/return False` | The framework raises uniformly, and the caller decides how to handle it |
| Type safety | Returns `dict \| bool` (easy to forget to check for falsy) | Returns `dict`, and raises on failure |

Migration steps:

1. Create a new widget class inheriting from `LocalWidgetBase` (local) or `NetworkWidgetBase` / `ExtNetworkWidgetBase` (network)
2. Extract the data retrieval/parsing code from the original function's business logic and put it into `_fetch_data` / `_parse_data` or the parsing method specified by `parse_func`
3. Configure `NEED_CACHE` and `LOCAL_INTERVAL`
4. Callers uniformly use `widget.get_data()` / `await widget.get_data_async()`

> The legacy widget base class was split into two classes, `WidgetBase` and `LocalWidgetBase`; they have since been merged into `LocalWidgetBase` during the refactor, so simply inherit from it during migration.

---

## FAQ

**Q: Where is the cache database file?**

`data/cache/widgets_cache.db`. `CacheManager.init_db()` is called automatically in `LocalWidgetBase.__init__()` (idempotent).

**Q: What is the relationship between the widget cache and user configuration?**

They are independent. The widget cache (`widgets_cache.db`) manages runtime data per widget; user configuration is managed by `cfg` (the qfluentwidgets configuration system, persisted in `data/config.json`), which widgets reference through config items such as `CONFIG_ITEM`.

**Q: How does a widget obtain an API Key?**

The framework does not mandate a key management approach. `NetworkWidgetBase` subclasses set `PARAMS`, while `ExtNetworkWidgetBase` subclasses configure it in the `params` of `API_DATA`:

```python
class MyWidget(NetworkWidgetBase):
    PARAMS = {"key": cfg.my_api_key.value}
```

**Q: Are the asynchronous methods compatible with PySide6 + qasync?**

Fully compatible. `ui.py` sets the global event loop to `QEventLoop`, and `httpx.AsyncClient` uses the standard asyncio interface underneath, making it transparent to qasync.

**Q: Can the same widget have both synchronous and asynchronous calls?**

Yes. `get_data()` is used in synchronous contexts and `get_data_async()` in asynchronous contexts, and both share the same cache. Mixing them is not recommended, but it is technically feasible.

**Q: How do I configure automatic retries?**

Set the `RETRY_COUNT` and `RETRY_DELAY` class variables:

```python
class MyWidget(NetworkWidgetBase):
    RETRY_COUNT = 3      # retry 3 times after failure (4 requests in total)
    RETRY_DELAY = 2.0    # 2 seconds between retries
```

- Only `httpx.HTTPError` (network/HTTP errors) is retried, not code bugs (`Exception`)
- Defaults are `RETRY_COUNT=2` (3 attempts in total) and `RETRY_DELAY=1.0` seconds
- Synchronous retries use `time.sleep` and asynchronous retries use `asyncio.sleep`; neither blocks its respective event loop
- `_sync_request` / `_async_request` / `_request_api` / `_request_api_async` all benefit from the retry logic

---

> Document version 2.0 · Maintainer: HuangTao · Last updated: 2026-08-25

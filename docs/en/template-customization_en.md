# StartInfo Template Customization Guide

[简体中文](../template-customization.md) | English

> **Note:** The application interface itself is internationalized (Simplified Chinese / Traditional Chinese / English), but the template system is not: the values the application injects into templates (`greeting`, `weekday`, `holiday`, `weather`, `lunar_date` and so on) are always Simplified Chinese. You may write the static text of a template in any language, but these injected values will remain Chinese until the data layer is internationalized.

## 1. What Templates Do

The application can read Jinja2 template files (`*.j2`) and format them for display. The application injects a rich set of variables into every template, so by writing templates and combining them with conditional syntax you can customize all kinds of layouts, wording, and even complete HTML pages.

## 2. Template Folder Path

`Program installation folder\data\templates`

## 3. Importing Templates

1. Import a template file from **Settings** in the main application.
2. Double-click a template file (`.j2` or `.html`) and choose to import the template.
3. Copy the template file directly into the `templates` folder.

## 4. Enabling a Template

1. After importing a template in Settings, click "Enable Now".
2. At any time, go to **Settings -> Personalization -> Templates**, select the template you want to use and enable it.

---

## 5. Variable Reference (Core)

To make template authoring easier, StartInfo V2.4.0 groups its variables into **"display data variables"** and **"logic/control variables"**.

### 5.1 Display Data Variables
These variables contain concrete text or numbers and are used directly as text substitutions in a template (call them with `{{ variable_name }}`).

| Information Category | Variable Name | Content (Example) | Description |
|:--------------:|:--------------------|:-------------------|:-----------------------|
|    **Greeting**     | `greeting`          | 下午好！               | Greeting generated automatically from the current time |
|    **Startup Count**    | `startup_times`     | 2                  | Number of times the computer has been started today |
|     **Date**     | `date`              | 2026年4月2日          | Current Gregorian (solar) date |
|    **Lunar Date**    | `lunar_date`        | 农历：七月初五           | Current lunar date (the variable includes the "农历：" prefix) |
|    **Current Time**    | `time`              | 14:51:21           | Current time, accurate to the second |
|  **Time emoji**   | `time_emoji`        | 🕒                 | Icon that changes with the time of day |
|    **Weekday n**     | `weekday`           | 四                  | Day of the week (Chinese numeral) |
|   **Week n**    | `week_num`          | 13                 | Week number within the current year |
|   **Day n**    | `day_num`           | 92                 | Day number within the current year |
|    **Year Progress**    | `year_progress`     | 25.21%             | Percentage of this year that has already passed |
|    **Year Remaining**    | `year_remain`       | 74.79%             | Percentage of this year that is left |
|   **Holiday Status**    | `holiday`           | 工作日                | Holiday, adjusted working day, or weekend status |
|   **24 Solar Terms**    | `solar_term`        | 春分后                | Current solar term stage |
|    **City Name**    | `city_name`         | 恩施                 | The city the user is located in |
|    **Weather Condition**    | `weather`           | 阴                  | Text description of the current weather |
|  **Weather emoji**   | `weather_emoji`     | ☁️                 | Icon corresponding to the weather |
|     **Temperature**     | `temperature`       | 15℃                | Real-time temperature |
|    **Feels-like Temperature**    | `feels_like`        | 15℃                | Real-time apparent temperature |
|     **Humidity**     | `humidity`          | 78%                | Air humidity |
|     **Wind Direction**     | `wind_direction`    | 南风                 | Real-time wind direction |
|     **Wind Speed**     | `wind_speed`        | 6km/h              | Real-time wind speed |
|    **Air Quality**    | `air_quality`       | 优(PM2.5 指数:30)     | Air quality and the detailed index |
|   **Countdown Name**    | `countdown_name`    | 中考                 | The countdown event name you defined in Settings |
|   **Countdown Days**    | `countdown_number`  | 79                 | Days remaining until the target date |
|    **Historical Date**    | `historical_date`   | 2014年4月2日          | Today in history - the date |
|    **Historical Event**    | `historical_event`  | 解放军18名高级将领...      | Today in history - event details |
| **Quote of the Day (main content)** | `words_primary`     | 根在黑暗中深扎...         | Quote of the day - main content |
| **Quote of the Day (secondary content)** | `words_secondary`   | Roots grow deep... | Quote of the day - secondary content |
|   **MC Server**    | `mc_server_name`    | World of Kivotos   | Server name |
|    **MC Latency**    | `mc_server_latency` | 74.8               | Server response latency (milliseconds) |
|   **MC Current Players**   | `mc_server_current` | 0                  | Number of players currently online |
|   **MC Max Players**   | `mc_server_max`     | 45                 | Maximum player capacity of the server |
|   **MC Online Friends**   | `mc_online_friends` | `['玩家A', '玩家B']`   | This is a **list**, and must be rendered with a for loop |
|    **Daily Luck**    | `character` | 50                 | Today's luck value |

### 5.2 Logic/Control Variables (Component Switches)
These variables mostly return `True` or `False`. Combined with `{% if %}` syntax, they let you check whether the user has enabled a given feature in "Settings", so the interface can show and hide sections dynamically.

|    Corresponding Setting Switch     | Variable Name | Description |
|:-------------:| :--- |:------------------------------------|
|   **Global Master Control**    | `is_all_off` | **Highest priority.** If `True`, the user has turned off the display of all information. |
|   **Greeting Switch**   | `greeting_switch` | Whether to display the greeting. |
|  **Startup Count Switch**   | `startup_times_switch`| Whether to display today's startup count. |
|  **Date and Time Switch**   | `datetime_switch` | Whether to display the date and time (this is the master switch; sub-switches only take effect when it is on). |
|   **Lunar Date Switch**    | `lunar_date_switch` | Whether to display the lunar date. |
|  **24 Solar Terms Switch**   | `solar_term_switch` | Whether to display the 24 solar terms information. |
|  **Holiday Switch**   | `holiday_switch` | Whether to display the holiday, working day, or rest day. |
|  **Other Data Switch**  | `other_date_switch` | Whether to display the week number, day number, and year progress. |
|  **Weather Module Switch**   | `weather_switch` | Whether to display the weather card information. |
|  **Today in History Switch**   | `historical_switch` | Whether to display today in history. |
|  **Quote of the Day Switch**   | `words_switch` | Whether to display the quote of the day module. |
| **MC Server Info Switch** | `mc_server_check_switch`| Whether the MC server player-online detection feature is enabled. |
|  **Daily Luck Switch**   | `daily_character_switch` | Whether to display the daily luck module. |
|   *(System check)*    | `is_countdown_available`| Checks whether there is currently a valid, unexpired countdown. |
|   *(System check)*    | `is_mc_server_online` | Checks whether the MC server is currently reachable. |

### 5.3 Birthday Greeting (Experimental Component)
Triggered on a specific date; these are special variables:
* `birthday_star`: name of the birthday person
* `age`: age on the birthday
* `life_days`: number of days the birthday person has been in this world

---

## 6. Writing a Basic Template and Adapting to Switches

In v2.4.0 it is strongly recommended to wrap each module with `{% if switch_variable %}`. That way, when the user turns off a piece of information in Settings, the template automatically hides the corresponding content, avoiding blank lines or meaningless layout gaps.

**Basic template example (`default.j2`):**

```jinja2
{% if is_all_off -%}
★ 开机速览 ★
提示：当前未开启任何信息展示模块。
您可以点击下方“设置”按钮进行配置。
{% else -%}
{# --- 顶部问候 --- #}
{%- if greeting_switch or startup_times_switch -%}
★ {% if greeting_switch %}{{ greeting }}{% endif %}{% if greeting_switch and startup_times_switch %} {% endif %}{% if startup_times_switch %}今天已开机{{ startup_times }}次{% endif %} ★
{{ "\n" }}
{%- endif -%}

{# --- 日期时间 (总开关) --- #}
{%- if datetime_switch -%}
★今天是{{ date }}{% if lunar_date_switch %} {{ lunar_date }}{% endif %} {{ weekday }}{% if other_date_switch %} 第{{ week_num }}周 第{{ day_num }}天{% endif %}
{% if holiday_switch %}节假日：{{ holiday }}{% if solar_term_switch %} | {% endif %}{% endif %}{% if solar_term_switch %}24节气：{{ solar_term }}{% endif %}{% if daily_character_switch %}
🎲今日人品：{{ character }}{% endif %}
{% if other_date_switch %}今年已过{{ year_progress }} 还剩{{ year_remain }}{% endif %}
{{ time_emoji }}当前时间：{{ time }}
{%- if is_countdown_available -%}
★📅距离【{{ countdown_name }}】还有 {{ countdown_number }}天★
{%- endif %}
{{ "\n" }}
{%- endif -%}

{# --- 天气信息 --- #}
{%- if weather_switch -%}
{{ city_name }}天气：{{ weather_emoji }}{{ weather }} | 🌡{{ temperature }} (体感{{ feels_like }})
★🍃{{ wind_direction }} {{ wind_speed }} | 🌁空气质量：{{ air_quality }}
{{ "\n" }}
{%- endif -%}

{# --- MC服务器状态 (新加入) --- #}
{%- if mc_server_check_switch -%}
★ MC服务器: {{ mc_server_name }} ★
{%- if is_mc_server_online -%}
🌐 状态: 在线 | ⚡ 延迟: {{ mc_server_latency }}ms | 📊 人数: {{ mc_server_current }}/{{ mc_server_max }}
{%- if mc_online_friends %}
✨ 在线好友: {% for name in mc_online_friends %}[{{ name }}]{{ " " if not loop.last }}{% endfor %}
{%- else %}
💤 暂无好友在线
{%- endif %}
{%- else -%}
❌ 服务器目前处于离线状态
{%- endif %}
{{ "\n" }}
{%- endif -%}

{# --- 历史上的今天 --- #}
{%- if historical_switch -%}
★历史上的今天★
{{ historical_date }} {{ historical_event }}
{{ "\n" }}
{%- endif -%}

{# --- 每日一言 --- #}
{%- if words_switch -%}
★每日一言★
{{ words_primary }}
{{ words_secondary }}
{{ "\n" }}
{%- endif -%}
{%- endif -%}
```

**Rendered output of the template above:**
```text
★ 下午好！ 今天已开机1次 ★

★今天是2026年8月16日 农历：七月初五 日 第33周 第229天
节假日：休息日 | 24节气：立秋后
🎲今日人品：98，欧皇！
今年已过62.47% 还剩37.53%
🕠当前时间：17:21:03

恩施天气：🌥️多云 | 🌡35℃ (体感35℃)
★🍃西南风 15km/h | 🌁空气质量：优(PM2.5 指数:3)

★历史上的今天★
2016年8月16日 前国际足联主席阿维兰热去世

★每日一言★
饭可以一日不吃，水可以一日不喝，但题不可以一日不贺。
——「贺指导」
```

---

## 7. Advanced Templates (HTML/CSS)

Jinja2 templates natively support HTML and CSS code. If you want to build a nicer, card-style dashboard page, you can write HTML directly inside a `.j2` file.

### ⚠️ Essential Adaptation Trick: Transparent Background
Because the StartInfo main application has its own light/dark theme switching, when you write the CSS for an HTML template you **must set the bottom-most background to fully transparent** [cite: 1, 2]. Otherwise you will get an ugly solid white or solid black backdrop that does not blend into the main application's popup window.

**You must include the following global CSS code:**

```html
<style>
    body {
        font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        margin: 0;
        padding: 0;
        /* 强制透明背景，完美适配深浅色模式 */
        background-color: transparent !important;
    }
</style>
```

> **Tip**: Besides `body`, if you use cards (`div`), try to use semi-transparent colors (such as `rgba(128,128,128,0.2)`) for their borders as well, and add `background: transparent !important;` to keep the polished look.

---

## 8. FAQ

### Q: Why do some variables not appear in my template?
A: Check whether the spelling matches the variable names given in this document exactly (for example, `solar_term` cannot be written as `solarterm`). Also check whether that variable sits inside a `{% if %}` switch statement that is currently off.

### Q: Some information in the date/time component (lunar date / solar term / holiday / year progress) does not show up?
A: Those are each controlled by a separate sub-switch - `lunar_date_switch`, `solar_term_switch`, `holiday_switch`, `other_date_switch` - and they only take effect when the master switch `datetime_switch` is on. Check in Settings -> Detailed configuration of the date and time component that the corresponding switches are enabled.

### Q: How do I display complex array data?
A: For lists such as `mc_online_friends`, you need Jinja2's for loop syntax:
```jinja2
{% for name in mc_online_friends %}
    玩家: {{ name }}
{% endfor %}
```

### Q: Can I use advanced dictionary mapping logic?
A: Absolutely! For example, if you want custom messages for different weather conditions:
```jinja2
{%- set weather_messages = {
    '晴': '☀️ 阳光明媚，适合出门！',
    '雨': '🌧️ 别忘了带伞哦～'
} -%}
{{ weather_messages.get(weather, '🌤️ 保持好心情！') }}
```

***

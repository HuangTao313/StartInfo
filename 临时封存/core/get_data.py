import time
from typing import Any
import zhdate
import asyncio
import aiohttp
import json
from . import ht_lib as lib

# 获取api信息
api = lib.read_json(lib.API_PATH)
# 获取emoji
emoji = lib.read_json(lib.EMOJI_PATH)
time_emoji = emoji['time']
weather_emoji = emoji['weather']

# 获取当前时间emoji
def get_time_emoji(current_time) -> str:
    # 获取当前时间
    hour = current_time.tm_hour  # 24小时制的小时
    minute = current_time.tm_min  # 分钟

    # 转换为12小时制
    hour_12 = hour % 12
    if hour_12 == 0:
        hour_12 = 12  # 12点

    # 四舍五入逻辑
    if 0 <= minute < 15:
        rounded_time = f"{hour_12}:00"
    elif 15 <= minute < 45:
        rounded_time = f"{hour_12}:30"
    else:
        # 分钟 >= 45，选择下一个整点
        hour_12 = (hour_12 % 12) + 1
        if hour_12 == 13:
            hour_12 = 1  # 12点之后是1点
        rounded_time = f"{hour_12}:00"

    return time_emoji.get(rounded_time, time_emoji['9:00'])

# 获取当前本地时间
local_time = time.localtime()
# 获取日期信息
def get_date() -> dict[str, str] | bool:
    """
    获取日期和时间相关信息
    返回包含静态日期信息和动态时间信息的元组
    """
    try:
        # 日期相关信息
        date_str = f"{local_time.tm_year}年{local_time.tm_mon}月{local_time.tm_mday}日"
        lunar_date = str(zhdate.ZhDate.today())
        weekday = ['日', '一', '二', '三', '四', '五', '六'][int(time.strftime('%w', local_time))]
        week_num = int(time.strftime('%W', local_time))  # 当前是一年中的第几周
        day_num = int(time.strftime('%j', local_time))  # 当前是一年中的第几天

        # 年度进度百分比计算
        is_leap = local_time.tm_year % 4 == 0 and (local_time.tm_year % 100 != 0 or local_time.tm_year % 400 == 0)
        total_days = 366 if is_leap else 365  # 闰年366天，平年365天
        year_progress = round((int(day_num) / int(total_days)) * 100, 2)  # 已过的年份百分比
        year_remain = round(100 - year_progress, 2)  # 剩余年份百分比



        # 返回格式化的日期和时间信息
        # 包含：日期、农历日期、星期、年内周数、年内天数
        data = {
            'date': date_str,
            'lunar_date': lunar_date,
            'weekday': weekday,
            'week_num': week_num,
            'day_num': day_num,
            'year_progress': f'{year_progress}%',
            'year_remain': f'{year_remain}%',
        }
        return data

    except Exception as e:
        lib.log.error(f'获取时间信息失败：{str(e)}')
        return False

# 获取时间信息
def get_time() -> dict[str, str] | bool:
    try:
        # 时间相关信息
        time_str = time.strftime('%X', local_time)
        # 获取时间表情符号
        time_emoji = get_time_emoji(local_time)
        data = {
            'time': time_str,
            'time_emoji': time_emoji,
        }
        return data
    except Exception as e:
        error_msg = f'获取时间信息失败：{str(e)}'
        lib.log.error(error_msg)
        return False

# 获取天气和空气质量
# 获取天气emoji
def get_weather_emoji(weather_type) -> str:
    weather_type = str(weather_type).strip()

    # 1. 精确匹配
    emoji = weather_emoji.get(weather_type)
    if emoji is not None:
        return emoji

    # 2. 关键词回退：优先级可调整
    if '雨' in weather_type:
        # 优先使用“小雨”的 emoji 作为通用雨
        return weather_emoji.get('小雨', '🌧️')
    elif '雪' in weather_type:
        # 优先使用“小雪”的 emoji 作为通用雪
        return weather_emoji.get('小雪', '❄️')
    elif '雷' in weather_type or '电' in weather_type:
        return weather_emoji.get('雷阵雨', '⛈️')
    elif '雾' in weather_type or '霾' in weather_type:
        return weather_emoji.get('雾', '🌫️')
    elif '沙尘' in weather_type or '扬沙' in weather_type:
        return weather_emoji.get('沙尘暴', '💨')

    # 3. 完全未知类型：返回默认天气（阴天）
    return '☁️'
# 获取天气和空气质量信息
async def get_weather_air_quality() -> dict[str, str | Any] | bool | str:
    if lib.is_internet():
        if api is not None:
            city_name = lib.file.read('Weather', 'city_name')
            api_key = lib.decrypt(api['qweather.com']['api_key'])
            city_id = lib.file.read('Weather', 'city_id')
            try:
                # 1. 创建异步HTTP客户端
                async with aiohttp.ClientSession() as session:
                    # 2. 并发获取天气和空气质量数据
                    weather_url = api['qweather.com']['url_weather']
                    air_url = api['qweather.com']['url_air']
                    params = {
                        "key": api_key,
                        "location": city_id
                    }

                    # 并发执行两个请求（同时发出，自动等待最慢的那个完成）
                    weather_task = session.get(weather_url, params=params)
                    air_task = session.get(air_url, params=params)

                    # 等待两个请求都完成
                    weather_response, air_response = await asyncio.gather(
                        weather_task,
                        air_task
                    )

                    # 解析响应数据
                    weather_data = await weather_response.json()
                    air_data = await air_response.json()

                    # 3. 处理数据（同步逻辑，无阻塞）
                    now = weather_data.get("now", {})
                    if now:
                        weather = now.get('text', '')
                        temperature = now.get('temp', '')
                        feels_like = now.get('feelsLike', '')
                        humidity = now.get('humidity', '')
                        wind_direction = now.get('windDir', '')
                        wind_speed = now.get('windSpeed', '')
                        air_quality = air_data.get("now", {}).get("aqi", "")
                        air_level = air_data.get("now", {}).get("category", "")
                        air_quality_text = f"{air_level}(PM2.5指数:{air_quality})"
                        weather_emoji = get_weather_emoji(weather)

                        # 格式化输出信息
                        data = {
                            'get_time': int(time.time()),
                            'city_name': city_name,
                            'weather': weather,
                            'temperature': f'{temperature}℃',
                            'feels_like': f'{feels_like}℃',
                            'humidity': f'{humidity}%',
                            'wind_direction': wind_direction,
                            'wind_speed': f'{wind_speed}km/h',
                            'air_quality': air_quality_text,
                            'weather_emoji': weather_emoji
                        }
                        return data

                    else:
                        lib.log.error('天气：获取失败')
                        return False

            except Exception as e:
                lib.log.error(f'获取天气信息失败：{str(e)}')
                return False
        else:
            lib.log.error('天气：获取api_key失败')
            return False
    else:
        lib.log.warning('天气：请联网后获取')
        return False

# 获取历史上的今天信息
async def get_today_in_history() -> dict[str, str | Any] | bool:
    if lib.is_internet():
        if api is not None:
            url = api['www.mxnzp.com']['today_in_history']['url']
            params = {
                "args": 1,
                "app_id": lib.decrypt(api['www.mxnzp.com']['today_in_history']['app_id']),
                "app_secret": lib.decrypt(api['www.mxnzp.com']['today_in_history']['app_secret'])
            }

            try:
                # 1. 创建异步HTTP客户端
                async with aiohttp.ClientSession() as session:
                    # 2. 发起异步请求（关键：你用 await 等待网络响应）
                    async with session.get(url, params=params) as response:
                        # 3. 等待响应内容（自动等待网络完成）
                        data = await response.json()

                        if data["code"] == 1:
                            history_data = data["data"]
                            if len(history_data) > 0:
                                history = history_data[0]
                                # 格式化输出信息
                                data = {
                                    'historical_date': f"{history['year']}年{history['month']}月{history['day']}日",
                                    'historical_event': history['title']
                                }
                                return data
                            else:
                                lib.log.error('历史上的今天：没有找到历史上的今天的信息')
                                return False
                        else:
                            lib.log.error('历史上的今天：请求失败')
                            return False

            except aiohttp.ClientError as e:
                lib.log.error(f'历史上的今天：请求异常 - {str(e)}')
                return False
        else:
            lib.log.error('历史上的今天：获取api_key失败')
            return False
    else:
        lib.log.warning('历史上的今天：请联网后获取')
        return False

# 查询节假日和24节气信息
async def get_holiday_solar_term() ->  dict[str, str] | bool:
    if lib.is_internet():
        if api is not None:
            current_time = time.localtime()
            formatted_time = time.strftime("%Y%m%d", current_time)
            solarTerms_params = {
                "args": 1,
                "app_id": lib.decrypt(api['www.mxnzp.com']['holiday_solar_term']['app_id']),
                "app_secret": lib.decrypt(api['www.mxnzp.com']['holiday_solar_term']['app_secret'])
            }

            url = api['www.mxnzp.com']['holiday_solar_term']['url']

            try:
                # 1. 创建异步HTTP客户端
                async with aiohttp.ClientSession() as session:
                    # 2. 发起异步请求（关键：使用 await 等待网络响应）
                    async with session.get(f'{url}/{formatted_time}', params=solarTerms_params) as response:
                        # 3. 等待响应内容（自动等待网络完成）
                        data_solar_term = await response.json()
                        if data_solar_term["code"] == 1:
                            solar_term_data = data_solar_term["data"]["solarTerms"]
                            holiday_data = data_solar_term["data"]["typeDes"]

                            # 修正1：避免返回字符串中包含"节假日信息："
                            holiday = holiday_data if holiday_data else "没有节假日"
                            solar_term = solar_term_data if solar_term_data else "没有找到24节气"
                            # 格式化输出
                            return {'holiday': holiday, 'solar_term': solar_term}

                        else:
                            lib.log.error('节假日和24节气信息：请求失败')
                            return False

            except aiohttp.ClientError as e:  # 修正2：使用aiohttp异常类型
                lib.log.error(f'节假日和24节气信息：请求异常 - {str(e)}')
                return False
        else:
            lib.log.error('节假日和24节气信息：获取api_key失败')
            return False
    else:
        lib.log.warning('节假日和24节气信息：请联网后获取')
        return False

# 获取金山词霸每日一言
async def get_every_day_words() -> dict[str, str] | bool:
    if lib.is_internet():
        url = api['open.iciba.com']
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    # 直接获取文本内容（绕过Content-Type检查）
                    text = await response.text()
                    # 用标准json解析（不依赖Content-Type）
                    data = json.loads(text)
                    content = data.get('content', '')
                    note = data.get('note', '')
                    # 格式化输出
                    return {
                        'every_day_words_zh': note,
                        'every_day_words_en': content
                    }

        except Exception as e:
            lib.log.error(f'金山词霸每日一言：获取失败：{e}')
            return False
    else:
        lib.log.warning('金山词霸每日一言：请联网后获取')
        return False

# 获取问候语
def get_greeting():
    hour = int(time.strftime('%H', local_time))
    return '早上好！' if 6 <= hour < 11 else '中午好！' if 11 <= hour < 12 else '下午好！' if 12 <= hour < 17 else '晚上好！'

# 获取所有信息
async def get_all_data() -> list[dict[str,str]] | bool:
    # 异步获取所以信息
    try:
        date = get_date()
        holiday_solar_term, weather_air_quality, today_in_history, everyday_words = await asyncio.gather(
            get_holiday_solar_term(),
            get_weather_air_quality(),
            get_today_in_history(),
            get_every_day_words()
        )

        # 返回全部信息
        return [date, holiday_solar_term, weather_air_quality, today_in_history, everyday_words]

    # 处理异常
    except Exception as e:
        lib.log.error(f'获取所有信息：获取失败：{e}')
        return False

# 格式化数据
# 将原始数据转化为缓存格式
def format_data_to_json(data: list[dict[str, str]]) -> dict | bool:
    if len(data) != 5:
        lib.log.error('缓存格式转换失败：数据长度不合法')
        return False

    try:
        return {
            'date': data[0] | data[1],
            'weather': data[2],
            'other': {
                'get_date': int(time.strftime("%Y%m%d", time.localtime())),
                'historical_date': data[3].get('historical_date', ''),
                'historical_event': data[3].get('historical_event', ''),
                'every_day_words_zh': data[4].get('every_day_words_zh', ''),
                'every_day_words_en': data[4].get('every_day_words_en', '')
            }
        }
    except Exception as e:
        lib.log.error(f'缓存格式转换出错: {e}')
        return False

# 将原始数据转化为展示格式
def format_data_to_jinja2(data: list[dict[str, str]]) -> dict | bool:
    if len(data) != 5:
        lib.log.error('展示格式转换失败：数据长度不合法')
        return False

    try:
        # 初始化默认值
        info = {key: '获取失败' for key in [
            'greeting', 'date', 'lunar_date', 'time', 'time_emoji', 'weekday',
            'week_num', 'day_num', 'year_progress', 'year_remain', 'holiday',
            'solar_term', 'weather', 'weather_emoji', 'temperature', 'feels_like',
            'humidity', 'wind_direction', 'wind_speed', 'air_quality',
            'historical_date', 'historical_event', 'every_day_words_zh', 'every_day_words_en'
        ]}

        # 填充动态数据
        info['greeting'] = get_greeting()
        if (time_info := get_time()):
            info.update(time_info)

        # 安全合并各模块（跳过 False 值）
        for item in data:
            if item is not False:
                info.update(item)

        # 隐藏内部字段
        info.pop('get_time', None)
        return info

    except Exception as e:
        lib.log.error(f'展示格式转换出错: {e}')
        return False

def format_json_to_jinja2(json_data: dict) -> dict | bool:
    """从 data.json 的嵌套结构转换为 Jinja2 单层字典"""
    try:
        # 检查输入是否为有效字典
        if not isinstance(json_data, dict):
            lib.log.warning(f'format_json_to_jinja2: 输入数据类型错误: {type(json_data)}')
            # 返回一个基本的字典而不是 False
            return {key: '获取失败' for key in [
                'greeting', 'date', 'lunar_date', 'time', 'time_emoji', 'weekday',
                'week_num', 'day_num', 'year_progress', 'year_remain', 'holiday',
                'solar_term', 'weather', 'weather_emoji', 'temperature', 'feels_like',
                'humidity', 'wind_direction', 'wind_speed', 'air_quality',
                'historical_date', 'historical_event', 'every_day_words_zh', 'every_day_words_en'
            ]}

        date = json_data.get('date', {})
        weather = json_data.get('weather', {})
        other = json_data.get('other', {})

        info = {key: '获取失败' for key in [
            'greeting', 'date', 'lunar_date', 'time', 'time_emoji', 'weekday',
            'week_num', 'day_num', 'year_progress', 'year_remain', 'holiday',
            'solar_term', 'weather', 'weather_emoji', 'temperature', 'feels_like',
            'humidity', 'wind_direction', 'wind_speed', 'air_quality',
            'historical_date', 'historical_event', 'every_day_words_zh', 'every_day_words_en'
        ]}

        info['greeting'] = get_greeting()
        if (time_info := get_time()):
            info.update(time_info)

        # 安全合并各部分数据（仅当它们是字典时才合并）
        for data_part in [date, weather, other]:
            if isinstance(data_part, dict):
                info.update(data_part)

        info.pop('get_time', None)      # 隐藏时间戳
        info.pop('get_date', None)      # 隐藏存储用日期
        return info

    except Exception as e:
        lib.log.error(f'JSON 转展示格式出错: {e}')
        # 返回一个基本的字典而不是 False
        return {key: '获取失败' for key in [
            'greeting', 'date', 'lunar_date', 'time', 'time_emoji', 'weekday',
            'week_num', 'day_num', 'year_progress', 'year_remain', 'holiday',
            'solar_term', 'weather', 'weather_emoji', 'temperature', 'feels_like',
            'humidity', 'wind_direction', 'wind_speed', 'air_quality',
            'historical_date', 'historical_event', 'every_day_words_zh', 'every_day_words_en'
        ]}
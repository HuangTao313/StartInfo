import time
import datetime
from typing import Any
import zhdate
import asyncio
import aiohttp
import json
from . import ht_lib as lib
from .config import cfg

# 获取 api 信息
api = lib.read_json(lib.API_PATH)
# 获取 emoji
emoji = lib.read_json(lib.EMOJI_PATH)
time_emoji = emoji['time']
weather_emoji = emoji['weather']

# 获取当前时间 emoji
def get_time_emoji(current_time) -> str:
    # 获取当前时间
    hour = current_time.tm_hour  # 24 小时制的小时
    minute = current_time.tm_min  # 分钟

    # 转换为 12 小时制
    hour_12 = hour % 12
    if hour_12 == 0:
        hour_12 = 12  # 12 点

    # 四舍五入逻辑
    if 0 <= minute < 15:
        rounded_time = f"{hour_12}:00"
    elif 15 <= minute < 45:
        rounded_time = f"{hour_12}:30"
    else:
        # 分钟 >= 45，选择下一个整点
        hour_12 = (hour_12 % 12) + 1
        if hour_12 == 13:
            hour_12 = 1  # 12 点之后是 1 点
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

        # 使用 from_datetime 获取农历日期，避免 today() 的问题
        try:
            from datetime import datetime
            lunar_date = str(zhdate.ZhDate.from_datetime(datetime.now()))
        except Exception:
            # 如果 from_datetime 也失败，尝试手动构造
            try:
                lunar_date = str(zhdate.ZhDate(local_time.tm_year, local_time.tm_mon, local_time.tm_mday))
            except Exception:
                # 彻底失败，返回一个占位值
                lunar_date = '农历'

        weekday = ['日', '一', '二', '三', '四', '五', '六'][int(time.strftime('%w', local_time))]
        week_num = int(time.strftime('%W', local_time))  # 当前是一年中的第几周
        day_num = int(time.strftime('%j', local_time))  # 当前是一年中的第几天

        # 年度进度百分比计算
        is_leap = local_time.tm_year % 4 == 0 and (local_time.tm_year % 100 != 0 or local_time.tm_year % 400 == 0)
        total_days = 366 if is_leap else 365  # 闰年 366 天，平年 365 天
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
        # 返回一个包含默认值的字典，而不是 False
        return {
            'date': f"{local_time.tm_year}年{local_time.tm_mon}月{local_time.tm_mday}日",
            'lunar_date': f'农历{local_time.tm_mon}月{local_time.tm_mday}日',
            'weekday': '日',
            'week_num': 0,
            'day_num': 0,
            'year_progress': '0%',
            'year_remain': '100%',
        }

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
# 获取天气 emoji
def get_weather_emoji(weather_type) -> str:
    weather_type = str(weather_type).strip()

    # 1. 精确匹配
    emoji = weather_emoji.get(weather_type)
    if emoji is not None:
        return emoji

    # 2. 关键词回退：优先级可调整
    if '雨' in weather_type:
        # 优先使用"小雨"的 emoji 作为通用雨
        return weather_emoji.get('小雨', '🌧️')
    elif '雪' in weather_type:
        # 优先使用"小雪"的 emoji 作为通用雪
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
@lib.async_retry_on_value(False)
async def get_weather_air_quality() -> dict[str, str | Any] | bool | str:
    if lib.is_internet():
        if api is not None:
            # 添加安全检查，确保配置项是 ConfigItem 对象
            try:
                city_name = cfg.city_name.value if hasattr(cfg.city_name, 'value') else str(cfg.city_name)
                city_id = cfg.city_id.value if hasattr(cfg.city_id, 'value') else str(cfg.city_id)
            except Exception as e:
                lib.log.error(f'天气：获取城市配置失败 - {str(e)}')
                return False

            api_key = lib.decrypt(api['qweather.com']['api_key'])
            try:
                # 1. 创建异步 HTTP 客户端
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
                        air_quality_text = f"{air_level}(PM2.5 指数:{air_quality})"
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
            lib.log.error('天气：获取 api_key 失败')
            return False
    else:
        lib.log.warning('天气：获取失败，请联网后获取')
        return False

# 获取历史上的今天信息
@lib.async_retry_on_value(False)
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
                # 1. 创建异步 HTTP 客户端
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
            lib.log.error('历史上的今天：获取 api_key 失败')
            return False
    else:
        lib.log.warning('历史上的今天：请联网后获取')
        return False

# 查询节假日和 24 节气信息
@lib.async_retry_on_value(False)
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
                # 1. 创建异步 HTTP 客户端
                async with aiohttp.ClientSession() as session:
                    # 2. 发起异步请求（关键：使用 await 等待网络响应）
                    async with session.get(f'{url}/{formatted_time}', params=solarTerms_params) as response:
                        # 3. 等待响应内容（自动等待网络完成）
                        data_solar_term = await response.json()
                        if data_solar_term["code"] == 1:
                            solar_term_data = data_solar_term["data"]["solarTerms"]
                            holiday_data = data_solar_term["data"]["typeDes"]

                            # 修正 1：避免返回字符串中包含"节假日信息："
                            holiday = holiday_data if holiday_data else "没有节假日"
                            solar_term = solar_term_data if solar_term_data else "没有找到 24 节气"
                            # 格式化输出
                            return {'holiday': holiday, 'solar_term': solar_term}

                        else:
                            lib.log.error('节假日和 24 节气信息：请求失败')
                            return False

            except aiohttp.ClientError as e:  # 修正 2：使用 aiohttp 异常类型
                lib.log.error(f'节假日和 24 节气信息：请求异常 - {str(e)}')
                return False
        else:
            lib.log.error('节假日和 24 节气信息：获取 api_key 失败')
            return False
    else:
        lib.log.warning('节假日和 24 节气信息：请联网后获取')
        return False

# 获取金山词霸每日一言
@lib.async_retry_on_value(False)
async def get_every_day_words() -> dict[str, str] | bool:
    if lib.is_internet():
        url = api['open.iciba.com']
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    # 直接获取文本内容（绕过 Content-Type 检查）
                    text = await response.text()
                    # 用标准 json 解析（不依赖 Content-Type）
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

# MC 服务器玩家在线情况检测
@lib.async_retry_on_value(False)
async def get_mc_server_status():
    # 延迟导入
    from mcstatus import JavaServer
    """
    纯异步函数：获取 MC 服务器状态并比对好友列表
    返回：(dict) 包含在线人数、最大人数、延迟和在线好友名单
    """

    results = {
        "mc_server_name": cfg.minecraft_server_name.value,
        "is_mc_server_online": False,
        "mc_server_current": 0,
        "mc_server_max": 0,
        "mc_server_latency": 0,
        "mc_online_friends": []
    }

    # 获取用户配置
    ip = cfg.minecraft_server_ip.value
    port = cfg.minecraft_server_port.value
    if not ip or port in [None, '未知','']:
        lib.log.error('MC 服务器玩家在线情况检测：请填写完整的服务器地址和端口')
        return False

    server_addr = f'{ip}:{port}'
    friends_list = cfg.minecraft_server_friends_list.value

    try:
        # 1. 异步探测服务器 (mcstatus 内部自带超时处理)
        server = await JavaServer.async_lookup(server_addr)
        status = await server.async_status()

        results["is_mc_server_online"] = True
        results["mc_server_current"] = status.players.online
        results["mc_server_max"] = status.players.max
        results["mc_server_latency"] = round(status.latency, 1)

        # 2. 处理好友比对逻辑
        # 提取采样玩家名单 (注意：部分服务器可能不返回具体名单)
        if status.players.sample:
            online_names = [p.name for p in status.players.sample]
            results["mc_online_friends"] = [name for name in friends_list if name in online_names]

    except Exception as e:
        # 这里的异常捕获保证了即使 IP 填错或服务器炸了，主程序也不会崩
        lib.log.error(f'MC 服务器玩家在线情况检测：获取失败：{e}')
        results["is_mc_server_online"] = False

    return results



# 生日祝福检测
def check_birthday() -> bool | dict[str, int | Any]:
    """
    检测今天是否有人生日
    :return: 如果有人生日，返回 {'birthday_star': '寿星名称', 'age': 年龄，'life_days': '今天是 xx 来到这个世界上的第 x 天'}；否则返回 False
    """
    # 检查是否启用了生日祝福功能
    try:
        birthday_wishes_enabled = cfg.birthday_wishes_switch.value if hasattr(cfg.birthday_wishes_switch, 'value') else cfg.birthday_wishes_switch
        if not birthday_wishes_enabled:
            return False
    except Exception as e:
        lib.log.error(f'生日：获取生日配置失败 - {str(e)}')
        return False

    # 获取生日列表
    try:
        birthday_dict = cfg.birthday_dict.value if hasattr(cfg.birthday_dict, 'value') else cfg.birthday_dict
    except Exception as e:
        lib.log.error(f'生日：获取生日列表失败 - {str(e)}')
        return False

    # 如果生日列表为空，返回 False
    if not birthday_dict:
        return False

    # 获取今天的月和日
    today_month_day = time.strftime("%m%d", time.localtime())
    current_year = time.localtime().tm_year

    # 遍历生日列表，检查是否有人今天生日
    for name, birthday_str in birthday_dict.items():
        # 检查生日格式是否正确（YYYYMMDD）
        if not isinstance(birthday_str, str) or len(birthday_str) != 8:
            lib.log.warning(f'生日格式错误：{name} - {birthday_str}')
            continue

        # 提取出生年月日
        try:
            birth_year = int(birthday_str[:4])
            birth_month_day = birthday_str[4:8]
        except ValueError:
            lib.log.warning(f'生日格式错误：{name} - {birthday_str}')
            continue

        # 检查是否是今天生日
        if birth_month_day == today_month_day:
            # 计算年龄
            age = current_year - birth_year

            # 计算来到这个世界上的总天数
            from datetime import datetime
            birth_date = datetime(birth_year, int(birthday_str[4:6]), int(birthday_str[6:8]))
            today_date = datetime.now()
            life_days = (today_date - birth_date).days

            lib.log.info(f'检测到生日：{name} 今天满 {age} 岁')
            return {
                'birthday_star': name,
                'age': age,
                'life_days': life_days
            }

    # 没有人今天生日
    return False

# 获取倒数日
def get_countdown_day() -> dict[str, int]:
    """
        计算从今天到目标日期的剩余天数
        target_date_str 格式要求：'YYYY-MM-DD'
        """
    # 判断用户是否启用倒数日功能
    if not cfg.countdown_switch.value:
        return {'is_countdown_available': False}

    # 1. 获取当前日期（只要日期，不要时分秒，方便对齐）
    today = datetime.datetime.now().date()
    # 2.获取目标日期
    target_date_str = cfg.countdown_date.value
    try:
        # 2. 将字符串转换为 datetime 对象
        # %Y-%m-%d 对应 2026-06-21 这种格式
        target_date_obj = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()

        # 3. 两个日期对象直接相减，得到一个 timedelta 对象
        remaining = target_date_obj - today

        # 如果天数小于 -3，则判断为过期，返回 False
        if remaining.days < -3:
            return {'is_countdown_available': False}

        # 4. 返回天数 (.days 属性)
        return {
            'is_countdown_available': True,
            'countdown_text': cfg.countdown_text.value,
            'countdown_number': remaining.days
        }

    # 用户设置的日期格式错误，返回 False
    except ValueError:
        return {'is_countdown_available': False}

# 获取问候语
def get_greeting():
    hour = int(time.strftime('%H', local_time))
    return '早上好！' if 6 <= hour < 11 else '中午好！' if 11 <= hour < 12 else '下午好！' if 12 <= hour < 17 else '晚上好！'

# 获取自定义信息开关
def get_custom_info_switch() -> dict:
    switch_dict = {
        'greeting_switch': cfg.greeting_switch.value,
        'startup_times_switch': cfg.startup_times_switch.value,
        'datetime_switch': cfg.datetime_switch.value,
        'countdown_switch': cfg.countdown_switch.value,
        'weather_switch': cfg.weather_switch.value,
        'historical_switch': cfg.historical_switch.value,
        'words_switch': cfg.words_switch.value,
        'mc_server_check_switch': cfg.minecraft_server_checker_switch.value
    }

    # 使用 .values() 获取所有的开关状态 (True/False)
    # any() 会检查里面只要有一个 True，就返回 True
    # 如果全都是 False，any() 返回 False，则满足 not 条件
    switch_dict['is_all_off'] = not any(switch_dict.values())

    return switch_dict

# 获取所有信息
async def get_all_data() -> list[dict[str,str]] | bool:
    # 异步获取所以信息
    try:
        date = get_date()
        if cfg.minecraft_server_checker_switch.value:
            holiday_solar_term, weather_air_quality, today_in_history, everyday_words, minecraft_server_status = await asyncio.gather(
                get_holiday_solar_term(),
                get_weather_air_quality(),
                get_today_in_history(),
                get_every_day_words(),
                get_mc_server_status()
            )

            # 返回全部信息（6 个元素）
            return [date, holiday_solar_term, weather_air_quality, today_in_history, everyday_words, minecraft_server_status]

        else:
            holiday_solar_term, weather_air_quality, today_in_history, everyday_words = await asyncio.gather(
                get_holiday_solar_term(),
                get_weather_air_quality(),
                get_today_in_history(),
                get_every_day_words()
            )

            # 返回全部信息（5 个元素，兼容旧版）
            return [date, holiday_solar_term, weather_air_quality, today_in_history, everyday_words]

    # 处理异常
    except Exception as e:
        lib.log.error(f'获取所有信息：获取失败：{e}')
        return False

# 格式化数据
# 将原始数据转化为缓存格式
def format_data_to_json(data: list[dict[str, str]]) -> dict | bool:
    """将原始数据转换为缓存格式 (data.json 格式)"""
    # 检查数据是否有效
    if not data or data is False:
        lib.log.error('缓存格式转换失败：数据无效')
        return False
    # 支持 5 个元素（旧版）或 6 个元素（含 MC 服务器状态）
    if len(data) not in [5, 6]:
        lib.log.error('缓存格式转换失败：数据长度不合法')
        return False

    try:
        # 安全合并 data[0] 和 data[1]，处理 False 值的情况
        date_part = {}
        if isinstance(data[0], dict):
            date_part.update(data[0])
        if isinstance(data[1], dict):
            date_part.update(data[1])

        # 安全处理 data[3] 和 data[4]
        data3 = data[3] if isinstance(data[3], dict) else {}
        data4 = data[4] if isinstance(data[4], dict) else {}

        # 构建基础返回结构
        result = {
            'date': date_part,
            'weather': data[2],
            'other': {
                'get_date': int(time.strftime("%Y%m%d", time.localtime())),
                'historical_date': data3.get('historical_date', ''),
                'historical_event': data3.get('historical_event', ''),
                'every_day_words_zh': data4.get('every_day_words_zh', ''),
                'every_day_words_en': data4.get('every_day_words_en', '')
            }
        }

        # 如果有 MC 服务器状态数据（第 6 个元素），添加到缓存
        if len(data) == 6 and isinstance(data[5], dict):
            mc_status = data[5]
            result['minecraft_server_data'] = {
                'get_time': int(time.time()),
                'mc_server_name': mc_status.get('mc_server_name', ''),
                'is_mc_server_online': mc_status.get('is_mc_server_online', False),
                'mc_server_current': mc_status.get('mc_server_current', 0),
                'mc_server_max': mc_status.get('mc_server_max', 0),
                'mc_server_latency': mc_status.get('mc_server_latency', 0),
                'mc_online_friends': mc_status.get('mc_online_friends', [])
            }

        return result
    except Exception as e:
        lib.log.error(f'缓存格式转换出错：{e}')
        return False

# 将原始数据转化为展示格式
def format_data_to_jinja2(data: list[dict[str, str]]) -> dict | bool:
    """将原始数据转换为 Jinja2 模板展示格式（单层字典）"""
    # 检查数据是否有效
    if not data or data is False:
        lib.log.error('展示格式转换失败：数据无效')
        return False
    # 支持 5 个元素（旧版）或 6 个元素（含 MC 服务器状态）
    if len(data) not in [5, 6]:
        lib.log.error('展示格式转换失败：数据长度不合法')
        return False

    try:
        # 初始化默认值
        info = {key: '获取失败' for key in [
            'greeting', 'date', 'lunar_date', 'time', 'time_emoji', 'weekday',
            'week_num', 'day_num', 'year_progress', 'year_remain', 'holiday',
            'solar_term', 'weather', 'weather_emoji', 'temperature', 'feels_like',
            'humidity', 'wind_direction', 'wind_speed', 'air_quality',
            'historical_date', 'historical_event', 'every_day_words_zh', 'every_day_words_en',
            'mc_server_name', 'is_mc_server_online', 'mc_server_current', 'mc_server_max',
            'mc_server_latency', 'mc_online_friends'
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
        lib.log.error(f'展示格式转换出错：{e}')
        return False

def format_json_to_jinja2(json_data: dict) -> dict | bool:
    """从 data.json 的嵌套结构转换为 Jinja2 单层字典"""
    try:
        # 检查输入是否为有效字典
        if not isinstance(json_data, dict):
            lib.log.warning(f'format_json_to_jinja2: 输入数据类型错误：{type(json_data)}')
            # 返回一个基本的字典而不是 False
            return {key: '获取失败' for key in [
                'greeting', 'date', 'lunar_date', 'time', 'time_emoji', 'weekday',
                'week_num', 'day_num', 'year_progress', 'year_remain', 'holiday',
                'solar_term', 'weather', 'weather_emoji', 'temperature', 'feels_like',
                'humidity', 'wind_direction', 'wind_speed', 'air_quality',
                'historical_date', 'historical_event', 'every_day_words_zh', 'every_day_words_en',
                'mc_server_name', 'is_mc_server_online', 'mc_server_current', 'mc_server_max',
                'mc_server_latency', 'mc_online_friends'
            ]}

        date = json_data.get('date', {})
        weather = json_data.get('weather', {})
        other = json_data.get('other', {})
        minecraft_server_data = json_data.get('minecraft_server_data', {})

        info = {key: '获取失败' for key in [
            'greeting', 'date', 'lunar_date', 'time', 'time_emoji', 'weekday',
            'week_num', 'day_num', 'year_progress', 'year_remain', 'holiday',
            'solar_term', 'weather', 'weather_emoji', 'temperature', 'feels_like',
            'humidity', 'wind_direction', 'wind_speed', 'air_quality',
            'historical_date', 'historical_event', 'every_day_words_zh', 'every_day_words_en',
            'mc_server_name', 'is_mc_server_online', 'mc_server_current', 'mc_server_max',
            'mc_server_latency', 'mc_online_friends'
        ]}

        info['greeting'] = get_greeting()
        if (time_info := get_time()):
            info.update(time_info)

        # 安全合并各部分数据（仅当它们是字典时才合并）
        for data_part in [date, weather, other, minecraft_server_data]:
            if isinstance(data_part, dict):
                info.update(data_part)

        info.pop('get_time', None)      # 隐藏时间戳
        info.pop('get_date', None)      # 隐藏存储用日期
        return info

    except Exception as e:
        lib.log.error(f'JSON 转展示格式出错：{e}')
        # 返回一个基本的字典而不是 False
        return {key: '获取失败' for key in [
            'greeting', 'date', 'lunar_date', 'time', 'time_emoji', 'weekday',
            'week_num', 'day_num', 'year_progress', 'year_remain', 'holiday',
            'solar_term', 'weather', 'weather_emoji', 'temperature', 'feels_like',
            'humidity', 'wind_direction', 'wind_speed', 'air_quality',
            'historical_date', 'historical_event', 'every_day_words_zh', 'every_day_words_en',
            'mc_server_name', 'is_mc_server_online', 'mc_server_current', 'mc_server_max',
            'mc_server_latency', 'mc_online_friends'
        ]}

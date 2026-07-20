import datetime
import time
import zhdate
from datetime import datetime
from typing import Any

from . import ht_lib as lib
from .widgets_core import LocalWidgetBase, NetworkWidgetBase
from .config import cfg

# StartInfo默认组件
# 于2026.6.30开始重构
# 获取 api 信息
api = lib.read_json(lib.API_PATH)

# 管理日志
log = lib.log

# 获取 emoji
emoji = lib.read_json(lib.EMOJI_PATH)
time_emoji = emoji['time']
weather_emoji = emoji['weather']

# 获取全局日期和时间信息
global_date = datetime.today().strftime('%Y%m%d')
global_time = time.localtime()

# ===== 本地组件 =====
# 1.日期和时间组件
class DateTimeWidget(LocalWidgetBase):
    WIDGET_NAME = 'DateTime'
    NEED_CACHE = False

    def _get_time_emoji(self,current_time) -> str:
        """
        获取当前时间emoji
        Args:
            current_time: 当前时间

        Returns:
            str: 时间emoji
        """
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

    def _get_time(self) -> dict[str, str | Any] | dict[str, str]:
        """
        获取当前时间和时间emoji
        Returns:
            dict[str, str | Any] | dict[str, str]: 当前时间和时间emoji，出错时返回默认值
        """
        try:
            current_time = time.localtime()
            time_str = time.strftime('%X', current_time)
            time_emoji = self._get_time_emoji(current_time)
            return {
                'time': time_str,
                'time_emoji': time_emoji,
            }

        # 如果失败 返回默认值
        except Exception as e:
            error_msg = f'获取时间信息失败：{str(e)}'
            log.error(error_msg)
            return {
                'time': '12:00:00',
                'time_emoji': '🕛',
            }

    # 获取当前日期信息
    def _get_date(self) -> dict[str, str | int]:
        """
           获取日期和时间相关信息

        Returns:
            dict[str, str | int]: 包含静态日期信息和动态时间信息的元组
           """
        try:
            current_time = time.localtime()
            date_str = f"{current_time.tm_year}年{current_time.tm_mon}月{current_time.tm_mday}日"

            # 使用 from_datetime 获取农历日期，避免 today() 的问题
            try:
                lunar_date = str(zhdate.ZhDate.from_datetime(datetime.now()))
            except Exception:
                # 如果 from_datetime 也失败，尝试手动构造
                try:
                    lunar_date = str(zhdate.ZhDate(current_time.tm_year, current_time.tm_mon, current_time.tm_mday))
                except Exception:
                    # 彻底失败，返回一个占位值
                    lunar_date = '农历'

            weekday = ['日', '一', '二', '三', '四', '五', '六'][int(time.strftime('%w', current_time))]
            week_num = int(time.strftime('%W', current_time))
            day_num = int(time.strftime('%j', current_time))

            # 年度进度百分比计算
            is_leap = current_time.tm_year % 4 == 0 and (current_time.tm_year % 100 != 0 or current_time.tm_year % 400 == 0)
            total_days = 366 if is_leap else 365
            year_progress = round((int(day_num) / int(total_days)) * 100, 2)
            year_remain = round(100 - year_progress, 2)

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
            log.error(f'获取时间信息失败：{str(e)}')
            fallback = time.localtime()
            return {
                'date': f'{fallback.tm_year}年{fallback.tm_mon}月{fallback.tm_mday}日',
                'lunar_date': f'农历{fallback.tm_mon}月{fallback.tm_mday}日',
                'weekday': '日',
                'week_num': 0,
                'day_num': 0,
                'year_progress': '0%',
                'year_remain': '100%',
            }

    def _fetch_data(self) -> dict:
        """合并日期和时间信息

        Returns:
            dict: 包含日期和时间信息的字典
        """
        data = self._get_date()
        data.update(self._get_time())
        return data

# 2.倒数日
class CountDownDayWidget(LocalWidgetBase):
    WIDGET_NAME = 'CountDownDay'
    NEED_CACHE = False

    def _fetch_data(self) -> dict:
        """
        计算从今天到目标日期的剩余天数

        Returns:
            dict: 包含倒数日信息的字典
        """
        # 判断用户是否启用倒数日功能
        # if not cfg.countdown_switch.value:
        #     return {'is_countdown_available': False}

        # 1. 获取当前日期（只要日期，不要时分秒，方便对齐）
        today = datetime.now().date()
        # 2.获取目标日期
        target_date_str = cfg.countdown_date.value
        try:
            # 2. 将字符串转换为 datetime 对象
            # %Y-%m-%d 对应 2026-06-21 这种格式
            target_date_obj = datetime.strptime(target_date_str, "%Y-%m-%d").date()

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

# 3.生日
class BirthdayWidget(LocalWidgetBase):
    WIDGET_NAME = 'Birthday'
    NEED_CACHE = True
    LOCAL_INTERVAL = '1d'

    def mark_as_shown(self) -> None:
        """标记生日祝福今天已显示，明天之前不再重复检测。"""
        lib.file.write('General', 'last_birthday_date', time.strftime('%Y%m%d', time.localtime()))

    def _fetch_data(self) -> dict | None:
        """刷新生日信息并自动缓存"""
        try:
            # 获取生日字典
            birthday_dict = cfg.birthday_dict.value

        except Exception as e:
            log.error(f'生日：获取生日配置失败 - {str(e)}')
            return None

        # 如果生日列表为空，返回 None
        if not birthday_dict:
            return None

            # 获取今天的月和日
        today_month_day = time.strftime("%m%d", global_time)
        current_year = global_time.tm_year

        # 遍历生日列表，检查是否有人今天生日
        for name, birthday_str in birthday_dict.items():
            # 检查生日格式是否正确（YYYYMMDD）
            if not isinstance(birthday_str, str) or len(birthday_str) != 8:
                log.warning(f'生日格式错误：{name} - {birthday_str}')
                continue

            # 提取出生年月日
            try:
                birth_year = int(birthday_str[:4])
                birth_month_day = birthday_str[4:8]
            except ValueError:
                log.warning(f'生日格式错误：{name} - {birthday_str}')
                continue

            # 检查是否是今天生日
            if birth_month_day == today_month_day:
                # 计算年龄
                age = current_year - birth_year

                # 计算来到这个世界上的总天数
                birth_date = datetime(birth_year, int(birthday_str[4:6]), int(birthday_str[6:8]))
                today_date = datetime.now()
                life_days = (today_date - birth_date).days

                log.info(f'检测到生日：{name} 今天满 {age} 岁')
                return {
                    'birthday_star': name,
                    'age': age,
                    'life_days': life_days
                }

        # 没有人今天生日，返回None
        return None

# 4.问候语(暂定)
class GreetingWidget(LocalWidgetBase):
    WIDGET_NAME = 'Greeting'
    NEED_CACHE = False
    
    def _fetch_data(self) -> str:
        hour = int(time.strftime('%H', global_time))
        return '早上好！' if 6 <= hour < 11 else '中午好！' if 11 <= hour < 12 else '下午好！' if 12 <= hour < 17 else '晚上好！'

# 5.开机次数
class StartupTimesWidget(LocalWidgetBase):
    """开机次数组件

    开机次数使用手动缓存管理（不走基类的自动流程），
    因为需要自定义：开机自启时自增/重置，手动打开时只读不写。
    """
    WIDGET_NAME = 'StartupTimes'
    NEED_CACHE = False

    def _read_value(self, path: str, default: object = 0) -> int | Any:
        """读取缓存路径的值，不存在时返回默认值。"""
        cached = self._read_cache_path(path)
        return cached[0] if cached is not None else default

    def _reset_times(self) -> None:
        """重置开机次数为 1，记录今天日期。"""
        self._update_cache_path('times', 1)
        self._update_cache_path('get_date', global_date)

    def _add_times(self) -> int:
        """自增开机次数。

        Returns:
            int: 新的开机次数
        """
        current = self._read_value('times')
        new_times = current + 1
        self._update_cache_path('times', new_times)
        return new_times

    def _fetch_data(self) -> dict:
        """获取开机次数信息。

        Returns:
            dict: 开机次数信息，示例：{'times': 1}
        """
        if '--startup' in lib.global_argv:
            last_date = self._read_value('get_date', default='')
            if global_date != last_date:
                # 新的一天 → 重置
                self._reset_times()
                return {'times': 1}
            else:
                # 同一天多次启动 → 自增
                times = self._add_times()
                return {'times': times}
        else:
            # 手动打开，只读不写
            times = self._read_value('times')
            return {'times': times}

# ===== 联网组件 =====
# 1.天气
class WeatherWidget(NetworkWidgetBase):
    # 基本信息
    WIDGET_NAME = 'Weather'
    NEED_CACHE = True
    LOCAL_INTERVAL = f'{cfg.weather_interval.value}m'
    API_URL = api['qweather.com']['url_weather']
    PARAMS = {
        'key': lib.decrypt(api['qweather.com']['api_key']),
        'location' : cfg.city_id.value,
    }

    def _get_weather_emoji(self,weather_type) -> str:
        """获取天气emoji"""
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

    def _parse_data(self, raw_data: dict) -> dict | None:
        """解析 API 返回的完整响应，提取 now 对象中的字段。"""
        now = raw_data.get('now')
        if now:
            weather = now.get('text', '')
            weather_emoji = self._get_weather_emoji(weather)

            return {
                'city_name': cfg.city_name.value,
                'weather': weather,
                'temperature': f'{now.get('temp', '')}℃',
                'feels_like': f'{now.get('feelsLike', '')}℃',
                'humidity': f'{now.get('humidity', '')}%',
                'wind_direction': now.get('windDir', ''),
                'wind_speed': f'{now.get('windSpeed', '')}km/h',
                'weather_emoji': weather_emoji,
            }

        else:
            self.skip_cache()
            log.error('天气：获取失败')
            return None

# 2.空气质量
class AirQualityWidget(NetworkWidgetBase):
    WIDGET_NAME = 'AirQuality'
    NEED_CACHE = True
    LOCAL_INTERVAL = f'{cfg.air_quality_interval.value}m'
    API_URL = api['qweather.com']['url_air']
    PARAMS = {
        'key': lib.decrypt(api['qweather.com']['api_key']),
        'location': cfg.city_id.value,
    }

    def _parse_data(self, raw_data: dict) -> dict | None:
        """解析数据"""
        now = raw_data.get('now')
        if now:
            air_quality = now.get("aqi", '')
            air_level = now.get("category", '')
            air_quality_text = f'{air_level}(PM2.5 指数:{air_quality})'

            return {'air_quality': air_quality_text}

        else:
            self.skip_cache()
            log.error('空气质量：获取失败')
            return None

# 3.历史上的今天
class TodayInHistoryWidget(NetworkWidgetBase):
    WIDGET_NAME = 'TodayInHistory'
    NEED_CACHE = True
    LOCAL_INTERVAL = '1d'
    API_URL = api['www.mxnzp.com']['today_in_history']['url']
    PARAMS = {
        "args": 1,
        "app_id": lib.decrypt(api['www.mxnzp.com']['today_in_history']['app_id']),
        "app_secret": lib.decrypt(api['www.mxnzp.com']['today_in_history']['app_secret'])
    }

    def _parse_data(self, raw_data: dict) -> dict | None:
        """解析数据"""
        if raw_data['code'] == 1:
            history_data = raw_data['data']
            if len(history_data) > 0:
                history = history_data[0]
                # 格式化输出信息
                return {
                    'historical_date': f"{history['year']}年{history['month']}月{history['day']}日",
                    'historical_event': history['title']
                }
            else:
                lib.log.error('历史上的今天：没有找到历史上的今天的信息')
                return None
        else:
            self.skip_cache()
            lib.log.error('历史上的今天：请求失败')
            return None

# 4.节假日和24节气
class HolidayAndSolarTermWidget(NetworkWidgetBase):
    WIDGET_NAME = 'HolidayAndSolarTerm'
    NEED_CACHE = True
    LOCAL_INTERVAL = '1d'
    # API_URL 在 _fetch_data 中动态拼接日期，留空占位
    API_URL = ''
    PARAMS = {
        'args': 1,
        'app_id': lib.decrypt(api['www.mxnzp.com']['holiday_solar_term']['app_id']),
        'app_secret': lib.decrypt(api['www.mxnzp.com']['holiday_solar_term']['app_secret']),
    }

    def _set_url(self) -> None:
        """拼接当天日期到 URL 上。"""
        base_url = api['www.mxnzp.com']['holiday_solar_term']['url']
        today = time.strftime('%Y%m%d')
        self.API_URL = f'{base_url}/{today}'

    def _fetch_data(self) -> dict:
        """同步获取。"""
        self._set_url()
        return self._sync_request()

    async def _fetch_data_async(self) -> dict:
        """异步获取。"""
        self._set_url()
        return await self._async_request()

    def _parse_data(self, raw_data: dict) -> dict | None:
        """解析 API 响应，同时提取节气和节假日信息。"""
        if raw_data.get('code') == 1:
            data = raw_data['data']
            holiday = data.get('typeDes') or '没有节假日'
            solar_term = data.get('solarTerms') or '没有找到 24 节气'
            return {'holiday': holiday, 'solar_term': solar_term}

        else:
            self.skip_cache()
            log.error('节假日和 24 节气信息：请求失败')
            return None

# 5.金山词霸每日一言
class EveryDayWordsWidget(NetworkWidgetBase):
    WIDGET_NAME = 'EveryDayWords'
    NEED_CACHE = True
    LOCAL_INTERVAL = '1d'
    API_URL = api['open.iciba.com']

    def _parse_data(self, raw_data: dict) -> dict | None:
        """解析数据"""
        if raw_data:
            content = raw_data.get('content', '')
            note = raw_data.get('note', '')

            return {
                'every_day_words_zh': note,
                'every_day_words_en': content
            }

        else:
            self.skip_cache()
            log.error('金山词霸每日一言：请求失败')
            return None

# 6.MC 服务器状态
class MCServerStatusWidget(LocalWidgetBase):
    WIDGET_NAME = 'MCServerStatus'
    NEED_CACHE = True
    LOCAL_INTERVAL = f'{cfg.minecraft_server_data_refresh_interval.value}s'

    def _build_status(self, status) -> dict:
        """从 mcstatus 的 status 对象提取公共字段。"""
        friends = cfg.minecraft_server_friends_list.value

        results = {
            'mc_server_name': cfg.minecraft_server_name.value,
            'is_mc_server_online': True,
            'mc_server_current': status.players.online,
            'mc_server_max': status.players.max,
            'mc_server_latency': round(status.latency, 1),
            'mc_online_friends': [],
        }

        try:
            if status.players.sample:
                online_names = [p.name for p in status.players.sample]
                results['mc_online_friends'] = [
                    name for name in friends if name in online_names
                ]

        except Exception as e:
            self.skip_cache()
            log.warning(f'MC 服务器：获取玩家列表失败 - {e}')

        return results

    def _fetch_data(self) -> dict | None:
        """同步获取 MC 服务器状态。"""
        from mcstatus import JavaServer

        if not cfg.minecraft_server_checker_switch.value:
            self.skip_cache()
            log.info('MC 服务器：开关未开启，跳过检测')
            return None

        ip = cfg.minecraft_server_ip.value
        port = cfg.minecraft_server_port.value
        if not ip or port in [None, '未知', '']:
            self.skip_cache()
            log.error('MC 服务器：请填写完整的服务器地址和端口')
            return None

        try:
            server = JavaServer.lookup(f'{ip}:{port}')
            status = server.status()
            results = self._build_status(status)
            log.info(f'MC 服务器（同步）：{results["mc_server_current"]}人在线')
            return results

        except Exception as e:
            self.skip_cache()
            log.error(f'MC 服务器（同步）：获取失败：{e}')
            return None

    async def _fetch_data_async(self) -> dict | None:
        """异步获取 MC 服务器状态。"""
        from mcstatus import JavaServer

        if not cfg.minecraft_server_checker_switch.value:
            self.skip_cache()
            log.info('MC 服务器：开关未开启，跳过检测')
            return {}

        ip = cfg.minecraft_server_ip.value
        port = cfg.minecraft_server_port.value
        if not ip or port in [None, '未知', '']:
            self.skip_cache()
            log.error('MC 服务器：请填写完整的服务器地址和端口')
            return None

        try:
            server = await JavaServer.async_lookup(f'{ip}:{port}')
            status = await server.async_status()
            results = self._build_status(status)
            log.info(f'MC 服务器（异步）：{results["mc_server_current"]}人在线')
            return results

        except Exception as e:
            self.skip_cache()
            log.error(f'MC 服务器（异步）：获取失败：{e}')
            return None
import datetime
import time

from datetime import datetime

import httpx

from lunar_python import Lunar, Solar
from lunar_python.util import HolidayUtil
from typing import Any

from . import base_lib as lib
from .widgets_core import (LocalWidgetBase, NetworkWidgetBase, ExtNetworkWidgetBase,
                           APIConfig, register)
from .config import cfg

# StartInfo内置组件
# 组件系统及组件于2026-06-30开始重构
# 获取 api 信息
api = lib.read_json(lib.API_FILE_PATH)

# 日志
log = lib.log

# 获取 emoji
emoji = lib.read_json(lib.EMOJI_PATH)
time_emoji = emoji['time']
weather_emoji = emoji['weather']

# 获取全局日期和时间信息
global_date = datetime.today().strftime('%Y%m%d')
global_time = time.localtime()
global_now = datetime.now()

# ===== 本地组件 =====
# 1.日期和时间组件(含农历/24节气/节假日/其他数据子开关)
@register(
    cfg.datetime_switch, 'datetime_switch',
    extra_template_keys={
        'lunar_date_switch': cfg.lunar_date_switch,
        'solar_term_switch': cfg.solar_term_switch,
        'holiday_switch': cfg.holiday_switch,
        'other_date_switch': cfg.other_date_switch,
    },
)
class DateTimeWidget(LocalWidgetBase):
    WIDGET_NAME = 'DateTime'
    NEED_CACHE = False
    lunar = Lunar.fromDate(global_now)

    @staticmethod
    def _get_time_emoji(current_time) -> str:
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
            rounded_time = f'{hour_12}:00'
        elif 15 <= minute < 45:
            rounded_time = f'{hour_12}:30'
        else:
            # 分钟 >= 45，选择下一个整点
            hour_12 = (hour_12 % 12) + 1
            if hour_12 == 13:
                hour_12 = 1  # 12 点之后是 1 点
            rounded_time = f'{hour_12}:00'

        return time_emoji.get(rounded_time, time_emoji['9:00'])

    def _get_time(self) -> dict[str, str | Any] | dict[str, str]:
        """
        获取当前时间和时间emoji
        Returns:
            dict[str, str | Any] | dict[str, str]: 当前时间和时间emoji，出错时返回默认值
        """
        try:
            time_str = time.strftime('%X', global_time)
            time_emoji = self._get_time_emoji(global_time)
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

    def _get_date(self) -> dict[str, str] | None:
        """获取阳历日期"""
        try:
            date = datetime.today().strftime('%Y年%m月%d日')

            weekday = ['日', '一', '二', '三', '四', '五', '六'][int(time.strftime('%w', global_time))]

            return {
                'date': date,
                'weekday': weekday
            }

        except Exception as e:
            log.error(f'[{self.WIDGET_NAME}] 获取阳历日期失败：{str(e)}')
            return None
            
    def _get_lunar_date(self) -> dict[str, str] | None:
        """获取农历日期"""
        try:
            lunar_date = f'农历：{self.lunar.getMonthInChinese()}月{self.lunar.getDayInChinese()}'
            return {'lunar_date': lunar_date}
        
        except Exception as e:
            log.error(f'[{self.WIDGET_NAME}] 获取农历日期失败:{str(e)}')

    def _get_other_data(self) -> dict[str, int | str] | None:
        """获取其他时间信息"""
        try:
            week_num = int(time.strftime('%W', global_time))
            day_num = int(time.strftime('%j', global_time))

            # 年度进度百分比计算
            is_leap = global_time.tm_year % 4 == 0 and (global_time.tm_year % 100 != 0 or global_time.tm_year % 400 == 0)
            total_days = 366 if is_leap else 365
            year_progress = round((int(day_num) / int(total_days)) * 100, 2)
            year_remain = round(100 - year_progress, 2)

            data = {
                'week_num': week_num,
                'day_num': day_num,
                'year_progress': f'{year_progress}%',
                'year_remain': f'{year_remain}%'
            }
            return data

        except Exception as e:
            log.error(f'[{self.WIDGET_NAME}] 获取其他信息失败:{str(e)}')
            return None

    def _get_solar_term(self) -> dict | None:
        """获取24节气信息"""
        try:
            solar_term = self.lunar.getJieQi()
            if solar_term == '':
                solar_term = f'{self.lunar.getPrevJieQi()}后'

            return {'solar_term': solar_term}

        except Exception as e:
            log.error(f'[{self.WIDGET_NAME}] 获取24节气失败:{e}')
            return None

    def _get_holiday(self) -> dict | None:
        """获取节假日信息"""
        try:
            solar = Solar.fromDate(global_now)
            date_str = solar.toYmd()
            holiday = HolidayUtil.getHoliday(date_str)

            if holiday:
                if holiday.isWork():
                    data = '工作日'
                else:
                    data = holiday.getName()

            else:
                # 不在特殊节假日安排中
                if solar.getWeek() in (0, 6):
                    data = '休息日'

                else:
                    data = '工作日'

            return {'holiday': data}

        except Exception as e:
            log.error(f'[{self.WIDGET_NAME}] 获取节假日信息失败:{str(e)}')
            return None

    def _fetch_data(self) -> dict[str, str] | None:
        """合并所有信息"""
        # 阳历日期和时间默认显示（helper 异常返回 None 时兜底为空字典，避免 None.update 崩溃）
        data = self._get_date() or {}
        data.update(self._get_time())

        # 按需获取需要显示的信息
        info_config = [
            (cfg.lunar_date_switch, self._get_lunar_date),
            (cfg.solar_term_switch, self._get_solar_term),
            (cfg.holiday_switch, self._get_holiday),
            (cfg.other_date_switch, self._get_other_data)
        ]

        for switch, func in info_config:
            if switch.value:
                data.update(func() or {})

        return data


# 2.倒数日
@register(cfg.countdown_switch, 'countdown_switch')
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
        today = global_now.date()
        # 2.获取目标日期
        target_date_str = cfg.countdown_date.value
        try:
            # 2. 将字符串转换为 datetime 对象
            # %Y-%m-%d 对应 2026-06-21 这种格式
            target_date_obj = datetime.strptime(target_date_str, '%Y-%m-%d').date()

            # 3. 两个日期对象直接相减，得到一个 timedelta 对象
            remaining = target_date_obj - today

            # 如果天数小于 -3，则判断为过期，返回 False
            if remaining.days < -3:
                return {'is_countdown_available': False}

            # 4. 返回天数 (.days 属性)
            return {
                'is_countdown_available': True,
                'countdown_name': cfg.countdown_name.value,
                'countdown_number': remaining.days
            }

        # 用户设置的日期格式错误，返回 False
        except ValueError:
            return {'is_countdown_available': False}


# 3.生日
@register(cfg.birthday_wishes_switch)  # 生日无模板开关，不注入
class BirthdayWidget(LocalWidgetBase):
    WIDGET_NAME = 'Birthday'
    NEED_CACHE = True
    LOCAL_INTERVAL = '1d'

    def mark_as_shown(self) -> None:
        """标记生日祝福今天已显示，明天之前不再重复检测。"""
        self._update_cache_path('last_birthday_date', global_date)

    def read_last_birthday_date(self):
        """获取最后检查生日的日期"""
        return self._read_cache_value('last_birthday_date', '')

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
        today_month_day = time.strftime('%m%d', global_time)
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


# 4.问候语
@register(cfg.greeting_switch, 'greeting_switch')
class GreetingWidget(LocalWidgetBase):
    WIDGET_NAME = 'Greeting'
    NEED_CACHE = False
    
    def _fetch_data(self) -> dict:
        hour = int(time.strftime('%H', global_time))
        greeting = '早上好！' if 6 <= hour < 11 else '中午好！' if 11 <= hour < 12 else '下午好！' if 12 <= hour < 18 else '晚上好！'
        return {'greeting': greeting}


# 5.开机次数
@register(cfg.startup_times_switch, 'startup_times_switch')
class StartupTimesWidget(LocalWidgetBase):
    """开机次数组件

    开机次数使用手动缓存管理（不走基类的自动流程），
    因为需要自定义：开机自启时自增/重置，手动打开时只读不写。
    """
    WIDGET_NAME = 'StartupTimes'
    NEED_CACHE = False

    def _reset_times(self) -> None:
        """重置开机次数为 1，记录今天日期。"""
        self._update_cache_path('times', 1)
        self._update_cache_path('get_date', global_date)

    def _add_times(self) -> int:
        """自增开机次数。

        Returns:
            int: 新的开机次数
        """
        current = self._read_cache_value('times')
        new_times = current + 1
        self._update_cache_path('times', new_times)
        return new_times

    def _fetch_data(self) -> dict:
        """获取开机次数信息。

        Returns:
            dict: 开机次数信息，示例：{'times': 1}
        """
        if '--startup' in lib.global_argv:
            last_date = self._read_cache_value('get_date', default='')
            if global_date != last_date:
                # 新的一天 → 重置
                self._reset_times()
                return {'startup_times': 1}
            else:
                # 同一天多次启动 → 自增
                times = self._add_times()
                return {'startup_times': times}
        else:
            # 手动打开，只读不写
            times = self._read_cache_value('times')
            return {'startup_times': times}


# 6.今日人品
@register(cfg.daily_character_switch, 'daily_character_switch')
class DailyCharacterWidget(LocalWidgetBase):
    WIDGET_NAME = 'DailyCharacter'
    NEED_CACHE = True
    LOCAL_INTERVAL = '1d'

    def _fetch_data(self) -> dict:
        # 延迟导入
        from random import randint
        character = randint(0,100)
        # 根据人品质拼接文案
        if 0 <= character <= 10:
            return {'character': f'{character}....是百分制哦 '}

        elif 10 < character <= 30:
            return {'character': f'{character}，也许还能将就？'}

        elif 30 < character <= 60:
            return {'character': f'{character}，加油啊下次及格'}

        elif 60 < character <= 90:
            if character == 78:
                return {'character': f'{character}，暗广！'}

            else:
                return {'character': f'{character}'}

        else:
            if character == 91:
                return {'character': f'{character},干什么！'}

            else:
                return {'character': f'{character}，欧皇！'}


# ===== 联网组件 =====
# 1.天气
@register(cfg.weather_switch, 'weather_switch')
class WeatherWidget(ExtNetworkWidgetBase):
    # 基本信息
    WIDGET_NAME = 'Weather'
    NEED_CACHE = True
    LOCAL_INTERVAL = f'{cfg.weather_data_refresh_interval.value}m'
    CONFIG_ITEM = cfg.weather_source

    # 动态获取city_id，避免在初次启动选择城市后仍使用旧值
    @property
    def API_DATA(self) -> dict:
        api_host = (
            cfg.qweather_api_host.value
            .strip()
            .removeprefix("https://")
            .removeprefix("http://")
            .rstrip("/")
        )

        qweather_base_url = f"https://{api_host}"
        api_key = cfg.qweather_api_key.value.strip()
        location = cfg.city_id.value[cfg.weather_source.value]

        return {
            'qweather': {
                'weather': {
                    'url': f'{qweather_base_url}{api['qweather']['weather_path']}',
                    'params': {
                        'key': api_key,
                        'location': location,
                    },
                    'parse_func': '_parse_qweather_weather',
                },
                'air_quality': {
                    'url': f'{qweather_base_url}{api['qweather']['air_quality_path']}',
                    'params': {
                        'key': api_key,
                        'location': location,
                    },
                    'parse_func': '_parse_qweather_air_quality',
                }
            },
            'xiaomi_weather': {
                'all': {
                    'url': api['xiaomi_weather']['url'],
                    'params': {
                        'latitude': 0,
                        'longitude': 0,
                        'locationKey': f'weathercn:{cfg.city_id.value[cfg.weather_source.value]}',
                        'days': 1,
                        'appKey': 'weather20151024',
                        'sign': 'zUFJoAR2ZVrDy1vF3D07',
                        'isGlobal': 'false',
                        'locale': 'zh_cn',
                    },
                    'parse_func': '_parse_xiaomi_weather'
                }
            }
        }

    @staticmethod
    def _get_weather_emoji(weather_type) -> str:
        """获取天气emoji"""
        weather_type = str(weather_type).strip()

        # 1. 精确匹配
        emoji = weather_emoji.get(weather_type)
        if emoji is not None:
            return emoji

        # 2. 关键词回退：优先级可调整
        if '雨' in weather_type:
            # 优先使用'小雨'的 emoji 作为通用雨
            return weather_emoji.get('小雨', '🌧️')

        elif '雪' in weather_type:
            # 优先使用'小雪'的 emoji 作为通用雪
            return weather_emoji.get('小雪', '❄️')

        elif '雷' in weather_type or '电' in weather_type:
            return weather_emoji.get('雷阵雨', '⛈️')

        elif '雾' in weather_type or '霾' in weather_type:
            return weather_emoji.get('雾', '🌫️')

        elif '沙尘' in weather_type or '扬沙' in weather_type:
            return weather_emoji.get('沙尘暴', '💨')

        # 3. 完全未知类型：返回默认天气（阴天）
        return '☁️'

    @staticmethod
    def _convert_wind_direction(value) -> str:
        """将风向角度转为中文风向（如 141.0 → 东南风），与和风天气的风向格式统一"""
        try:
            angle = float(value) % 360
        except (TypeError, ValueError):
            # 非法值原样返回
            return str(value) if value else ''

        # 8 方位：从北(0°)起顺时针每 45° 一档
        directions = ['北风', '东北风', '东风', '东南风', '南风', '西南风', '西风', '西北风']
        index = int((angle + 22.5) // 45) % 8
        return directions[index]

    @staticmethod
    def _aqi_to_level(aqi: int) -> str:
        """按 AQI 指数划分等级(与和风天气的 category 一致)"""
        if aqi <= 50:
            return '优'

        if aqi <= 100:
            return '良'

        if aqi <= 150:
            return '轻度污染'

        if aqi <= 200:
            return '中度污染'

        if aqi <= 300:
            return '重度污染'

        return '严重污染'

    def _parse_qweather_weather(self, raw_data: dict) -> dict | None:
        """解析和风天气的天气数据"""
        now = raw_data.get('now')
        if not now:
            self.skip_cache()
            log.error(f'[{self.WIDGET_NAME}] 和风天气-天气信息获取失败')
            return None

        # 必需字段：天气类型缺失视为失败，不缓存
        weather = now.get('text')
        if not weather:
            self.skip_cache()
            log.error(f'[{self.WIDGET_NAME}] 和风天气-天气信息缺少 text 字段')
            return None

        # text 多处使用提前取出；其余字段单层且只用一次 → 内联
        return {
            'city_name': cfg.city_name.value[cfg.weather_source.value],
            'weather': weather,
            'temperature': self._fmt(now.get('temp'), '℃'),
            'feels_like': self._fmt(now.get('feelsLike'), '℃'),
            'humidity': self._fmt(now.get('humidity'), '%'),
            'wind_direction': self._fmt(now.get('windDir')),
            'wind_speed': self._fmt(now.get('windSpeed'), 'km/h'),
            'weather_emoji': self._get_weather_emoji(weather),
        }

    def _parse_qweather_air_quality(self, raw_data: dict) -> dict | None:
        """解析和风天气的空气质量数据"""
        now = raw_data.get('now')
        if now:
            air_level = now.get('category', '')
            pm25 = now.get('pm2p5', '')
            air_quality_text = f'{air_level}(PM2.5 指数:{pm25})'

            return {'air_quality': air_quality_text}

        else:
            self.skip_cache()
            log.error(f'[{self.WIDGET_NAME}] 和风天气-空气质量信息获取失败')
            return None

    def _parse_xiaomi_weather(self, raw_data: dict) -> dict | None:
        """解析小米天气数据（天气代码需映射为中文，另含 AQI 换算）"""
        current = raw_data.get('current')
        if not current:
            self.skip_cache()
            log.error(f'[{self.WIDGET_NAME}] 小米天气信息获取失败')
            return None

        # 必需字段：天气代码缺失视为失败，不缓存
        weather_code = current.get('weather')
        if weather_code is None:
            self.skip_cache()
            log.error(f'[{self.WIDGET_NAME}] 小米天气-缺少 weather 字段')
            return None

        # 天气代码需映射为中文；其余嵌套字段（≥2 层）提前取出
        weather = api['xiaomi_weather']['weather_status'].get(weather_code, '未知')
        temp_data = current.get('temperature')
        feels_data = current.get('feelsLike')
        humidity_data = current.get('humidity')
        wind_data = current.get('wind')

        temp = temp_data.get('value') if temp_data else None
        temp_unit = temp_data.get('unit') if temp_data else ''
        feels = feels_data.get('value') if feels_data else None
        feels_unit = feels_data.get('unit') if feels_data else ''
        humidity = humidity_data.get('value') if humidity_data else None
        direction = wind_data.get('direction', {}) if wind_data else {}
        speed = wind_data.get('speed', {}) if wind_data else {}

        result = {
            'city_name': cfg.city_name.value[cfg.weather_source.value],
            'weather': weather,
            'temperature': self._fmt(temp, temp_unit),
            'feels_like': self._fmt(feels, feels_unit),
            'humidity': self._fmt(humidity, '%'),
            'wind_direction': self._convert_wind_direction(direction.get('value')),
            'wind_speed': self._fmt(speed.get('value'), 'km/h'),
            'weather_emoji': self._get_weather_emoji(weather),
        }

        # 空气质量：可选字段，小米接口无 category，按 AQI 指数换算等级
        # 缺失/损坏时只省略 air_quality，不影响天气主数据缓存
        aqi_data = raw_data.get('aqi')
        aqi_value = aqi_data.get('aqi') if aqi_data else None
        if aqi_value:
            try:
                aqi = int(aqi_value)
                pm25 = aqi_data.get('pm25', '')
                result['air_quality'] = f'{self._aqi_to_level(aqi)}(PM2.5 指数:{pm25})'
            except (TypeError, ValueError):
                log.warning(f'[{self.WIDGET_NAME}] 小米天气-空气质量指数异常: {aqi_value}')

        return result


# 2.历史上的今天
@register(cfg.historical_switch, 'historical_switch')
class TodayInHistoryWidget(NetworkWidgetBase):
    WIDGET_NAME = 'TodayInHistory'
    NEED_CACHE = True
    LOCAL_INTERVAL = '1d'
    API_URL = api['xxapi_history_url']

    def _parse_data(self, raw_data: dict) -> dict | None:
        """解析数据"""
        if raw_data.get('code') != 200:
            self.skip_cache()
            log.error(f'[{self.WIDGET_NAME}] 请求失败')
            return None

        history_data = raw_data.get('data')
        if not history_data or not isinstance(history_data, list):
            log.error(f'[{self.WIDGET_NAME}] 没有找到历史上的今天的信息')
            self.skip_cache()
            return None

        # 依赖 "日期 事件" 空格分隔格式
        history = history_data[0].split() if isinstance(history_data[0], str) else []
        if len(history) < 2:
            log.error(f'[{self.WIDGET_NAME}] 历史上的今天数据格式异常')
            self.skip_cache()
            return None

        # 格式化输出信息
        return {
            'historical_date': history[0],
            'historical_event': history[1]
        }


# 3.每日一言
@register(cfg.words_switch, 'words_switch')
class DailyWordsWidget(ExtNetworkWidgetBase):
    WIDGET_NAME = 'EveryDayWords'
    NEED_CACHE = True
    LOCAL_INTERVAL = '1d'
    CONFIG_ITEM = cfg.words_source
    API_DATA = {
        'iciba': {
            'words': {
                'url': 'https://open.iciba.com/dsapi/',
                'parse_func': '_parse_iciba',
            }
        },
        'hitokoto':{
            'words': {
                'url': 'https://v1.hitokoto.cn/',
                'parse_func': '_parse_hitokoto',
            }
        }
    }

    # 解析函数
    def _parse_iciba(self, raw_data) -> dict | None:
        if raw_data:
            content = raw_data.get('content', '')
            note = raw_data.get('note', '')
            return {
                'words_primary': note,
                'words_secondary': content
            }

        else:
            self.skip_cache()
            log.error('每日一言：获取失败')
            return None

    def _parse_hitokoto(self, raw_data: dict) -> dict | None:
        if raw_data:
            hitokoto = raw_data.get('hitokoto', '')
            source = raw_data.get('from', '')
            from_who = raw_data.get('from_who', None)
            # 如果from_who字段为空
            if from_who is None:
                from_text = f'——「{source}」'

            else:
                from_text = f'——{from_who}「{source}」'

            return {
                'words_primary': hitokoto,
                'words_secondary': from_text
            }

        else:
            self.skip_cache()
            log.error('每日一言：获取失败')
            return None


# 4.MC 服务器信息
class MCServerError(Exception):
    """MC 服务器信息获取失败，message 为用户可读的错误描述。"""

@register(cfg.mc_server_info_switch, 'mc_server_check_switch')
class MCServerInfoWidget(LocalWidgetBase):
    WIDGET_NAME = 'MCServerStatus'
    NEED_CACHE = True
    LOCAL_INTERVAL = f'{cfg.mc_server_data_refresh_interval.value}s'

    def _build_status(self, status) -> dict:
        """从 mcstatus 的 status 对象提取公共字段。"""
        friends = cfg.mc_server_friends_list.value

        results = {
            'mc_server_name': cfg.mc_server_name.value,
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

    def _fetch_data(self) -> dict:
        """同步获取 MC 服务器状态。

        :raises MCServerError: 地址未配置或获取失败时抛出，message 可直接展示给用户
        """
        from mcstatus import JavaServer

        ip = cfg.mc_server_ip.value
        port = cfg.mc_server_port.value
        if not ip or port in [None, '未知', '']:
            self.skip_cache()
            log.error('MC 服务器：请填写完整的服务器地址和端口')
            raise MCServerError('请填写完整的服务器地址和端口')

        try:
            server = JavaServer.lookup(f'{ip}:{port}')
            status = server.status()
            results = self._build_status(status)
            log.info(f'MC 服务器（同步）：{results['mc_server_current']}人在线')
            return results

        except Exception as e:
            self.skip_cache()
            log.error(f'MC 服务器（同步）：获取失败：{e}')
            raise MCServerError(f'获取失败：{e}') from e

    async def _fetch_data_async(self) -> dict:
        """异步获取 MC 服务器状态。

        :raises MCServerError: 地址未配置或获取失败时抛出，message 可直接展示给用户
        """
        from mcstatus import JavaServer

        ip = cfg.mc_server_ip.value
        port = cfg.mc_server_port.value
        if not ip or port in [None, '未知', '']:
            self.skip_cache()
            log.error('MC 服务器：请填写完整的服务器地址和端口')
            raise MCServerError('请填写完整的服务器地址和端口')

        try:
            server = await JavaServer.async_lookup(f'{ip}:{port}')
            status = await server.async_status()
            results = self._build_status(status)
            log.info(f'MC 服务器（异步）：{results['mc_server_current']}人在线')
            return results

        except Exception as e:
            self.skip_cache()
            log.error(f'MC 服务器（异步）：获取失败：{e}')
            raise MCServerError(f'获取失败：{e}') from e


# 5.GitHub仓库信息
@register(cfg.github_repo_switch, 'github_repo_switch')
class GitHubRepoInfoWidget(ExtNetworkWidgetBase):
    WIDGET_NAME = 'GitHubRepoInfo'
    NEED_CACHE = True
    LOCAL_INTERVAL = f'{cfg.github_repo_data_refresh_interval.value}h'

    # 动态获取API_DATA
    @property
    def API_DATA(self) -> dict[str, dict[str, dict[str, str]]]:
        base_url = f'{api['github_rest_api_prefix']}{cfg.github_repo_owner.value}/{cfg.github_repo_name.value}'
        return {
            'github_rest_api': {
                'common': {
                    'url': base_url,
                    'parse_func': '_parse_common'
                },
                'releases': {
                    'url': f'{base_url}/releases/latest',
                    'parse_func': '_parse_releases'
                }
            }
        }

    def _parse_common(self, raw_data: dict) -> dict[str, Any | None] | None:
        """解析common部分的数据"""
        if not raw_data:
            self.skip_cache()
            return None

        return {
            'repo_name': cfg.github_repo_name.value,
            'repo_stars': raw_data.get('stargazers_count'),
            'forks': raw_data.get('forks_count'),
        }

    def _parse_releases(self, raw_data: dict) -> dict | None:
        """处理 releases 部分的数据（/releases/latest 返回单个 release 对象）"""
        if not isinstance(raw_data, dict):
            self.skip_cache()
            return None

        return {'last_tag': raw_data.get('tag_name') or ''}

    def _request_api(self, api_name: str, api_config: APIConfig) -> dict | None:
        try:
            return super()._request_api(api_name, api_config)
        except ConnectionError as e:
            if self._is_releases_404(api_name, e):
                # 仓库从未发布过 release：/releases/latest 返回 404，视为无最新版本
                log.info(f'[{self.WIDGET_NAME}] 仓库暂无 release，跳过最新版本')
                return {'last_tag': ''}
            raise

    async def _request_api_async(self, api_name: str, api_config: APIConfig) -> dict | None:
        try:
            return await super()._request_api_async(api_name, api_config)
        except ConnectionError as e:
            if self._is_releases_404(api_name, e):
                log.info(f'[{self.WIDGET_NAME}] 仓库暂无 release，跳过最新版本')
                return {'last_tag': ''}
            raise

    @staticmethod
    def _is_releases_404(api_name: str, exc: ConnectionError) -> bool:
        """判断是否为 releases 接口的 404（仓库从未发布过 release）。"""
        cause = exc.__cause__
        return (
            api_name == 'releases'
            and isinstance(cause, httpx.HTTPStatusError)
            and cause.response.status_code == 404
        )
import httpx
import sqlite3
from pathlib import Path
from . import ht_lib as lib
from .config import cfg, qconfig
from .paths import DB_FOLDER_PATH

# 获取api信息
api = lib.read_json(lib.API_FILE_PATH)
# 日志
log = lib.log

# # IP定位
# def get_ip_location() -> str | bool:
#     """
#     使用高德地图 API 自动定位当前公网 IP 所在地
#
#     Returns:
#         str: 成功时返回城市名称（如'黄石市'、'恩施土家族苗族自治州'）
#         bool: 失败时返回 False
#     """
#     try:
#         with httpx.Client(timeout=5.0) as client:
#             response = client.get(
#                 'https://restapi.amap.com/v3/ip',
#                 params={
#                     'key': api['restapi.amap.com']['api_key'],
#                     'output': 'json',
#                 },
#             )
#             response.raise_for_status()
#             return _parse_ip_location_data(response.json())
#     except Exception as e:
#         log.error(f'程序初始化-IP定位请求异常: {str(e)}')
#         return False
#
# def _parse_ip_location_data(data: dict) -> str | bool:
#     """内部函数：解析高德IP定位数据"""
#     if data.get('status') == '1':
#         log.info(f'程序初始化-高德IP定位API返回数据: {data}')
#
#         raw_city = data.get('city', '')
#
#         if isinstance(raw_city, list):
#             city_name = raw_city[0].strip() if raw_city else ''
#         elif isinstance(raw_city, str):
#             city_name = raw_city.strip()
#         else:
#             city_name = ''
#
#         if city_name and city_name != '未知':
#             log.info(f'程序初始化-高德IP定位成功: {city_name}')
#             return city_name
#         else:
#             log.warning(f'程序初始化-高德IP定位返回无效城市名: {repr(raw_city)}')
#             return False
#     else:
#         error_msg = data.get('info', '未知错误')
#         error_code = data.get('infocode', '无错误码')
#         log.error(f'程序初始化-高德IP定位失败: {error_msg} (错误码: {error_code})')
#         return False

# # 获取城市ID
# def get_city_info_by_location(amap_location=None) -> dict | bool:
#     """
#     通过IP定位获取实际城市名和city_id
#
#     Returns:
#         dict{'city_id':'city_id','display':'display'} city_id和显示名
#         bool: False 失败时返回
#     """
#     db_path = DB_FOLDER_PATH / 'China_cities.db'
#     if not db_path.exists():
#         log.error('程序初始化失败：中国城市数据库不存在')
#         return False
#
#     if not amap_location:
#         log.error('程序初始化失败：请检查 IP 定位是否正常')
#         return False
#
#     try:
#         conn = sqlite3.connect(str(db_path))
#         cursor = conn.cursor()
#
#         # 第一级：直接完全匹配
#         cursor.execute('SELECT city_id, display FROM cities WHERE name = ?', (amap_location,))
#         row = cursor.fetchone()
#         if row:
#             conn.close()
#             return {'city_id': row[0], 'display': row[1]}
#
#         # 第二级：清理后缀再试
#         clean_name = amap_location.replace('市', '').replace('州', '').replace('区', '').replace('县', '')
#         cursor.execute('SELECT city_id, display FROM cities WHERE name = ?', (clean_name,))
#         row = cursor.fetchone()
#         if row:
#             conn.close()
#             return {'city_id': row[0], 'display': row[1]}
#
#         # 第三级：模糊搜索兜底
#         cursor.execute('SELECT city_id, display FROM cities WHERE name LIKE ?', (f'%{clean_name}%',))
#         row = cursor.fetchone()
#         conn.close()
#         if row:
#             return {'city_id': row[0], 'display': row[1]}
#
#         return False
#
#     except Exception as e:
#         log.error(f'程序初始化-城市数据库查询异常: {str(e)}')
#         return False
#
# # 程序初始化
# def init_app() -> bool | list[bool | str]:
#     """
#     程序初始化函数（同步）
#     """
#     if lib.is_internet():
#         try:
#             city = get_ip_location()
#             result = get_city_info_by_location(city)
#             if not isinstance(result, dict):
#                 log.error('程序初始化失败：城市信息获取失败')
#                 return False
#
#             if result:
#                 actual_city_name = result.get('display', '未知')
#                 city_id = result.get('city_id', '未知')
#                 log.info(f'程序初始化，已定位到城市：{actual_city_name}')
#                 qconfig.set(cfg.city_name, actual_city_name, save=True)
#                 qconfig.set(cfg.city_id, city_id, save=True)
#                 log.info(f'程序初始化-已获取城市ID：{city_id}')
#                 return [True, actual_city_name]
#
#             else:
#                 log.error('程序初始化失败：无法获取位置信息或城市ID')
#                 return False
#
#         except Exception as e:
#             log.error(f'程序初始化失败：{str(e)}')
#             return False
#
#     else:
#         log.warning('程序初始化失败：请检查网络连接')
#         return False

# 创建快捷方式
def create_shortcut() -> bool:
    """
    创建快捷方式并移动到启动文件夹
    """
    try:
        if lib.system == 'Windows':
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(lib.SHORTCUT_PATH))
            shortcut.Targetpath = str(lib.EXE_PATH)
            shortcut.Arguments = '--startup'
            shortcut.WorkingDirectory = str(lib.MAIN_PATH)
            shortcut.save()
            log.info(f'快捷方式已创建并移动到启动文件夹: {lib.SHORTCUT_PATH}')
            return True
        else:
            pass

    except Exception as e:
        log.error(f'创建快捷方式失败: {str(e)}')
        return False


# 检查开机启动项是否存在
def is_shortcut_exist() -> bool:
    """
    检测指定的 .exe 文件是否已经添加到开机启动项
    :return: 如果存在返回 True，否则返回 False
    """
    # 如果系统是MacOS
    if lib.system == 'Windows':
        if lib.WIN_STARTUP_PATH.exists():
            # 检查快捷方式的目标路径是否与指定的目标路径一致
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(lib.SHORTCUT_PATH))
            if shortcut.Targetpath == str(lib.EXE_PATH):
                log.info(f'快捷方式已存在，且目标路径正确: {lib.SHORTCUT_PATH}')
                return True

            else:
                log.info(f'快捷方式已存在，但目标路径不匹配: {lib.SHORTCUT_PATH}')
                return False

        else:
            log.info(f'快捷方式不存在: {lib.SHORTCUT_PATH}')
            return False

    # 如果系统是MacOS
    else:
        # 暂时留空
        pass

# 删除开机启动项
def remove_shortcut() -> bool:
    """
    删除开机启动项中的快捷方式
    """
    try:
        # 如果系统是MacOS
        if lib.system == 'Windows':
            if lib.SHORTCUT_PATH.exists():
                lib.SHORTCUT_PATH.unlink(missing_ok = True)
                log.info(f'快捷方式已删除: {lib.SHORTCUT_PATH}')

            else:
                log.info(f'快捷方式不存在: {lib.SHORTCUT_PATH}')
            return True

        # 如果系统是MacOS
        else:
            # 暂时留空
            pass

    except Exception as e:
        log.error(f'删除快捷方式时出错: {e}')
        return False

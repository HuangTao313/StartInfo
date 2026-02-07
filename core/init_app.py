import aiohttp
from win32com.client import Dispatch
from . import ht_lib as lib

# 获取api信息
api = lib.read_json(lib.API_PATH)

# IP定位
async def get_ip_location() -> str | bool:
    """
    使用高德地图 API 自动定位当前公网 IP 所在地

    Returns:
        str: 成功时返回城市名称（如"黄石市"、"恩施土家族苗族自治州"）
        bool: 失败时返回 False
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    'https://restapi.amap.com/v3/ip',
                    params={
                        'key': lib.decrypt(api['restapi.amap.com']['api_key']),
                        'output': 'json'
                    }
            ) as resp:
                data = await resp.json()

                if data.get('status') == '1':
                    # 🔥 修复：处理高德返回空数组 [] 的情况
                    raw_city = data.get('city', '')

                    # 高德可能返回 []（空数组）或 ""（空字符串）或正常字符串
                    if isinstance(raw_city, list):
                        # 如果是数组，取第一个元素或设为空字符串
                        city_name = raw_city[0].strip() if raw_city else ''
                    elif isinstance(raw_city, str):
                        # 如果是字符串，正常处理
                        city_name = raw_city.strip()
                    else:
                        # 其他类型（理论上不应该出现）设为空字符串
                        city_name = ''

                    # 检查城市名是否有效
                    if city_name and city_name != '未知':
                        lib.log.info(f"程序初始化-高德IP定位成功: {city_name}")
                        return city_name
                    else:
                        lib.warning(f"程序初始化-高德IP定位返回无效城市名: {repr(raw_city)}")
                        return False
                else:
                    # API请求失败，记录详细错误信息
                    error_msg = data.get('info', '未知错误')
                    error_code = data.get('infocode', '无错误码')
                    lib.log.error(f"程序初始化-高德IP定位失败: {error_msg} (错误码: {error_code})")
                    return False

    except Exception as e:
        lib.log.error(f"程序初始化-IP定位请求异常: {str(e)}")
        return False

# 获取城市ID
async def get_city_info_by_location() -> tuple[str, str] | bool:
    """
    通过IP定位获取实际城市名和city_id

    Returns:
        tuple[str, str]: (实际城市名, city_id)
        bool: False 失败时返回
    """
    # 获取IP定位结果
    initial_city = await get_ip_location()
    if not initial_city:
        return False

    # 使用定位结果查询和风天气，获取实际城市名和ID
    api_key = lib.decrypt(api['qweather.com']['api_key'])
    city_url = api['qweather.com']['url_city_id']

    params = {'key': api_key, 'location': initial_city, 'lang': 'zh'}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(city_url, params=params) as resp:
                city_data = await resp.json()

        location_list = city_data.get('location', [])
        if not location_list:
            lib.log.warning(f"和风天气未找到匹配的城市: {initial_city}")
            return False

        # 优先选择排名最高的城市
        sorted_locations = sorted(location_list, key=lambda x: int(x.get('rank', '999')))
        best_match = sorted_locations[0]
        actual_city_name = best_match.get('name', initial_city)
        city_id = best_match.get('id', '')

        if city_id:
            return (actual_city_name, city_id)
        else:
            return False

    except Exception as e:
        lib.log.error(f"获取城市信息时异常: {str(e)}")
        return False

# 程序初始化
async def init_app():
    if lib.is_internet():
        try:
            result = await get_city_info_by_location()
            if result:
                actual_city_name, city_id = result
                lib.log.info(f'程序初始化，已定位到城市：{actual_city_name}')
                lib.file.write('Weather', 'city_name', value=actual_city_name)
                lib.file.write('Weather', 'city_id', value=city_id)
                lib.log.info(f'程序初始化-已获取城市ID：{city_id}')
                return [True, actual_city_name]

            else:
                lib.log.error('程序初始化失败：无法获取位置信息或城市ID')
                return False

        except Exception as e:
            lib.log.error(f'程序初始化失败：{str(e)}')
            return False

    else:
        lib.log.warning('程序初始化失败：请检查网络连接')
        return False

# 创建快捷方式
def create_shortcut() -> bool:
    '''
    创建快捷方式并移动到启动文件夹
    :param EXE_PATH: 目标 .exe 文件的完整路径
    '''
    try:
        # 创建快捷方式
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(lib.SHORTCUT_PATH))  # 转换为字符串
        shortcut.Targetpath = str(lib.EXE_PATH)
        shortcut.Arguments = '--startup'
        shortcut.WorkingDirectory = str(lib.MAIN_PATH)  # 设置工作目录
        shortcut.save()
        lib.log.info(f'快捷方式已创建并移动到启动文件夹: {lib.SHORTCUT_PATH}')
        return True
    except Exception as e:
        lib.log.error(f'创建快捷方式失败: {str(e)}')
        return False


# 检查开机启动项是否存在
def is_shortcut_exist() -> bool:
    '''
    检测指定的 .exe 文件是否已经添加到开机启动项
    :param exe_path: 目标 .exe 文件的完整路径
    :param shortcut_name: 快捷方式的名称（不需要 .lnk 后缀）
    :param startup_path: 启动文件夹路径
    :return: 如果存在返回 True，否则返回 False
    '''
    # 检查快捷方式是否存在
    if lib.STARTUP_PATH.exists():
        # 检查快捷方式的目标路径是否与指定的目标路径一致
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(lib.SHORTCUT_PATH))
        if shortcut.Targetpath == str(lib.EXE_PATH):
            lib.log.info(f'快捷方式已存在，且目标路径正确: {lib.SHORTCUT_PATH}')
            return True
        else:
            lib.log.info(f'快捷方式已存在，但目标路径不匹配: {lib.SHORTCUT_PATH}')
            return False
    else:
        lib.log.info(f'快捷方式不存在: {lib.SHORTCUT_PATH}')
        return False

# 删除开机启动项
def remove_shortcut() -> bool:
    '''
    删除开机启动项中的快捷方式
    :param shortcut_name: 快捷方式的名称（不需要 .lnk 后缀）
    :param startup_path: 启动文件夹路径
    '''
    try:
        if lib.SHORTCUT_PATH.exists():
            lib.SHORTCUT_PATH.unlink(missing_ok = True)
            lib.log.info(f'快捷方式已删除: {lib.SHORTCUT_PATH}')
        else:
            lib.log.info(f'快捷方式不存在: {lib.SHORTCUT_PATH}')
        return True
    except Exception as e:
        lib.log.error(f'删除快捷方式时出错: {e}')
        return False
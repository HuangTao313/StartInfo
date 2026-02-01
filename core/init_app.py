from typing import Any
import aiohttp
import asyncio
from win32com.client import Dispatch
from . import ht_lib as lib

# 获取api信息
api = lib.read_json(lib.API_PATH)

# IP定位
async def get_ip_location() -> tuple[Any] | bool | dict[str, bool | str]:
    '''
    使用高德地图 API 自动定位当前公网 IP 所在地

    :param amap_key: 高德地图 Web 服务 API Key
    '''
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    'https://restapi.amap.com/v3/ip',
                    params={'key': lib.decrypt(api['restapi.amap.com']['api_key']), 'output': 'json'}
            ) as resp:
                data = await resp.json()

                if data.get('status') == '1':
                    # 返回城市名称
                    city_name = data.get('city', '未知')
                    return city_name

                else:
                    return False

    except Exception as e:
        return False

# 程序初始化
async def init_app():
    if lib.is_internet():
        try:
            # 使用IP定位并缓存
            city_name = await get_ip_location()  # 假设这是你上面写的异步IP定位函数
            if city_name != False:
                lib.log.info(f'程序初始化，已定位到城市：{city_name}')
                lib.file.write('Weather', 'city_name', value=city_name)

                # 获取city_id并缓存
                api_key = lib.decrypt(api['qweather.com']['api_key'])
                city_url = api['qweather.com']['url_city_id']

                # 使用 params 参数（自动处理 URL 编码）
                params = {
                    'key': api_key,
                    'location': city_name,
                    'lang': 'zh'
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(city_url, params=params) as resp:
                        city_data = await resp.json()

                # 提取 city_id
                city_id = city_data.get('location', [{}])[0].get('id', '')
                lib.file.write('Weather', 'city_id', value=city_id)
                lib.log.info(f'已获取城市ID：{city_id}')
                return [True,city_name]

            else:
                lib.log.error('程序初始化失败：无法获取位置信息')
                return False

        except Exception as e:
            lib.log.error(f'程序初始化失败：{str(e)}')
            return False
    else:
        lib.log.warning('程序初始化失败：请检查网络连接')
        return False

# 初始化/修复缓存文件
# Options = ['first_open', 'reset_times', 'reset_times_date', 'city_name', 'city_id', 'date']
# Data = ['times','holiday_solar','text']
# def repair_cache(args = None) -> None:
#     # 初始化Options
#     Options = ['first_open', 'reset_times', 'reset_times_date', 'city_name', 'city_id', 'date']
#     # 初始化Options
#     i = 0
#     while i < 6:
#         lib.write('Options', Options[i])
#         i += 1
#     # 初始化Data
#     Data = ['times','holiday_solar','text']
#     i_2 = 0
#     while i_2 < 3:
#         lib.write('Data', Data[i_2])
#         i_2 += 1
#     # 如果是初始化模式
#     if args == 'new':
#         easter_num = 1
#         data = ['name', 'is_get', 'get_date', 'get_way']
#         easter_name = ['你被骗了', '不听劝', '我全都要']
#
#         while easter_num <= 3:  # 外层循环控制 3 个彩蛋
#             section_name = f'Easter_egg{easter_num}'  # 当前彩蛋的 section 名称
#             name_index = easter_num - 1  # 当前彩蛋名称的索引
#
#             for key in data:  # 内层循环控制每个彩蛋的 4 个字段
#                 if key == 'name':
#                     text = easter_name[name_index]  # 获取对应的彩蛋名称
#                 elif key == 'is_get':
#                     text = 'False'
#                 elif key == 'get_date':
#                     text = '未获得'
#                 elif key == 'get_way':
#                     text = '？？？'
#                 else:
#                     text = ''  # 对于 get_date 和 get_way，写入空字符串
#                 lib.write(section_name, key, text)  # 调用 write 函数写入配置
#
#             easter_num += 1  # 外层循环计数加 1

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
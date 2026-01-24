import datetime
import os
import ybc_box as box
import sys
import time
import random
import asyncio
import subprocess
import zipfile
import aiohttp
from pathlib import Path
import shutil
import lib
import init_app
import get_data
import ui

# 初始化日志管理器
log = lib.log
# 初始化文件读写
file = lib.file
# 当前日期
date = int(time.strftime("%Y%m%d", time.localtime()))
if file.read('Data', 'other', 'get_date') != date:
    # 次数重置
    file.write('General', 'data_reset_times', value=0)

# 彩蛋设置 你被骗了
def easter_egg(type) -> bool | None:
    # 随机获得
    if type == 'random':
        a = random.randint(1, 10)
        if a <= 3:
            # 彩蛋触发
            return True

    # 缓存已获得的彩蛋
    elif type == 'cache':
        date = datetime.datetime.now().strftime("%Y年%m月%d日")
        file.write('Easter_egg', 'is_get', value=True)
        file.write('Easter_egg', 'get_date', value=date)

# 启动主程序main.exe
def start_main() -> None:
    try:
        os.startfile(lib.EXE_PATH)
        log.info('设置-已启动主程序')

    except Exception as e:
        error_text = f'启动主程序失败：{str(e)}'
        log.error(error_text)
        ui.error_dialog(error_text)

# async def check_update() -> bool:
#     """
#     异步下载 JSON 文件并保存到指定路径
#
#     :param url: JSON 文件的 URL
#     :param save_path: 保存的本地路径 (Path 对象)
#     :return: 是否成功
#     """
#     # 确保父目录存在
#     VERSION_PATH = lib.MAIN_PATH / 'data'
#     VERSION_FILE_PATH = VERSION_PATH / 'version.json'
#
#     try:
#         # 双重解密URL - 添加错误处理
#         api_data = lib.read_json(lib.API_PATH)
#         if 'check_update_url' not in api_data:
#             log.error("API配置中缺少check_update_url字段")
#             return False
#
#         url = lib.decrypt(lib.read_json(lib.API_PATH)['check_update_url'])
#     except Exception as e:
#         log.error(f"解密更新URL失败: {e}")
#         return False
#
#     # 创建目录
#     try:
#         VERSION_PATH.mkdir(parents=True, exist_ok=True)
#     except Exception as e:
#         log.error(f"创建版本目录失败: {e}")
#         return False
#
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
#                 response.raise_for_status()
#
#                 # 直接以二进制模式写入（保留原始内容）
#                 with open(VERSION_FILE_PATH, 'wb') as f:
#                     async for chunk in response.content.iter_chunked(8192):
#                         f.write(chunk)
#
#         log.info(f"JSON 已保存到: {VERSION_FILE_PATH}")
#         return True
#
#     except (aiohttp.ClientError, asyncio.TimeoutError) as e:
#         error_msg = f"检查更新失败: {e}"
#         log.error(error_msg)
#         print(error_msg)
#         return False
#     except IOError as e:
#         error_msg = f"文件写入失败: {e}"
#         log.error(error_msg)
#         print(error_msg)
#         return False
#     except Exception as e:
#         error_msg = f"检查更新过程中发生未知错误: {e}"
#         log.error(error_msg)
#         print(error_msg)
#         return False


# 主程序
def main():
    while True:
        # 检测是否已经添加到开机启动项
        if not init_app.is_shortcut_exist():
            # 如果不存在，则创建快捷方式
            state = '未添加到开机启动项'
            a = '添加到开机启动项'
        else:
            # 如果存在，可以选择删除
            state = '已添加到开机启动项'
            a = '删除从开机启动项'
        message = \
            f'''    {lib.TITLE}
    
        当前状态:{state}
    
        (∩^o^)⊃━☆ﾟ.*･｡
    
        主程序路径:
        {lib.EXE_PATH}'''
        choices = [a, '打开开机启动项文件夹', '启动主程序', '导入模版', '模板列表', '重新定位并更新天气数据',
                 '关于', '卸载', '关闭']
        # 彩蛋设置 你被骗了
        if not file.read('Easter_egg', 'is_get'):
            # 如果成功触发
            if easter_egg('random'):
                choices.insert(-1, '诶，这是什么？')
                log.info('设置-彩蛋触发')

        # 只要有1个彩蛋被触发过，就启用成就系统
        else:
            choices.insert(-1, '彩蛋列表')

        meum = box.choicebox(message, choices)
        match meum:
            case '添加到开机启动项':
                init_app.create_shortcut()
                log.info('设置-已添加开机启动项')
                ui.dialog(lib.TITLE, '已添加到开机启动项(・ω・)')

            case '打开开机启动项文件夹':
                os.startfile(lib.STARTUP_PATH)
                log.info('设置-已打开开机启动项文件夹')

            case '删除从开机启动项':
                init_app.remove_shortcut()
                log.info('设置-已删除开机启动项')
                ui.dialog(lib.TITLE, '已删除开机启动项(・ω・)')

            # 其他功能
            case '启动主程序':
                start_main()

            case '导入模版':
                file_path = ui.file_dialog("选择模版文件", "", "jinja2模板文件 (*.j2);;文本文件(兼容) (*.txt)")
                if file_path != None:
                    template_path = Path(file_path)
                    # 检查模板文件是否存在
                    if template_path.exists():
                        # 自动创建模版文件夹(如果不存在) - 使用 parents=True 和 exist_ok=True 确保创建所有必要目录
                        lib.TEMPLATE_FOLDER_PATH.mkdir(parents=True, exist_ok=True)

                        # 将用户选择的模板文件复制到模板文件夹
                        new_template_path = lib.TEMPLATE_FOLDER_PATH / template_path.name
                        # 如果模板已经导入，则提示用户
                        if new_template_path.exists():
                            warning_text = f'模版文件{template_path.name}已存在，请勿重复导入'
                            ui.dialog(lib.TITLE, warning_text)
                            log.warning(warning_text)

                        else:
                            # 导入模板
                            try:
                                shutil.copy(template_path, new_template_path)
                                log.info(f'模版文件已导入：{new_template_path}')
                                # 询问用户是否立即启用模版
                                if ui.dialog(lib.TITLE, f'已导入模板{template_path.name}，是否立即启用？', ['是', '否']):
                                    file.write('General', 'template_file', value=template_path.name)
                                    # 尝试启动主程序
                                    start_main()

                            except Exception as e:
                                log.error(f'导入模版文件失败：{e}')
                                ui.dialog(lib.TITLE, f'导入模板失败：{str(e)}')
                else:
                    log.info('用户取消了文件选择或选择的文件不存在')
                    ui.dialog(lib.TITLE, '请选择jinja2模板文件(*.j2)')

            case '模板列表':
                template_files = [p.name for p in lib.TEMPLATE_FOLDER_PATH.glob("*.j2") if p.is_file()]
                template_now = file.read('General', 'template_file')
                choice = box.choicebox(f'请选择模板文件：\n当前模板文件：{template_now}', template_files)
                if choice != None and choice != template_now:
                    file.write('General', 'template_file', value=choice)
                    log.info(f'设置-已切换模版文件：{choice}')
                    if ui.dialog(lib.TITLE, f'已选择切换文件：{choice}\n是否立即启动主程序？', ['是','否']):
                       start_main()

            case '重新定位并更新天气数据':
                # 安全读取次数，处理可能的解密失败
                stored_data = file.read('General', 'data_reset_times')
                try:
                    if stored_data:
                        times = int(lib.decrypt(stored_data))
                    else:
                        times = 0  # 默认值
                except (ValueError, TypeError):
                    log.warning('解密次数数据失败，使用默认值6')
                    times = 6

                if times <= 5:
                    city_name = asyncio.run(init_app.init_app())
                    if city_name and True in city_name:
                        weather_air = asyncio.run(get_data.get_weather_air_quality())
                        if weather_air:
                            file.update('Data', 'weather', update_dict=weather_air)
                            log.info(f'设置-已重新定位到：{city_name[1]}并更新天气数据')
                            yn = ui.dialog(lib.TITLE,f'已重新进行IP定位：{city_name[1]}\n是否立即重启主程序？\n(｡・ω・｡)',['是','否'])
                            if yn:
                                os.startfile(lib.EXE_PATH)
                        else:
                            log.error('设置-获取天气数据失败')
                            ui.dialog(lib.TITLE, '天气数据获取失败╥﹏╥...\n请检查网络连接')
                    else:
                        log.error('设置-重新定位失败')
                        ui.dialog(lib.TITLE, '定位失败╥﹏╥...\n请检查网络连接并重新运行程序')
                else:
                    log.warning('设置-已超出每日重新定位次数')
                    ui.dialog(lib.TITLE, '再玩就坏了！\n(／‵Д′)／~ ╧╧')

                # 次数自增1（使用加密存储）
                try:
                    file.write('General', 'data_reset_times', value=lib.encrypt(str(times + 1)))
                except Exception as e:
                    log.error(f'写入重置次数数据失败: {e}')

            case '关于':
                text = lib.CHANGELOG_PATH.read_text(encoding='utf-8')
                yn = ui.dialog(lib.TITLE, text, ['确认', '检查更新(开发中)'])
                if not yn:
                    pass

            case '卸载':
                if lib.UNINS_PATH.exists():
                    log.info('设置-已打开卸载程序')
                    os.startfile(lib.UNINS_PATH)
                else:
                    log.error('设置-未找到卸载程序')
                    ui.error_dialog('未找到卸载程序')
            # 彩蛋
            case '诶，这是什么？':
                # 检测联网状态
                if lib.is_internet():
                    os.startfile(
                        'https://www.bilibili.com/video/BV1GJ411x7h7/?share_source=copy_web&vd_source=38def69ab42f952f952de6d2c41c54bd')
                    time.sleep(2)
                    easter_egg('cache')
                    log.info('设置-用户已触发彩蛋')
                    ui.dialog(lib.TITLE,f'达成成就：你被骗了\n(成功触发《Never Gonna Give You Up》彩蛋)\n⁽⁽٩(๑˃̶͈̀ ᗨ ˂̶͈́)۶⁾⁾',['我真厉害'])
                else:
                    log.warning('设置-彩蛋-未联网')
                    ui.dialog(lib.TITLE, '这里什么都没有\n⁽⁽٩(๑˃̶͈̀ ᗨ ˂̶͈́)۶⁾',['真的什么都没有吗？'])

            case '彩蛋列表':
                easters_text = \
    f'''彩蛋：{file.read('Easter_egg', 'name')}
    获取日期：{file.read('Easter_egg', 'get_date')}'''
                log.info('设置-已打开彩蛋信息')
                ui.dialog(lib.TITLE, easters_text)

            case '关闭' | None:
                log.info('设置-已关闭程序')
                ui.app_manager.quit()
                sys.exit()

# 下载文件
# def download_file(url: str, file_name: str) -> bool:
#     """使用aria2下载文件（带断点续传）"""
#     # 检测下载缓存文件夹是否存在
#     if not lib.DOWNLOAD_PATH.exists():
#         lib.DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
#     # 检测Aria2可执行文件是否存在
#     if not lib.ARIA2_PATH.exists():
#         log.error(f"Aria2可执行文件不存在: {lib.ARIA2_PATH}")
#         return False
#
#     max_connections = '4'
#     cmd = [
#         str(lib.ARIA2_PATH),
#         '-d', str(lib.DOWNLOAD_PATH),
#         '-o', file_name,
#         '-x', max_connections,
#         '-s', max_connections,
#         '-k', '1M',
#         url
#     ]
#
#     try:
#         log.info(f'下载器-开始下载: {url} -> {file_name}')
#         subprocess.run(cmd, check=True, text=True, capture_output=True)
#         log.info(f'下载器-下载完成: {file_name}')
#         return True
#     except subprocess.CalledProcessError as e:
#         log.error(f'下载失败 (退出码 {e.returncode}): {e.stderr.strip() or e.stdout.strip()}')
#         return False
#     except Exception as e:
#         log.error(f'下载过程中发生异常: {str(e)}')
#         return False
#
#
# def unzip_file(zip_path: str, extract_to: str) -> bool:
#     """解压ZIP文件到指定目录（支持中文文件名 - 关键修复！）"""
#     os.makedirs(extract_to, exist_ok=True)
#     try:
#         # 重要：移除 encoding 参数！
#         with zipfile.ZipFile(zip_path, 'r') as zip_ref:
#             # 遍历文件列表并修复中文文件名
#             for file in zip_ref.namelist():
#                 # 关键修复：处理中文文件名
#                 try:
#                     # 将文件名从CP437编码转换为GBK（Windows系统默认编码）
#                     fixed_name = file.encode('cp437').decode('gbk', errors='replace')
#                 except Exception as e:
#                     # 备用方案：尝试UTF-8
#                     try:
#                         fixed_name = file.encode('cp437').decode('utf-8', errors='replace')
#                     except:
#                         fixed_name = file  # 无法转换则保留原始名称
#
#                 # 构建目标路径
#                 target_path = os.path.join(extract_to, fixed_name)
#                 os.makedirs(os.path.dirname(target_path), exist_ok=True)
#
#                 # 跳过目录条目（以'/'结尾）
#                 if file.endswith('/'):
#                     continue
#
#                 # 解压文件
#                 with zip_ref.open(file) as source, open(target_path, 'wb') as target:
#                     target.write(source.read())
#
#             log.info(f" 解压成功! 共 {len(zip_ref.namelist())} 个文件解压到: {extract_to}")
#             return True
#     except Exception as e:
#         log.error(f"解压失败: {str(e)}")
#         return False

if __name__ == "__main__":
    try:
        # 初始化UI
        app = ui.app_manager.init_app()
        # 弹出主窗口
        main()
        ui.app_manager.quit()
    except Exception as e:
        log.error(str(e))
        ui.error_dialog(str(e))
        ui.app_manager.quit()
        sys.exit()
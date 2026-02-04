import datetime
import os
import ybc_box as box
import sys
import time
import random
import asyncio
from pathlib import Path
import shutil
import core.ht_lib as lib
import core.init_app as init_app
import core.get_data as get_data
import core.ui as ui

# 显示导入
import deps

# 初始化日志管理器

log = lib.log
# 初始化文件读写
file = lib.file
# 更新器路径
UPDATER_PATH = lib.MAIN_PATH / 'updater.exe'

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
        log.error(f'设置{error_text}')
        ui.error_dialog(error_text)
    sys.exit()




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
f'''{lib.TITLE}

当前状态:{state}

(∩^o^)⊃━☆ﾟ.*･｡'''
        choices = [a, '打开开机启动项文件夹', '启动主程序', '导入模版', '模板列表', '打开模板文件夹', '打开模板自定义文档', '重新定位并更新天气数据',
                 '删除下载缓存', '关于', '卸载', '关闭']
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
                ui.dialog(lib.TITLE,  '已添加到开机启动项(・ω・)')

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
                template_file_path: Path = ui.file_dialog("选择模版文件", "", "jinja2模板文件 (*.j2)")
                # 如果文件路径不为空
                if template_file_path is not None:
                    # 尝试导入模板
                    is_success, text = lib.import_template(template_file_path)
                    # 如果导入成功
                    if is_success:
                        # 询问用户是否立即激活模版
                        if ui.dialog(lib.TITLE, f'已成功导入模板：{template_file_path.name}，是否立即启用？', ['是', '否']):
                            is_activate_success, text = lib.activate_template(template_file_path)
                            # 判断是否激活成功
                            if is_activate_success:
                                ui.dialog(lib.TITLE, text)
                            else:
                                ui.error_dialog(text)

                # 如果文件路径为空
                else:
                    log.info('设置-用户取消了文件选择或选择的文件不存在')
                    ui.dialog(lib.TITLE, '请选择jinja2模板文件(*.j2)')

            case '模板列表':
                template_files = [p.name for p in lib.TEMPLATE_FOLDER_PATH.glob("*.j2") if p.is_file()]
                template_now = file.read('General', 'template_file')
                choice = box.choicebox(f'请选择模板文件：\n当前模板文件：{template_now}', template_files)
                if choice is not None and choice != template_now:
                    is_success, text = lib.activate_template(choice)
                    # 如果成功启用
                    if is_success:
                        # 询问用户是否立即启动主程序
                        if ui.dialog(lib.TITLE, f'{text}\n是否立即启动主程序？', ['是','否']):
                           start_main()

                    else:
                        ui.error_dialog(text)

            case '打开模板文件夹':
                try:
                    os.startfile(lib.TEMPLATE_FOLDER_PATH)

                except Exception as e:
                    error_text = f'打开模板文件夹失败：{str(e)}'
                    log.error(f'设置{error_text}')
                    ui.error_dialog(error_text)

            case '打开模板自定义文档':
                try:
                    os.startfile(str(lib.TEMPLATE_FOLDER_PATH / '自定义模板文档.md'))

                except Exception as e:
                    error_text = f'打开模板自定义文档失败：{str(e)}'
                    log.error(f'设置{error_text}')
                    ui.error_dialog(error_text)

            case '重新定位并更新天气数据':
                # 安全读取次数，处理可能的解密失败
                stored_data = file.read('General', 'data_reset_times')
                try:
                    if stored_data:
                        times = int(lib.decrypt(stored_data))
                    else:
                        times = 0  # 默认值
                except (ValueError, TypeError):
                    log.warning('设置-解密次数数据失败，使用默认值6')
                    times = 6

                if times <= 5:
                    city_name : list = asyncio.run(init_app.init_app())
                    if True in city_name:
                        weather_air = asyncio.run(get_data.get_weather_air_quality())
                        if isinstance(weather_air, dict):
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
                    log.error(f'设置-写入重置次数数据失败: {e}')

            case '删除下载缓存':
                # 检查下载缓存文件夹是否存在
                if lib.DOWNLOAD_PATH.exists():
                    # 尝试删除
                    try:
                        shutil.rmtree(lib.DOWNLOAD_PATH)
                        ui.dialog(lib.TITLE, '已删除下载缓存')

                    except Exception as e:
                        error_text = f'删除下载缓存失败: {str(e)}'
                        log.error(f'设置{error_text}')
                        ui.error_dialog(error_text)

                else:
                    log.info('设置-未发现下载缓存')
                    ui.dialog(lib.TITLE, '未发现下载缓存')

            case '关于':
                text = f'发布日期：{lib.CURRENT_VERSION_JSON.get('release_date','获取发布日期失败')}\n{lib.CURRENT_VERSION_JSON.get('changelog','更新日志获取失败')}'
                yn = ui.dialog(lib.TITLE, text, ['确认', '检查更新'])
                if not yn:
                    # 检查更新器是否存在
                    if UPDATER_PATH.exists():
                        try:
                            os.startfile(UPDATER_PATH)
                            ui.app_manager.quit()
                            sys.exit()

                        except Exception as e:
                            log.error(f'设置-打开更新程序失败: {e}')
                            ui.error_dialog(str(e))

                    else:
                        log.error('设置-未找到更新程序')
                        ui.error_dialog('未找到更新程序')

            case '卸载':
                if lib.UNINS_PATH.exists():
                    log.info('设置-已打开卸载程序')
                    os.startfile(lib.UNINS_PATH)
                    sys.exit()
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

if __name__ == "__main__":
    try:
        # 初始化UI
        ui.app_manager.init_app()
        # 弹出主窗口
        main()
        app.quit()
        ui.app_manager.quit()

    except Exception as e:
        log.error(f'设置-{str(e)}')
        ui.error_dialog(str(e))
        ui.app_manager.quit()
        sys.exit()
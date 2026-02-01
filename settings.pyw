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
        log.error(error_text)
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
                file_path = ui.file_dialog("选择模版文件", "", "jinja2模板文件 (*.j2)")
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
                    log.error(f'写入重置次数数据失败: {e}')

            case '关于':
                text = lib.CURRENT_VERSION_JSON.get('changelog','更新日志获取失败')
                yn = ui.dialog(lib.TITLE, text, ['确认', '检查更新'])
                if not yn:
                    # 检查更新器是否存在
                    if UPDATER_PATH.exists():
                        try:
                            os.startfile(UPDATER_PATH)

                        except Exception as e:
                            log.error(f'打开更新程序失败: {e}')
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
        log.error(str(e))
        ui.error_dialog(str(e))
        ui.app_manager.quit()
        sys.exit()
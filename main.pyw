import os
import time
import sys
import asyncio
import subprocess
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import core.ht_lib as lib
import core.init_app as init_app
import core.get_data as get_data
import core.ui as ui

# 显式导入
import deps

# 获取启动参数
args = sys.argv
# 初始化日志管理器
log = lib.log
# 初始化文件读写
file = lib.file

# 加载模板
def load_template(data: dict[str, str]) -> str | None:
    """加载并渲染模板（支持默认模板回退）"""
    env = Environment(loader=FileSystemLoader(str(lib.TEMPLATE_FOLDER_PATH)))
    templates_to_try = [lib.TEMPLATE_PATH.name, 'default.j2']

    for template_name in templates_to_try:
        try:
            template = env.get_template(template_name)
            result = template.render(**data)

            log.info(f'主程序-已加载模版：{template_name}')
            return result

        except Exception as e:
            # 如果是主模板加载失败，显示错误对话框
            if template_name == lib.TEMPLATE_PATH.name:
                yn = ui.dialog(
                    f'程序运行时发生错误╥﹏╥...',
                    f'未找到模版文件：{lib.TEMPLATE_PATH.name}\n请检查模版文件是否存在！',

                    ['加载默认模板', '打开模板文件夹']
                )
                if yn:
                    lib.activate_template('default.j2')
                if not yn:
                    os.startfile(lib.TEMPLATE_FOLDER_PATH)
                    app.quit()
                    sys.exit()
            # 如果是默认模板也加载失败，弹窗报错并记录日志
            elif template_name == 'default.j2':
                error_text = f'默认模板加载失败：{str(e)}'
                log.error(f'主程序-{error_text}')
                ui.error_dialog(error_text)
                app.quit()
                sys.exit()

    return f'模板加载失败：找不到可用模板'

# 程序初始化
def init():
    # 检查网络连接情况
    if lib.is_internet():
        log.info('主程序-检测到第一次启动，开始执行程序初始化')
        if asyncio.run(init_app.init_app()):
            file.write('General', 'is_first_startup', value=False)
            log.info('主程序-程序初始化完成')

        # 检查开机启动项是否存在
        if not init_app.is_shortcut_exist():
            if ui.dialog(lib.TITLE, '检测到第一次启动，是否将程序添加到开机启动项(・ω・)', ['是', '否']):
                init_app.create_shortcut()
                log.info('主程序-用户已添加开机启动项')
    else:
        ui.dialog(lib.TITLE, '未检测到网络连接，请检查网络连接并重新启动程序！\n╥﹏╥...')
        log.warning('主程序-程序初始化失败：当前未联网')

# 处理模板
def handle_j2_template(j2_file_path: Path):
    """处理 .j2 模板文件的逻辑"""
    # 提示用户选择操作
    user_choice = ui.dialog(
        lib.TITLE,
        f'检测到jinja2模板文件：{j2_file_path.name}，请选择对该模板文件的操作：',
        ['导入模板', '编辑模板']
    )

    # 编辑模板
    if not user_choice:
        log.info('(主程序-启动模式：编辑模板文件)')
        # 尝试使用VsCode打开模板文件
        try:
            import shutil
            # 1. 查找 VS Code 的真实路径
            vsc_path = shutil.which('code') or shutil.which('code.cmd')

            if vsc_path:
                # 2. 使用找到的绝对路径执行（关键！）
                subprocess.run([vsc_path, str(j2_file_path)], check=True)
                log.info(f'主程序-已使用 VSCode 打开模板文件：{j2_file_path}')
            else:
                raise FileNotFoundError("VS Code 未安装或未添加到系统 PATH")

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            log.error(f"主程序-无法使用 VSCode 打开模板文件: {e}")
            # 回退到记事本（可选）
            try:
                subprocess.run(['notepad.exe', str(j2_file_path)], check=True)
                log.info(f'主程序-已使用记事本打开模板文件：{j2_file_path}')
            except Exception as fallback_e:
                log.error(f'主程序-回退到记事本也失败了: {fallback_e}')
                ui.error_dialog(f'无法打开模板文件，请手动编辑：{j2_file_path}')

        # 关闭程序
        ui.app_manager.quit()
        sys.exit()

    # 导入模板
    is_success, result_message = lib.import_template(j2_file_path)
    if not is_success:
        log.error(f"主程序-模板导入失败：{result_message}")
        ui.error_dialog(result_message)
        return

    # 询问是否立即激活模板
    activate_choice = ui.dialog(
        lib.TITLE,
        f'已成功导入模板：{j2_file_path.name}，是否立即启用？',
        ['是', '否']
    )

    if not activate_choice:
        # 用户选择不立即启用
        ui.app_manager.quit()
        sys.exit()

    # 用户选择立即启用
    is_activate_success, activate_result = lib.activate_template(j2_file_path)
    # 如果启用失败
    if not is_activate_success:
        log.error(f"主程序-启用模板失败：{activate_result}")
        ui.error_dialog(activate_result)

# 程序入口
def main():
    # 获取当前日期
    date = int(time.strftime("%Y%m%d",time.localtime()))
    general_data_get_date = file.read('Data', 'other', 'get_date')
    weather_data_get_time = file.read('Data', 'weather', 'get_time')
    weather_data_get_time = 0 if weather_data_get_time == None else weather_data_get_time
    # 如果一般数据已过期
    if general_data_get_date != date:
        # 次数重置
        lib.times('reset')
        log.info('主程序-启动次数已重置')
        # 如果联网
        if lib.is_internet():
            # 更新所有数据
            data = asyncio.run(get_data.get_all_data())
            # 格式化数据
            jinja2_data = get_data.format_data_to_jinja2(data)
            # 添加开机次数信息
            jinja2_data['startup_times'] = lib.times('read')
            json_data = get_data.format_data_to_json(data)
            # 缓存数据
            if isinstance(json_data, dict):
                file.update('Data',update_dict=json_data)
                # 加载模版
                text = load_template(jinja2_data)
                log.info('(主程序-启动模式：更新所有数据并缓存)')

            else:
                start_mode = f'获取数据失败：\n{json_data}'
                log.error(f'主程序{start_mode}')
                ui.error_dialog(start_mode)
                app.quit()
                sys.exit()

        # 如果未联网
        else:
            startup_times = lib.times('read')
            # 读取缓存
            data = file.read('Data')
            # 格式化数据
            jinja2_data = get_data.format_json_to_jinja2(data)
            # 添加时间信息
            jinja2_data | get_data.get_time()
            # 添加开机次数信息
            jinja2_data['startup_times'] = startup_times
            # 加载模版
            text = load_template(jinja2_data)
            # 次数自增
            lib.times('add')
            log.info(f'(主程序-启动模式：未联网，读取旧数据)')
            log.info(f'主程序-启动次数已自增为{startup_times}次')

    # 如果一般数据未过期
    else:
        timestamp = int(time.time())
        # 如果天气数据过期
        if timestamp - weather_data_get_time > lib.WEATHER_DATA_EXPIRE_TIME:
            # 获取天气数据
            weather_data = asyncio.run(get_data.get_weather_air_quality())
            # 缓存数据
            if isinstance(weather_data, dict):
                file.update('Data', 'weather', update_dict=weather_data)
                start_mode = '(启动模式：更新天气数据并读取其他缓存数据)'

            else:
                start_mode = f'天气数据获取失败：{weather_data}'
                log.error(f'主程序-{start_mode}')
                ui.error_dialog(f'天气数据获取失败：\n{weather_data}')
                app.quit()
                sys.exit()

        else:
            start_mode = '(启动模式：读取缓存数据)'

        # 读取缓存数据
        data = file.read('Data')
        # 格式化数据
        jinja2_data = get_data.format_json_to_jinja2(data)
        # 添加时间信息
        if isinstance(jinja2_data, dict):
            jinja2_data | get_data.get_time()
            # 添加开机次数信息
            jinja2_data['startup_times'] = lib.times('read')
            # 加载模版
            text = load_template(jinja2_data)
            log.info(f'主程序-{start_mode}')
            # 检查是否为开机启动

        else:
            start_mode = f'缓存数据读取失败：\n{jinja2_data}'
            log.error(f'主程序-{start_mode}' )
            ui.error_dialog(start_mode)
            app.quit()
            sys.exit()

        is_auto_start = "--startup" in args
        if is_auto_start:
            # 次数自增
            lib.times('add')
            log.info(f'主程序-启动次数已自增为{lib.times('read')}次')

    # 弹窗
    box = ui.dialog(lib.TITLE,text,['确定','打开设置'])
    if not box:
        os.startfile(lib.SETTINGS_PATH)
        log.info('主程序-用户打开了设置，程序正常结束')
        sys.exit(0)
    else:
        log.info('主程序-用户点击了确定，程序正常结束')
        sys.exit()

if __name__ == '__main__':
    try:
        # 初始化
        app = ui.app_manager.init_app()
        # 禁止多开
        checker = lib.SingleInstance()
        if checker.is_running:
            # 显示提示
            ui.dialog(lib.TITLE, '程序已运行，请勿重复启动！')
            ui.app_manager.quit()
            log.warning('主程序-检测到多开，请勿重复启动')
            sys.exit()

        # 正常启动
        else:
            # 如果是更新后第一次启动
            if '--update' in args:
                ui.dialog(lib.TITLE, f'已成功更新到{lib.VERSION}(・ω・)\n{lib.CURRENT_VERSION_JSON.get('changelog','更新日志获取失败')}')

            # 如果是安装后第一次启动
            elif file.read('General', 'is_first_startup'):
                init()

            # 如果是从jinja2模板文件启动
            else:
                j2_file_path: Path = next(
                    (Path(arg) for arg in sys.argv[1:] if arg.endswith('.j2') and Path(arg).is_file()),
                    None
                )
                if j2_file_path:
                    handle_j2_template(j2_file_path)  # 处理模板文件

            # 启动主函数
            main()

    except Exception as e:
            log.error(f'主程序-程序运行时发生错误：{str(e)}')
            ui.error_dialog(str(e))
            ui.app_manager.quit()
            sys.exit()
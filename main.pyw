import os
import time
import sys
import asyncio
import subprocess

import aiohttp
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from settings import start_settings
from core.config import cfg
import core.ht_lib as lib
import core.init_app as init_app
import core.get_data as get_data
import core.ui as ui

# 获取启动参数
args = sys.argv
# 初始化日志管理器
log = lib.log
# 初始化文件读写
file = lib.file

# 生日信息变量（在 main() 函数内根据启动次数决定是否检测）
birthday_info = False

# 加载模板
def load_template(data: dict[str, str]) -> str | None:
    """加载并渲染模板（支持默认模板回退）"""
    # FileSystemLoader 需要目录路径，而不是文件路径
    env = Environment(loader=FileSystemLoader(str(lib.TEMPLATE_FOLDER_PATH)))

    # 根据是否有生日信息确定尝试加载的模板顺序
    # 从 data 中检查是否有生日信息（birthday_star 字段）
    if data.get('birthday_star'):
        # 有生日信息：优先尝试生日模板，然后是当前激活的模板，最后是默认模板
        templates_to_try = ['birthday_wishes.j2', lib.TEMPLATE_PATH.name, 'default.j2']
    else:
        # 无生日信息：尝试当前激活的模板，然后是默认模板
        templates_to_try = [lib.TEMPLATE_PATH.name, 'default.j2']

    for template_name in templates_to_try:
        try:
            template = env.get_template(template_name)
            result = template.render(**data)

            log.info(f'主程序-已加载模版：{template_name}')
            return result

        except Exception as e:
            # 如果是当前激活的模板加载失败，显示错误对话框
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
                    sys.exit()
            # 如果是生日模板加载失败，记录日志并继续尝试下一个模板
            elif template_name == 'birthday_wishes.j2':
                log.warning(f'主程序-生日模板加载失败：{str(e)}，尝试使用其他模板')
            # 如果是默认模板也加载失败，弹窗报错并记录日志
            elif template_name == 'default.j2':
                error_text = f'默认模板加载失败：{str(e)}'
                log.error(f'主程序-{error_text}')
                ui.error_dialog(error_text)
                sys.exit()

    return f'模板加载失败：找不到可用模板'

# 程序初始化（内部函数，仅在main中调用）
async def _init_internal(session):
    """内部初始化函数，在main的事件循环中执行"""
    # 询问用户是否添加开机启动项
    # 检查开机启动项是否存在
    if not init_app.is_shortcut_exist():
        if ui.dialog(lib.TITLE, '检测到第一次启动，是否将程序添加到开机启动项(・ω・)', ['是', '否']):
            init_app.create_shortcut()
            log.info('主程序-用户已添加开机启动项')

    # 检查网络连接情况
    if lib.is_internet():
        # 开始初始化流程
        log.info('主程序-检测到第一次启动，开始执行程序初始化')

        # IP定位并获取city_id
        if await init_app.init_app(session=session):
            file.write('General', 'is_first_startup', value=False)
            log.info('主程序-程序初始化完成')

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
async def main():
    """异步主函数，使用全局共享的 ClientSession 统一管理事件循环"""
    # 获取当前日期和时间
    date = int(time.strftime("%Y%m%d", time.localtime()))
    timestamp = int(time.time())
    general_data_get_date = file.read('Data', 'other', 'get_date')
    weather_data_get_time_read = file.read('Data', 'weather', 'get_time')
    weather_data_get_time = 0 if weather_data_get_time_read == None else weather_data_get_time_read

    # 预设变量，用于统一渲染
    jinja2_data = None
    start_mode = ""

    # # 使用全局共享的 ClientSession
    async with aiohttp.ClientSession() as session:
        # 如果是安装后第一次启动，执行初始化
        if file.read('General', 'is_first_startup'):
            await _init_internal(session)
        # 如果一般数据已过期
        if general_data_get_date != date:
            # 次数重置
            lib.times('reset')
            log.info('主程序-启动次数已重置')

            # 如果联网
            if lib.is_internet():
                # 更新所有数据
                data = await get_data.get_all_data(session=session)
                # 格式化数据
                jinja2_data = get_data.format_data_to_jinja2(data)

                # 检查数据格式化是否成功
                if isinstance(jinja2_data, bool):
                    start_mode = f'数据格式化失败：数据无效'
                    log.error(f'主程序-{start_mode}')
                    ui.error_dialog(start_mode)
                    sys.exit()

                json_data = get_data.format_data_to_json(data)
                # 缓存数据
                if isinstance(json_data, dict):
                    file.update('Data', update_dict=json_data)
                    start_mode = '(主程序-启动模式：更新所有数据并缓存)'
                else:
                    start_mode = f'获取数据失败：\n{json_data}'
                    log.error(f'主程序{start_mode}')
                    ui.error_dialog(start_mode)
                    sys.exit()

            # 如果未联网
            else:
                # 读取缓存
                data = file.read('Data')
                # 格式化数据
                jinja2_data = get_data.format_json_to_jinja2(data)
                start_mode = '(主程序-启动模式：未联网，读取旧数据)'

        # 如果一般数据未过期
        else:
            start_mode = '(主程序-启动模式：读取缓存数据)'

            # 如果天气数据过期
            if timestamp - weather_data_get_time > lib.WEATHER_DATA_EXPIRE_TIME:
                # 获取天气数据
                weather_data = await get_data.get_weather_air_quality(session=session)
                # 缓存数据
                if isinstance(weather_data, dict):
                    file.update('Data', 'weather', update_dict=weather_data)
                    start_mode = '(启动模式：更新天气数据并读取其他缓存数据)'
                else:
                    log.error(f'主程序-天气数据获取失败：{weather_data}，将使用缓存数据')
                    start_mode = '(启动模式：天气数据获取失败，读取缓存数据)'

            # 如果用户启用了MC服务器玩家信息检测，检查MC服务器数据是否过期
            if cfg.minecraft_server_checker_switch.value:
                mc_server_data_get_time_read = file.read('Data', 'minecraft_server_data', 'get_time')
                mc_server_data_get_time = 0 if mc_server_data_get_time_read in (None, '', '未知') else int(mc_server_data_get_time_read)
                if timestamp - mc_server_data_get_time >= cfg.minecraft_server_data_refresh_interval.value:
                    # 获取MC服务器信息
                    mc_server_data = await get_data.get_mc_server_status()
                    # 缓存数据
                    if isinstance(mc_server_data, dict):
                        mc_server_data['get_time'] = int(time.time())
                        file.update('Data', 'minecraft_server_data', update_dict=mc_server_data)
                        log.info('主程序-已更新MC服务器数据缓存')
                    else:
                        log.error(f'主程序-获取MC服务器数据失败：{mc_server_data}，将使用缓存数据')

            # 读取缓存数据
            data = file.read('Data')
            # 格式化数据
            jinja2_data = get_data.format_json_to_jinja2(data)

        # ======================================================
        # ✨ 统一补充区：这里处理所有分支都要干的事情
        # ======================================================
        if isinstance(jinja2_data, dict):
            # 添加时间信息
            time_info = get_data.get_time()
            if isinstance(time_info, dict):
                jinja2_data.update(time_info)

            # 添加开机次数信息
            startup_times = lib.times('read')
            jinja2_data['startup_times'] = startup_times

            # 添加生日信息（只在当天第 1 次启动时检测）
            last_birthday_date = file.read('General', 'last_birthday_date') or ''
            today_date = time.strftime("%Y%m%d", time.localtime())

            # 如果今天还没显示过生日祝福
            if last_birthday_date != today_date:
                birthday_info = get_data.check_birthday()
                if birthday_info is not False:
                    jinja2_data.update(birthday_info)
                    # 记录今天已显示过
                    file.write('General', 'last_birthday_date', value=today_date)
            else:
                birthday_info = False  # 今天已显示过，不再检测

            # 添加倒数日信息
            jinja2_data.update(get_data.get_countdown_day())

            # 添加自定义信息开关
            info_switchs = get_data.get_custom_info_switch()
            jinja2_data.update(info_switchs)

            # 加载模版
            text = load_template(jinja2_data)
            log.info(f'主程序-{start_mode}')

            # 检查是否为开机启动（处理次数自增）
            is_auto_start = "--startup" in args
            # 如果是自启动或者日期变更后的第一次启动
            if is_auto_start or general_data_get_date != date:
                # 次数自增
                lib.times('add')
                log.info(f'主程序-启动次数已自增为{lib.times("read")}次')
        else:
            # 数据异常处理
            error_msg = text = f'数据处理失败：{jinja2_data}'
            log.error(f'主程序-{error_msg}')
            ui.error_dialog(error_msg)
            sys.exit()

        # 自动关闭模式
        auto_close_mode = cfg.auto_close_time.value if cfg.auto_close_switch.value else False

        # 弹窗
        box = ui.main_window(text,auto_close_mode)

        if box == False:
            log.info('主程序-用户打开了设置')
            start_settings()
        else:
            log.info('主程序-用户点击了确定，程序正常结束')
            sys.exit()
                
if __name__ == '__main__':
    # try:
        # 初始化
        ui.app_manager.init_app()
        # 使用共享事件循环
        loop = asyncio.get_event_loop()
        asyncio.set_event_loop(loop)

        # 禁止多开
        checker = lib.SingleInstance(name='Local\\StartInfo-main')
        if checker.is_running:
            # 显示提示
            ui.dialog(lib.TITLE, '程序已运行，请勿重复启动！')
            log.warning('主程序-检测到多开，请勿重复启动')
            sys.exit()

        # 检测是否带有启动参数(args列表的长度≥1)
        if len(args) >= 1:
            # 如果是更新后第一次启动
            if '--update' in args:
                ui.dialog(lib.TITLE, f'已成功更新到{lib.VERSION}(・ω・)\n{lib.CURRENT_VERSION_JSON.get('changelog', '更新日志获取失败')}')
                from settings import delete_download_cache
                # 删除下载缓存
                delete_download_cache()

            # 如果是以--settings参数启动
            elif '--settings' in args:
                # 启动设置
                start_settings()

            # 如果是以--updater参数启动
            elif '--updater' in args:
                from core.updater import start_updater
                # 启动更新器
                start_updater()

            # 如果是从jinja2模板文件启动
            else:
                j2_file_path: Path = next(
                    (Path(arg) for arg in sys.argv[1:] if arg.endswith('.j2') and Path(arg).is_file()),
                    None
                )
                if j2_file_path:
                    handle_j2_template(j2_file_path)  # 处理模板文件

        # 预先保存 qasync loop 引用，用于手动清理
        qasync_loop = asyncio.get_event_loop()

        # 使用原生 asyncio 事件循环运行主函数（aiohttp 兼容性最佳）
        try:
            asyncio.run(main())
        except SystemExit:
            # main() 内调用了 sys.exit()（用户点击确定 / 异常退出）
            # 先关闭 qasync 事件循环，避免 shutdown 时 "Signal source has been deleted" 警告
            qasync_loop.close()
            raise

        # main() 正常返回后（设置窗口等已在内部自行管理事件循环），直接退出
        sys.exit(0)

    # except Exception as e:
    #         log.error(f'主程序-程序运行时发生错误：{str(e)}')
    #         ui.error_dialog(str(e))

    # finally:
    #     # 程序退出前清理资源
    #     try:
    #         # 检查是否有正在运行的事件循环
    #         try:
    #             loop = asyncio.get_running_loop()
    #         except RuntimeError:
    #             # 没有正在运行的事件循环，创建一个
    #             loop = asyncio.new_event_loop()
    #             asyncio.set_event_loop(loop)
    #             loop_created = True
    #         else:
    #             loop_created = False
    #
    #         # 在现有的事件循环中关闭session
    #         if lib.async_session._initialized and lib.async_session._session:
    #             loop.run_until_complete(lib.async_session.close())
    #             log.info('主程序-已关闭全局共享的 ClientSession')
    #
    #         # 如果是我们创建的循环，关闭它
    #         if loop_created:
    #             loop.close()
    #     except Exception as e:
    #         log.error(f'主程序-清理资源时发生错误：{e}')
    #
    #     sys.exit()
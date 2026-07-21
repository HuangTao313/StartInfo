import os
import sys
import asyncio
import subprocess
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from core.ht_lib import log
import core.init_app as init_app
import core.ui as ui
from core.widgets import *
from settings import start_settings

# 加载模板
def load_template(data: dict[str, str]) -> str | None:
    '''加载并渲染模板（支持默认模板回退）'''
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

def init():
    '''程序初始化'''
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
        if init_app.init_app():
            file.write('General', 'is_first_startup', value=False)
            log.info('主程序-程序初始化完成')

        else:
            ui.dialog(lib.TITLE, '未检测到网络连接，请检查网络连接并重新启动程序！\n╥﹏╥...')
            log.warning('主程序-程序初始化失败：当前未联网')

def handle_j2_template(j2_file_path: Path):
    '''处理 .j2 模板文件的逻辑'''
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
                raise FileNotFoundError('VS Code 未安装或未添加到系统 PATH')

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            log.error(f'主程序-无法使用 VSCode 打开模板文件: {e}')
            # 回退到记事本（可选）
            try:
                subprocess.run(['notepad.exe', str(j2_file_path)], check=True)
                log.info(f'主程序-已使用记事本打开模板文件：{j2_file_path}')
            except Exception as fallback_e:
                log.error(f'主程序-回退到记事'
                          f'本也失败了: {fallback_e}')
                ui.error_dialog(f'无法打开模板文件，请手动编辑：{j2_file_path}')

        # 关闭程序
        sys.exit()

    # 导入模板
    is_success, result_message = lib.import_template(j2_file_path)
    if not is_success:
        log.error(f'主程序-模板导入失败：{result_message}')
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
        log.error(f'主程序-启用模板失败：{activate_result}')
        ui.error_dialog(activate_result)

async def main():
    '''程序主函数'''
    # 创建所有已启用的组件实例
    component_config = [
        (cfg.datetime_switch, DateTimeWidget),
        (cfg.countdown_switch, CountDownDayWidget),
        (cfg.birthday_wishes_switch, BirthdayWidget),
        (cfg.greeting_switch, GreetingWidget),
        (cfg.startup_times_switch, StartupTimesWidget),
        (cfg.weather_switch, WeatherWidget),
        (cfg.air_quality_switch, AirQualityWidget),
        (cfg.historical_switch, TodayInHistoryWidget),
        (cfg.holiday_solar_term_switch, HolidayAndSolarTermWidget),
        (cfg.words_switch, EveryDayWordsWidget),
        (cfg.minecraft_server_checker_switch, MCServerStatusWidget)
    ]

    active = []
    for switch, cls in component_config:
        if switch.value:
            active.append(cls())

    results = {}
    # ── 联网组件并发，本地组件同步 ──
    async_tasks, sync_widgets = [], []
    for widget in active:
        if isinstance(widget, NetworkWidgetBase):
            async_tasks.append(widget.get_data_async())

        else:
            sync_widgets.append(widget)

    # ── 并发获取 ──
    if async_tasks:
        async_values = await asyncio.gather(*async_tasks, return_exceptions=True)
        net_widgets = [w for w in active if isinstance(w, NetworkWidgetBase)]
        for comp, val in zip(net_widgets, async_values):
            if isinstance(val, Exception):
                log.error(f'{comp.WIDGET_NAME} 获取失败: {val}')
            elif val is not None:
                results[comp.WIDGET_NAME] = val

    # ── 同步获取 ──
    for comp in sync_widgets:
        try:
            data = comp.get_data()
            if data is not None:
                results[comp.WIDGET_NAME] = data

        except Exception as e:
            log.error(f'{comp.WIDGET_NAME} 获取失败: {e}')

    # ── 聚合为 Jinja2 字典 ──
    jinja2_data = {}
    for data in results.values():
        if isinstance(data, dict):
            jinja2_data.update(data)

    # ── 生日已显示过 → 移除生日字段，不走生日模板 ──
    last_birthday_date = lib.file.read('General', 'last_birthday_date') or ''
    today_str = time.strftime('%Y%m%d', time.localtime())
    if last_birthday_date == today_str:
        jinja2_data.pop('birthday_star', None)
        jinja2_data.pop('age', None)
        jinja2_data.pop('life_days', None)

    # ── 注入开关状态 ──
    switch_keys = {
        'greeting_switch': cfg.greeting_switch.value,
        'startup_times_switch': cfg.startup_times_switch.value,
        'datetime_switch': cfg.datetime_switch.value,
        'countdown_switch': cfg.countdown_switch.value,
        'weather_switch': cfg.weather_switch.value,
        'historical_switch': cfg.historical_switch.value,
        'words_switch': cfg.words_switch.value,
        'mc_server_check_switch': cfg.minecraft_server_checker_switch.value,
    }

    jinja2_data.update(switch_keys)
    jinja2_data['is_all_off'] = not any(switch_keys.values())

    # ── 判断生日是否已显示（弹窗前记录，弹窗后标记） ──
    birthday_data = results.get('Birthday')
    birthday_shown = birthday_data and birthday_data.get('birthday_star')

    # ── 渲染模板 → 弹窗 ──
    text = load_template(jinja2_data)
    log.info('主程序-数据加载完成')

    auto_close_mode = cfg.auto_close_time.value if cfg.auto_close_switch.value else False
    box = ui.main_window(text, auto_close_mode)

    # ── 生日已显示 → 标记今天不再重复 ──
    if birthday_shown:
        for comp in active:
            if isinstance(comp, BirthdayWidget):
                comp.mark_as_shown()
                break

    if box:
        log.info('主程序-用户点击确定，程序正常结束')
        sys.exit()
    else:
        log.info('主程序-用户打开设置')
        start_settings()

if __name__ == '__main__':
    # 初始化
    ui.app_manager.init_app()
    # 使用共享事件循环
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)

    # 禁止多开-Windows下
    if lib.system == 'Windows':
        checker = lib.WinSingleInstance(name='Local\\StartInfo-main')
        if checker.is_running:
            # 显示提示
            ui.dialog(lib.TITLE, '程序已运行，请勿重复启动！')
            log.warning('主程序-检测到多开，请勿重复启动')
            sys.exit()

    # 检测是否带有启动参数(args列表的长度≥1)
    if len(lib.global_argv) >= 1:
        # 如果是更新后第一次启动
        if '--update' in lib.global_argv:
            ui.dialog(lib.TITLE,
                      f'已成功更新到{lib.VERSION}(・ω・)\n{lib.CURRENT_VERSION_JSON.get('changelog', '更新日志获取失败')}')
            from settings import delete_download_cache

            # 删除下载缓存
            delete_download_cache()

        # 如果是以--settings参数启动
        elif '--settings' in lib.global_argv:
            # 启动设置
            from settings import start_settings
            start_settings()

        # 如果是以--updater参数启动
        elif '--updater' in lib.global_argv:
            from core.updater import start_updater

            # 启动更新器
            start_updater()

            sys.exit()

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
        # 先关闭 qasync 事件循环，避免 shutdown 时 'Signal source has been deleted' 警告
        qasync_loop.close()
        raise

    # main() 正常返回后（设置窗口等已在内部自行管理事件循环），直接退出
    sys.exit(0)

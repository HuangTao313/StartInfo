import asyncio
import os
import shutil
import time
from PySide6.QtWidgets import QWidget
from qfluentwidgets import (ScrollArea, ExpandLayout, SettingCardGroup, PrimaryPushSettingCard,ComboBoxSettingCard,
                            FluentIcon as FIF, PushSettingCard, InfoBar, InfoBarPosition)

from .widgets import *
from .. import ht_lib as lib
from ..config import cfg  # 导入刚才写的管家
from ..init_app import is_shortcut_exist, create_shortcut, remove_shortcut
from ..get_data import get_weather_air_quality, get_mc_server_status

# 常量定义
# 中国城市数据库路径
CITY_DB_PATH = lib.JSON_PATH / 'China_citys_db.json'

class BasicSettingsWidget(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # 1. 开启透明背景（ScrollArea 层面）
        self.enableTransparentBackground()

        # 2. 创建唯一的底盘并设置透明
        self.scrollWidget = QWidget()
        self.scrollWidget.setObjectName("scrollWidget")  # 给底盘起个名
        self.scrollWidget.setStyleSheet("background: transparent;")  # 这里的 QWidget 尽量精准

        # 3. 设置布局（绑定到底盘上）
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # ---------------------------------------------------------
        # 注意！下面不要再写 self.scrollWidget = QWidget() 了
        # ---------------------------------------------------------

        # 4. 创建组并添加卡片
        # ===== 基本设置 =====
        self.generalGroup = SettingCardGroup("基本设置", self.scrollWidget)

        # 3. 手敲一个开关卡片（绑定到大脑）
        # 开机自启
        self.startupCard = ZhSwitchSettingCard(
            FIF.POWER_BUTTON,
            '开机自启',
            '是否开机启动',
            configItem=None,
            parent=self.generalGroup
        )

        # 检查开机启动状态
        actual_status = is_shortcut_exist()
        self.startupCard.setChecked(actual_status)

        # 自动关闭
        self.autoCloseCard = ZhSwitchSettingCard(
            FIF.CLOSE,
            '主窗口自动关闭',
            '主窗口在一段后自动关闭，程序结束运行',
            configItem=cfg.auto_close_switch,
            parent=self.generalGroup
        )

        self.autoCloseTimer = TextSettingCard(
            icon=FIF.STOP_WATCH,
            title='自动关闭时间(单位：秒/s)',
            content='主窗口自动关闭时间(范围：30~300秒，默认60秒)',
            configItem=cfg.auto_close_time,
            parent=self.generalGroup
        )

        # 关闭设置窗口后的行为
        self.closeSettingsAction = ComboBoxSettingCard(
            texts=['重启到主程序', '直接退出'],
            icon=FIF.CLOSE,
            title="关闭设置窗口后的行为",
            content="重启到主程序或直接退出",
            configItem=cfg.close_settings_action,
            parent=self.generalGroup
        )

        self.deleteDownloadTempCard = PrimaryPushSettingCard(
            icon=FIF.DELETE,
            title='删除下载缓存',
            content='删除因程序更新下载的临时文件',
            text='删除下载缓存',
            parent=self.generalGroup
        )

        # 添加进组
        self.generalGroup.addSettingCard(self.startupCard)
        self.generalGroup.addSettingCard(self.autoCloseCard)
        self.generalGroup.addSettingCard(self.autoCloseTimer)
        self.generalGroup.addSettingCard(self.closeSettingsAction)
        self.generalGroup.addSettingCard(self.deleteDownloadTempCard)
        self.expandLayout.addWidget(self.generalGroup)

        # ===== 天气 =====
        # 启用天气功能
        self.weatherGroup = SettingCardGroup("天气", self.scrollWidget)
        self.weatherSwitchCard = ZhSwitchSettingCard(
            icon=FIF.CLOUD,
            title="显示天气",
            content="显示当前天气",
            configItem=cfg.weather_switch,
            parent=self.weatherGroup
        )

        # 选择城市
        self.cityChooseCard = PushSettingCard(
            text="选择城市",
            icon=FIF.SEARCH,
            title=f"选择城市(当前: {cfg.city_name.value})",
            content="获取天气的城市",
            parent=self.weatherGroup
        )

        # 天气数据自动刷新时间
        self.weatherRefreshTimeCard = TextSettingCard(
            icon=FIF.STOP_WATCH,
            title="天气数据刷新间隔(单位：分钟/m)",
            content="天气数据自动刷新时间(范围：15~60分钟，默认30分钟)",
            configItem=cfg.weather_interval,
            parent=self.weatherGroup
        )

        # 刷新天气数据
        self.weatherRefreshCard = PrimaryPushSettingCard(
            text="刷新天气数据",
            icon=FIF.SYNC,
            title="刷新天气数据",
            content="刷新天气数据",
            parent=self.weatherGroup
        )

        # 添加进组
        self.weatherGroup.addSettingCard(self.weatherSwitchCard)
        self.weatherGroup.addSettingCard(self.cityChooseCard)
        self.weatherGroup.addSettingCard(self.weatherRefreshTimeCard)
        self.weatherGroup.addSettingCard(self.weatherRefreshCard)
        self.expandLayout.addWidget(self.weatherGroup)

        # ===== 倒数日 =====
        self.countdownGroup = SettingCardGroup("倒数日", self.scrollWidget)
        # 启用倒数日功能
        self.countdownCard = ZhSwitchSettingCard(
            icon=FIF.CALENDAR,
            title='启用倒数日',
            content='在主窗口显示：“距离【xx】还有xx天”',
            configItem=cfg.countdown_switch,
            parent=self.countdownGroup
        )

        # 倒数日设置项待开发.....
        self.countdownTextCard = TextSettingCard(
            icon=FIF.EDIT,
            title='倒数日文本',
            content='倒数日文本',
            configItem=cfg.countdown_text,
            parent=self.countdownGroup
        )

        self.countdownDateCard = CalendarSettingCard(
    icon=FIF.CALENDAR,
    title='倒数目标日期',
    content='设置你需要倒计时的重要日子',
    configItem=cfg.countdown_date, # 假设你定义了这个配置
    parent=self.countdownGroup
)

        # 添加进组
        self.countdownGroup.addSettingCard(self.countdownCard)
        self.countdownGroup.addSettingCard(self.countdownTextCard)
        self.countdownGroup.addSettingCard(self.countdownDateCard)
        self.expandLayout.addWidget(self.countdownGroup)

        # ===== 生日祝福 =====
        self.birthdayWishesGroup = SettingCardGroup("生日祝福(暂不支持多人同天生日)", self.scrollWidget)

        self.birthdayWishesSwitchCard = ZhSwitchSettingCard(
            icon=FIF.CALENDAR,
            title='启用生日祝福',
            content='在生日当天显示生日祝福',
            configItem=cfg.birthday_wishes_switch,
            parent=self.birthdayWishesGroup
        )

        self.birthdayListCard = PrimaryPushSettingCard(
            text="编辑生日列表",
            icon=FIF.SEARCH,
            title="编辑生日列表",
            content=r"编辑生日列表(目前仅支持手动更改.\data\json\config.json的BirthdayWishes\birthday_dict字典)",
            parent=self.birthdayWishesGroup
        )

        # 添加进组
        self.birthdayWishesGroup.addSettingCard(self.birthdayWishesSwitchCard)
        self.birthdayWishesGroup.addSettingCard(self.birthdayListCard)
        self.expandLayout.addWidget(self.birthdayWishesGroup)

        # ===== Minecraft Java服务器检测器=====
        self.mcServerCheckerGroup = SettingCardGroup("Minecraft Java版服务器玩家在线情况检测", self.scrollWidget)
        self.mcServerCheckSwitchCard = ZhSwitchSettingCard(
            icon=FIF.GLOBE,
            title='启用Minecraft Java版服务器玩家在线情况检测',
            content='快速查看MC服务器玩家在线情况，支持检查朋友在线情况',
            configItem=cfg.minecraft_server_checker_switch,
            parent=self.mcServerCheckerGroup
        )

        self.mcServerNameCard = TextSettingCard(
            icon=FIF.GAME,
            title='服务器名称',
            content='Minecraft Java版服务器名称',
            configItem=cfg.minecraft_server_name,
            parent=self.mcServerCheckerGroup
        )

        self.mcServerIPCard = TextSettingCard(
            icon=FIF.CLOUD,
            title='服务器IP地址',
            content='Minecraft Java版服务器IP',
            configItem=cfg.minecraft_server_ip,
            parent=self.mcServerCheckerGroup
        )

        self.mcServerPortCard = TextSettingCard(
            icon=FIF.INFO,
            title='服务器端口号',
            content='Minecraft Java版服务器端口号(一般为25565)',
            configItem=cfg.minecraft_server_port,
            parent=self.mcServerCheckerGroup
        )

        self.mcServerDataRefreshIntervalCard = TextSettingCard(
            icon=FIF.STOP_WATCH,
            title='服务器数据刷新间隔(单位：秒/s)',
            content='Minecraft Java版服务器数据自动刷新时间(范围：5~3600秒，默认60秒)',
            configItem=cfg.minecraft_server_data_refresh_interval,
            parent=self.mcServerCheckerGroup
        )

        self.mcFriendsListCard = PrimaryPushSettingCard(
            text='编辑朋友列表',
            icon=FIF.PEOPLE,
            title='编辑朋友列表',
            content=r'编辑朋友列表(目前仅支持手动修改.\data\json\config.json的MinecraftJavaServerChecker\friends_list列表)',
            parent=self.mcServerCheckerGroup
        )

        # 立即刷新
        self.mcServerDataRefreshCard = PrimaryPushSettingCard(
            text='立即刷新',
            icon=FIF.SYNC,
            title='立即刷新',
            content='立即刷新Minecraft Java服务器数据',
            parent=self.mcServerCheckerGroup
        )

        # 添加进组
        self.mcServerCheckerGroup.addSettingCard(self.mcServerCheckSwitchCard)
        self.mcServerCheckerGroup.addSettingCard(self.mcServerNameCard)
        self.mcServerCheckerGroup.addSettingCard(self.mcServerIPCard)
        self.mcServerCheckerGroup.addSettingCard(self.mcServerPortCard)
        self.mcServerCheckerGroup.addSettingCard(self.mcServerDataRefreshIntervalCard)
        self.mcServerCheckerGroup.addSettingCard(self.mcFriendsListCard)
        self.mcServerCheckerGroup.addSettingCard(self.mcServerDataRefreshCard)
        self.expandLayout.addWidget(self.mcServerCheckerGroup)

        # ========= 其他信息 ========
        self.otherGroup = SettingCardGroup("其他信息", self.scrollWidget)
        self.greetingSwitchCard = ZhSwitchSettingCard(
            icon=FIF.HEART,
            title='显示问候语',
            content='显示当前时间对应的问候语',
            configItem=cfg.greeting_switch,
            parent=self.otherGroup
        )

        self.startupTimesSwitchCard = ZhSwitchSettingCard(
            icon=FIF.POWER_BUTTON,
            title='显示开机次数',
            content='显示开机次数',
            configItem=cfg.startup_times_switch,
            parent=self.otherGroup
        )

        self.datetimeSwitchCard = ZhSwitchSettingCard(
            icon=FIF.DATE_TIME,
            title='显示时间和日期',
            content='显示当前时间、日期',
            configItem=cfg.datetime_switch,
            parent=self.otherGroup
        )

        self.historicalSwitchCard = ZhSwitchSettingCard(
            icon=FIF.HISTORY,
            title='显示历史上的今天',
            content='显示历史上的今天信息',
            configItem=cfg.historical_switch,
            parent=self.otherGroup
        )

        self.wordsSwitchCard = ZhSwitchSettingCard(
            icon=FIF.ALIGNMENT,
            title='显示每日一言',
            content='显示每日一言信息',
            configItem=cfg.words_switch,
            parent=self.otherGroup
        )

        # 添加进组
        self.otherGroup.addSettingCard(self.greetingSwitchCard)
        self.otherGroup.addSettingCard(self.startupTimesSwitchCard)
        self.otherGroup.addSettingCard(self.datetimeSwitchCard)
        self.otherGroup.addSettingCard(self.historicalSwitchCard)
        self.otherGroup.addSettingCard(self.wordsSwitchCard)
        self.expandLayout.addWidget(self.otherGroup)

        # ===== 调试 =====
        self.debugGroup = SettingCardGroup("调试", self.scrollWidget)
        # 日志等级
        self.logLevelCard = ComboBoxSettingCard(
            icon=FIF.ALIGNMENT,
            title="日志等级",
            content="调整程序的日志等级",
            texts=cfg.log_level_list,
            configItem=cfg.log_level,
            parent=self.debugGroup
        )

        # 打开日志文件夹
        self.openLogFolderCard = PrimaryPushSettingCard(
            text="打开日志文件夹",
            icon=FIF.FOLDER,
            title="打开日志文件夹",
            content="打开程序日志文件夹",
            parent=self.debugGroup
        )

        # 禁用旧版设置
        self.banOldSwitchCard = ZhSwitchSettingCard(
            icon=FIF.CLOSE,
            title="禁用旧版设置",
            content="直接启动新版设置",
            configItem=cfg.ban_old_settings,
            parent=self.debugGroup
        )

        # 添加进组
        self.debugGroup.addSettingCard(self.logLevelCard)
        self.debugGroup.addSettingCard(self.openLogFolderCard)
        self.debugGroup.addSettingCard(self.banOldSwitchCard)
        self.expandLayout.addWidget(self.debugGroup)

        # 最后把底盘装进滚动区域
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName("basic_settings_page")

        # 绑定信号与槽
        self.startupCard.checkedChanged.connect(self.onStartupChanged)
        self.deleteDownloadTempCard.clicked.connect(self.onDeleteDownloadTempClicked)
        self.cityChooseCard.clicked.connect(self.onCityChooseClicked)
        self.weatherRefreshCard.clicked.connect(self.onWeatherRefreshClicked)
        self.birthdayListCard.clicked.connect(self.StartConfigFile)
        self.mcFriendsListCard.clicked.connect(self.StartConfigFile)
        self.mcServerDataRefreshCard.clicked.connect(self.onMCSeverDataRefreshClicked)
        self.openLogFolderCard.clicked.connect(self.onOpenLogFolderClicked)
        
        # 绑定输入值检测回调
        self.autoCloseTimer.textChanged.connect(
            lambda text: self.check_input(text, 30, 300, cfg.auto_close_time, self.autoCloseTimer)
        )
        self.weatherRefreshTimeCard.textChanged.connect(
            lambda text: self.check_input(text, 15, 60, cfg.weather_interval, self.weatherRefreshTimeCard)
        )
        self.mcServerDataRefreshIntervalCard.textChanged.connect(
            lambda text: self.check_input(text, 5, 3600, cfg.minecraft_server_data_refresh_interval, self.mcServerDataRefreshIntervalCard)
        )

    # 定义槽函数
    def onStartupChanged(self, is_enabled: bool):
        if is_enabled:
            result = create_shortcut()
            if result:
                Notify.success(content='已添加开机启动项', parent=self)

            else:
                Notify.error(content='添加开机启动项失败，请查看日志', parent=self)
        else:
            result = remove_shortcut()
            if result:
                Notify.success(content='已删除开机启动项', parent=self)
            else:
                Notify.error(content='已删除开机启动项，请查看日志', parent=self)

    def onDeleteDownloadTempClicked(self):
        # 检查下载缓存文件夹是否存在
        if lib.DOWNLOAD_PATH.exists():
            # 尝试删除
            try:
                shutil.rmtree(lib.DOWNLOAD_PATH)
                lib.log.info(f'设置-已删除下载缓存')
                Notify.success(content='已删除下载缓存', parent=self)

            except Exception as e:
                error_text = f'删除下载缓存失败: {str(e)}'
                lib.log.error(f'设置{error_text}')
                Notify.error(content=error_text, parent=self)

        else:
            lib.log.info('设置-未发现下载缓存')
            Notify.info(content='未发现下载缓存', parent=self)

    def onCityChooseClicked(self):
        city_list = lib.read_json(CITY_DB_PATH)

        # 2. 弹出窗口
        box = CitySearchBox(city_list, self)

        # 3. 如果用户点击了“确定”按钮
        if box.exec():
            city_id = box.get_selected_city_id()
            display_name = box.get_selected_city_display()

            if city_id:
                old_city_id = cfg.city_id.value
                # 保存到你的 config.py
                cfg.set(cfg.city_id, city_id)
                cfg.set(cfg.city_name, display_name)

                # 如果城市更新，则重新获取天气数据
                if city_id != old_city_id:
                    Notify.success(title=f'已设置城市 {display_name}', content='正在获取天气数据...',parent=self)
                    self.cityChooseCard.setTitle(f'选择城市(当前: {display_name})')
                    self.onWeatherRefreshClicked()

    def onWeatherRefreshClicked(self):
        # 安全读取次数，处理可能的解密失败
        stored_data = lib.file.read('General', 'data_reset_times')
        try:
            if stored_data:
                times = int(lib.decrypt(stored_data))
            else:
                times = 0  # 默认值
        except (ValueError, TypeError):
            log.warning('设置-解密次数数据失败，使用默认值6')
            times = 6

        if times <= 5:
                weather_data = asyncio.run(get_weather_air_quality())
                if isinstance(weather_data, dict):
                    lib.file.update('Data', 'weather', update_dict=weather_data)
                    lib.log.info(f'设置-已更新天气数据')
                    Notify.success('天气数据已更新',parent=self)

                else:
                    lib.log.error('设置-获取天气数据失败')
                    Notify.error(title='天气数据获取失败',content='请检查网络连接',parent=self)


        else:
            log.warning('设置-已超出每日重新定位次数')
            Notify.warning(title='已超出每日手动刷新次数',content='请勿频繁刷新',parent=self)

        # 次数自增1（使用加密存储）
        try:
            lib.file.write('General', 'data_reset_times', value=lib.encrypt(str(times + 1)))
        except Exception as e:
            lib.log.error(f'设置-写入重置次数数据失败: {e}')

    def StartConfigFile(self):
        try:
            os.startfile(lib.CONFIG_FILE_PATH)

        except Exception as e:
            lib.log.error(f'设置-打开配置文件失败: {e}')
            Notify.error(title='打开配置文件失败', content=str(e), parent=self)

    def onMCSeverDataRefreshClicked(self):
        mc_server_data = asyncio.run(get_mc_server_status())
        time_now = int(time.time())
        lib.file.update('Data', 'minecraft_server_data', update_dict=mc_server_data)
        lib.file.write('Data', 'minecraft_server_data', 'get_time',value=time_now)
        Notify.success(title=f'已更新{cfg.minecraft_server_name.value}服务器数据', content=f'当前{mc_server_data.get('mc_server_current','未知')}人在线', parent=self)
        lib.log.info(f'设置-已更新{cfg.minecraft_server_name.value}服务器数据')

    # 打开日志文件夹
    def onOpenLogFolderClicked(self):
        os.startfile(lib.LOG_FOLDER_PATH)

    # 输入值校验
    def check_input(self, value, min_value, max_value, config_item, card):
        """
        验证用户输入的数字是否在有效范围内
        
        参数:
            value: 用户输入的字符串值
            min_value: 最小允许值
            max_value: 最大允许值
            config_item: 关联的配置项，用于恢复默认值
            card: 对应的 TextSettingCard 实例，用于回滚 UI
        """
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            # 输入不是有效整数
            Notify.warning(
                title='输入错误', 
                content=f'请输入有效的整数，已恢复为 {config_item.value}', 
                parent=self
            )
            card.lineEdit.setText(str(config_item.value))
            return
        
        # 检查是否在有效范围内
        if not min_value <= int_value <= max_value:
            Notify.warning(
                title='输入错误', 
                content=f'请输入 {min_value}~{max_value} 之间的值，已恢复为 {config_item.value}', 
                parent=self
            )
            # 回滚到配置项中的值
            card.lineEdit.setText(str(config_item.value))
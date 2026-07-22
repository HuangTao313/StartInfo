"""基本设置页面。"""

import os
import shutil

from qfluentwidgets import (ComboBoxSettingCard, FluentIcon as FIF,
                            PrimaryPushSettingCard, PushSettingCard,
                            SettingCardGroup)

from .setting_card_base import BaseSettingPage
from .ui_widgets import (CalendarSettingCard, CitySearchBox, Notify,
                         TextSettingCard, ZhSwitchSettingCard, action)
from .ui_widgets import ExpandGroupCard
from .. import ht_lib as lib
from ..config import cfg, qconfig
from ..init_app import create_shortcut, remove_shortcut
from ..ui import log


class BasicSettingsPage(BaseSettingPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent, object_name='basic_settings_page')

        # ── 基本设置 ──
        generalGroup = SettingCardGroup('基本设置', self.scrollWidget)

        self.startupCard = ZhSwitchSettingCard(FIF.POWER_BUTTON, '开机自启', '是否开机启动', config_item=None,
                                               parent=generalGroup)
        self.startupCard.setChecked(False)
        self.startupCard.checkedChanged.connect(self._onStartupChanged)

        self.autoCloseCard = ZhSwitchSettingCard(FIF.CLOSE, '主窗口自动关闭', '主窗口在一段后自动关闭，程序结束运行',
                                                 config_item=cfg.auto_close_switch, parent=generalGroup)

        self.autoCloseTimer = TextSettingCard(config_item=cfg.auto_close_time, icon=FIF.STOP_WATCH,
                                              title='自动关闭时间(单位：秒/s)',
                                              content='主窗口自动关闭时间(范围：30~300秒，默认60秒)', parent=generalGroup)
        self.autoCloseTimer.textChanged.connect(
            lambda text: self._check_input(text, 30, 300, cfg.auto_close_time, self.autoCloseTimer)
        )

        self.closeSettingsAction = ComboBoxSettingCard(
            texts=['重启到主程序', '直接退出'], icon=FIF.CLOSE,
            title='关闭设置窗口后的行为', content='重启到主程序或直接退出',
            configItem=cfg.close_settings_action, parent=generalGroup,
        )

        self.deleteDownloadTempCard = PrimaryPushSettingCard(
            icon=FIF.DELETE, title='删除下载缓存',
            content='删除因程序更新下载的临时文件', text='删除下载缓存',
            parent=generalGroup,
        )
        self.deleteDownloadTempCard.clicked.connect(self._onDeleteDownloadTempClicked)

        generalGroup.addSettingCard(self.startupCard)
        generalGroup.addSettingCard(self.autoCloseCard)
        generalGroup.addSettingCard(self.autoCloseTimer)
        generalGroup.addSettingCard(self.closeSettingsAction)
        generalGroup.addSettingCard(self.deleteDownloadTempCard)
        self.expandLayout.addWidget(generalGroup)

        # ── 天气 ──
        weatherGroup = SettingCardGroup('天气&空气质量(请先选择您所在的城市)', self.scrollWidget)

        self.weatherSwitchCard = ZhSwitchSettingCard(icon=FIF.CLOUD, title='显示天气', content='显示当前城市的天气信息',
                                                     config_item=cfg.weather_switch, parent=weatherGroup)

        self.airQualitySwitchCard = ZhSwitchSettingCard(icon=FIF.LEAF, title='显示空气质量', content='显示当前城市的空气质量信息',
                                                        config_item=cfg.air_quality_switch, parent=weatherGroup)

        # 创建手风琴组件
        self.weatherDetailCard = ExpandGroupCard(
            FIF.CLOUD, '天气信息详细配置', '城市、刷新间隔', parent=weatherGroup,
        )

        self.cityChooseCard = PushSettingCard(
            text='选择城市', icon=FIF.SEARCH,
            title=f'选择城市(当前: {cfg.city_name.value})',
            content='获取天气的城市', parent=self.weatherDetailCard,
        )
        self.cityChooseCard.clicked.connect(self._onCityChooseClicked)

        self.weatherRefreshTimeCard = TextSettingCard(config_item=cfg.weather_interval, icon=FIF.STOP_WATCH,
                                                      title='天气信息刷新间隔(单位：分钟/m)',
                                                      content='天气信息自动刷新时间(范围：15~60分钟，默认30分钟)',
                                                      parent=self.weatherDetailCard)
        self.weatherRefreshTimeCard.textChanged.connect(
            lambda text: self._check_input(text, 15, 60, cfg.weather_interval, self.weatherRefreshTimeCard)
        )

        self.airQualityRefreshTimeCard = TextSettingCard(config_item=cfg.air_quality_interval, icon=FIF.STOP_WATCH,
                                                         title='空气质量信息刷新间隔(单位：分钟/m)',
                                                         content='天气信息自动刷新时间(范围：15~240分钟，默认120分钟)')
        self.airQualityRefreshTimeCard.textChanged.connect(
            lambda text: self._check_input(text, 15, 240, cfg.air_quality_interval, self.airQualityRefreshTimeCard)
        )


        self.weatherRefreshCard = PrimaryPushSettingCard(
            text='刷新天气信息', icon=FIF.SYNC,
            title='刷新天气信息', content='刷新天气信息', parent=self.weatherDetailCard,
        )
        self.weatherRefreshCard.clicked.connect(self._onRefreshWeather)

        self.airQualityRefreshCard = PrimaryPushSettingCard(
            text='刷新空气质量信息', icon=FIF.SYNC,
            title='刷新空气质量信息', content='刷新空气质量信息', parent=self.weatherDetailCard,
        )

        self.airQualityRefreshCard.clicked.connect(self._onRefreshAirQuality)

        self.weatherDetailCard.addCard(self.cityChooseCard)
        self.weatherDetailCard.addCard(self.weatherRefreshTimeCard)
        self.weatherDetailCard.addCard(self.airQualityRefreshTimeCard)
        self.weatherDetailCard.addCard(self.weatherRefreshCard)
        self.weatherDetailCard.addCard(self.airQualityRefreshCard)
        weatherGroup.addSettingCard(self.weatherSwitchCard)
        weatherGroup.addSettingCard(self.airQualitySwitchCard)
        weatherGroup.addSettingCard(self.weatherDetailCard)
        self.expandLayout.addWidget(weatherGroup)

        # ── 倒数日 ──
        countdownGroup = SettingCardGroup('倒数日', self.scrollWidget)
        self.countdownCard = ZhSwitchSettingCard(icon=FIF.CALENDAR, title='启用倒数日',
                                                 content='在主窗口显示："距离【xx】还有xx天"',
                                                 config_item=cfg.countdown_switch, parent=countdownGroup)

        # 创建手风琴组件
        self.countdownDetailCard = ExpandGroupCard(
            FIF.GLOBE, '倒数日详细配置', '倒数日名称、日期信息', parent=countdownGroup,
        )

        self.countdownTextCard = TextSettingCard(config_item=cfg.countdown_name, icon=FIF.EDIT, title='倒数日名称',
                                                 content='倒数日名称', parent=self.countdownDetailCard)
        self.countdownDateCard = CalendarSettingCard(icon=FIF.CALENDAR, title='倒数目标日期',
                                                     content='设置你需要倒计时的日期', config_item=cfg.countdown_date,
                                                     parent=self.countdownDetailCard)

        self.countdownDetailCard.addCard(self.countdownTextCard)
        self.countdownDetailCard.addCard(self.countdownDateCard)
        countdownGroup.addSettingCard(self.countdownCard)
        countdownGroup.addSettingCard(self.countdownDetailCard)
        self.expandLayout.addWidget(countdownGroup)

        # ── 生日祝福 ──
        birthdayGroup = SettingCardGroup('生日祝福(暂不支持多人同天生日)', self.scrollWidget)
        self.birthdayWishesSwitchCard = ZhSwitchSettingCard(icon=FIF.CALENDAR, title='启用生日祝福',
                                                            content='在生日当天显示生日祝福',
                                                            config_item=cfg.birthday_wishes_switch,
                                                            parent=birthdayGroup)
        self.birthdayListCard = PrimaryPushSettingCard(
            text='编辑生日列表', icon=FIF.SEARCH, title='编辑生日列表',
            content=r'编辑生日列表(目前仅支持手动更改.\data\json\config.json的BirthdayWishes\birthday_dict字典)',
            parent=birthdayGroup,
        )
        self.birthdayListCard.clicked.connect(self._openConfigFile)
        birthdayGroup.addSettingCard(self.birthdayWishesSwitchCard)
        birthdayGroup.addSettingCard(self.birthdayListCard)
        self.expandLayout.addWidget(birthdayGroup)

        # ── Minecraft 服务器检测器 ──
        mcGroup = SettingCardGroup('Minecraft Java版服务器玩家在线情况检测', self.scrollWidget)
        self.mcServerCheckSwitchCard = ZhSwitchSettingCard(icon=FIF.GLOBE,
                                                           title='启用Minecraft Java版服务器玩家在线情况检测',
                                                           content='快速查看MC服务器玩家在线情况，支持检查朋友在线情况',
                                                           config_item=cfg.minecraft_server_checker_switch,
                                                           parent=mcGroup)

        # 手风琴：详细配置收起来
        self.mcDetailCard = ExpandGroupCard(
            FIF.GLOBE, '服务器详细配置', '配置服务器名称、IP、端口等信息', parent=mcGroup,
        )

        self.mcServerNameCard = TextSettingCard(config_item=cfg.minecraft_server_name, icon=FIF.GAME,
                                                title='服务器名称', content='Minecraft Java版服务器名称',
                                                parent=self.mcDetailCard)
        self.mcServerIPCard = TextSettingCard(config_item=cfg.minecraft_server_ip, icon=FIF.CLOUD, title='服务器IP地址',
                                              content='Minecraft Java版服务器IP', parent=self.mcDetailCard)
        self.mcServerPortCard = TextSettingCard(config_item=cfg.minecraft_server_port, icon=FIF.INFO,
                                                title='服务器端口号',
                                                content='Minecraft Java版服务器端口号(一般为25565)',
                                                parent=self.mcDetailCard)
        self.mcServerDataRefreshIntervalCard = TextSettingCard(config_item=cfg.minecraft_server_data_refresh_interval,
                                                               icon=FIF.STOP_WATCH,
                                                               title='服务器信息刷新间隔(单位：秒/s)',
                                                               content='Minecraft Java版服务器信息自动刷新时间(范围：5~3600秒，默认60秒)',
                                                               parent=self.mcDetailCard)
        self.mcServerDataRefreshIntervalCard.textChanged.connect(
            lambda text: self._check_input(text, 5, 3600, cfg.minecraft_server_data_refresh_interval,
                                           self.mcServerDataRefreshIntervalCard)
        )
        self.mcFriendsListCard = PrimaryPushSettingCard(
            text='编辑朋友列表', icon=FIF.PEOPLE, title='编辑朋友列表',
            content=r'编辑朋友列表(目前仅支持手动修改.\data\json\config.json的MinecraftJavaServerChecker\friends_list列表)',
            parent=self.mcDetailCard,
        )
        self.mcFriendsListCard.clicked.connect(self._openConfigFile)
        self.mcServerDataRefreshCard = PrimaryPushSettingCard(
            text='立即刷新', icon=FIF.SYNC, title='立即刷新',
            content='立即刷新Minecraft Java服务器信息', parent=self.mcDetailCard,
        )
        self.mcServerDataRefreshCard.clicked.connect(self._onRefreshMCServer)

        self.mcDetailCard.addCard(self.mcServerNameCard)
        self.mcDetailCard.addCard(self.mcServerIPCard)
        self.mcDetailCard.addCard(self.mcServerPortCard)
        self.mcDetailCard.addCard(self.mcServerDataRefreshIntervalCard)
        self.mcDetailCard.addCard(self.mcFriendsListCard)
        self.mcDetailCard.addCard(self.mcServerDataRefreshCard)
        mcGroup.addSettingCard(self.mcServerCheckSwitchCard)
        mcGroup.addSettingCard(self.mcDetailCard)
        self.expandLayout.addWidget(mcGroup)

        # ── 其他信息 ──
        otherGroup = SettingCardGroup('其他信息', self.scrollWidget)

        # 创建手风琴组件
        self.otherDetailCard = ExpandGroupCard(
            FIF.GLOBE, '其他信息开关', '问候语、开机次数、时间和日期等信息', parent=otherGroup,
        )

        self.greetingSwitchCard = ZhSwitchSettingCard(icon=FIF.HEART, title='显示问候语',
                                                      content='显示当前时间对应的问候语',
                                                      config_item=cfg.greeting_switch, parent=self.otherDetailCard)
        self.startupTimesSwitchCard = ZhSwitchSettingCard(icon=FIF.POWER_BUTTON, title='显示开机次数',
                                                          content='显示开机次数', config_item=cfg.startup_times_switch,
                                                          parent=self.otherDetailCard)
        self.datetimeSwitchCard = ZhSwitchSettingCard(icon=FIF.DATE_TIME, title='显示时间和日期',
                                                      content='显示当前时间、日期', config_item=cfg.datetime_switch,
                                                      parent=self.otherDetailCard)
        self.historicalSwitchCard = ZhSwitchSettingCard(icon=FIF.HISTORY, title='显示历史上的今天',
                                                        content='显示历史上的今天信息',
                                                        config_item=cfg.historical_switch, parent=self.otherDetailCard)
        self.wordsSwitchCard = ZhSwitchSettingCard(icon=FIF.ALIGNMENT, title='显示每日一言', content='显示每日一言信息',
                                                   config_item=cfg.words_switch, parent=self.otherDetailCard)

        self.otherDetailCard.addCard(self.greetingSwitchCard)
        self.otherDetailCard.addCard(self.startupTimesSwitchCard)
        self.otherDetailCard.addCard(self.datetimeSwitchCard)
        self.otherDetailCard.addCard(self.historicalSwitchCard)
        self.otherDetailCard.addCard(self.wordsSwitchCard)
        otherGroup.addSettingCard(self.otherDetailCard)
        self.expandLayout.addWidget(otherGroup)

        # ── 调试 ──
        debugGroup = SettingCardGroup('调试', self.scrollWidget)
        self.logLevelCard = ComboBoxSettingCard(
            icon=FIF.ALIGNMENT, title='日志等级', content='调整程序的日志等级，重启后生效',
            texts=cfg.log_level_list, configItem=cfg.log_level, parent=debugGroup,
        )
        self.openLogFolderCard = PrimaryPushSettingCard(
            text='打开日志文件夹', icon=FIF.FOLDER,
            title='打开日志文件夹', content='打开程序日志文件夹', parent=debugGroup,
        )
        self.openLogFolderCard.clicked.connect(lambda: os.startfile(lib.LOG_FOLDER_PATH))

        debugGroup.addSettingCard(self.logLevelCard)
        debugGroup.addSettingCard(self.openLogFolderCard)
        self.expandLayout.addWidget(debugGroup)

        self.finalise()

        # ------------------------------------------------------------------
        # 禁用其他系统暂未适配的功能
        # ------------------------------------------------------------------
        if lib.system != 'Windows':
            # 开机自启
            self.startupCard.setEnabled(False)
            # 关闭设置窗口后的行为锁定为【直接退出】
            qconfig.set(cfg.close_settings_action, 'exit', save=True)
            self.closeSettingsAction.setEnabled(False)


    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _check_input(self, text, min_val, max_val, config_item, card):
        """验证用户输入的数字是否在有效范围内。"""
        try:
            value = int(text)
        except (ValueError, TypeError):
            Notify.warning(
                title='输入错误',
                content=f'请输入有效的整数，已恢复为 {config_item.value}',
                parent=self,
            )
            card.setText(str(config_item.value))
            return

        if not min_val <= value <= max_val:
            Notify.warning(
                title='输入错误',
                content=f'请输入 {min_val}~{max_val} 之间的值，已恢复为 {config_item.value}',
                parent=self,
            )
            card.setText(str(config_item.value))

    def _openConfigFile(self):
        try:
            os.startfile(lib.CONFIG_FILE_PATH)
        except Exception as e:
            lib.log.error(f'设置-打开配置文件失败: {e}')
            Notify.error(title='打开配置文件失败', content=str(e), parent=self)

    # ------------------------------------------------------------------
    # 槽函数
    # ------------------------------------------------------------------

    def _onStartupChanged(self, is_enabled: bool):
        if is_enabled:
            if create_shortcut():
                Notify.success(content='已添加开机启动项', parent=self)
            else:
                Notify.error(content='添加开机启动项失败，请查看日志', parent=self)
        else:
            if remove_shortcut():
                Notify.success(content='已删除开机启动项', parent=self)
            else:
                Notify.error(content='删除开机启动项失败，请查看日志', parent=self)

    @action('已删除下载缓存', '删除失败')
    def _onDeleteDownloadTempClicked(self):
        if lib.DOWNLOAD_PATH.exists():
            shutil.rmtree(lib.DOWNLOAD_PATH)
            lib.log.info('设置-已删除下载缓存')
            return True
        else:
            Notify.info(content='未发现下载缓存', parent=self)
            return False

    def _onCityChooseClicked(self):
        box = CitySearchBox(self)
        if box.exec():
            city_id = box.get_selected_city_id()
            display_name = box.get_selected_city_display()
            if city_id:
                old_city_id = cfg.city_id.value
                cfg.set(cfg.city_id, city_id)
                cfg.set(cfg.city_name, display_name)
                self.cityChooseCard.setTitle(f'选择城市(当前: {display_name})')
                if city_id != old_city_id:
                    Notify.success(title=f'已设置城市 {display_name}', content='正在获取天气信息...', parent=self)
                    self._onRefreshWeather()

    @action('天气信息已更新', '获取失败')
    async def _onRefreshWeather(self):
        self.weatherRefreshCard.setEnabled(False)
        try:
            from core.widgets import WeatherWidget
            w = WeatherWidget()
            return await w.get_data_async(force_refresh=True)

        finally:
            self.weatherRefreshCard.setEnabled(True)

    @action('空气质量信息已更新', '获取失败')
    async def _onRefreshAirQuality(self):
        self.airQualityRefreshCard.setEnabled(False)
        try:
            from core.widgets import AirQualityWidget
            w = AirQualityWidget()
            return await w.get_data_async(force_refresh=True)

        finally:
            self.airQualityRefreshCard.setEnabled(True)

    @action('MC 服务器信息已更新', '刷新失败')
    async def _onRefreshMCServer(self):
        self.mcServerDataRefreshCard.setEnabled(False)
        try:
            from core.widgets import MCServerStatusWidget
            mc = MCServerStatusWidget()
            return await mc.get_data_async(force_refresh=True)

        finally:
            self.mcServerDataRefreshCard.setEnabled(True)
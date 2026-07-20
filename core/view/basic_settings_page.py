"""基本设置页面。"""

import os
import shutil

from PySide6.QtCore import QThread, Signal
from qfluentwidgets import (ComboBoxSettingCard, FluentIcon as FIF,
                             PrimaryPushSettingCard, PushSettingCard,
                             SettingCardGroup)

from .. import ht_lib as lib
from ..config import cfg
from ..init_app import create_shortcut, remove_shortcut
from .action_helpers import action
from .base_setting_card import BaseSettingPage
from .ui_widgets import (CalendarSettingCard, CitySearchBox, Notify,
                         TextSettingCard, ZhSwitchSettingCard)

# 常量
CITY_DB_PATH = lib.JSON_PATH / 'China_citys_db.json'


class BasicSettingsPage(BaseSettingPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent, object_name='basic_settings_page')

        # ── 基本设置 ──
        generalGroup = SettingCardGroup('基本设置', self.scrollWidget)

        self.startupCard = ZhSwitchSettingCard(
            FIF.POWER_BUTTON, '开机自启', '是否开机启动',
            configItem=None, parent=generalGroup,
        )
        self.startupCard.setChecked(False)
        self.startupCard.checkedChanged.connect(self._onStartupChanged)

        self.autoCloseCard = ZhSwitchSettingCard(
            FIF.CLOSE, '主窗口自动关闭', '主窗口在一段后自动关闭，程序结束运行',
            configItem=cfg.auto_close_switch, parent=generalGroup,
        )

        self.autoCloseTimer = TextSettingCard(
            icon=FIF.STOP_WATCH, title='自动关闭时间(单位：秒/s)',
            content='主窗口自动关闭时间(范围：30~300秒，默认60秒)',
            configItem=cfg.auto_close_time, parent=generalGroup,
        )
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
        weatherGroup = SettingCardGroup('天气', self.scrollWidget)

        self.weatherSwitchCard = ZhSwitchSettingCard(
            icon=FIF.CLOUD, title='显示天气', content='显示当前天气',
            configItem=cfg.weather_switch, parent=weatherGroup,
        )

        self.cityChooseCard = PushSettingCard(
            text='选择城市', icon=FIF.SEARCH,
            title=f'选择城市(当前: {cfg.city_name.value})',
            content='获取天气的城市', parent=weatherGroup,
        )
        self.cityChooseCard.clicked.connect(self._onCityChooseClicked)

        self.weatherRefreshTimeCard = TextSettingCard(
            icon=FIF.STOP_WATCH, title='天气数据刷新间隔(单位：分钟/m)',
            content='天气数据自动刷新时间(范围：15~60分钟，默认30分钟)',
            configItem=cfg.weather_interval, parent=weatherGroup,
        )
        self.weatherRefreshTimeCard.textChanged.connect(
            lambda text: self._check_input(text, 15, 60, cfg.weather_interval, self.weatherRefreshTimeCard)
        )

        self.weatherRefreshCard = PrimaryPushSettingCard(
            text='刷新天气数据', icon=FIF.SYNC,
            title='刷新天气数据', content='刷新天气数据', parent=weatherGroup,
        )
        self.weatherRefreshCard.clicked.connect(self._onRefreshWeather)

        weatherGroup.addSettingCard(self.weatherSwitchCard)
        weatherGroup.addSettingCard(self.cityChooseCard)
        weatherGroup.addSettingCard(self.weatherRefreshTimeCard)
        weatherGroup.addSettingCard(self.weatherRefreshCard)
        self.expandLayout.addWidget(weatherGroup)

        # ── 倒数日 ──
        countdownGroup = SettingCardGroup('倒数日', self.scrollWidget)
        self.countdownCard = ZhSwitchSettingCard(
            icon=FIF.CALENDAR, title='启用倒数日',
            content='在主窗口显示："距离【xx】还有xx天"',
            configItem=cfg.countdown_switch, parent=countdownGroup,
        )
        self.countdownTextCard = TextSettingCard(
            icon=FIF.EDIT, title='倒数日文本', content='倒数日文本',
            configItem=cfg.countdown_text, parent=countdownGroup,
        )
        self.countdownDateCard = CalendarSettingCard(
            icon=FIF.CALENDAR, title='倒数目标日期',
            content='设置你需要倒计时的重要日子',
            configItem=cfg.countdown_date, parent=countdownGroup,
        )
        countdownGroup.addSettingCard(self.countdownCard)
        countdownGroup.addSettingCard(self.countdownTextCard)
        countdownGroup.addSettingCard(self.countdownDateCard)
        self.expandLayout.addWidget(countdownGroup)

        # ── 生日祝福 ──
        birthdayGroup = SettingCardGroup('生日祝福(暂不支持多人同天生日)', self.scrollWidget)
        self.birthdayWishesSwitchCard = ZhSwitchSettingCard(
            icon=FIF.CALENDAR, title='启用生日祝福',
            content='在生日当天显示生日祝福',
            configItem=cfg.birthday_wishes_switch, parent=birthdayGroup,
        )
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
        self.mcServerCheckSwitchCard = ZhSwitchSettingCard(
            icon=FIF.GLOBE, title='启用Minecraft Java版服务器玩家在线情况检测',
            content='快速查看MC服务器玩家在线情况，支持检查朋友在线情况',
            configItem=cfg.minecraft_server_checker_switch, parent=mcGroup,
        )
        self.mcServerNameCard = TextSettingCard(
            icon=FIF.GAME, title='服务器名称', content='Minecraft Java版服务器名称',
            configItem=cfg.minecraft_server_name, parent=mcGroup,
        )
        self.mcServerIPCard = TextSettingCard(
            icon=FIF.CLOUD, title='服务器IP地址', content='Minecraft Java版服务器IP',
            configItem=cfg.minecraft_server_ip, parent=mcGroup,
        )
        self.mcServerPortCard = TextSettingCard(
            icon=FIF.INFO, title='服务器端口号',
            content='Minecraft Java版服务器端口号(一般为25565)',
            configItem=cfg.minecraft_server_port, parent=mcGroup,
        )
        self.mcServerDataRefreshIntervalCard = TextSettingCard(
            icon=FIF.STOP_WATCH, title='服务器数据刷新间隔(单位：秒/s)',
            content='Minecraft Java版服务器数据自动刷新时间(范围：5~3600秒，默认60秒)',
            configItem=cfg.minecraft_server_data_refresh_interval, parent=mcGroup,
        )
        self.mcServerDataRefreshIntervalCard.textChanged.connect(
            lambda text: self._check_input(text, 5, 3600, cfg.minecraft_server_data_refresh_interval,
                                           self.mcServerDataRefreshIntervalCard)
        )
        self.mcFriendsListCard = PrimaryPushSettingCard(
            text='编辑朋友列表', icon=FIF.PEOPLE, title='编辑朋友列表',
            content=r'编辑朋友列表(目前仅支持手动修改.\data\json\config.json的MinecraftJavaServerChecker\friends_list列表)',
            parent=mcGroup,
        )
        self.mcFriendsListCard.clicked.connect(self._openConfigFile)
        self.mcServerDataRefreshCard = PrimaryPushSettingCard(
            text='立即刷新', icon=FIF.SYNC, title='立即刷新',
            content='立即刷新Minecraft Java服务器数据', parent=mcGroup,
        )
        self.mcServerDataRefreshCard.clicked.connect(self._onRefreshMCServer)
        mcGroup.addSettingCard(self.mcServerCheckSwitchCard)
        mcGroup.addSettingCard(self.mcServerNameCard)
        mcGroup.addSettingCard(self.mcServerIPCard)
        mcGroup.addSettingCard(self.mcServerPortCard)
        mcGroup.addSettingCard(self.mcServerDataRefreshIntervalCard)
        mcGroup.addSettingCard(self.mcFriendsListCard)
        mcGroup.addSettingCard(self.mcServerDataRefreshCard)
        self.expandLayout.addWidget(mcGroup)

        # ── 其他信息 ──
        otherGroup = SettingCardGroup('其他信息', self.scrollWidget)
        self.greetingSwitchCard = ZhSwitchSettingCard(
            icon=FIF.HEART, title='显示问候语', content='显示当前时间对应的问候语',
            configItem=cfg.greeting_switch, parent=otherGroup,
        )
        self.startupTimesSwitchCard = ZhSwitchSettingCard(
            icon=FIF.POWER_BUTTON, title='显示开机次数', content='显示开机次数',
            configItem=cfg.startup_times_switch, parent=otherGroup,
        )
        self.datetimeSwitchCard = ZhSwitchSettingCard(
            icon=FIF.DATE_TIME, title='显示时间和日期', content='显示当前时间、日期',
            configItem=cfg.datetime_switch, parent=otherGroup,
        )
        self.historicalSwitchCard = ZhSwitchSettingCard(
            icon=FIF.HISTORY, title='显示历史上的今天', content='显示历史上的今天信息',
            configItem=cfg.historical_switch, parent=otherGroup,
        )
        self.wordsSwitchCard = ZhSwitchSettingCard(
            icon=FIF.ALIGNMENT, title='显示每日一言', content='显示每日一言信息',
            configItem=cfg.words_switch, parent=otherGroup,
        )
        otherGroup.addSettingCard(self.greetingSwitchCard)
        otherGroup.addSettingCard(self.startupTimesSwitchCard)
        otherGroup.addSettingCard(self.datetimeSwitchCard)
        otherGroup.addSettingCard(self.historicalSwitchCard)
        otherGroup.addSettingCard(self.wordsSwitchCard)
        self.expandLayout.addWidget(otherGroup)

        # ── 调试 ──
        debugGroup = SettingCardGroup('调试', self.scrollWidget)
        self.logLevelCard = ComboBoxSettingCard(
            icon=FIF.ALIGNMENT, title='日志等级', content='调整程序的日志等级',
            texts=cfg.log_level_list, configItem=cfg.log_level, parent=debugGroup,
        )
        self.openLogFolderCard = PrimaryPushSettingCard(
            text='打开日志文件夹', icon=FIF.FOLDER,
            title='打开日志文件夹', content='打开程序日志文件夹', parent=debugGroup,
        )
        self.openLogFolderCard.clicked.connect(lambda: os.startfile(lib.LOG_FOLDER_PATH))

        self.banOldSwitchCard = ZhSwitchSettingCard(
            icon=FIF.CLOSE, title='禁用旧版设置', content='直接启动新版设置',
            configItem=cfg.ban_old_settings, parent=debugGroup,
        )
        debugGroup.addSettingCard(self.logLevelCard)
        debugGroup.addSettingCard(self.openLogFolderCard)
        debugGroup.addSettingCard(self.banOldSwitchCard)
        self.expandLayout.addWidget(debugGroup)

        self.finalise()

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _check_input(self, text, min_val, max_val, config_item, card):
        """验证数值输入并修正。"""
        try:
            value = int(text)
            if isinstance(config_item.validator, type(cfg.auto_close_time.validator).__bases__[-1]):
                pass
            if min_val <= value <= max_val:
                return
        except (ValueError, TypeError):
            pass
        corrected = config_item.validator.correct(text)
        config_item._set(corrected)
        card.setText(str(corrected))

    @staticmethod
    def _openConfigFile():
        try:
            os.startfile(lib.CONFIG_FILE_PATH)
        except Exception as e:
            lib.log.error(f'设置-打开配置文件失败: {e}')
            Notify.error(title='打开配置文件失败', content=str(e))

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
        city_list = lib.read_json(CITY_DB_PATH)
        box = CitySearchBox(city_list, self)
        if box.exec():
            city_id = box.get_selected_city_id()
            display_name = box.get_selected_city_display()
            if city_id:
                old_city_id = cfg.city_id.value
                cfg.set(cfg.city_id, city_id)
                cfg.set(cfg.city_name, display_name)
                self.cityChooseCard.setTitle(f'选择城市(当前: {display_name})')
                if city_id != old_city_id:
                    Notify.success(title=f'已设置城市 {display_name}', content='正在获取天气数据...', parent=self)
                    self._onRefreshWeather()

    @action('天气数据已更新', '获取失败')
    async def _onRefreshWeather(self):
        from core.widgets import WeatherWidget
        w = WeatherWidget()
        return await w.get_data_async(force_refresh=True)

    @action('MC 服务器数据已更新', '刷新失败')
    async def _onRefreshMCServer(self):
        from core.widgets import MCServerStatusWidget
        mc = MCServerStatusWidget()
        return await mc.get_data_async()

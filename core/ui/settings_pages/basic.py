"""基本设置页面。"""

import shutil

from qasync import asyncSlot
from PySide6.QtCore import QTimer
from qfluentwidgets import (ComboBoxSettingCard, FluentIcon as FIF,
                            HyperlinkCard, PrimaryPushSettingCard,
                            PushSettingCard, SettingCardGroup,
                            MessageBox)

from ...base_lib import restart_program, open_target
from ...config import cfg
from ...i18n import get_language_names
from ...logger import log
from ...paths import CACHE_FOLDER_PATH, LOG_FOLDER_PATH
from ...startup import create_shortcut, is_shortcut_exist, remove_shortcut
from ..app import app_manager
from ..ui_widgets import BaseSettingPage, CitySearchBox, Notify
from ..setting_cards import (DateTableEditSettingCard, ExpandGroupCard,
                             ListEditingSettingCard, NumberSettingCard,
                             TextSettingCard, ExtSwitchSettingCard)


class BasicSettingsPage(BaseSettingPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent, object_name='basic_settings_page')

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # ── 基本设置 ──
        self.generalGroup = SettingCardGroup(self.tr('基本设置'), self.contentWidget)

        self.startupCard = ExtSwitchSettingCard(
            FIF.POWER_BUTTON, self.tr('开机自启'), self.tr('是否开机启动'),
            config_item=None, parent=self.generalGroup
        )
        self.startupCard.setChecked(is_shortcut_exist())

        self.autoCloseCard = ExtSwitchSettingCard(
            FIF.CLOSE, self.tr('主窗口自动关闭'),
            self.tr('主窗口在一段后自动关闭，程序结束运行'),
            config_item=cfg.auto_close_switch, parent=self.generalGroup
        )

        self.autoCloseTimeCard = NumberSettingCard(
            config_item=cfg.auto_close_time, icon=FIF.STOP_WATCH,
            title=self.tr('自动关闭时间(单位：秒/s)'),
            content=self.tr('主窗口自动关闭时间(范围：30~300秒，默认60秒)'),
            min_value=30, max_value=300,
            parent=self.generalGroup
        )

        self.closeSettingsActionCard = ComboBoxSettingCard(
            texts=[self.tr('重启到主程序'), self.tr('直接退出')], icon=FIF.CLOSE,
            title=self.tr('关闭设置窗口后的行为'), content=self.tr('重启到主程序或直接退出'),
            configItem=cfg.close_settings_action, parent=self.generalGroup
        )

        languages = get_language_names()
        self.languageCard = ComboBoxSettingCard(
            texts=languages, icon=FIF.LANGUAGE,
            title=self.tr('语言'), content=self.tr('切换程序的显示语言'),
            configItem=cfg.language, parent=self.generalGroup
        )

        self.generalGroup.addSettingCards([
            self.startupCard,
            self.autoCloseCard,
            self.autoCloseTimeCard,
            self.closeSettingsActionCard,
            self.languageCard
        ])
        self.expandLayout.addWidget(self.generalGroup)

        # ── 日期和时间 ──
        self.dateTimeGroup = SettingCardGroup(self.tr('日期和时间'), self.contentWidget)
        self.datetimeSwitchCard = ExtSwitchSettingCard(
            icon=FIF.DATE_TIME, title=self.tr('日期和时间组件'),
            content=self.tr('显示当前的日期、时间以及其他信息'),
            config_item=cfg.datetime_switch, parent=self.dateTimeGroup
        )

        # 创建手风琴组件
        self.dateTimeDetailCard = ExpandGroupCard(
            FIF.MORE, self.tr('日期和时间组件详细配置'),
            self.tr('是否显示农历日期、24节气、节假日'),
            parent=self.dateTimeGroup
        )

        self.lunarDateSwitchCard = ExtSwitchSettingCard(
            icon=FIF.CALENDAR, title=self.tr('显示农历信息'),
            content=self.tr('例如：农历二月十九'),
            config_item=cfg.lunar_date_switch, parent=self.dateTimeDetailCard
        )

        self.solarTermSwitchCard = ExtSwitchSettingCard(
            icon=FIF.LEAF, title=self.tr('显示24节气信息'),
            content=self.tr('例如：谷雨、春分'),
            config_item=cfg.solar_term_switch, parent=self.dateTimeDetailCard
        )

        self.holidaySwitchCard = ExtSwitchSettingCard(
            icon=FIF.CALENDAR, title=self.tr('显示节假日信息'),
            content=self.tr('有节日时显示节日，无节日时显示休息日或工作日'),
            config_item=cfg.holiday_switch, parent=self.dateTimeDetailCard
        )

        self.otherDataSwitchCard = ExtSwitchSettingCard(
            icon=FIF.MESSAGE, title=self.tr('显示其他信息'),
            content=self.tr('今年的第几周、第几天以及今年已过进度'),
            config_item=cfg.other_date_switch, parent=self.dateTimeDetailCard
        )

        self.dateTimeDetailCard.addCards([
            self.lunarDateSwitchCard,
            self.solarTermSwitchCard,
            self.holidaySwitchCard,
            self.otherDataSwitchCard
        ])
        self.dateTimeGroup.addSettingCards([
            self.datetimeSwitchCard,
            self.dateTimeDetailCard
        ])
        self.expandLayout.addWidget(self.dateTimeGroup)

        # ── 天气 ──
        self.weatherGroup = SettingCardGroup(self.tr('天气(需选择城市)'), self.contentWidget)

        self.weatherSwitchCard = ExtSwitchSettingCard(
            icon=FIF.CLOUD, title=self.tr('天气组件'), content=self.tr('显示当前城市的天气信息'),
            config_item=cfg.weather_switch, parent=self.weatherGroup
        )

        # 创建手风琴组件
        self.weatherDetailCard = ExpandGroupCard(
            FIF.MORE, self.tr('天气组件详细配置'), self.tr('数据源、城市、刷新间隔'),
            parent=self.weatherGroup
        )

        self.weatherSourceCard = ComboBoxSettingCard(
            icon=FIF.CLOUD_DOWNLOAD, title=self.tr('数据源'), content=self.tr('设置天气数据源'),
            texts=[self.tr('小米天气'), self.tr('和风天气(需API Host、API Key)')],
            configItem=cfg.weather_source, parent=self.weatherDetailCard
        )

        self.cityChooseCard = PushSettingCard(
            text=self.tr('选择城市'), icon=FIF.SEARCH,
            title=self.tr('选择城市(当前: {city})').format(
                city=cfg.city_name.value[cfg.weather_source.value]),
            content=self.tr('获取天气的城市'), parent=self.weatherDetailCard
        )

        self.weatherRefreshTimeCard = NumberSettingCard(
            icon=FIF.STOP_WATCH, title=self.tr('天气信息刷新间隔(单位：分钟/m)'),
            content=self.tr('天气信息自动刷新时间(范围：15~60分钟，默认30分钟)'),
            config_item=cfg.weather_data_refresh_interval,
            min_value=15, max_value=60, parent=self.weatherDetailCard
        )

        self.weatherRefreshCard = PrimaryPushSettingCard(
            text=self.tr('立即刷新'), icon=FIF.SYNC,
            title=self.tr('刷新天气信息'), content=self.tr('刷新天气信息'),
            parent=self.weatherDetailCard
        )

        self.qweatherApiHostCard = TextSettingCard(
            icon=FIF.CODE, title=self.tr('和风天气API Host'),
            content=self.tr('设置和风天气API Host，从[和风天气开发控制台-设置]获取，例如abc1234xyz.def.qweatherapi.com'),
            config_item=cfg.qweather_api_host, parent=self.weatherDetailCard
        )

        self.qweatherApiKeyCard = TextSettingCard(
            icon=FIF.VPN, title=self.tr('和风天气API Key'),
            content=self.tr('设置和风天气API Key，从[和风天气开发控制台-项目管理]获取'),
            config_item=cfg.qweather_api_key, parent=self.weatherDetailCard
        )

        self.qweatherConsoleCard = HyperlinkCard(
            icon=FIF.COMMAND_PROMPT, title=self.tr('和风天气开发控制台'), text=self.tr('打开'),
            content=self.tr('打开和风天气开发控制台(https://console.qweather.com/home)'),
            url='https://console.qweather.com/home',
            parent=self.weatherDetailCard
        )

        self.weatherDetailCard.addCards([
            self.weatherSourceCard,
            self.cityChooseCard,
            self.weatherRefreshTimeCard,
            self.weatherRefreshCard
        ])
        self.weatherGroup.addSettingCards([
            self.weatherSwitchCard,
            self.weatherDetailCard
        ])
        self.expandLayout.addWidget(self.weatherGroup)
        # 和风天气专属卡片按当前数据源决定是否显示
        self._update_qweather_cards_visibility()

        # ── 倒数日 ──
        self.countdownGroup = SettingCardGroup(self.tr('倒数日'), self.contentWidget)
        self.countdownCard = ExtSwitchSettingCard(
            icon=FIF.CALENDAR, title=self.tr('倒数日组件'),
            content=self.tr('在主窗口显示："距离【xx】还有xx天"'),
            config_item=cfg.countdown_switch, parent=self.countdownGroup
        )

        # 创建手风琴组件
        # self.countdownDetailCard = ExpandGroupCard(
        #     FIF.MORE, self.tr('倒数日组件详细配置'), self.tr('倒数日名称、日期信息'),
        #     parent=self.countdownGroup
        # )
        #
        # self.countdownTextCard = TextSettingCard(
        #     config_item=cfg.countdown_name, icon=FIF.EDIT, title=self.tr('倒数日名称'),
        #     content=self.tr('倒数日名称'), parent=self.countdownDetailCard
        # )
        # self.countdownDateCard = CalendarSettingCard(
        #     icon=FIF.CALENDAR, title=self.tr('倒数目标日期'),
        #     content=self.tr('设置你需要倒计时的日期'), config_item=cfg.countdown_date,
        #     parent=self.countdownDetailCard
        # )
        #
        # self.countdownDetailCard.addCards([
        #     self.countdownTextCard,
        #     self.countdownDateCard
        # ])
        self.countdownDayListCard = DateTableEditSettingCard(
            config_item=cfg.countdown_days_dict, icon=FIF.CALENDAR, title=self.tr('编辑'),
            content=self.tr('添加或删除倒数日，双击表格可修改名称与日期'),
            text=self.tr('编辑倒数日列表'), date_column_name=self.tr('日期'),
            success_text=self.tr('已保存新的倒数日列表'),
            parent=self.countdownGroup
        )

        self.countdownGroup.addSettingCards([
            self.countdownCard,
            self.countdownDayListCard
            # self.countdownDetailCard
        ])
        self.expandLayout.addWidget(self.countdownGroup)

        # ── 生日祝福 ──
        self.birthdayGroup = SettingCardGroup(self.tr('生日祝福(暂不支持多人同天生日)'), self.contentWidget)
        self.birthdayWishesSwitchCard = ExtSwitchSettingCard(
            icon=FIF.CALENDAR, title=self.tr('生日祝福功能'),
            content=self.tr('在生日当天显示生日祝福'),
            config_item=cfg.birthday_wishes_switch, parent=self.birthdayGroup
        )
        self.birthdayListCard = DateTableEditSettingCard(
            config_item=cfg.birthday_dict, icon=FIF.CALENDAR, title=self.tr('编辑'),
            content=self.tr('添加或删除生日记录，双击表格可修改名称与生日'),
            text=self.tr('编辑生日列表'), date_column_name=self.tr('生日'),
            success_text=self.tr('已保存新的生日列表'),
            parent=self.birthdayGroup
        )
        self.birthdayGroup.addSettingCards([
            self.birthdayWishesSwitchCard,
            self.birthdayListCard
        ])
        self.expandLayout.addWidget(self.birthdayGroup)

        # ── Minecraft 服务器检测器 ──
        self.mcServerGroup = SettingCardGroup(
            self.tr('Minecraft Java版服务器玩家在线情况检测'), self.contentWidget)
        self.MCServerCheckSwitchCard = ExtSwitchSettingCard(
            icon=FIF.GLOBE, title=self.tr('Minecraft Java版服务器玩家在线情况检测组件'),
            content=self.tr('快速查看MC服务器玩家在线情况，支持检查朋友在线情况'),
            config_item=cfg.mc_server_info_switch, parent=self.mcServerGroup
        )

        # 手风琴：详细配置收起来
        self.MCDetailCard = ExpandGroupCard(
            FIF.MORE, self.tr('服务器信息详细配置'),
            self.tr('配置服务器名称、IP、端口等信息'),
            parent=self.mcServerGroup
        )
        self.mcServerNameCard = TextSettingCard(
            config_item=cfg.mc_server_name, icon=FIF.GAME,
            title=self.tr('服务器名称'), content=self.tr('Minecraft Java版服务器名称'),
            parent=self.MCDetailCard
        )
        self.mcServerIPCard = TextSettingCard(
            config_item=cfg.mc_server_ip, icon=FIF.CLOUD,
            title=self.tr('服务器IP地址'), content=self.tr('Minecraft Java版服务器IP'),
            parent=self.MCDetailCard
        )
        self.mcServerPortCard = TextSettingCard(
            config_item=cfg.mc_server_port, icon=FIF.INFO,
            title=self.tr('服务器端口号'),
            content=self.tr('Minecraft Java版服务器端口号(一般为25565)'),
            parent=self.MCDetailCard
        )
        self.mcServerDataRefreshIntervalCard = NumberSettingCard(
            config_item=cfg.mc_server_data_refresh_interval,
            icon=FIF.STOP_WATCH,
            title=self.tr('服务器信息刷新间隔(单位：秒/s)'),
            content=self.tr('Minecraft Java版服务器信息自动刷新时间(范围：5~3600秒，默认60秒)'),
            min_value=5, max_value=3600,
            parent=self.MCDetailCard
        )
        self.mcFriendsListCard = ListEditingSettingCard(
            config_item=cfg.mc_server_friends_list, icon=FIF.PEOPLE, title=self.tr('编辑'),
            content=self.tr(r'编辑朋友列表'), text=self.tr('编辑朋友列表'),
            success_text=self.tr('已保存新的朋友列表'), parent=self.MCDetailCard
        )
        self.mcServerDataRefreshCard = PrimaryPushSettingCard(
            text=self.tr('立即刷新'), icon=FIF.SYNC, title=self.tr('立即刷新'),
            content=self.tr('立即刷新Minecraft Java服务器信息'),
            parent=self.MCDetailCard
        )

        self.MCDetailCard.addCards([
            self.mcServerNameCard,
            self.mcServerIPCard,
            self.mcServerPortCard,
            self.mcServerDataRefreshIntervalCard,
            self.mcFriendsListCard,
            self.mcServerDataRefreshCard
        ])
        self.mcServerGroup.addSettingCards([
            self.MCServerCheckSwitchCard,
            self.MCDetailCard
        ])
        self.expandLayout.addWidget(self.mcServerGroup)

        # ── 每日一言 ──
        self.wordsGroup = SettingCardGroup(self.tr('每日一言'), self.contentWidget)
        self.wordsSwitchCard = ExtSwitchSettingCard(
            icon=FIF.MESSAGE, title=self.tr('每日一言组件'), content=self.tr('显示每日一言信息'),
            config_item=cfg.words_switch, parent=self.wordsGroup
        )

        self.wordsDetailCard = ExpandGroupCard(
            FIF.MORE, self.tr('每日一言组件详细配置'),
            self.tr('配置数据来源、打开一言官网(友情链接)'),
            parent=self.wordsGroup
        )

        self.wordsSourceCard = ComboBoxSettingCard(
            texts=[self.tr('一言网'), self.tr('金山词霸')], icon=FIF.SEARCH,
            title=self.tr('每日一言数据来源'), content=self.tr('【金山词霸每日一言】或【一言网】'),
            configItem=cfg.words_source, parent=self.wordsDetailCard
        )

        self.friendlyLinksCard = HyperlinkCard(
            url='https://hitokoto.cn', icon=FIF.HEART,
            title=self.tr('友情链接'), text=self.tr('一言网'),
            content=self.tr('一言网(hitokoto.cn)创立于 2016 年，隶属于萌创团队，目前网站主要提供一句话服务，属于公益性运营，欢迎各位捐助一言网。'),
            parent=self.wordsDetailCard
        )

        self.wordsDetailCard.addCards([
            self.wordsSourceCard,
            self.friendlyLinksCard
        ])
        self.wordsGroup.addSettingCards([
            self.wordsSwitchCard,
            self.wordsDetailCard
        ])
        self.expandLayout.addWidget(self.wordsGroup)

        # ── GitHub仓库状态 ─
        self.githubRepoGroup = SettingCardGroup(
            self.tr('GitHub仓库信息组件(仅支持公开仓库)'), self.contentWidget)
        self.githubRepoSwitchCard = ExtSwitchSettingCard(
            icon=FIF.GITHUB, title=self.tr('GitHub仓库信息组件'),
            content=self.tr('显示Github仓库的名称、star数、fork数等信息'),
            config_item=cfg.github_repo_switch, parent=self.githubRepoGroup
        )

        # 创建手风琴组件
        self.githubRepoDetailCard = ExpandGroupCard(
            FIF.MORE, self.tr('GitHub仓库信息组件详细配置'),
            self.tr('仓库作者名、仓库名、数据刷新间隔'),
            parent=self.githubRepoGroup
        )

        self.repoOwnerCard = TextSettingCard(
            icon=FIF.PEOPLE, title=self.tr('仓库作者'),
            content=self.tr('仓库作者的名称'),
            config_item=cfg.github_repo_owner, parent=self.githubRepoDetailCard
        )

        self.repoNameCard = TextSettingCard(
            icon=FIF.MESSAGE, title=self.tr('仓库名称'),
            content=self.tr('仓库名称'),
            config_item=cfg.github_repo_name, parent=self.githubRepoDetailCard
        )

        self.repoDataRefreshTimeCard = NumberSettingCard(
            icon=FIF.STOP_WATCH, title=self.tr('GitHub仓库信息刷新间隔(单位：小时/h)'),
            content=self.tr('GitHub仓库信息自动刷新时间(范围：1~24小时(1天)，默认1小时)'),
            config_item=cfg.github_repo_data_refresh_interval,
            min_value=1, max_value=24, parent=self.githubRepoDetailCard
        )

        self.repoRefreshCard = PrimaryPushSettingCard(
            text=self.tr('立即刷新'), icon=FIF.SYNC,
            title=self.tr('刷新GitHub仓库信息'), content=self.tr('刷新GitHub仓库信息'),
            parent=self.githubRepoDetailCard
        )

        self.githubRepoDetailCard.addCards([
            self.repoOwnerCard,
            self.repoNameCard,
            self.repoDataRefreshTimeCard,
            self.repoRefreshCard
        ])
        self.githubRepoGroup.addSettingCards([
            self.githubRepoSwitchCard,
            self.githubRepoDetailCard
        ])
        self.expandLayout.addWidget(self.githubRepoGroup)

        # ── 其他信息 ──
        self.otherGroup = SettingCardGroup(self.tr('其他组件'), self.contentWidget)

        # 创建手风琴组件
        self.otherDetailCard = ExpandGroupCard(
            FIF.MORE, self.tr('其他组件开关'),
            self.tr('问候语、开机次数、时间和日期等组件'),
            parent=self.otherGroup
        )

        self.greetingSwitchCard = ExtSwitchSettingCard(
            icon=FIF.HEART, title=self.tr('问候语组件'),
            content=self.tr('显示当前时间对应的问候语'),
            config_item=cfg.greeting_switch, parent=self.otherDetailCard
        )

        self.startupTimesSwitchCard = ExtSwitchSettingCard(
            icon=FIF.POWER_BUTTON, title=self.tr('开机次数组件'),
            content=self.tr('显示开机次数'), config_item=cfg.startup_times_switch,
            parent=self.otherDetailCard
        )

        self.historicalSwitchCard = ExtSwitchSettingCard(
            icon=FIF.HISTORY, title=self.tr('历史上的今天组件'),
            content=self.tr('显示历史上的今天信息'),
            config_item=cfg.historical_switch, parent=self.otherDetailCard
        )

        self.dailyCharacterSwitchCard = ExtSwitchSettingCard(
            icon=FIF.EXPRESSIVE_INPUT_ENTRY, title=self.tr('每日人品组件'),
            content=self.tr('显示每日人品'),
            config_item=cfg.daily_character_switch, parent=self.otherDetailCard
        )

        self.otherDetailCard.addCards([
            self.greetingSwitchCard,
            self.startupTimesSwitchCard,
            self.historicalSwitchCard,
            self.dailyCharacterSwitchCard
        ])
        self.otherGroup.addSettingCard(self.otherDetailCard)
        self.expandLayout.addWidget(self.otherGroup)

        # ── 调试 ──
        self.debugGroup = SettingCardGroup(self.tr('调试'), self.contentWidget)

        self.deleteCaCheCard = PrimaryPushSettingCard(
            icon=FIF.DELETE, title=self.tr('删除缓存'),
            content=self.tr('删除程序在运行中产生的缓存数据'), text=self.tr('立即删除'),
            parent=self.debugGroup
        )

        self.logLevelCard = ComboBoxSettingCard(
            icon=FIF.ALIGNMENT, title=self.tr('日志等级'),
            content=self.tr('调整程序的日志等级，重启后生效'),
            texts=cfg.LOG_LEVELS, configItem=cfg.log_level, parent=self.debugGroup
        )

        self.openLogFolderCard = PrimaryPushSettingCard(
            text=self.tr('打开日志文件夹'), icon=FIF.FOLDER,
            title=self.tr('打开日志文件夹'), content=self.tr('打开程序日志文件夹'),
            parent=self.debugGroup
        )

        self.debugGroup.addSettingCards([
            self.deleteCaCheCard,
            self.logLevelCard,
            self.openLogFolderCard
        ])
        self.expandLayout.addWidget(self.debugGroup)

        self.finalise()

    def _connect_signals(self):
        """连接信号与槽。"""
        self.startupCard.checkedChanged.connect(self._onStartupChanged)
        self.deleteCaCheCard.clicked.connect(self._onDeleteCaCheClicked)
        cfg.weather_source.valueChanged.connect(self._onWeatherSourceChanged)
        cfg.weather_source.valueChanged.connect(self._update_qweather_cards_visibility)
        self.cityChooseCard.clicked.connect(self._onCityChooseClicked)
        self.weatherRefreshCard.clicked.connect(self._onRefreshWeather)
        self.mcServerDataRefreshCard.clicked.connect(self._onRefreshMCServer)
        cfg.words_source.valueChanged.connect(self._onWordsSourceChanged)
        cfg.language.valueChanged.connect(self._onLanguageChanged)
        self.repoRefreshCard.clicked.connect(self._onRefreshGitHubRepo)
        self.openLogFolderCard.clicked.connect(self._onOpenLogFolderClicked)

    # ------------------------------------------------------------------
    # 槽函数
    # ------------------------------------------------------------------

    def _onLanguageChanged(self, language: str):
        """语言卡片选择后（qfw 卡片已自动保存配置）热重载翻译器。

        已打开窗口的文案在构造时已固化，不会随翻译器刷新，
        询问用户是否立即重启以完全应用新语言。
        """
        if not app_manager.switch_language(language):
            Notify.error(self.tr('语言切换失败，请查看日志'), parent=self)
            return

        self.box = MessageBox(self.tr('切换语言'), self.tr('语言将在重启后完全生效，是否立即重启？'), self)
        self.box.yesButton.setText(self.tr('立即重启'))
        self.box.cancelButton.setText(self.tr('稍后重启'))
        if self.box.exec():
            restart_program('--settings')

    def _onStartupChanged(self, is_enabled: bool):
        if is_enabled:
            if create_shortcut():
                Notify.success(content=self.tr('已添加开机启动项'), parent=self)
            else:
                Notify.error(content=self.tr('添加开机启动项失败，请查看日志'), parent=self)
        else:
            if remove_shortcut():
                Notify.success(content=self.tr('已删除开机启动项'), parent=self)
            else:
                Notify.error(content=self.tr('删除开机启动项失败，请查看日志'), parent=self)

    def _onOpenLogFolderClicked(self) -> None:
        if LOG_FOLDER_PATH.exists():
            open_target(LOG_FOLDER_PATH)
            Notify.success(self.tr('已打开日志文件夹'), parent=self)

        else:
            Notify.error(self.tr('日志文件夹不存在'), parent=self)

    def _onDeleteCaCheClicked(self) -> bool | None:
        if CACHE_FOLDER_PATH.exists():
            shutil.rmtree(CACHE_FOLDER_PATH)

            # 复位初始化标记，使后续缓存写入能在下次 init_db 时重建目录与表
            from ...widgets import CacheManager
            CacheManager.reset()
            log.info('已删除缓存')
            Notify.success(self.tr('已删除缓存'), parent=self)
            return True

        else:
            Notify.info(content=self.tr('未发现缓存'), parent=self)
            return None

    def _onCityChooseClicked(self) -> None:
        box = CitySearchBox(self)
        if box.exec():
            city_id = box.get_selected_city_id()
            display_name = box.get_selected_city_display()
            if city_id:
                # city_id / city_name 按数据提供方分别存储
                source = box.weather_source
                city_ids = dict(cfg.city_id.value)
                old_city_id = city_ids.get(source)
                city_ids[source] = city_id

                city_names = dict(cfg.city_name.value)
                city_names[source] = display_name

                cfg.set(cfg.city_id, city_ids, save=True)
                cfg.set(cfg.city_name, city_names, save=True)
                self.cityChooseCard.setTitle(
                    self.tr('选择城市(当前: {city})').format(city=display_name))
                if city_id != old_city_id:
                    Notify.success(
                        title=self.tr('已设置城市 {city}').format(city=display_name),
                        content=self.tr('正在获取天气信息...'),
                        parent=self
                    )
                    self._onRefreshWeather()

    def _update_qweather_cards_visibility(self):
        """和风天气专属配置卡片仅在数据源为和风天气时显示。"""
        show = cfg.weather_source.value == 'qweather'
        changed = False
        for card in (self.qweatherApiHostCard,
                     self.qweatherApiKeyCard,
                     self.qweatherConsoleCard):
            in_list = card in self.weatherDetailCard.widgets
            if show and not in_list:
                self.weatherDetailCard.addGroupWidget(card)
                card.show()
                changed = True
            elif not show and in_list:
                self.weatherDetailCard.removeGroupWidget(card)
                # removeGroupWidget 只会从布局移除，不会隐藏控件，
                # 若不隐藏，卡片会以浮动子控件的形式叠在手风琴左上角
                card.hide()
                changed = True
            elif not show:
                card.hide()

        if changed:
            QTimer.singleShot(0, self._refresh_weather_detail_layout)

    def _refresh_weather_detail_layout(self):
        """卡片增删后重算手风琴与天气分组高度，触发布局重排。

        手风琴展开时高度由内部动画驱动，内容变化后不会自动更新；
        这里直接按内部视图的实际 sizeHint 重设固定高度并复位滚动条，
        再让天气分组 adjustSize，使页面 ExpandLayout 重排下方卡片。
        注意：库自带的 _adjustViewSize 用的是各控件未受约束的 sizeHint
        （固定高度卡片会偏小），故不用它，改取 viewLayout 的 sizeHint。
        """
        acc = self.weatherDetailCard
        acc.expandAni.stop()

        acc.viewLayout.activate()
        content_h = acc.viewLayout.sizeHint().height()
        acc.spaceWidget.setFixedHeight(content_h)

        if acc.isExpand:
            acc.verticalScrollBar().setValue(0)
            acc.setFixedHeight(acc.card.height() + content_h)
        else:
            acc.setFixedHeight(acc.card.height())

        self.weatherGroup.adjustSize()
        self.weatherGroup.updateGeometry()

    @asyncSlot()
    async def _onWeatherSourceChanged(self):
        from ...widgets import WeatherWidget
        widget = WeatherWidget()
        cache_source = widget.get_cached_source()

        # 如果选择的数据源和缓存的数据源不一致
        if widget.DATA_SOURCE != cache_source:
            # 更新当前选择的城市
            self.cityChooseCard.setTitle(
                self.tr('选择城市(当前: {city})').format(
                    city=cfg.city_name.value[widget.DATA_SOURCE]))
            # 如果对应数据源的city_id未配置
            city_ids = cfg.city_id.value
            city_names = cfg.city_name.value
            data_source = widget.DATA_SOURCE
            if not city_ids.get(data_source) or not city_names.get(data_source):
                Notify.info(content=self.tr('更换天气数据源后请重新选择城市'), parent=self)

            # 和风天气需先配置 API Host 和 API Key
            if data_source == 'qweather':
                if not (cfg.qweather_api_host.value.strip() and cfg.qweather_api_key.value.strip()):
                    Notify.warning(self.tr('未填写API Host或API Key'), parent=self)
                    return

            # 两个数据源切换后都立即刷新，行为保持一致
            self.weatherSourceCard.setEnabled(False)
            self.weatherRefreshCard.setEnabled(False)
            try:
                await widget.get_data_async(force_refresh=True)
                self._notify_widget_result(
                    widget, self.tr('天气信息更新成功'), self.tr('天气信息更新失败'))

            except Exception as e:
                log.error(f'设置-天气信息更新失败：{e}')
                Notify.error(
                    content=self.tr('未知错误：{error}').format(error=e),
                    title=self.tr('天气信息更新失败'), parent=self)

            finally:
                self.weatherSourceCard.setEnabled(True)
                self.weatherRefreshCard.setEnabled(True)

    @asyncSlot()
    async def _onRefreshWeather(self):
        from ...widgets import WeatherWidget
        widget = WeatherWidget()
        # 如果数据源是和风天气，检查API Host和API Key是否可用
        if widget.DATA_SOURCE == 'qweather':
            if not (cfg.qweather_api_host.value.strip() and cfg.qweather_api_key.value.strip()):
                Notify.warning(self.tr('未填写API Host或API Key'), parent=self)
                return

        self.weatherRefreshCard.setEnabled(False)
        try:
            await widget.get_data_async(force_refresh=True)
            self._notify_widget_result(
                widget, self.tr('天气信息更新成功'), self.tr('天气信息更新失败'))

        except Exception as e:
            log.error(f'设置-天气信息更新失败：{e}')
            Notify.error(content=self.tr('未知错误：{error}').format(error=e),
                         title=self.tr('天气信息更新失败'), parent=self)

        finally:
            self.weatherRefreshCard.setEnabled(True)

    @asyncSlot()
    async def _onRefreshMCServer(self):
        self.mcServerDataRefreshCard.setEnabled(False)
        from ...widgets import MCServerError, MCServerInfoWidget
        try:
            mc = MCServerInfoWidget()
            data = await mc.get_data_async(force_refresh=True)

            # 成功提示中附带在线朋友信息（≤3 个时列出名单）
            content = self.tr('MC 服务器信息已更新')
            online_friends = (data or {}).get('mc_online_friends') or []
            if online_friends:
                friend_count = len(online_friends)
                if friend_count <= 3:
                    content += self.tr('，当前有 {count} 个朋友在线：{friends}').format(
                        count=friend_count, friends='、'.join(online_friends))
                else:
                    content += self.tr('，当前有 {count} 个朋友在线').format(count=friend_count)
            Notify.success(content=content, parent=self)

        except MCServerError as e:
            log.error(f'设置-MC 服务器信息更新失败：{e}')
            Notify.error(content=str(e), title=self.tr('MC 服务器信息更新失败'), parent=self)

        except Exception as e:
            log.error(f'设置-MC 服务器信息更新失败：{e}')
            Notify.error(content=self.tr('未知错误：{error}').format(error=e),
                         title=self.tr('MC 服务器信息更新失败'), parent=self)

        finally:
            self.mcServerDataRefreshCard.setEnabled(True)

    @asyncSlot()
    async def _onRefreshGitHubRepo(self):
        from ...widgets import GitHubRepoInfoWidget
        # 未填写仓库作者或仓库名称时不予刷新，弹警告
        if not (cfg.github_repo_owner.value.strip() and cfg.github_repo_name.value.strip()):
            Notify.warning(self.tr('请先填写仓库作者和仓库名称'), parent=self)
            return

        self.repoRefreshCard.setEnabled(False)
        try:
            widget = GitHubRepoInfoWidget()
            await widget.get_data_async(force_refresh=True)
            self._notify_widget_result(
                widget, self.tr('GitHub仓库信息更新成功'), self.tr('GitHub仓库信息更新失败'))

        except Exception as e:
            log.error(f'设置-GitHub仓库信息更新失败：{e}')
            Notify.error(content=self.tr('未知错误：{error}').format(error=e),
                         title=self.tr('GitHub仓库信息更新失败'), parent=self)

        finally:
            self.repoRefreshCard.setEnabled(True)

    def _notify_widget_result(self, widget, success_msg: str, fail_title: str) -> None:
        """根据组件获取结果弹提示：组件记录有错误信息则弹错误，否则弹成功。"""
        if getattr(widget, 'last_error', ''):
            Notify.error(content=widget.last_error, title=fail_title, parent=self)
        else:
            Notify.success(content=success_msg, parent=self)

    @asyncSlot()
    async def _onWordsSourceChanged(self):
        from ...widgets import DailyWordsWidget
        widget = DailyWordsWidget()
        cache_source = widget.get_cached_source()
        # 如果选择的数据源和缓存的数据源不一致
        if widget.DATA_SOURCE != cache_source:
            self.wordsSourceCard.setEnabled(False)
            # 开始刷新每日一言信息
            try:
                await widget.get_data_async(force_refresh=True)
                self._notify_widget_result(
                    widget, self.tr('每日一言信息更新成功'), self.tr('每日一言信息更新失败'))

            except Exception as e:
                log.error(f'设置-每日一言信息更新失败：{e}')
                Notify.error(content=self.tr('未知错误：{error}').format(error=e),
                             title=self.tr('每日一言信息更新失败'), parent=self)

            finally:
                self.wordsSourceCard.setEnabled(True)
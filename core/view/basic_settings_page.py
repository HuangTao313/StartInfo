"""基本设置页面。"""

import os
import shutil

from qasync import asyncSlot
from qfluentwidgets import (ComboBoxSettingCard, FluentIcon as FIF,
                            HyperlinkCard, PrimaryPushSettingCard,
                            PushSettingCard, SettingCardGroup)

from .ui_widgets import (BirthdayEditBox, CalendarSettingCard, CitySearchBox,
                         ExpandGroupCard, ListEditingBox, Notify, TextSettingCard,
                         ExtSwitchSettingCard, BaseSettingPage)
from .. import base_lib as lib
from ..config import cfg, qconfig
from ..startup import create_shortcut, is_shortcut_exist, remove_shortcut
from ..ui import log


class BasicSettingsPage(BaseSettingPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent, object_name='basic_settings_page')

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # ── 基本设置 ──
        generalGroup = SettingCardGroup('基本设置', self.contentWidget)

        self.startupCard = ExtSwitchSettingCard(
            FIF.POWER_BUTTON, '开机自启', '是否开机启动',
            config_item=None, parent=generalGroup
        )
        self.startupCard.setChecked(is_shortcut_exist())

        self.autoCloseCard = ExtSwitchSettingCard(
            FIF.CLOSE, '主窗口自动关闭', '主窗口在一段后自动关闭，程序结束运行',
            config_item=cfg.auto_close_switch, parent=generalGroup
        )

        self.autoCloseTimer = TextSettingCard(
            config_item=cfg.auto_close_time, icon=FIF.STOP_WATCH,
            title='自动关闭时间(单位：秒/s)',
            content='主窗口自动关闭时间(范围：30~300秒，默认60秒)',
            parent=generalGroup
        )

        self.closeSettingsAction = ComboBoxSettingCard(
            texts=['重启到主程序', '直接退出'], icon=FIF.CLOSE,
            title='关闭设置窗口后的行为', content='重启到主程序或直接退出',
            configItem=cfg.close_settings_action, parent=generalGroup
        )

        self.deleteDownloadTempCard = PrimaryPushSettingCard(
            icon=FIF.DELETE, title='删除下载缓存',
            content='删除因程序更新下载的临时文件', text='立即删除',
            parent=generalGroup
        )

        generalGroup.addSettingCards([
            self.startupCard,
            self.autoCloseCard,
            self.autoCloseTimer,
            self.closeSettingsAction,
            self.deleteDownloadTempCard
        ])
        self.expandLayout.addWidget(generalGroup)

        # ── 日期和时间 ──
        dateTimeGroup = SettingCardGroup('日期和时间', self.contentWidget)
        self.datetimeSwitchCard = ExtSwitchSettingCard(
            icon=FIF.DATE_TIME, title='日期和时间组件',
            content='显示当前的日期、时间以及其他信息',
            config_item=cfg.datetime_switch, parent=dateTimeGroup
        )

        # 创建手风琴组件
        self.dateTimeDetailCard = ExpandGroupCard(
            FIF.MORE, '日期和时间组件详细配置', '是否显示农历日期、24节气、节假日',
            parent=dateTimeGroup
        )

        self.lunarDateSwitchCard = ExtSwitchSettingCard(
            icon=FIF.CALENDAR, title='显示农历信息', content='例如：农历二月十九',
            config_item=cfg.lunar_date_switch, parent=self.dateTimeDetailCard
        )

        self.solarTermSwitchCard = ExtSwitchSettingCard(
            icon=FIF.LEAF, title='显示24节气信息', content='例如：谷雨、春分',
            config_item=cfg.solar_term_switch, parent=self.dateTimeDetailCard
        )

        self.holidaySwitchCard = ExtSwitchSettingCard(
            icon=FIF.CALENDAR, title='显示节假日信息',
            content='有节日时显示节日，无节日时显示休息日或工作日',
            config_item=cfg.holiday_switch, parent=self.dateTimeDetailCard
        )

        self.otherDataSwitchCard = ExtSwitchSettingCard(
            icon=FIF.MESSAGE, title='显示其他信息',
            content='今年的第几周、第几天以及今年已过进度',
            config_item=cfg.other_date_switch, parent=self.dateTimeDetailCard
        )

        self.dateTimeDetailCard.addCards([
            self.lunarDateSwitchCard,
            self.solarTermSwitchCard,
            self.holidaySwitchCard,
            self.otherDataSwitchCard
        ])
        dateTimeGroup.addSettingCards([
            self.datetimeSwitchCard,
            self.dateTimeDetailCard
        ])
        self.expandLayout.addWidget(dateTimeGroup)

        # ── 天气 ──
        weatherGroup = SettingCardGroup('天气(需选择城市)', self.contentWidget)

        self.weatherSwitchCard = ExtSwitchSettingCard(
            icon=FIF.CLOUD, title='天气组件', content='显示当前城市的天气信息',
            config_item=cfg.weather_switch, parent=weatherGroup
        )

        # 创建手风琴组件
        self.weatherDetailCard = ExpandGroupCard(
            FIF.MORE, '天气组件详细配置', '数据源、城市、刷新间隔',
            parent=weatherGroup
        )

        self.weatherSourceCard = ComboBoxSettingCard(
            icon=FIF.CLOUD_DOWNLOAD, title='数据源', content='设置天气数据源',
            texts=['小米天气', '和风天气(需API Host、API Key)'],
            configItem=cfg.weather_source, parent=self.weatherDetailCard
        )

        self.cityChooseCard = PushSettingCard(
            text='选择城市', icon=FIF.SEARCH,
            title=f'选择城市(当前: {cfg.city_name.value[cfg.weather_source.value]})',
            content='获取天气的城市', parent=self.weatherDetailCard
        )

        self.weatherRefreshTimeCard = TextSettingCard(
            icon=FIF.STOP_WATCH, title='天气信息刷新间隔(单位：分钟/m)',
            content='天气信息自动刷新时间(范围：15~60分钟，默认30分钟)',
            config_item=cfg.weather_data_refresh_interval, parent=self.weatherDetailCard
        )

        self.weatherRefreshCard = PrimaryPushSettingCard(
            text='立即刷新', icon=FIF.SYNC,
            title='刷新天气信息', content='刷新天气信息',
            parent=self.weatherDetailCard
        )

        self.qweatherApiHostCard = TextSettingCard(
            icon=FIF.CODE, title='和风天气API Host',
            content='设置和风天气API Host，从[和风天气开发控制台-设置]获取，例如abc1234xyz.def.qweatherapi.com',
            config_item=cfg.qweather_api_host, parent=self.weatherDetailCard
        )

        self.qweatherApiKeyCard = TextSettingCard(
            icon=FIF.VPN, title='和风天气API Key',
            content='设置和风天气API Key，从[和风天气开发控制台-项目管理]获取',
            config_item=cfg.qweather_api_key, parent=self.weatherDetailCard
        )

        self.qweatherConsoleCard = HyperlinkCard(
            icon=FIF.COMMAND_PROMPT, title='和风天气开发控制台', text='打开',
            content='打开和风天气开发控制台(https://console.qweather.com/home?lang=zh)',
            url='https://console.qweather.com/home?lang=zh',
            parent=self.weatherDetailCard
        )

        self.weatherDetailCard.addCards([
            self.weatherSourceCard,
            self.cityChooseCard,
            self.weatherRefreshTimeCard,
            self.weatherRefreshCard,
            self.qweatherApiHostCard,
            self.qweatherApiKeyCard,
            self.qweatherConsoleCard
        ])
        weatherGroup.addSettingCards([
            self.weatherSwitchCard,
            self.weatherDetailCard
        ])
        self.expandLayout.addWidget(weatherGroup)

        # ── 倒数日 ──
        countdownGroup = SettingCardGroup('倒数日', self.contentWidget)
        self.countdownCard = ExtSwitchSettingCard(
            icon=FIF.CALENDAR, title='倒数日组件',
            content='在主窗口显示："距离【xx】还有xx天"',
            config_item=cfg.countdown_switch, parent=countdownGroup
        )

        # 创建手风琴组件
        self.countdownDetailCard = ExpandGroupCard(
            FIF.MORE, '倒数日组件详细配置', '倒数日名称、日期信息',
            parent=countdownGroup
        )

        self.countdownTextCard = TextSettingCard(
            config_item=cfg.countdown_name, icon=FIF.EDIT, title='倒数日名称',
            content='倒数日名称', parent=self.countdownDetailCard
        )
        self.countdownDateCard = CalendarSettingCard(
            icon=FIF.CALENDAR, title='倒数目标日期',
            content='设置你需要倒计时的日期', config_item=cfg.countdown_date,
            parent=self.countdownDetailCard
        )

        self.countdownDetailCard.addCards([
            self.countdownTextCard,
            self.countdownDateCard
        ])
        countdownGroup.addSettingCards([
            self.countdownCard,
            self.countdownDetailCard
        ])
        self.expandLayout.addWidget(countdownGroup)

        # ── 生日祝福 ──
        birthdayGroup = SettingCardGroup('生日祝福(暂不支持多人同天生日)', self.contentWidget)
        self.birthdayWishesSwitchCard = ExtSwitchSettingCard(
            icon=FIF.CALENDAR, title='生日祝福功能',
            content='在生日当天显示生日祝福',
            config_item=cfg.birthday_wishes_switch, parent=birthdayGroup
        )
        self.birthdayListCard = PrimaryPushSettingCard(
            text='编辑生日列表', icon=FIF.CALENDAR, title='编辑',
            content='添加或删除生日记录，双击表格可修改名称与生日',
            parent=birthdayGroup
        )
        birthdayGroup.addSettingCards([
            self.birthdayWishesSwitchCard,
            self.birthdayListCard
        ])
        self.expandLayout.addWidget(birthdayGroup)

        # ── Minecraft 服务器检测器 ──
        mcServerGroup = SettingCardGroup('Minecraft Java版服务器玩家在线情况检测', self.contentWidget)
        self.MCServerCheckSwitchCard = ExtSwitchSettingCard(
            icon=FIF.GLOBE, title='Minecraft Java版服务器玩家在线情况检测组件',
            content='快速查看MC服务器玩家在线情况，支持检查朋友在线情况',
            config_item=cfg.mc_server_info_switch, parent=mcServerGroup
        )

        # 手风琴：详细配置收起来
        self.MCDetailCard = ExpandGroupCard(
            FIF.MORE, '服务器信息详细配置', '配置服务器名称、IP、端口等信息',
            parent=mcServerGroup
        )
        self.mcServerNameCard = TextSettingCard(
            config_item=cfg.mc_server_name, icon=FIF.GAME,
            title='服务器名称', content='Minecraft Java版服务器名称',
            parent=self.MCDetailCard
        )
        self.mcServerIPCard = TextSettingCard(
            config_item=cfg.mc_server_ip, icon=FIF.CLOUD,
            title='服务器IP地址', content='Minecraft Java版服务器IP',
            parent=self.MCDetailCard
        )
        self.mcServerPortCard = TextSettingCard(
            config_item=cfg.mc_server_port, icon=FIF.INFO,
            title='服务器端口号',
            content='Minecraft Java版服务器端口号(一般为25565)',
            parent=self.MCDetailCard
        )
        self.mcServerDataRefreshIntervalCard = TextSettingCard(
            config_item=cfg.mc_server_data_refresh_interval,
            icon=FIF.STOP_WATCH,
            title='服务器信息刷新间隔(单位：秒/s)',
            content='Minecraft Java版服务器信息自动刷新时间(范围：5~3600秒，默认60秒)',
            parent=self.MCDetailCard
        )
        self.mcFriendsListCard = PrimaryPushSettingCard(
            text='编辑朋友列表', icon=FIF.PEOPLE, title='编辑',
            content=r'编辑朋友列表', parent=self.MCDetailCard
        )
        self.mcServerDataRefreshCard = PrimaryPushSettingCard(
            text='立即刷新', icon=FIF.SYNC, title='立即刷新',
            content='立即刷新Minecraft Java服务器信息',
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
        mcServerGroup.addSettingCards([
            self.MCServerCheckSwitchCard,
            self.MCDetailCard
        ])
        self.expandLayout.addWidget(mcServerGroup)

        # ── 每日一言 ──
        wordsGroup = SettingCardGroup('每日一言', self.contentWidget)
        self.wordsSwitchCard = ExtSwitchSettingCard(
            icon=FIF.MESSAGE, title='每日一言组件', content='显示每日一言信息',
            config_item=cfg.words_switch, parent=wordsGroup
        )

        self.wordsDetailCard = ExpandGroupCard(
            FIF.MORE, '每日一言组件详细配置', '配置数据来源、打开一言官网(友情链接)',
            parent=wordsGroup
        )

        self.wordsSourceCard = ComboBoxSettingCard(
            texts=['一言网', '金山词霸'], icon=FIF.SEARCH,
            title='每日一言数据来源', content='【金山词霸每日一言】或【一言网】',
            configItem=cfg.words_source, parent=self.wordsDetailCard
        )

        self.friendlyLinksCard = HyperlinkCard(
            url='https://hitokoto.cn', icon=FIF.HEART,
            title='友情链接', text='一言网',
            content='一言网(hitokoto.cn)创立于 2016 年，隶属于萌创团队，目前网站主要提供一句话服务，属于公益性运营，欢迎各位捐助一言网。',
            parent=self.wordsDetailCard
        )

        self.wordsDetailCard.addCards([
            self.wordsSourceCard,
            self.friendlyLinksCard
        ])
        wordsGroup.addSettingCards([
            self.wordsSwitchCard,
            self.wordsDetailCard
        ])
        self.expandLayout.addWidget(wordsGroup)

        # ── GitHub仓库状态 ─
        githubRepoGroup = SettingCardGroup('GitHub仓库信息组件(仅支持公开仓库)', self.contentWidget)
        self.githubRepoSwitchCard = ExtSwitchSettingCard(
            icon=FIF.GITHUB, title='GitHub仓库信息组件',
            content='显示Github仓库的名称、star数、fork数等信息',
            config_item=cfg.github_repo_switch, parent=githubRepoGroup
        )

        # 创建手风琴组件
        self.githubRepoDetailCard = ExpandGroupCard(
            FIF.MORE, 'GitHub仓库信息组件详细配置', '仓库作者名、仓库名、数据刷新间隔',
            parent=githubRepoGroup
        )

        self.repoOwnerCard = TextSettingCard(
            icon=FIF.PEOPLE, title='仓库作者',
            content='仓库作者的名称',
            config_item=cfg.github_repo_owner, parent=self.githubRepoDetailCard
        )

        self.repoNameCard = TextSettingCard(
            icon=FIF.MESSAGE, title='仓库名称',
            content='仓库名称',
            config_item=cfg.github_repo_name, parent=self.githubRepoDetailCard
        )

        self.repoDataRefreshTimeCard = TextSettingCard(
            icon=FIF.STOP_WATCH, title='GitHub仓库信息刷新间隔(单位：小时/h)',
            content='GitHub仓库信息自动刷新时间(范围：1~24小时(1天)，默认1小时)',
            config_item=cfg.github_repo_data_refresh_interval, parent=self.githubRepoDetailCard
        )

        self.repoRefreshCard = PrimaryPushSettingCard(
            text='立即刷新', icon=FIF.SYNC,
            title='刷新GitHub仓库信息', content='刷新GitHub仓库信息',
            parent=self.githubRepoDetailCard
        )

        self.githubRepoDetailCard.addCards([
            self.repoOwnerCard,
            self.repoNameCard,
            self.repoDataRefreshTimeCard,
            self.repoRefreshCard
        ])
        githubRepoGroup.addSettingCards([
            self.githubRepoSwitchCard,
            self.githubRepoDetailCard
        ])
        self.expandLayout.addWidget(githubRepoGroup)

        # ── 其他信息 ──
        otherGroup = SettingCardGroup('其他组件', self.contentWidget)

        # 创建手风琴组件
        self.otherDetailCard = ExpandGroupCard(
            FIF.MORE, '其他组件开关', '问候语、开机次数、时间和日期等组件',
            parent=otherGroup
        )

        self.greetingSwitchCard = ExtSwitchSettingCard(
            icon=FIF.HEART, title='问候语组件',
            content='显示当前时间对应的问候语',
            config_item=cfg.greeting_switch, parent=self.otherDetailCard
        )

        self.startupTimesSwitchCard = ExtSwitchSettingCard(
            icon=FIF.POWER_BUTTON, title='开机次数组件',
            content='显示开机次数', config_item=cfg.startup_times_switch,
            parent=self.otherDetailCard
        )

        self.historicalSwitchCard = ExtSwitchSettingCard(
            icon=FIF.HISTORY, title='历史上的今天组件',
            content='显示历史上的今天信息',
            config_item=cfg.historical_switch, parent=self.otherDetailCard
        )

        self.dailyCharacterSwitchCard = ExtSwitchSettingCard(
            icon=FIF.EXPRESSIVE_INPUT_ENTRY, title='每日人品组件',
            content='显示每日人品',
            config_item=cfg.daily_character_switch, parent=self.otherDetailCard
        )

        self.otherDetailCard.addCards([
            self.greetingSwitchCard,
            self.startupTimesSwitchCard,
            self.historicalSwitchCard,
            self.dailyCharacterSwitchCard
        ])
        otherGroup.addSettingCard(self.otherDetailCard)
        self.expandLayout.addWidget(otherGroup)

        # ── 调试 ──
        debugGroup = SettingCardGroup('调试', self.contentWidget)
        self.logLevelCard = ComboBoxSettingCard(
            icon=FIF.ALIGNMENT, title='日志等级',
            content='调整程序的日志等级，重启后生效',
            texts=cfg.LOG_LEVELS, configItem=cfg.log_level, parent=debugGroup
        )
        self.openLogFolderCard = PrimaryPushSettingCard(
            text='打开日志文件夹', icon=FIF.FOLDER,
            title='打开日志文件夹', content='打开程序日志文件夹',
            parent=debugGroup
        )

        debugGroup.addSettingCards([
            self.logLevelCard,
            self.openLogFolderCard
        ])
        self.expandLayout.addWidget(debugGroup)

        self.finalise()

    def _connect_signals(self):
        """连接信号与槽。"""
        self.startupCard.checkedChanged.connect(self._onStartupChanged)
        self.autoCloseTimer.textChanged.connect(self._onAutoCloseTimeChanged)
        self.deleteDownloadTempCard.clicked.connect(self._onDeleteDownloadTempClicked)
        cfg.weather_source.valueChanged.connect(self._onWeatherSourceChanged)
        self.cityChooseCard.clicked.connect(self._onCityChooseClicked)
        self.weatherRefreshTimeCard.textChanged.connect(self._onWeatherRefreshTimeChanged)
        self.weatherRefreshCard.clicked.connect(self._onRefreshWeather)
        self.birthdayListCard.clicked.connect(self._onEditBirthdayList)
        self.mcServerDataRefreshIntervalCard.textChanged.connect(
            self._onMcServerDataRefreshIntervalChanged
        )
        self.mcFriendsListCard.clicked.connect(self._onEditFriendsList)
        self.mcServerDataRefreshCard.clicked.connect(self._onRefreshMCServer)
        cfg.words_source.valueChanged.connect(self._onWordsSourceChanged)
        self.repoDataRefreshTimeCard.textChanged.connect(
            self._onGitHubRepoRefreshTimeChanged
        )
        self.repoRefreshCard.clicked.connect(self._onRefreshGitHubRepo)
        self.openLogFolderCard.clicked.connect(self._onOpenLogFolderClicked)

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
                parent=self
            )
            card.setText(str(config_item.value))
            return

        if not min_val <= value <= max_val:
            Notify.warning(
                title='输入错误',
                content=f'请输入 {min_val}~{max_val} 之间的值，已恢复为 {config_item.value}',
                parent=self
            )
            card.setText(str(config_item.value))

    def _openConfigFile(self):
        try:
            os.startfile(lib.CONFIG_FILE_PATH)
        except Exception as e:
            log.error(f'设置-打开配置文件失败: {e}')
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

    def _onAutoCloseTimeChanged(self, text):
        """自动关闭时间的输入校验。"""
        self._check_input(text, 30, 300, cfg.auto_close_time, self.autoCloseTimer)

    def _onWeatherRefreshTimeChanged(self, text):
        """天气刷新间隔的输入校验。"""
        self._check_input(text, 15, 60, cfg.weather_data_refresh_interval, self.weatherRefreshTimeCard)

    def _onMcServerDataRefreshIntervalChanged(self, text):
        """MC服务器刷新间隔的输入校验。"""
        self._check_input(
            text, 5, 3600, cfg.mc_server_data_refresh_interval,
            self.mcServerDataRefreshIntervalCard
        )

    def _onGitHubRepoRefreshTimeChanged(self, text):
        """GitHub仓库信息刷新间隔的输入校验。"""
        self._check_input(
            text, 1, 24, cfg.github_repo_data_refresh_interval,
            self.repoDataRefreshTimeCard
        )

    def _onOpenLogFolderClicked(self) -> None:
        if lib.LOG_FOLDER_PATH.exists():
            os.startfile(lib.LOG_FOLDER_PATH)
            Notify.success('已打开日志文件夹', parent=self)

        else:
            Notify.error('日志文件夹不存在', parent=self)

    def _onDeleteDownloadTempClicked(self) -> bool | None:
        if lib.DOWNLOAD_PATH.exists():
            shutil.rmtree(lib.DOWNLOAD_PATH)
            lib.log.info('已删除下载缓存')
            Notify.success('已删除下载缓存', parent=self)
            return True

        else:
            Notify.info(content='未发现下载缓存', parent=self)
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
                self.cityChooseCard.setTitle(f'选择城市(当前: {display_name})')
                if city_id != old_city_id:
                    Notify.success(
                        title=f'已设置城市 {display_name}', content='正在获取天气信息...',
                        parent=self
                    )
                    self._onRefreshWeather()

    @asyncSlot()
    async def _onWeatherSourceChanged(self):
        from ..widgets import WeatherWidget
        widget = WeatherWidget()
        cache_source = widget.get_cached_source()

        # 如果选择的数据源和缓存的数据源不一致
        if widget.DATA_SOURCE != cache_source:
            # 更新当前选择的城市
            self.cityChooseCard.setTitle(f'选择城市(当前: {cfg.city_name.value[widget.DATA_SOURCE]})')
            # 如果对应数据源的city_id未配置
            city_ids = cfg.city_id.value
            city_names = cfg.city_name.value
            data_source = widget.DATA_SOURCE
            if not city_ids[data_source] or not city_names[data_source]:
                Notify.info(content='更换天气数据源后请重新选择城市', parent=self)

            # 如果数据源是和风天气，检查API Host和API Key是否可用
            if data_source == 'qweather':
                if not (cfg.qweather_api_host.value.strip() and cfg.qweather_api_key.value.strip()):
                    Notify.warning('未填写API Host或API Key', parent=self)
                    return

            else:
                # 开始刷新天气信息
                self.weatherSourceCard.setEnabled(False)
                self.weatherRefreshCard.setEnabled(False)
                try:
                    await widget.get_data_async(force_refresh=True)
                    self._notify_widget_result(widget, '天气信息更新成功', '天气信息更新失败')

                except Exception as e:
                    log.error(f'设置-天气信息更新失败：{e}')
                    Notify.error(content=f'未知错误：{e}', title='天气信息更新失败', parent=self)

                finally:
                    self.weatherSourceCard.setEnabled(True)
                    self.weatherRefreshCard.setEnabled(True)

    @asyncSlot()
    async def _onRefreshWeather(self):
        from core.widgets import WeatherWidget
        widget = WeatherWidget()
        # 如果数据源是和风天气，检查API Host和API Key是否可用
        if widget.DATA_SOURCE == 'qweather':
            if not (cfg.qweather_api_host.value.strip() and cfg.qweather_api_key.value.strip()):
                Notify.warning('未填写API Host或API Key', parent=self)
                return

        self.weatherRefreshCard.setEnabled(False)
        try:
            await widget.get_data_async(force_refresh=True)
            self._notify_widget_result(widget, '天气信息更新成功', '天气信息更新失败')

        except Exception as e:
            log.error(f'设置-天气信息更新失败：{e}')
            Notify.error(content=f'未知错误：{e}', title='天气信息更新失败', parent=self)

        finally:
            self.weatherRefreshCard.setEnabled(True)

    @asyncSlot()
    async def _onRefreshMCServer(self):
        self.mcServerDataRefreshCard.setEnabled(False)
        from core.widgets import MCServerError, MCServerInfoWidget
        try:
            mc = MCServerInfoWidget()
            data = await mc.get_data_async(force_refresh=True)

            # 成功提示中附带在线朋友信息（≤3 个时列出名单）
            content = 'MC 服务器信息已更新'
            online_friends = (data or {}).get('mc_online_friends') or []
            if online_friends:
                friend_count = len(online_friends)
                if friend_count <= 3:
                    content += f'，当前有 {friend_count} 个朋友在线：' \
                               f'{"、".join(online_friends)}'
                else:
                    content += f'，当前有 {friend_count} 个朋友在线'
            Notify.success(content=content, parent=self)

        except MCServerError as e:
            log.error(f'设置-MC 服务器信息更新失败：{e}')
            Notify.error(content=str(e), title='MC 服务器信息更新失败', parent=self)

        except Exception as e:
            log.error(f'设置-MC 服务器信息更新失败：{e}')
            Notify.error(content=f'未知错误：{e}', title='MC 服务器信息更新失败', parent=self)

        finally:
            self.mcServerDataRefreshCard.setEnabled(True)

    @asyncSlot()
    async def _onRefreshGitHubRepo(self):
        from core.widgets import GitHubRepoInfoWidget
        # 未填写仓库作者或仓库名称时不予刷新，弹警告
        if not (cfg.github_repo_owner.value.strip() and cfg.github_repo_name.value.strip()):
            Notify.warning('请先填写仓库作者和仓库名称', parent=self)
            return

        self.repoRefreshCard.setEnabled(False)
        try:
            widget = GitHubRepoInfoWidget()
            await widget.get_data_async(force_refresh=True)
            self._notify_widget_result(widget, 'GitHub仓库信息更新成功', 'GitHub仓库信息更新失败')

        except Exception as e:
            log.error(f'设置-GitHub仓库信息更新失败：{e}')
            Notify.error(content=f'未知错误：{e}', title='GitHub仓库信息更新失败', parent=self)

        finally:
            self.repoRefreshCard.setEnabled(True)

    def _notify_widget_result(self, widget, success_msg: str, fail_title: str) -> None:
        """根据组件获取结果弹提示：组件记录有错误信息则弹错误，否则弹成功。"""
        if getattr(widget, 'last_error', ''):
            Notify.error(content=widget.last_error, title=fail_title, parent=self)
        else:
            Notify.success(content=success_msg, parent=self)

    def _onEditBirthdayList(self) -> None:
        birthday_dict = cfg.birthday_dict.value
        box = BirthdayEditBox(parent=self)
        # 如果用户点击保存
        if box.exec():
            # 如果新列表不与原列表相等
            if box.result != birthday_dict:
                # 执行保存逻辑
                qconfig.set(cfg.birthday_dict, box.result, save=True)
                Notify.success('已保存新的生日列表', parent=self)
                log.info(f'设置-已保存新的生日列表：{box.result}')

    def _onEditFriendsList(self) -> None:
        friends_list = cfg.mc_server_friends_list.value
        box = ListEditingBox(title='编辑朋友列表', items=friends_list, parent=self)
        # 如果用户点击保存
        if box.exec():
            # 如果新列表不与原列表相等
            if box.result != friends_list:
                # 执行保存逻辑
                qconfig.set(cfg.mc_server_friends_list, box.result, save=True)
                Notify.success('已保存新的朋友列表', parent=self)
                log.info(f'设置-已保存新的朋友列表：{box.result}')

    @asyncSlot()
    async def _onWordsSourceChanged(self):
        from ..widgets import DailyWordsWidget
        widget = DailyWordsWidget()
        cache_source = widget.get_cached_source()
        # 如果选择的数据源和缓存的数据源不一致
        if widget.DATA_SOURCE != cache_source:
            self.wordsSourceCard.setEnabled(False)
            # 开始刷新每日一言信息
            try:
                await widget.get_data_async(force_refresh=True)
                self._notify_widget_result(widget, '每日一言信息更新成功', '每日一言信息更新失败')

            except Exception as e:
                log.error(f'设置-每日一言信息更新失败：{e}')
                Notify.error(content=f'未知错误：{e}', title='每日一言信息更新失败', parent=self)

            finally:
                self.wordsSourceCard.setEnabled(True)
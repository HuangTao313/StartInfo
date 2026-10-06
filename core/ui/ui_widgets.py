"""core.ui 可复用界面组件。

设置页基底（BaseSettingPage）、城市搜索与更新弹窗（CitySearchBox、
UpdateDownloadBox）以及通知 / 异步操作工具（Notify、action）。
设置卡及其专属编辑弹窗见 setting_cards（其 Notify 依赖来自本模块，
本模块不得反向导入 setting_cards）。
"""

import sqlite3
import asyncio
import functools
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidgetItem, QWidget, QHBoxLayout
from qasync import asyncSlot
from qfluentwidgets import (SearchLineEdit, ListWidget, ScrollArea, ExpandLayout,
                            MessageBoxBase, SubtitleLabel, BodyLabel, InfoBar,
                            InfoBarPosition, ProgressBar)

from .app import tr
from ..base_lib import open_target, is_installation
from ..config import cfg
from ..logger import log
from ..paths import WEATHER_DB_FILE_PATHS
from ..updater import GITHUB_RELEASES_URL, download_and_verify_async, launch_installer


class BaseSettingPage(ScrollArea):
    """
    设置页面基底 —— 所有设置页面继承此类。
    ScrollArea 壳子：透明背景 + 底盘 + ExpandLayout（内容水平居中）。
    """

    def __init__(self, parent=None, object_name=''):
        super().__init__(parent=parent)
        self.enableTransparentBackground()

        self.scrollWidget = QWidget()
        self.scrollWidget.setObjectName('scrollWidget')
        self.scrollWidget.setStyleSheet('background: transparent;')

        # 内容容器：承载卡片，限制宽度区间，在滚动视口中水平居中
        self.contentWidget = QWidget(self.scrollWidget)
        self.contentWidget.setObjectName('contentWidget')
        self.contentWidget.setStyleSheet('background: transparent;')
        # 窗口最大化后内容保持该宽度并居中，两侧留白；
        # 最小宽度保证卡片正常展开（不依赖卡片的 sizeHint）
        self.contentWidget.setMinimumWidth(800)
        self.contentWidget.setMaximumWidth(1000)

        self.expandLayout = ExpandLayout(self.contentWidget)

        # 外层水平布局：内容容器拉伸占满视口（受 min/max 约束），
        # 超宽时容器停在 1000 并居中
        outer_layout = QHBoxLayout(self.scrollWidget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(self.contentWidget, 1)

        if object_name:
            self.setObjectName(object_name)

    def finalise(self):
        """所有卡片创建完毕后调用，将底盘装入滚动区域。"""
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

class CitySearchBox(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 1. 初始化 UI 组件
        self.titleLabel = SubtitleLabel(self.tr('搜索城市'))
        self.text = self.tr('请输入城市名进行搜索')
        # 仅有和风天气城市数据库支持搜索省份
        if self.weather_source == 'qweather':
            self.text += self.tr('(支持搜索省份)')

        self.hintLabel = BodyLabel(self.text)
        self.searchEdit = SearchLineEdit(self)
        self.cityList = ListWidget(self)

        # 2. 配置组件属性
        self.searchEdit.setPlaceholderText(self.tr('例如：北京 / 上海 / 武汉'))
        self.searchEdit.setClearButtonEnabled(True)
        self.yesButton.setText(self.tr('选择此城市'))
        self.cancelButton.setText(self.tr('取消'))

        # 3. 设置布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.hintLabel)
        self.viewLayout.addWidget(self.searchEdit)
        self.viewLayout.addWidget(self.cityList)

        # 4. 设置弹窗尺寸
        self.widget.setMinimumWidth(500)
        self.widget.setFixedHeight(600)

        # 5. 绑定搜索逻辑
        self.searchEdit.textChanged.connect(self._onSearchChanged)

        # 初始显示全部
        self._onSearchChanged('')

    @property
    def weather_source(self) -> str:
        """当前选中的数据提供方(qweather / xiaomi_weather)，实时读取配置"""
        return cfg.weather_source.value

    @property
    def _db_path(self) -> str:
        """根据当前数据提供方动态拼接城市数据库路径"""
        return str(WEATHER_DB_FILE_PATHS[self.weather_source])

    def _onSearchChanged(self, text):
        """使用 SQL LIKE 查询过滤城市(按数据提供方使用各自的数据库)"""
        self.cityList.clear()
        search_key = text.strip()

        if not Path(self._db_path).exists():
            log.error(f'城市搜索-城市数据库不存在: {self._db_path}')
            return

        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        like_pattern = f'%{search_key}%'

        if self.weather_source == 'qweather':
            # 和风库：cities(name, city_id, full, display)，支持按省份全称搜索
            if search_key:
                cursor.execute(
                    'SELECT name, city_id, full, display FROM cities '
                    'WHERE name LIKE ? OR full LIKE ? LIMIT 100',
                    (like_pattern, like_pattern)
                )
            else:
                cursor.execute('SELECT name, city_id, full, display FROM cities LIMIT 100')
            rows = cursor.fetchall()

        else:
            # 小米库：citys(name, city_num)，无 full/display 之分，两者均使用 name
            if search_key:
                cursor.execute(
                    'SELECT city_num, name FROM citys WHERE name LIKE ? LIMIT 100',
                    (like_pattern,)
                )
            else:
                cursor.execute('SELECT city_num, name FROM citys LIMIT 100')
            rows = [(name, city_num, name, name) for city_num, name in cursor.fetchall()]

        for row in rows:
            _, city_id, full, display = row
            item = QListWidgetItem(full)
            item.setData(Qt.UserRole, {'city_id': city_id, 'full': full, 'display': display})
            self.cityList.addItem(item)

        conn.close()

    # def get_selected_city(self):
    #     ''' 获取当前选中的城市 '''
    #     item = self.cityList.currentItem()
    #     return item.text() if item else None

    def get_selected_city_id(self):
        """ 获取当前选中城市的 city_id """
        # 1. 获取当前选中的项目
        item = self.cityList.currentItem()
        if not item:
            return None

        # 2. 从 UserRole 中取出我们之前存进去的 info 字典
        city_info = item.data(Qt.UserRole)

        # 3. 返回字典里的 city_id
        return city_info.get('city_id')

    def get_selected_city_display(self):
        """ 获取用于写入配置文件的 display 值 (如：北京·海淀) """
        item = self.cityList.currentItem()
        if not item:
            return None
        # 取出 UserRole 里的字典，拿 display
        return item.data(Qt.UserRole).get('display')

class Notify:
    """弹窗提醒工具类"""

    @staticmethod
    def info(content: str, title: str = None, duration: int = 2000, parent=None):
        """显示普通信息提示"""
        # 默认标题延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
        if title is None:
            title = tr('提示')
        # 如果调用时没传 parent，尝试从 AppManager 获取主窗口（假设你存了）
        # 或者在调用时手动传 self
        InfoBar.info(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=parent
        )

    @staticmethod
    def success(content: str, title: str = None, duration: int = 2000, parent=None):
        """显示成功绿条弹窗"""
        # 默认标题延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
        if title is None:
            title = tr('成功')
        # 如果调用时没传 parent，尝试从 AppManager 获取主窗口（假设你存了）
        # 或者在调用时手动传 self
        InfoBar.success(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=parent
        )

    @staticmethod
    def warning(content: str, title: str = None, duration: int = 5000, parent=None):
        """显示橙色警告弹窗"""
        # 默认标题延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
        if title is None:
            title = tr('警告')
        InfoBar.warning(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=parent
        )

    @staticmethod
    def error(content: str, title: str = None, duration: int = 5000, parent=None):
        """显示错误红条弹窗"""
        # 默认标题延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
        if title is None:
            title = tr('错误')
        InfoBar.error(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=parent
        )

def action(success_msg: str = '', fail_msg: str = None):
    """装饰器：自动包装异步方法 → asyncSlot → InfoBar 反馈。

    用法：
        @action('天气数据已更新', '获取失败')
        async def on_refresh_weather(self):
            w = WeatherWidget()
            return await w.get_data_async()

        方法返回值非空 → 显示 success_msg
        返回 None      → 静默（表示无需操作，不弹任何提示）
        返回 False     → 显示 fail_msg
        抛出异常       → 显示异常信息

    也适用于同步方法：
        @action('删除成功')
        def on_delete(self):
            shutil.rmtree(path)
            return True
    """
    def deco(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 默认失败提示延迟翻译：默认参数在模块加载时求值，那时还没有翻译器
            _fail_msg = tr('操作失败') if fail_msg is None else fail_msg
            try:
                result = func(self, *args, **kwargs)
                # 如果是协程，await
                if hasattr(result, '__await__'):
                    result = await result
                if result:
                    InfoBar.success(title=success_msg, content='', parent=self,
                                    position=InfoBarPosition.TOP,
                                    duration=2000)
                elif result is None:
                    # 返回 None 表示无需操作（如数据源未变更），静默处理
                    pass
                else:
                    InfoBar.error(title=_fail_msg, content='', parent=self,
                                  position=InfoBarPosition.TOP,
                                  duration=2000)
                return result

            except Exception as e:
                log.error(f'设置-操作失败: {e}')
                InfoBar.error(title=str(e), content='', parent=self,
                              position=InfoBarPosition.TOP,
                              duration=3000)
        return asyncSlot()(wrapper)
    return deco

def _format_size(size: int) -> str:
    """把字节数格式化为易读的 B/KB/MB 文本。"""
    if size < 1024:
        return f'{size}B'
    if size < 1024 * 1024:
        return f'{size / 1024:.1f}KB'
    return f'{size / (1024 * 1024):.1f}MB'


class UpdateDownloadBox(MessageBoxBase):
    """检查更新确认 + 下载进度弹窗。

    - 初始显示新版本信息与「立即更新/取消更新」按钮。
    - Windows 安装版：点击「立即更新」后清除文案，切换为下载进度条，异步下载安装包；
      下载期间主按钮变为「取消」，点击后中止下载、删除残缺文件并关闭弹窗。
      下载完成后先渲染进度、关闭弹窗，再启动安装程序并优雅退出应用。
    - 非 Windows 或 Windows 便携版：点击「立即更新」跳转 GitHub Releases 页面并关闭弹窗。
    """

    def __init__(self, update_info: dict, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self._last_percent = -1
        # 下载阶段状态：_downloading 表示正在下载，_cancel_requested 表示用户已请求取消
        self._downloading = False
        self._cancel_requested = False

        # ── 初始：新版本信息 ──
        self.titleLabel = SubtitleLabel(self.tr('发现新版本'))
        self.contentLabel = BodyLabel(
            self.tr('版本号：{version}\n'
                    '发布日期：{release_date}\n'
                    '更新日志：\n'
                    '{changelog}').format(
                version=update_info.get('version', self.tr('获取失败')),
                release_date=update_info.get('release_date', self.tr('获取失败')),
                changelog=update_info.get('changelog', self.tr('暂无更新日志')),
            ),
            self,
        )
        self.contentLabel.setWordWrap(True)

        # ── 下载进度（初始隐藏）──
        self.progressLabel = BodyLabel(self.tr('正在下载新版本安装包：0%'), self)
        self.progressBar = ProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.contentLabel)
        self.viewLayout.addWidget(self.progressLabel)
        self.viewLayout.addWidget(self.progressBar)

        self.yesButton.setText(self.tr('立即更新'))
        self.cancelButton.setText(self.tr('取消更新'))
        self.widget.setMinimumWidth(480)

        self.progressLabel.hide()
        self.progressBar.hide()

        # 基类的按钮连接的是名称混淆的私有方法，这里断开后接管点击
        self.yesButton.clicked.disconnect()
        self.cancelButton.clicked.disconnect()
        self.yesButton.clicked.connect(self._onYesClicked)
        self.cancelButton.clicked.connect(self._onCancelClicked)

    def _onYesClicked(self, checked: bool = False):
        if not is_installation():
            # 非 Windows 或 Windows 便携版：跳转到 GitHub 最新构建的 Releases 页面
            open_target(GITHUB_RELEASES_URL)
            self.accept()
            return

        # Windows 安装版：清除文案，切换为下载进度视图
        self._switch_to_download_view()
        asyncio.ensure_future(self._download_and_install())

    def _onCancelClicked(self, checked: bool = False):
        if self._downloading:
            # 下载中：仅标记取消并禁用按钮，待下载协程清理完残缺文件后由回调关闭弹窗
            self._cancel_requested = True
            self.yesButton.setEnabled(False)
            return

        self.reject()

    def _switch_to_download_view(self):
        """清除文案，切换为下载进度视图。

        保留主按钮位的单个取消按钮：隐藏次按钮，把 yesButton 从
        「立即更新」改接为取消（按钮点击已在 __init__ 中接管）。
        """
        self._downloading = True
        self.titleLabel.setText(self.tr('正在更新'))
        self.contentLabel.hide()
        self.progressLabel.setText(self.tr('正在下载新版本安装包：0%'))
        self.progressLabel.show()
        self.progressBar.show()
        self.cancelButton.hide()
        self.yesButton.setText(self.tr('取消'))
        self.yesButton.clicked.disconnect(self._onYesClicked)
        self.yesButton.clicked.connect(self._onCancelClicked)

    async def _download_and_install(self):
        try:
            installer_path, error_msg = await download_and_verify_async(
                self.update_info, progress_callback=self._on_download_progress,
                cancel_check=lambda: self._cancel_requested)
        except Exception as e:
            log.error(f'更新器-更新过程异常: {e}')
            installer_path, error_msg = None, self.tr('更新过程发生异常：{error}').format(error=e)

        # 用户取消：残缺文件已由下载函数清理，静默关闭弹窗
        if self._cancel_requested:
            self.reject()
            return

        if installer_path is None:
            self._show_download_error(error_msg)
            return

        # 下载校验完成：等 UI 收尾、窗口完全关闭后再启动安装程序
        await self._finish_for_install(installer_path)

    async def _finish_for_install(self, installer_path: Path):
        """收尾时序：渲染完 100% 帧 → 关闭弹窗 → 启动 setup.exe → 优雅退出。

        进程不能在事件循环运行中被 sys.exit 强杀（退出码 0xC0000409），
        必须先关窗再启动安装程序，最后走 QApplication.quit() 正常退出。
        """
        self._downloading = False
        self.progressBar.setValue(100)
        self.progressLabel.setText(self.tr('下载完成，正在准备安装...'))
        self.yesButton.setEnabled(False)

        # 给事件循环留出渲染最后一帧的时间
        await asyncio.sleep(0.3)

        self.accept()
        # 等待弹窗关闭动画结束、窗口完全退出
        await asyncio.sleep(0.2)

        if not launch_installer(installer_path):
            # 弹窗已关闭，错误提示只能挂到主窗口上
            Notify.error(self.tr('启动安装程序失败，请到缓存目录手动运行安装包。'),
                         parent=self.window())
            return

        # 安装程序已启动，优雅退出主事件循环（Inno 的 /CLOSEAPPLICATIONS 会兜底）
        QApplication.quit()

    def _on_download_progress(self, downloaded: int, total: int):
        if total > 0:
            percent = min(100, int(downloaded / total * 100))
            # 整数百分比去重，避免 ProgressBar 动画频繁重启导致卡顿
            if percent != self._last_percent:
                self._last_percent = percent
                self.progressBar.setValue(percent)
            self.progressLabel.setText(
                self.tr('正在下载新版本安装包：{percent}% ({downloaded} / {total})').format(
                    percent=percent,
                    downloaded=_format_size(downloaded),
                    total=_format_size(total)))
        else:
            self.progressLabel.setText(
                self.tr('正在下载新版本安装包：{downloaded}').format(
                    downloaded=_format_size(downloaded)))

    def _show_download_error(self, error_msg: str):
        self._downloading = False
        self.titleLabel.setText(self.tr('下载失败'))
        self.progressLabel.setText(error_msg)
        self.progressBar.error()  # 进度条置为错误状态（红色）
        # 单按钮收尾：yesButton 已连着 _onCancelClicked（非下载状态 → reject 关闭）
        self.yesButton.setText(self.tr('关闭'))
        self.yesButton.setEnabled(True)
"""core.ui 可复用设置控件。

设置页使用的卡片、编辑框与表格委托。
依赖方向固定为 controls → dialogs，不得反向依赖。
"""

import sqlite3
from pathlib import Path
from typing import Union

from PySide6.QtCore import Qt, Signal, QDate, QLocale, QSize, QPersistentModelIndex
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QAbstractItemDelegate, QAbstractItemView, QHeaderView, QListWidgetItem, QTableWidgetItem, QWidget, QHBoxLayout
from qfluentwidgets import SwitchSettingCard, qconfig, SearchLineEdit, MessageBoxBase, SubtitleLabel, ListWidget, BodyLabel, SettingCard, FluentIconBase, LineEdit, ConfigItem, CalendarPicker, ExpandGroupSettingCard, Action, CommandBar, FluentIcon, ZhDatePicker, TableWidget, TableItemDelegate, ScrollArea, ExpandLayout

from ..config import cfg
from ..logger import log
from ..paths import WEATHER_DB_FILE_PATHS
from .switch_button import IndicatorPosition, SwitchButton
from .dialogs import Notify


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

class ExtSwitchSettingCard(SwitchSettingCard):
    """
    替换 SwitchButton 的开关设置卡片
    （状态文字经 tr() 交由外部 qm 翻译文件处理）
    """
    def __init__(self, icon, title, content=None, config_item=None, parent=None):
        super().__init__(icon, title, content, config_item, parent)
        # 用新的 SwitchButton 替换父类创建的开关
        self._replaceSwitchButton()
        # 初始化时强制同步一次状态文字
        self._updateText(self.isChecked())

    def _replaceSwitchButton(self):
        """ 把父类创建的 SwitchButton 从布局中移除，换成新的 SwitchButton """
        old_button = self.switchButton
        index = self.hBoxLayout.indexOf(old_button)
        self.hBoxLayout.removeWidget(old_button)
        old_button.deleteLater()

        # 创建新开关并插回原位置
        self.switchButton = SwitchButton(
            self.tr('Off'), self, IndicatorPosition.RIGHT)
        # 继承旧开关的选中状态（父类构造时已从 config 同步到旧开关上）
        # 注意：必须在连接 checkedChanged 之前设置，避免触发多余的信号链
        self.switchButton.setChecked(old_button.isChecked())
        self.hBoxLayout.insertWidget(index, self.switchButton, 0, Qt.AlignRight)

        # 复刻父类的信号连接（父类的 __onCheckedChanged 是私有方法，无法直接引用）
        self.switchButton.checkedChanged.connect(self._onSwitchCheckedChanged)

    def _onSwitchCheckedChanged(self, is_checked: bool):
        self.setValue(is_checked)
        self.checkedChanged.emit(is_checked)

    def _updateText(self, is_checked: bool):
        # 状态文字走标准 tr() 路径，由外部 qm 翻译文件提供译文
        self.switchButton.setText(self.tr('On') if is_checked else self.tr('Off'))

    def setValue(self, is_checked: bool):
        if self.configItem:
            qconfig.set(self.configItem, is_checked)

        self.switchButton.setChecked(is_checked)
        self._updateText(is_checked)


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


class TextSettingCard(SettingCard):
    """ 支持文本输入的设置卡 """

    textChanged = Signal(str)

    def __init__(self, config_item: ConfigItem, icon: Union[str, QIcon, FluentIconBase],
                 title, content=None, parent=None):
        """
        参数:
        ----------
        configItem: ConfigItem
            配置项，关联 qconfig

        icons: str | QIcon | FluentIconBase
            图标

        title: str
            标题

        content: str
            描述内容

        parent: QWidget
            父组件
        """
        super().__init__(icon, title, content, parent)
        self.configItem = config_item

        # 1. 创建输入框
        self.lineEdit = LineEdit(self)
        self.lineEdit.setFixedWidth(200)

        # 2. 初始化数值
        if self.configItem:
            self.lineEdit.setText(str(config_item.value))
            # 只有存在配置项时才绑定自动更新信号
            self.configItem.valueChanged.connect(self.setText)
        else:
            self.lineEdit.setPlaceholderText(self.tr('未关联配置项...'))

        # 3. 布局
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.lineEdit, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        # 4. 信号绑定
        self.lineEdit.editingFinished.connect(self.__onEditingFinished)

    def __onEditingFinished(self):
        """ 输入完成的回调 """
        text = self.lineEdit.text()
        self.setText(text)
        self.textChanged.emit(text)

    def setText(self, text: str):
        """ 更新配置和 UI """
        str_text = str(text)

        # 只有存在配置项时才写入 qconfig
        if self.configItem:
            qconfig.set(self.configItem, str_text)

        # 同步 UI
        if self.lineEdit.text() != str_text:
            self.lineEdit.setText(str_text)



class CalendarSettingCard(SettingCard):
    """ 日历选择设置卡 """

    dateChanged = Signal(QDate)

    def __init__(self, icon: Union[str, QIcon, FluentIconBase], title, content=None,
                 config_item: ConfigItem = None, parent=None):
        """
        configItem 存储的通常是 ISO 格式的日期字符串 (如 '2026-06-20')
        """
        super().__init__(icon, title, content, parent)
        self.configItem = config_item

        # 1. 创建日历选择器
        self.calendarPicker = CalendarPicker(self)
        self.calendarPicker.locale = QLocale(QLocale.Chinese, QLocale.China)
        self.calendarPicker.setFixedWidth(200)

        # --- 汉化关键点 ---
        # 覆盖源码中的 'Pick a date'
        self.calendarPicker.setText(self.tr('选择一个日期'))
        # ----------

        # 2. 初始化日期
        if self.configItem and self.configItem.value:
            # 将配置中的字符串转为 QDate
            initial_date = QDate.fromString(str(self.configItem.value), Qt.ISODate)
            if initial_date.isValid():
                self.calendarPicker.setDate(initial_date)

        # 3. 布局 (模仿 QFW 标准布局)
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.calendarPicker, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        # 4. 信号绑定
        self.calendarPicker.dateChanged.connect(self.__onDateChanged)

        if self.configItem:
            self.configItem.valueChanged.connect(self.setDate)

    def __onDateChanged(self, date: QDate):
        """ 日期改变后的回调 """
        date_str = date.toString(Qt.ISODate)
        self.setDate(date_str)
        self.dateChanged.emit(date)

    def setDate(self, date_str: str):
        """ 更新配置和 UI """
        # 转换回 QDate 用于 UI 更新
        date = QDate.fromString(str(date_str), Qt.ISODate)
        if not date.isValid():
            return

        # 更新配置
        if self.configItem:
            qconfig.set(self.configItem, date_str)

        # 更新 UI
        if self.calendarPicker.date != date:
            self.calendarPicker.setDate(date)

class ExpandGroupCard(ExpandGroupSettingCard):
    """手风琴卡片——展开区域背景自动跟随主题，无需手动设透明。

    用法：
        detail = ExpandGroupCard(FIF.GLOBE, '标题', '描述')
        detail.addCards([card1, card2, ...])
        group.addSettingCard(detail)
    """

    def __init__(self, icon, title, content=None, parent=None):
        super().__init__(icon, title, content, parent)
        self.view.setStyleSheet('background: transparent;')
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

    def addCard(self, card: SettingCard):
        """添加一张标准设置卡到手风琴展开区域。"""
        self.addGroupWidget(card)

    def addCards(self, cards: list):
        """批量添加标准设置卡到手风琴展开区域。"""
        for card in cards:
            self.addCard(card)

class ListEditingBox(MessageBoxBase):

    def __init__(self, title: str | None = None, items: list = None, parent=None):
        super().__init__(parent)

        # 设置弹窗宽高
        self.widget.setMinimumWidth(500)
        self.widget.setFixedHeight(600)

        # 设置弹窗底部按钮
        self.yesButton.setText(self.tr('保存'))
        self.cancelButton.setText(self.tr('取消'))

        # 标题（默认标题延迟翻译：默认参数在类定义时求值，那时还没有 self）
        if title is None:
            title = self.tr('编辑列表')
        self.titleLabel = SubtitleLabel(title)
        self.hintLabel = BodyLabel(self.tr('不可添加重复元素'))

        # 工具栏
        self.commandBar = CommandBar()
        self.commandBar.setToolButtonStyle(
            Qt.ToolButtonTextBesideIcon
        )

        self.commandBar.setIconSize(
            QSize(18, 18)
        )

        # 元素输入框
        self.lineEdit = LineEdit()
        # 设置提示文本
        self.lineEdit.setPlaceholderText(self.tr('添加或编辑元素'))
        # 启用清空按钮
        self.lineEdit.setClearButtonEnabled(True)

        self.commandBar.addWidget(self.lineEdit)

        self.addButton = Action(
            FluentIcon.ADD,
            self.tr('添加'),
            triggered=self.addItem
        )

        self.editButton = Action(
            FluentIcon.EDIT,
            self.tr('编辑'),
            enabled=False,
            triggered=self.editItem
        )

        self.commandBar.addActions(
            [
                self.addButton,
                self.editButton,
            ]
        )

        # 分隔符
        self.commandBar.addSeparator()

        # 删除
        self.deleteButton = Action(
            FluentIcon.DELETE,
            self.tr('删除'),
            enabled=False,
            triggered=self.deleteItem
        )

        self.commandBar.addAction(self.deleteButton)

        # 列表组件
        self.listWidget = ListWidget()
        # 启用右键选中
        self.listWidget.setSelectRightClickedRow(True)

        # 添加列表项
        if items:
            for i in items:
                item = QListWidgetItem(i)
                self.listWidget.addItem(item)

        # 添加布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.hintLabel)
        self.viewLayout.addWidget(self.commandBar)
        self.viewLayout.addWidget(self.listWidget)

        # 绑定信号与槽
        # 改变选中的元素
        self.listWidget.currentItemChanged.connect(self._onItemChanged)

        # 编辑元素输入框
        self.lineEdit.textEdited.connect(self._onLineEdited)

    # 槽函数
    def _updateButtonState(self):
        """根据当前选中状态更新按钮"""

        item = self.listWidget.currentItem()

        hasItem = item is not None

        self.editButton.setEnabled(hasItem)
        self.deleteButton.setEnabled(hasItem)

        if item:
            self.lineEdit.setText(item.text())

    def _onItemChanged(self, current, previous):
        """将选中的列表元素添加到元素输入框"""

        if current:
            self.lineEdit.setText(current.text())

        self._updateButtonState()

    def _onLineEdited(self, text: str) -> None:
        """当输入框内存在列表内已有元素时，禁止重复添加"""

        text = text.strip()

        # 空文本禁止添加
        if not text:
            self.addButton.setEnabled(False)
            return

        # 获取当前选中的元素
        current = self.listWidget.currentItem()

        # 如果元素重复
        if self._isDuplicate(text, current):
            self.addButton.setEnabled(False)

        else:
            self.addButton.setEnabled(True)

    def _isDuplicate(self, text: str, exclude_item=None) -> bool:
        """检测列表中是否存在重复元素"""

        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)

            # 跳过当前正在编辑的元素
            if item == exclude_item:
                continue

            if item.text() == text:
                return True

        return False

    def addItem(self, checked=False) -> None:
        """添加列表元素"""

        text = self.lineEdit.text().strip()

        if not text:
            return

        if self._isDuplicate(text):
            return

        item = QListWidgetItem(text)

        self.listWidget.addItem(item)

        # 自动选中新添加的元素
        self.listWidget.setCurrentItem(item)

        self.lineEdit.clear()

    def editItem(self, checked=False) -> None:
        """编辑列表元素"""

        item = self.listWidget.currentItem()

        if item is None:
            return

        text = self.lineEdit.text().strip()

        if not text:
            return

        # 防止修改成其他已有元素
        for i in range(self.listWidget.count()):
            other = self.listWidget.item(i)

            if other != item and other.text() == text:
                return

        item.setText(text)

    def deleteItem(self, checked=False) -> None:
        """删除列表元素"""

        row = self.listWidget.currentRow()

        if row < 0:
            return

        self.listWidget.takeItem(row)

        # 删除后手动恢复选择状态
        if self.listWidget.count() > 0:

            # 优先选择原位置
            new_row = min(row, self.listWidget.count() - 1)

            self.listWidget.setCurrentRow(new_row)

        else:
            self.listWidget.clearSelection()
            self.lineEdit.clear()

        self._updateButtonState()

    def accept(self):
        """保存并关闭"""

        self.result = [
            self.listWidget.item(i).text()
            for i in range(self.listWidget.count())
        ]

        super().accept()


class BirthdayTableDelegate(TableItemDelegate):
    """ 生日表格委托：生日列以 ZhDatePicker 作为单元格编辑器 """

    # 生日列下标（第 0 列为名称）
    DATE_COLUMN = 1

    def __init__(self, parent):
        super().__init__(parent)
        # 正在编辑的单元格，供 initStyleOption 隐藏底层文本
        self._editingIndex = QPersistentModelIndex()

    def createEditor(self, parent, option, index):
        """双击生日单元格时创建日期选择器，名称列沿用默认文本编辑器"""
        self._editingIndex = QPersistentModelIndex(index)
        if index.column() != self.DATE_COLUMN:
            return super().createEditor(parent, option, index)

        editor = ZhDatePicker(parent)
        self._setEditorDate(editor, index)
        # 用户在滚轮面板中确认新日期后，立即提交并关闭编辑器
        editor.dateChanged.connect(lambda: self._commitEditor(editor))
        return editor

    def setEditorData(self, editor, index):
        """编辑开始时把单元格日期同步到编辑器"""
        if index.column() != self.DATE_COLUMN:
            super().setEditorData(editor, index)
            return

        self._setEditorDate(editor, index)

    def setModelData(self, editor, model, index):
        """编辑结束时把选择器日期写回单元格"""
        if index.column() != self.DATE_COLUMN:
            super().setModelData(editor, model, index)
            return

        date = editor.getDate()
        if date.isValid():
            model.setData(index, date, Qt.UserRole)
            model.setData(index, date.toString(Qt.ISODate), Qt.DisplayRole)

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # 日期单元格编辑期间不绘制底层文本，避免与半透明的日期选择器重叠
        if index.column() == self.DATE_COLUMN and self._isEditing(index):
            option.text = ''

    def updateEditorGeometry(self, editor, option, index):
        super().updateEditorGeometry(editor, option, index)
        if index.column() == self.DATE_COLUMN:
            # 编辑器遮盖的区域不会自动重绘，主动刷新以隐藏底层文本
            self.parent().viewport().update()

    def _isEditing(self, index) -> bool:
        """判断指定单元格是否正处于编辑状态"""
        view = self.parent()
        if not isinstance(view, QAbstractItemView):
            return False
        # 以视图编辑状态为总开关：编辑结束（含取消/焦点移出）后必然失效
        return (view.state() == QAbstractItemView.EditingState
                and self._editingIndex == index)

    def _setEditorDate(self, editor: ZhDatePicker, index):
        """把单元格 UserRole 中保存的 QDate 直接同步给选择器（不经字符串转换）"""
        date = index.data(Qt.UserRole)
        if isinstance(date, QDate) and date.isValid():
            editor.setDate(date)

    def _commitEditor(self, editor):
        """提交编辑器数据并结束编辑"""
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QAbstractItemDelegate.NoHint)


class BirthdayEditBox(MessageBoxBase):
    """ 生日列表编辑弹窗

    用法（与 ListEditingBox 一致，弹窗本身不写配置，由调用方保存）：
        box = BirthdayEditBox(parent=self)
        if box.exec():
            if box.result != cfg.birthday_dict.value:
                qconfig.set(cfg.birthday_dict, box.result, save=True)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 用户点击保存后的最终结果 {姓名: 'YYYYMMDD'}，取消时保持为空
        self.result = {}

        # 1. 设置弹窗宽高
        self.widget.setMinimumWidth(500)
        self.widget.setFixedHeight(600)

        # 2. 设置弹窗底部按钮
        self.yesButton.setText(self.tr('保存'))
        self.cancelButton.setText(self.tr('取消'))

        # 3. 标题与提示
        self.titleLabel = SubtitleLabel(self.tr('编辑生日列表'))
        self.hintLabel = BodyLabel(self.tr('双击名称或生日可编辑'))

        # 4. 工具栏（修改通过双击表格完成，无需单独按钮）
        self.commandBar = CommandBar()
        self.commandBar.setToolButtonStyle(
            Qt.ToolButtonTextBesideIcon
        )

        self.commandBar.setIconSize(
            QSize(18, 18)
        )

        self.addButton = Action(
            FluentIcon.ADD,
            self.tr('添加'),
            triggered=self.addItem
        )

        self.deleteButton = Action(
            FluentIcon.DELETE,
            self.tr('删除'),
            enabled=False,
            triggered=self.deleteItem
        )

        self.commandBar.addActions(
            [
                self.addButton,
                self.deleteButton,
            ]
        )

        # 5. 生日表格
        self.tableWidget = TableWidget(self)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels([self.tr('名称'), self.tr('生日')])
        self.tableWidget.verticalHeader().hide()
        # 仅双击 / F2 触发编辑
        self.tableWidget.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        # 生日列使用日期选择器编辑器
        self.tableWidget.setItemDelegate(BirthdayTableDelegate(self.tableWidget))
        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        # 日期选择器编辑器较宽，生日列给固定宽度
        self.tableWidget.setColumnWidth(1, 260)

        # 6. 从配置加载生日列表（编辑期间不修改原配置）
        self._loadBirthdays(cfg.birthday_dict.value)

        # 7. 添加布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.hintLabel)
        self.viewLayout.addWidget(self.commandBar)
        self.viewLayout.addWidget(self.tableWidget)

        # 8. 绑定信号与槽
        self.tableWidget.itemSelectionChanged.connect(self._updateButtonState)
        self.tableWidget.currentItemChanged.connect(
            lambda current, previous: self._updateButtonState())

    def _loadBirthdays(self, birthday_dict: dict) -> None:
        """把 cfg.birthday_dict（{姓名: 'YYYYMMDD'}）填充到表格"""
        for name, birthday_str in birthday_dict.items():
            self._appendRow(str(name), self._parseBirthday(birthday_str))

    @staticmethod
    def _parseBirthday(birthday_str) -> QDate:
        """把配置中的 'YYYYMMDD' 生日字符串转为 QDate，无法解析时返回无效 QDate"""
        if isinstance(birthday_str, str) and len(birthday_str) == 8 and birthday_str.isdigit():
            date = QDate(int(birthday_str[:4]), int(birthday_str[4:6]), int(birthday_str[6:8]))
            if date.isValid():
                return date

        log.warning(f'生日列表-无法解析的生日格式: {birthday_str}')
        return QDate()

    def _appendRow(self, name: str, date: QDate) -> None:
        """在表格末尾追加一行生日记录"""
        row = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row)
        self.tableWidget.setItem(row, 0, QTableWidgetItem(name))

        # 显示用 ISO 文本，同时在 UserRole 保存 QDate 供编辑器同步
        date_item = QTableWidgetItem(
            date.toString(Qt.ISODate) if date.isValid() else self.tr('未设置'))
        date_item.setData(Qt.UserRole, date)
        self.tableWidget.setItem(row, 1, date_item)

    def _updateButtonState(self):
        """根据当前选中状态更新按钮"""
        self.deleteButton.setEnabled(self.tableWidget.currentRow() >= 0)

    def addItem(self, checked=False) -> None:
        """添加一条生日记录（默认生日为今天）并直接进入名称编辑"""
        row = self.tableWidget.rowCount()
        self._appendRow('', QDate.currentDate())
        self.tableWidget.setCurrentCell(row, 0)
        self.tableWidget.editItem(self.tableWidget.item(row, 0))

    def deleteItem(self, checked=False) -> None:
        """删除当前选中的生日记录"""
        row = self.tableWidget.currentRow()

        # 未选中任何记录时直接返回
        if row < 0:
            return

        self.tableWidget.removeRow(row)
        self._updateButtonState()

    def validate(self) -> bool:
        """保存前校验：名称非空且不重复、日期有效"""
        names = set()

        for row in range(self.tableWidget.rowCount()):
            name = self.tableWidget.item(row, 0).text().strip()

            if not name:
                Notify.warning(
                    content=self.tr('第 {row} 行的名称不能为空').format(row=row + 1),
                    parent=self
                )
                return False

            # 配置以名称为字典键，重名会互相覆盖
            if name in names:
                Notify.warning(
                    content=self.tr('名称重复：{name}，生日列表以名称为唯一标识').format(name=name),
                    parent=self
                )
                return False

            names.add(name)

            date = self.tableWidget.item(row, 1).data(Qt.UserRole)
            if not (isinstance(date, QDate) and date.isValid()):
                Notify.warning(
                    content=self.tr('{name} 的生日无效，请双击生日单元格重新选择').format(name=name),
                    parent=self
                )
                return False

        return True

    def accept(self):
        """读取表格最终数据并关闭弹窗（不直接写入配置，由调用方保存）"""
        self.result = {}

        for row in range(self.tableWidget.rowCount()):
            name = self.tableWidget.item(row, 0).text().strip()
            date = self.tableWidget.item(row, 1).data(Qt.UserRole)
            # 保持配置原有格式 {姓名: 'YYYYMMDD'}
            self.result[name] = date.toString('yyyyMMdd')

        super().accept()
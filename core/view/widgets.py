from qfluentwidgets import (SwitchSettingCard, qconfig, SearchLineEdit, MessageBoxBase,
                              SubtitleLabel, ListWidget, BodyLabel, InfoBar, InfoBarPosition,
                            SettingCard, FluentIconBase, LineEdit,ConfigItem, CalendarPicker)
from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtCore import Qt, Signal, QDate

from typing import Union
from PySide6.QtGui import QIcon
# from PySide6.QtWidgets import QLabel


class ZhSwitchSettingCard(SwitchSettingCard):
    """
    支持中文状态文字的开关设置卡片
    """
    def __init__(self, icon, title, content=None, configItem=None, parent=None):
        super().__init__(icon, title, content, configItem, parent)
        # 初始化时强制同步一次中文
        self._updateText(self.isChecked())

    def _updateText(self, isChecked: bool):
        # 核心：直接绕过原本的 tr('On')，强制写入中文
        self.switchButton.setText("启用" if isChecked else "关闭")

    def setValue(self, isChecked: bool):
        # 彻底重写父类的逻辑，干掉那个烦人的 self.tr('On')
        if self.configItem:
            qconfig.set(self.configItem, isChecked)

        self.switchButton.setChecked(isChecked)
        self._updateText(isChecked)


class CitySearchBox(MessageBoxBase):
    def __init__(self, city_data, parent=None):
        super().__init__(parent)
        self.all_cities = city_data  # 传入你 read_json 读出来的列表

        # 1. 初始化 UI 组件
        self.titleLabel = SubtitleLabel("搜索城市", self)
        self.hintLabel = BodyLabel("请输入城市名进行搜索(支持输入省份)", self)
        self.searchEdit = SearchLineEdit(self)
        self.cityList = ListWidget(self)

        # 2. 配置组件属性
        self.searchEdit.setPlaceholderText("例如：北京 / 上海 / 武汉")
        self.searchEdit.setClearButtonEnabled(True)
        self.yesButton.setText("选择此城市")
        self.cancelButton.setText("取消")

        # 3. 设置布局（按照 CW 的顺序）
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.hintLabel)
        self.viewLayout.addWidget(self.searchEdit)
        self.viewLayout.addWidget(self.cityList)

        # 4. 设置弹窗尺寸（参考 CW 的 500x600）
        self.widget.setMinimumWidth(500)
        self.widget.setFixedHeight(600)

        # 5. 绑定搜索逻辑
        self.searchEdit.textChanged.connect(self._onSearchChanged)

        # 初始显示全部（或者前 100 个，防止数据量太大初始化慢）
        self._onSearchChanged("")

    def _onSearchChanged(self, text):
        """ 适配嵌套字典格式的过滤逻辑 """
        self.cityList.clear()

        search_key = text.lower().strip()
        count = 0

        # 使用 .items() 同时获取 键(name) 和 值(info)
        for name, info in self.all_cities.items():
            # 逻辑：如果搜索词在 键名 里，或者在 info['full'] 完整路径里
            if search_key in name.lower() or search_key in info.get('full', '').lower():
                # 创建列表项，显示 display 字段（如：北京·海淀）
                item = QListWidgetItem(info.get('full', name))

                # 把整个 info 字典存进 item，方便后面读取 city_id
                item.setData(Qt.UserRole, info)

                self.cityList.addItem(item)
                count += 1

            # 性能优化：搜索结果超过 100 个停止遍历
            if count >= 100:
                break

    # def get_selected_city(self):
    #     """ 获取当前选中的城市 """
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

    def __init__(self, configItem: ConfigItem, icon: Union[str, QIcon, FluentIconBase],
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
        self.configItem = configItem

        # 1. 创建输入框
        self.lineEdit = LineEdit(self)
        self.lineEdit.setFixedWidth(200)

        # 2. 初始化数值
        if self.configItem:
            self.lineEdit.setText(str(configItem.value))
            # 只有存在配置项时才绑定自动更新信号
            self.configItem.valueChanged.connect(self.setText)
        else:
            self.lineEdit.setPlaceholderText("未关联配置项...")

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
                 configItem: ConfigItem = None, parent=None):
        """
        configItem 存储的通常是 ISO 格式的日期字符串 (如 "2026-06-20")
        """
        super().__init__(icon, title, content, parent)
        self.configItem = configItem

        # 1. 创建日历选择器
        self.calendarPicker = CalendarPicker(self)
        self.calendarPicker.setFixedWidth(200)

        # --- 汉化关键点 ---
        # 覆盖源码中的 'Pick a date'
        self.calendarPicker.setText("选择一个日期")
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


class Notify:
    """弹窗提醒工具类"""

    @staticmethod
    def info(content: str, title: str = "信息", duration: int = 2000, parent=None):
        """显示普通信息提示"""
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
    def success(content: str, title: str = "成功", duration: int = 2000, parent=None):
        """显示成功绿条弹窗"""
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
    def warning(content: str, title: str = "警告", duration: int = 5000, parent=None):
        """显示橙色警告弹窗"""
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
    def error(content: str, title: str = "错误", duration: int = 5000, parent=None):
        """显示错误红条弹窗"""
        InfoBar.error(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=parent
        )
from .view.basic_settings_page import BasicSettingsWidget
from .view.custom_settings_page import CustomSettingsWidgets
from .view.about_settings_page import AboutSettingsWidgets


# # 这个保留，因为它是 Designer 画的普通页面
# class TestWidget(QWidget, Ui_Form):
#     def __init__(self, parent=None):
#         super().__init__(parent=parent)
#         self.setupUi(self)


# 【关键修改】只继承 BasicSettingsWidget
class BasicStettingsPage(BasicSettingsWidget):
    def __init__(self, parent=None):
        # 这里会调用 BasicSettingsWidget 的 __init__，
        # 从而自动完成 ScrollArea 的初始化和你手写的 SettingCard 布局
        super().__init__(parent=parent)

        # 注意：不要在这里调用 self.setupUi(self)！
        # 因为 Setting_test 现在的结构是 ScrollArea，
        # 而你的 ui_test.py 是针对普通 QWidget 生成的，强行安装会导致布局错乱。


class CustomSettingsPage(CustomSettingsWidgets):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

class AboutSettingsPage(AboutSettingsWidgets):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
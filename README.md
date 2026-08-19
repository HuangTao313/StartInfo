# 开机速览 StartInfo

一个基于 PySide6 + QFluentWidgets 开发的桌面信息展示工具。

## 功能

- 天气与空气质量
- 日期、时间、农历、24 节气、节假日
- 历史上的今天
- 今日人品
- Minecraft 服务器信息
- 更多功能……

## 下载

目前提供 Windows 安装版和便携版。

### Windows

**系统要求：**

- Windows 10 及以上版本
- 仅支持 64 位（x86_64）系统

**版本说明：**

- **安装版**：使用安装程序安装 StartInfo，适合大多数用户。
- **便携版**：无需安装，解压后即可使用，适合希望将程序放在指定目录或移动设备上的用户。

下载最新版本：

- 安装版：[StartInfo-win-x86_64-Setup.exe](https://github.com/HuangTao313/StartInfo/releases/latest/download/StartInfo-win-x86_64-Setup.exe)
- 便携版：[StartInfo-win-x86_64-Portable.zip](https://github.com/HuangTao313/StartInfo/releases/latest/download/StartInfo-win-x86_64-Portable.zip)

> 下载链接始终指向 GitHub 最新 Release 中对应的文件。
> 
> macOS 已完成相关功能适配，但目前暂未提供 macOS 构建版本。

## 从源码运行

首先克隆项目：

```bash
git clone https://github.com/HuangTao313/StartInfo.git
cd StartInfo
```
使用 uv 同步项目依赖：

```bash
uv sync
```

## 和风天气配置

如果使用和风天气作为天气数据源，需要在设置中配置自己的 API Host 和 API Key。

### 获取 API Host 和 API Key

1. 前往 [和风天气开发平台](https://dev.qweather.com/) 注册并登录账号。
2. 创建项目并获取 API Key。
3. 在开发控制台的设置页面查看自己的 API Host。

StartInfo 需要同时使用 API Host 和 API Key 才能正常请求和风天气 API。

### 在 StartInfo 中配置

打开 StartInfo 的设置页面，在天气相关设置中填写：

- **API Host**：填写和风天气控制台提供的 Host。
- **API Key**：填写和风天气控制台生成的 API Key。

API Host 的格式类似：

```text
xxxxxxxx.re.qweatherapi.com
```

填写 API Host 时，**不要添加 `https://` 或 `http://`**，StartInfo 会自动处理请求地址。

API Key 请直接填写控制台提供的 Key，无需添加引号或其他内容。

配置完成后，将天气数据源切换为和风天气即可。

> 和风天气 API Host 与 API Key 均与开发者账号相关，请使用自己的 API Host 和 API Key，不要使用他人的配置。

如果暂时不使用和风天气，可以切换至小米天气数据源。

## 安全说明

项目历史提交中曾出现过部分 API Key，目前这些 Key 均已全部重置并失效。

使用相关 API 时，请配置自己的 API Key。

## 文档

- [模板自定义文档](docs/template-customization.md)
- [组件开发文档](docs/widget-development.md)

> 目前 StartInfo 暂不支持插件系统，现有 Widget 均为内置组件，统一位于 [core/widgets.py](core/widgets.py)。

## 更新

StartInfo 支持多个更新源，目前包括：

- GitHub
- GitHub 镜像站
- 阿里云 OSS

## 开源协议

本项目采用 GNU GPLv3.0 许可证开源。

完整许可证内容请参见项目根目录的 [LICENSE](LICENSE) 文件。

## 依赖

StartInfo 主要使用以下项目：

- [Python](https://www.python.org/)
- [PySide6](https://doc.qt.io/qtforpython-6/gettingstarted.html#getting-started)
- [QFluentWidgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets/tree/PySide6)

## 致谢

感谢以下项目和资源：

- [Class-Widgets](https://github.com/Class-Widgets/Class-Widgets) — 部分设计思路参考
- [QWidgetSekai](https://github.com/Aegisir/QWidgetSekai) — 设置页面开关按钮移植自其 [switch_button.py](https://github.com/Aegisir/QWidgetSekai/blob/main/pyqt_project/SwitchButton/src/switch_button.py)，原始实现基于 PyQt5，已移植至 PySide6
- ### 接口与资料

- [XiaomiWeather API](https://github.com/huanghui0906/API/blob/master/XiaomiWeather.md) — 小米天气接口资料参考
- [Icons8](https://icons8.com/) — 程序图标资源

## 贡献者

感谢参与 StartInfo 开发、测试和反馈的贡献者。

<p>
  <a href="https://github.com/HuangTao313">
    <img src="https://github.com/HuangTao313.png" width="60px" alt="HuangTao">
  </a>
  <a href="https://github.com/Yuuka-doesnt-know">
    <img src="https://github.com/Yuuka-doesnt-know.png" width="60px" alt="Yukka-doesnt-know">
  </a>
</p>
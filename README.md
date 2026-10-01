<div align="center">

<img src="docs/images/startinfo.png" alt="StartInfo Logo" width="18%">

<h1>开机速览 / StartInfo</h1>

<p>一个基于 PySide6 + QFluentWidgets 开发的桌面信息展示工具。</p>

[![星标](https://img.shields.io/github/stars/HuangTao313/StartInfo?style=for-the-badge&color=orange&label=星标)](https://github.com/HuangTao313/StartInfo)
[![开源许可证](https://img.shields.io/github/license/HuangTao313/StartInfo?style=for-the-badge&color=darkgreen&label=开源许可证)](LICENSE)
[![下载量](https://img.shields.io/github/downloads/HuangTao313/StartInfo/total.svg?style=for-the-badge&color=green&label=下载量)](https://github.com/HuangTao313/StartInfo/releases)
[![最新版本](https://img.shields.io/github/v/release/HuangTao313/StartInfo?style=for-the-badge&label=最新版本)](https://github.com/HuangTao313/StartInfo/releases)

</div>

<p align="center">
简体中文 | <a href="docs/en/README_en.md">English</a>
</p>

> [!WARNING]
> **低频维护公告**
>
> 由于学业安排变化，作者后续可投入项目维护的时间有限，因此本项目将在未来进入低频维护状态。
>
> 项目仍会继续维护，但新功能开发和版本更新可能主要集中于寒暑假等较长假期。
>
> 如发现 Bug 或有改进建议，欢迎提交 Issue；如果您有能力参与开发，也欢迎提交 Pull Request。

# 功能

* 天气与空气质量
* 日期、时间、农历、24 节气、节假日
* 历史上的今天
* 今日人品
* Minecraft 服务器信息
* 更多功能……

# 截图

<table>
  <tr>
    <td style="text-align: center;">主界面（深色模式）</td>
    <td style="text-align: center;">设置界面（深色模式）</td>
  </tr>
  <tr>
    <td><img src="docs/images/main-window.png" width="100%" /></td>
    <td><img src="docs/images/settings.png" width="100%" /></td>
  </tr>
</table>

# 下载

目前提供 Windows 安装版和便携版。


## Windows

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


# 更新机制

StartInfo 支持多个更新源：

* GitHub (默认)
* GitHub 镜像站

为了避免更新接口被频繁请求，StartInfo 会对版本检查结果进行本地缓存。

版本信息缓存默认有效期为 **10分钟**。在缓存有效期间，再次检查更新不会重新请求服务器。

因此，如果 StartInfo 已经检查过一次更新，即使之后立即发布了新版本，用户也可能需要等待当前缓存过期后才能检测到新版本。

这是为了降低更新接口的请求压力，并避免更新接口被频繁请求。

# 和风天气配置

如果使用和风天气作为天气数据源，需要在设置中配置自己的 API Host 和 API Key。

## 获取 API Host 和 API Key

1. 前往 [和风天气开发平台](https://dev.qweather.com/) 注册并登录账号。
2. 创建项目并获取 API Key。
3. 在开发控制台的设置页面查看自己的 API Host。

StartInfo 需要同时使用 API Host 和 API Key 才能正常请求和风天气 API。

## 在 StartInfo 中配置

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

# 安全说明

项目历史提交中曾出现过部分 API Key，目前这些 Key 均已全部重置并失效。

使用相关 API 时，请配置自己的 API Key。

# AI 辅助开发

本项目开发过程中使用了 AI 辅助编程（Vibe Coding），包括代码编写、重构、调试、问题分析等。

项目的整体设计、功能规划、代码审查与最终维护由作者负责。

# 文档

- [开发指南](docs/development.md)
- [模板自定义文档](docs/template-customization.md)
- [组件开发文档](docs/widget-development.md)

# 依赖

StartInfo 主要使用以下项目：

- [Python](https://www.python.org/)
- [PySide6](https://doc.qt.io/qtforpython-6/gettingstarted.html#getting-started)
- [PySide6-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets/tree/PySide6)
- [Loguru](https://github.com/Delgan/loguru)

# 致谢

感谢以下项目和资源：

- [Class-Widgets](https://github.com/Class-Widgets/Class-Widgets) — 部分设计思路参考
- [QWidgetSekai](https://github.com/Aegisir/QWidgetSekai) — 设置页面开关按钮移植自其 [switch_button.py](https://github.com/Aegisir/QWidgetSekai/blob/main/pyqt_project/SwitchButton/src/switch_button.py)，原始实现基于 PyQt5，已移植至 PySide6
- ### 接口与资料

- [XiaomiWeather API](https://github.com/huanghui0906/API/blob/master/XiaomiWeather.md) — 小米天气接口资料参考

## 图标资源

- [AppIcon Forge](https://github.com/zhangyu1818/appicon-forge) — 用于生成应用程序图标
- [Material Design Icons](https://github.com/google/material-design-icons) — 主程序图标资源来源
- [Fluent UI System Icons](https://github.com/microsoft/fluentui-system-icons) — 设置窗口图标资源来源

## 贡献者

感谢参与 StartInfo 开发、测试和反馈的贡献者。

<p>
  <a href="https://github.com/HuangTao313">
    <img src="https://github.com/HuangTao313.png" width="60px" alt="HuangTao" style="border-radius: 50%;">
  </a>
  <a href="https://github.com/Yuuka-doesnt-know">
    <img src="https://github.com/Yuuka-doesnt-know.png" width="60px" alt="Yukka-doesnt-know" style="border-radius: 50%;">
  </a>
</p>

# 版权

本项目采用 GNU GPLv3.0 许可证开源。

完整许可证内容请参见项目根目录的 [LICENSE](LICENSE) 文件。

#

Copyright © 2023-2026 HuangTao313. Licensed under GPL-3.0.
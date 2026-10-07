# Qt TS 自动翻译工具

简体中文 | [English](README_en.md)

`translate_ts.py` 是 StartInfo 的开发辅助工具，用于调用有道**大模型翻译 API**（子曰翻译，默认 pro 模型），批量翻译 Qt Linguist 的 `.ts` 文件。

它主要用于生成**机器翻译初稿**，最终译文建议使用 Qt Linguist 人工检查。

---

## 1. 环境

需要：

* Python 3.11+
* `httpx`
* 有道智云**大模型翻译** API（接口详情见[官方文档](https://ai.youdao.com/DOCSIRMA/html/trans/api/dmxfy/index.html)）

StartInfo 已经使用 `httpx`，无需额外安装依赖。

工具文件：

```text
tools/
└── i18n/
    ├── .env
    ├── translate_ts.py
    └── translate_ts.md
```

---

## 2. 配置 API

在 `.env`（`tools/i18n/.env`，与脚本同目录）中填写：

```dotenv
YOUDAO_APP_KEY=你的应用ID
YOUDAO_APP_SECRET=你的应用密钥
```

并确保 `.env` 不提交到 Git：

```gitignore
tools/i18n/.env
```

> 注意：大模型翻译需要在有道智云控制台为**同一个应用（appKey）**单独开通「大模型翻译」服务，开通经典文本翻译不会自动带上。

---

## 3. 自定义提示词

大模型翻译模式支持自定义提示词。脚本内置了精简的项目提示词（`translate_ts.py` 中的 `TRANSLATION_PROMPT` 常量）：

```python
TRANSLATION_PROMPT = (
    "这是桌面应用「开机速览」(StartInfo)的界面文案翻译。"
    "应用名统一译为 StartInfo；组件统一译为 Widget(s)；"
    "保留 {} 占位符、换行符与原文格式，不要多加解释，只返回译文。"
)
```

当前约定的项目专有名词：

| 原文 | 译文 |
| --- | --- |
| 开机速览 | StartInfo |
| 组件 | Widget(s) |

如需调整约定（新增专有名词、修改措辞），直接编辑该常量即可。有道限制提示词 ≤1200 字符 / 400 单词。

模型通过 `HANDLE_OPTION` 常量切换：默认 `"0"`（pro，14B）。**注意：实测 lite（`"3"`，1.5B）会忽略提示词**，专有名词约定不生效，因此依赖提示词时必须使用 pro。

---

## 4. 基本用法

```powershell
uv run python tools/i18n/translate_ts.py 输入文件 输出文件 --to 目标语言
```

例如：

```powershell
uv run python tools/i18n/translate_ts.py `
    data/assets/i18n/startinfo/startinfo.zh_CN.ts `
    data/assets/i18n/startinfo/startinfo.en_US.ts `
    --to en
```

原始 `.ts` 不会被修改。

默认源语言为简体中文，也可以使用 `--from` 指定：

```powershell
uv run python tools/i18n/translate_ts.py input.ts output.ts --from zh_CN --to en
```

---

## 5. 语言代码

常用语言可以直接使用以下写法：

| 参数      | 有道语言代码   |
| ------- |----------|
| `zh_CN` | `zh-CHS` |
| `zh_TW` | `zh-CHT` |
| `zh_HK` | `zh-CHT` |
| `en_US` | `en`     |
| `en`    | `en`     |
| `ja`    | `ja`     |
| `ko`    | `ko`     |
| `fr`    | `fr`     |
| `de`    | `de`     |
| `es`    | `es`     |
| `ru`    | `ru`     |

例如：

```powershell
uv run python tools/i18n/translate_ts.py input.ts output.ts --to zh_TW
```

如果没有快捷映射，也可以直接使用有道 API 支持的语言代码。

---

## 6. 增量翻译

如果输出文件已经存在，脚本会读取其中已有的译文。

**已经完成的译文不会被覆盖。**

例如第一次运行：

```text
268 条 source
↓
生成英文 TS
```

之后修改代码并重新运行 `lupdate`，新增了 10 条 source：

```text
已有译文 → 保留
新增/未完成 → 自动翻译
```

因此可以反复运行，不需要每次重新翻译整个文件。

Qt TS 中标记为 `unfinished` 的条目也会重新进入翻译任务。

`obsolete` / `vanished` 条目不会请求翻译。

---

## 7. 翻译去重与并发

相同的 `<source>` 文本只请求一次 API。

例如：

```text
设置
设置
关闭
设置
关闭
```

实际只需要请求：

```text
设置
关闭
```

翻译结果会应用到所有对应条目。

脚本使用异步请求，最多同时进行 **3 个 API 请求**（大模型翻译接口 QPS 限制为 10，3 并发已留余量）。

```python
MAX_CONCURRENCY = 3
```

如果请求失败会自动重试。

---

## 8. 进度显示

运行过程中会显示简单的命令行进度：

```text
翻译中 [████████████████████░░░░░░░░] 180/268
```

翻译完成后会列出失败的条目。

失败的条目不会写入错误译文，可以之后重新运行脚本再次尝试。

---

## 9. StartInfo 推荐工作流程

**所有命令统一通过 `uv run` 执行**，确保使用项目虚拟环境里的 pyside6 工具（如 `uv run pyside6-lupdate`、`uv run pyside6-lrelease`），不要直接调用全局安装的版本。

```text
修改 Python 源码（写 self.tr('...') / tr('...') 标记）
      ↓
i18n_tool.py update        ← lupdate 扫描源码，更新所有 .ts
      ↓
translate_ts.py            ← 生成目标语言的机器翻译初稿
      ↓
Qt Linguist 人工校对
      ↓
i18n_tool.py release       ← lrelease 编译 .ts → .qm
```

### 9.1 扫描源码生成/更新 .ts

使用 `tools/i18n/i18n_tool.py`（封装了 pyside6-lupdate，自动递归扫描 `core/` 并包含 `main.py`、`settings.py`，一次更新 languages.json 中登记的所有语言的 .ts）：

```powershell
uv run python tools/i18n/i18n_tool.py update
```

已有的译文不会被覆盖，只新增/更新条目；代码里删除的文案会标记为 `obsolete` 而不是直接删除。

### 9.2 生成翻译初稿

```powershell
uv run python tools/i18n/translate_ts.py `
    data/assets/i18n/startinfo/startinfo.zh_CN.ts `
    data/assets/i18n/startinfo/startinfo.en_US.ts `
    --to en_US
```

然后使用 Qt Linguist 检查和修改译文。

### 9.3 编译 .ts → .qm

```powershell
uv run python tools/i18n/i18n_tool.py release
```

每个语言的 .qm 输出路径取自 languages.json 中该语言 `files` 列表里登记的 `startinfo/` 条目，与 `app.py` 运行时加载的路径自动保持一致。

### 9.4 一键全流程

修改代码后如果不需要人工校对，可以直接：

```powershell
uv run python tools/i18n/i18n_tool.py all
```

### 9.5 手动命令参考

脚本本质上是以下命令的封装（`lupdate` 需要显式列出源文件，`lrelease` 需要指定输出路径，跨平台终端语法不同，因此推荐使用脚本）：

```powershell
# 扫描 tr() 标记（文件较多，此处仅示意；完整列表见 i18n_tool.py 的 SCAN_FILES）
uv run pyside6-lupdate core/ui/app.py main.py settings.py -ts data/assets/i18n/startinfo/startinfo.zh_CN.ts

# 编译翻译文件
uv run pyside6-lrelease data/assets/i18n/startinfo/startinfo.zh_CN.ts -qm data/assets/i18n/startinfo/startinfo.zh_CN.qm
```

### 9.6 新增语言接入

1. 在 `data/assets/i18n/languages.json` 中添加语言条目（键为语言代码，`files` 里登记 `startinfo/startinfo.<目标语言>.qm`）
2. `uv run python tools/i18n/i18n_tool.py update` —— lupdate 会自动创建对应的 `.ts`
3. `uv run python tools/i18n/translate_ts.py data/assets/i18n/startinfo/startinfo.zh_CN.ts data/assets/i18n/startinfo/startinfo.<目标语言>.ts --to <目标语言>` 生成初稿
4. Qt Linguist 校对后，`uv run python tools/i18n/i18n_tool.py release` 编译
5. `.qm` 编译好后重启程序，即可在设置里切换到新语言

---

## 10. 注意事项

这个工具的定位是：

> **自动生成翻译初稿，而不是完全替代人工翻译。**

机器翻译尤其容易在以下内容中出现不自然或错误的表达：

* 短 UI 文案
* 设置项
* 技术名词
* 专有名词
* 上下文相关的词语
* 动态文案

因此建议最终使用 Qt Linguist 人工检查。

另外，`.ts` 是翻译源文件，`.qm` 是 Qt 运行时加载的编译文件。自动翻译工具只处理 `.ts`，不会直接修改 `.qm`。
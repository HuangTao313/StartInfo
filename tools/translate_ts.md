# Qt TS 自动翻译工具

`translate_ts.py` 是 StartInfo 的开发辅助工具，用于调用有道翻译 API，批量翻译 Qt Linguist 的 `.ts` 文件。

它主要用于生成**机器翻译初稿**，最终译文建议使用 Qt Linguist 人工检查。

---

## 1. 环境

需要：

* Python 3.11+
* `httpx`
* 有道智云翻译 API

StartInfo 已经使用 `httpx`，无需额外安装依赖。

工具文件：

```text
tools/
├── .env
├── translate_ts.py
└── translate_ts.md
```

---

## 2. 配置 API

在 `tools/.env` 中填写：

```dotenv
YOUDAO_APP_KEY=你的应用ID
YOUDAO_APP_SECRET=你的应用密钥
```

并确保 `.env` 不提交到 Git：

```gitignore
tools/.env
```

---

## 3. 基本用法

```powershell
python tools/translate_ts.py 输入文件 输出文件 --to 目标语言
```

例如：

```powershell
python tools/translate_ts.py `
    data/assets/i18n/startinfo/startinfo_zh_CN.ts `
    data/assets/i18n/startinfo/startinfo_en_US.ts `
    --to en
```

原始 `.ts` 不会被修改。

默认源语言为简体中文，也可以使用 `--from` 指定：

```powershell
python tools/translate_ts.py input.ts output.ts --from zh_CN --to en
```

---

## 4. 语言代码

常用语言可以直接使用以下写法：

| 参数      | 有道语言代码   |
| ------- |----------|
| `zh_CN` | `zh-CHS` |
| `zh_TW` | `zh-CHT` |
| `zh_HK` | `zh-CHT` |
| `en_US` | `en_US`  |
| `en`    | `en`     |
| `ja`    | `ja`     |
| `ko`    | `ko`     |
| `fr`    | `fr`     |
| `de`    | `de`     |
| `es`    | `es`     |
| `ru`    | `ru`     |

例如：

```powershell
python tools/translate_ts.py input.ts output.ts --to zh_TW
```

如果没有快捷映射，也可以直接使用有道 API 支持的语言代码。

---

## 5. 增量翻译

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

## 6. 翻译去重与并发

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

脚本使用异步请求，最多同时进行 **3 个 API 请求**。

```python
MAX_CONCURRENCY = 3
```

如果请求失败会自动重试。

---

## 7. 进度显示

运行过程中会显示简单的命令行进度：

```text
翻译中 [████████████████████░░░░░░░░] 180/268
```

翻译完成后会列出失败的条目。

失败的条目不会写入错误译文，可以之后重新运行脚本再次尝试。

---

## 8. StartInfo 推荐工作流程

```text
修改 Python 源码
      ↓
   lupdate
      ↓
startinfo_zh_CN.ts
      ↓
translate_ts.py
      ↓
目标语言 .ts
      ↓
Qt Linguist 人工校对
      ↓
  lrelease
      ↓
目标语言 .qm
```

更新中文 TS：

```powershell
pyside6-lupdate `
    (Get-ChildItem core -Recurse -Filter *.py | Select-Object -ExpandProperty FullName) `
    main.py settings.py `
    -ts data/assets/i18n/startinfo/startinfo_zh_CN.ts
```

生成英文初稿：

```powershell
python tools/translate_ts.py `
    data/assets/i18n/startinfo/startinfo_zh_CN.ts `
    data/assets/i18n/startinfo/startinfo_en_US.ts `
    --to en
```

然后使用 Qt Linguist 检查和修改译文。

最后使用：

```powershell
uv run pyside6-lrelease data/assets/i18n/startinfo/startinfo_en_US.ts
```

生成 `.qm`。

---

## 9. 注意事项

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
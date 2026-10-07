# Qt TS Auto-Translation Tool

[简体中文](README.md) | English

`translate_ts.py` is a development helper for StartInfo that batch-translates Qt Linguist `.ts` files by calling the Youdao **Large Model Translation API** (Ziyun translation, pro model by default).

It is intended to produce **machine-translation drafts**; the final translation should be reviewed manually with Qt Linguist.

---

## 1. Environment

Requirements:

* Python 3.11+
* `httpx`
* A Youdao Zhiyun **Large Model Translation** API account (see the [official documentation](https://ai.youdao.com/DOCSIRMA/html/trans/api/dmxfy/index.html) for API details)

StartInfo already uses `httpx`, so no extra dependencies are needed.

Tool files:

```text
tools/
└── i18n/
    ├── .env
    ├── translate_ts.py
    └── translate_ts.md
```

---

## 2. Configuring the API

Fill in the following in `.env` (`tools/i18n/.env`, in the same directory as the script):

```dotenv
YOUDAO_APP_KEY=your application ID
YOUDAO_APP_SECRET=your application secret
```

Make sure `.env` is not committed to Git:

```gitignore
tools/i18n/.env
```

> Note: Large model translation must be enabled separately for **the same application (appKey)** in the Youdao Zhiyun console. Enabling the classic text translation service does not enable it automatically.

---

## 3. Customizing the Prompt

Large model translation mode supports a custom prompt. The script ships with a concise project prompt (the `TRANSLATION_PROMPT` constant in `translate_ts.py`):

```python
TRANSLATION_PROMPT = (
    "这是桌面应用「开机速览」(StartInfo)的界面文案翻译。"
    "应用名统一译为 StartInfo；组件统一译为 Widget(s)；"
    "保留 {} 占位符、换行符与原文格式，不要多加解释，只返回译文。"
)
```

The current project-specific terminology conventions:

| Source | Translation |
| --- | --- |
| 开机速览 | StartInfo |
| 组件 | Widget(s) |

To adjust the conventions (add terminology, change wording), edit the constant directly. Youdao limits prompts to ≤1200 characters / 400 words.

The model is switched via the `HANDLE_OPTION` constant: the default `"0"` (pro, 14B). **Note: in testing, lite (`"3"`, 1.5B) ignores the prompt**, so the terminology conventions do not take effect — always use pro when relying on the prompt.

---

## 4. Basic Usage

```powershell
uv run python tools/i18n/translate_ts.py input_file output_file --to target_language
```

For example:

```powershell
uv run python tools/i18n/translate_ts.py `
    data/assets/i18n/startinfo/startinfo.zh_CN.ts `
    data/assets/i18n/startinfo/startinfo.en_US.ts `
    --to en
```

The original `.ts` file is never modified.

The default source language is Simplified Chinese; you can also specify it with `--from`:

```powershell
uv run python tools/i18n/translate_ts.py input.ts output.ts --from zh_CN --to en
```

---

## 5. Language Codes

Common languages can be used directly with the following shorthand:

| Argument | Youdao language code |
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

For example:

```powershell
uv run python tools/i18n/translate_ts.py input.ts output.ts --to zh_TW
```

If a language has no shorthand mapping, use any language code supported by the Youdao API directly.

---

## 6. Incremental Translation

If the output file already exists, the script reads the translations it contains.

**Existing translations are never overwritten.**

For example, the first run:

```text
268 source entries
↓
English TS generated
```

After you modify the code and re-run `lupdate`, 10 new source entries appear:

```text
Existing translations → kept
New/unfinished → translated automatically
```

So the script can be run repeatedly without re-translating the whole file every time.

Entries marked `unfinished` in the Qt TS file also re-enter the translation queue.

`obsolete` / `vanished` entries are never sent for translation.

---

## 7. Deduplication and Concurrency

Identical `<source>` text is requested from the API only once.

For example:

```text
设置
设置
关闭
设置
关闭
```

Only these requests are actually made:

```text
设置
关闭
```

The translation results are applied to all matching entries.

The script uses asynchronous requests with at most **3 concurrent API requests** (the large model translation endpoint is limited to 10 QPS, so 3 concurrent requests leave headroom).

```python
MAX_CONCURRENCY = 3
```

Failed requests are retried automatically.

---

## 8. Progress Display

A simple command-line progress bar is shown while running:

```text
翻译中 [████████████████████░░░░░░░░] 180/268
```

Failed entries are listed after translation completes.

Failed entries are never written with erroneous text; simply re-run the script later to retry them.

---

## 9. Recommended Workflow for StartInfo

**Run all commands through `uv run`** to make sure the pyside6 tools from the project's virtual environment are used (e.g. `uv run pyside6-lupdate`, `uv run pyside6-lrelease`) — do not call globally installed versions directly.

```text
Modify Python source (add self.tr('...') / tr('...') markers)
      ↓
i18n_tool.py update        ← lupdate scans the source and updates all .ts files
      ↓
translate_ts.py            ← generates machine-translation drafts for target languages
      ↓
Manual review in Qt Linguist
      ↓
i18n_tool.py release       ← lrelease compiles .ts → .qm
```

### 9.1 Scanning the Source to Generate/Update .ts

Use `tools/i18n/i18n_tool.py` (a wrapper around pyside6-lupdate that automatically scans `core/` recursively and includes `main.py` and `settings.py`, updating the .ts files for all languages registered in languages.json in one run):

```powershell
uv run python tools/i18n/i18n_tool.py update
```

Existing translations are not overwritten; only new/updated entries are added. Text removed from the code is marked `obsolete` rather than deleted outright.

### 9.2 Generating Translation Drafts

```powershell
uv run python tools/i18n/translate_ts.py `
    data/assets/i18n/startinfo/startinfo.zh_CN.ts `
    data/assets/i18n/startinfo/startinfo.en_US.ts `
    --to en_US
```

Then review and edit the translations with Qt Linguist.

### 9.3 Compiling .ts → .qm

```powershell
uv run python tools/i18n/i18n_tool.py release
```

The .qm output path for each language comes from the `startinfo/` entry in that language's `files` list in languages.json, and automatically stays in sync with the path loaded by `app.py` at runtime.

### 9.4 One-Command Full Pipeline

If no manual review is needed after modifying the code, run directly:

```powershell
uv run python tools/i18n/i18n_tool.py all
```

### 9.5 Manual Command Reference

The scripts are essentially wrappers around the following commands (`lupdate` requires source files to be listed explicitly and `lrelease` requires an explicit output path, and terminal syntax differs across platforms — hence the scripts are recommended):

```powershell
# Scan tr() markers (many files; shown for illustration only — see SCAN_FILES in i18n_tool.py for the full list)
uv run pyside6-lupdate core/ui/app.py main.py settings.py -ts data/assets/i18n/startinfo/startinfo.zh_CN.ts

# Compile the translation file
uv run pyside6-lrelease data/assets/i18n/startinfo/startinfo.zh_CN.ts -qm data/assets/i18n/startinfo/startinfo.zh_CN.qm
```

### 9.6 Adding a New Language

1. Add a language entry in `data/assets/i18n/languages.json` (keyed by language code, with `startinfo/startinfo.<target language>.qm` registered under `files`)
2. `uv run python tools/i18n/i18n_tool.py update` — lupdate creates the corresponding `.ts` automatically
3. `uv run python tools/i18n/translate_ts.py data/assets/i18n/startinfo/startinfo.zh_CN.ts data/assets/i18n/startinfo/startinfo.<target language>.ts --to <target language>` to generate a draft
4. After reviewing in Qt Linguist, `uv run python tools/i18n/i18n_tool.py release` to compile
5. Once the `.qm` is compiled, restart the application and switch to the new language in Settings

---

## 10. Caveats

The positioning of this tool is:

> **Automatically generate translation drafts — not fully replace human translators.**

Machine translation is particularly prone to unnatural or incorrect phrasing in:

* Short UI strings
* Settings items
* Technical terms
* Proper nouns
* Context-dependent words
* Dynamic text

For these reasons, a final manual review with Qt Linguist is recommended.

Also note that `.ts` is the translation source file and `.qm` is the compiled file loaded by Qt at runtime. The auto-translation tool only works on `.ts` files and never modifies `.qm` files directly.

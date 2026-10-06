"""i18n 流程脚本：封装 pyside6-lupdate / pyside6-lrelease，跨平台一致。

用法（统一通过 uv run 调用，确保使用项目虚拟环境的 pyside6 工具）::

    uv run python tools/i18n/i18n_tool.py update    # 扫描 tr() 标记，更新所有 .ts
    uv run python tools/i18n/i18n_tool.py release   # 编译所有 .ts → .qm
    uv run python tools/i18n/i18n_tool.py all       # 依次执行 update 和 release

语言列表读取 data/assets/i18n/languages.json；每个语言的 .ts 路径由
清单中登记的 startinfo .qm 条目推导（.qm → .ts），命名跟随清单。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LANGUAGES_JSON = PROJECT_ROOT / 'data' / 'assets' / 'i18n' / 'languages.json'

# lupdate 扫描范围：core 递归 + 两个入口脚本
SCAN_FILES = sorted((PROJECT_ROOT / 'core').rglob('*.py')) + [
    PROJECT_ROOT / 'main.py',
    PROJECT_ROOT / 'settings.py',
]


def load_manifest() -> dict:
    """读取 languages.json（语言代码 → name/version/files）。"""
    return json.loads(LANGUAGES_JSON.read_text(encoding='utf-8'))


def startinfo_qm_path(info: dict) -> str | None:
    """取该语言清单里 startinfo 的 qm 条目（相对 i18n 目录），无则返回 None。"""
    for file_path in info.get('files', []):
        if file_path.startswith('startinfo/'):
            return file_path
    return None


def pyside6_tool(name: str) -> Path:
    """定位虚拟环境内的 pyside6 可执行工具，不依赖 PATH。

    用 ``uv run python`` 执行本脚本时，sys.executable 就是 venv 解释器，
    其所在目录（Windows 为 Scripts/，POSIX 为 bin/）即工具所在目录。
    """
    suffix = '.exe' if sys.platform == 'win32' else ''
    tool = Path(sys.executable).parent / f'{name}{suffix}'

    if not tool.exists():
        raise SystemExit(
            f'未找到 {name}：{tool}\n'
            '请通过 uv run 在项目虚拟环境中执行本脚本，例如：\n'
            '    uv run python tools/i18n/i18n_tool.py update'
        )

    return tool


def ts_path(qm_entry: str) -> Path:
    """由清单登记的 qm 相对路径推导同名的 .ts 路径。"""
    return PROJECT_ROOT / 'data' / 'assets' / 'i18n' / qm_entry.replace('.qm', '.ts')


def run_update() -> None:
    """lupdate 扫描源码中的 tr() 标记，一次性更新所有语言的 .ts。"""
    manifest = load_manifest()

    ts_files = []
    for language, info in manifest.items():
        qm_entry = startinfo_qm_path(info)
        if qm_entry is None:
            print(f'警告：{language} 在 languages.json 中没有 startinfo 的 qm 条目，跳过')
            continue
        ts_files.append(ts_path(qm_entry))

    command = [
        str(pyside6_tool('pyside6-lupdate')),
        *[str(path) for path in SCAN_FILES],
        '-ts',
        *[str(path) for path in ts_files],
    ]

    print(f'扫描 {len(SCAN_FILES)} 个源文件，更新 {len(ts_files)} 个 .ts ...')
    result = subprocess.run(command, cwd=str(PROJECT_ROOT))

    if result.returncode != 0:
        raise SystemExit(f'lupdate 执行失败（退出码 {result.returncode}）')

    for path in ts_files:
        print(f'已更新：{path.relative_to(PROJECT_ROOT)}')


def run_release() -> None:
    """lrelease 把每个语言的 .ts 编译为 languages.json 中登记的 .qm。"""
    manifest = load_manifest()
    lrelease = pyside6_tool('pyside6-lrelease')

    for language, info in manifest.items():
        qm_entry = startinfo_qm_path(info)
        if qm_entry is None:
            print(f'警告：{language} 在 languages.json 中没有 startinfo 的 qm 条目，跳过')
            continue

        source = ts_path(qm_entry)
        if not source.exists():
            print(f'警告：{source.name} 不存在，跳过 {language}')
            continue

        # 与 app.py 运行时加载路径保持一致：qm 路径直接取清单登记的条目
        target = PROJECT_ROOT / 'data' / 'assets' / 'i18n' / qm_entry
        target.parent.mkdir(parents=True, exist_ok=True)

        print(f'编译 {source.name} → {target.relative_to(PROJECT_ROOT)} ...')
        result = subprocess.run(
            [str(lrelease), str(source), '-qm', str(target)],
            cwd=str(PROJECT_ROOT),
        )

        if result.returncode != 0:
            raise SystemExit(f'lrelease 执行失败（{language}，退出码 {result.returncode}）')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='StartInfo i18n 流程工具（封装 pyside6-lupdate / pyside6-lrelease）'
    )
    parser.add_argument(
        'command',
        choices=['update', 'release', 'all'],
        help='update=扫描 tr 标记更新 .ts；release=编译 .ts 为 .qm；all=依次执行',
    )

    args = parser.parse_args()

    if args.command in ('update', 'all'):
        run_update()
    if args.command in ('release', 'all'):
        run_release()


if __name__ == '__main__':
    main()

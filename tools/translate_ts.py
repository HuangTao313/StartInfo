from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx


API_URL = "https://openapi.youdao.com/api"
MAX_CONCURRENCY = 3
MAX_RETRIES = 4

LANGUAGE_MAP = {
    "zh_CN": "zh-CHS",
    "zh_TW": "zh-CHT",
    "zh_HK": "zh-CHT",
    "en_US": "en_US",
    "en": "en",
    "ja": "ja",
    "ko": "ko",
    "fr": "fr",
    "de": "de",
    "es": "es",
    "ru": "ru",
}


def load_env(path: Path) -> None:
    """读取简单的 KEY=VALUE 格式 .env。"""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")

        if key and key not in os.environ:
            os.environ[key] = value


def truncate(text: str) -> str:
    if len(text) <= 20:
        return text
    return text[:10] + str(len(text)) + text[-10:]


def sign_request(
    app_key: str,
    app_secret: str,
    query: str,
    salt: str,
    curtime: str,
) -> str:
    value = app_key + truncate(query) + salt + curtime + app_secret
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def translate(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    app_key: str,
    app_secret: str,
    text: str,
    source_lang: str,
    target_lang: str,
) -> str:
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            salt = str(uuid.uuid4())
            curtime = str(int(time.time()))

            params = {
                "q": text,
                "from": source_lang,
                "to": target_lang,
                "appKey": app_key,
                "salt": salt,
                "sign": sign_request(
                    app_key,
                    app_secret,
                    text,
                    salt,
                    curtime,
                ),
                "signType": "v3",
                "curtime": curtime,
            }

            try:
                response = await client.get(
                    API_URL,
                    params=params,
                    timeout=20,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("errorCode") not in (None, "0"):
                    raise RuntimeError(
                        f"有道 API 错误 {data['errorCode']}: "
                        f"{data.get('errorMessage', '未知错误')}"
                    )

                translations = data.get("translation")
                if not translations:
                    raise RuntimeError("API 未返回 translation")

                return translations[0]

            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(str(e)) from e

                await asyncio.sleep(2**attempt)

    raise RuntimeError("翻译失败")


def show_progress(done: int, total: int) -> None:
    width = 30
    filled = int(width * done / total)
    bar = "█" * filled + "░" * (width - filled)

    print(
        f"\r翻译中 [{bar}] {done}/{total}",
        end="",
        flush=True,
    )

def message_key(context: ET.Element, message: ET.Element) -> tuple[str, str]:
    context_name = context.findtext("name") or ""
    source = message.findtext("source") or ""
    return context_name, source


def get_translation(message: ET.Element) -> ET.Element:
    translation = message.find("translation")

    if translation is None:
        translation = ET.SubElement(message, "translation")

    return translation


def is_finished(message: ET.Element) -> bool:
    translation = message.find("translation")

    if translation is None:
        return False

    if translation.get("type") == "unfinished":
        return False

    return bool((translation.text or "").strip())


def parse_ts(path: Path) -> ET.ElementTree:
    return ET.parse(path)


def copy_existing_translations(
    source_tree: ET.ElementTree,
    output_tree: ET.ElementTree,
) -> list[tuple[ET.Element, str]]:
    """
    把已有输出文件中的正常译文复制到最新 source TS。

    返回需要翻译的消息：
        [(message_element, source_text), ...]
    """
    old_messages: dict[tuple[str, str], ET.Element] = {}

    for context in output_tree.getroot().findall("context"):
        for message in context.findall("message"):
            key = message_key(context, message)
            old_messages[key] = message

    pending = []

    for context in source_tree.getroot().findall("context"):
        for message in context.findall("message"):
            translation = message.find("translation")

            # lupdate 已经标记为 obsolete 的内容不需要翻译
            if translation is not None and translation.get("type") == "obsolete":
                continue

            key = message_key(context, message)
            old_message = old_messages.get(key)

            if old_message is not None and is_finished(old_message):
                old_translation = old_message.find("translation")
                new_translation = get_translation(message)

                new_translation.text = old_translation.text

                # 保留已有翻译的属性，但去掉 unfinished
                for key, value in old_translation.attrib.items():
                    new_translation.set(key, value)

                new_translation.attrib.pop("type", None)
                continue

            source = message.findtext("source") or ""

            if source.strip():
                pending.append((message, source))

    return pending


async def translate_pending(
    pending: list[tuple[ET.Element, str]],
    app_key: str,
    app_secret: str,
    source_lang: str,
    target_lang: str,
) -> None:
    if not pending:
        print("没有需要翻译的新内容。")
        return

    # 相同 source 只请求一次 API
    unique_sources = list(dict.fromkeys(source for _, source in pending))

    print(
        f"待翻译消息：{len(pending)} 条，"
        f"去重后 API 请求：{len(unique_sources)} 条"
    )

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    results: dict[str, str] = {}
    errors: dict[str, str] = {}

    completed = 0
    lock = asyncio.Lock()

    async with httpx.AsyncClient() as client:

        async def run(source: str) -> None:
            nonlocal completed

            try:
                results[source] = await translate(
                    client,
                    semaphore,
                    app_key,
                    app_secret,
                    source,
                    source_lang,
                    target_lang,
                )
            except Exception as e:
                errors[source] = str(e)

            async with lock:
                completed += 1
                show_progress(completed, len(unique_sources))

        await asyncio.gather(
            *(run(source) for source in unique_sources)
        )

    print()

    if errors:
        print(f"\n翻译失败：{len(errors)} 条")
        for source, error in errors.items():
            print(f"- {source}")
            print(f"  {error}")

    for message, source in pending:
        translated = results.get(source)

        if translated is None:
            continue

        translation = get_translation(message)
        translation.text = translated
        translation.attrib.pop("type", None)


def indent_xml(tree: ET.ElementTree) -> None:
    try:
        ET.indent(tree, space="    ")
    except AttributeError:
        pass


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="使用有道翻译 API 增量翻译 Qt .ts 文件"
    )
    parser.add_argument("source", type=Path, help="源 .ts 文件")
    parser.add_argument("output", type=Path, help="输出 .ts 文件")
    parser.add_argument(
        "--from",
        dest="source_lang",
        default="zh_CN",
        help="源语言，默认 zh_CN",
    )
    parser.add_argument(
        "--to",
        required=True,
        help="目标语言，例如 en_US、zh_TW",
    )

    args = parser.parse_args()

    if args.source_lang not in LANGUAGE_MAP:
        raise SystemExit(f"不支持的源语言：{args.source_lang}")

    if args.to not in LANGUAGE_MAP:
        raise SystemExit(f"不支持的目标语言：{args.to}")

    if not args.source.exists():
        raise SystemExit(f"源文件不存在：{args.source}")

    load_env(Path(__file__).with_name(".env"))

    app_key = os.getenv("YOUDAO_APP_KEY")
    app_secret = os.getenv("YOUDAO_APP_SECRET")

    if not app_key or not app_secret:
        raise SystemExit(
            "未找到 YOUDAO_APP_KEY 或 YOUDAO_APP_SECRET。\n"
            "请在 tools/.env 中配置。"
        )

    source_tree = parse_ts(args.source)

    if args.output.exists():
        output_tree = parse_ts(args.output)
        print(f"读取已有翻译：{args.output}")
    else:
        output_tree = None
        print("输出文件不存在，将进行首次翻译。")

    if output_tree is None:
        # 第一次运行：直接以 source TS 作为输出基础。
        pending = []

        for context in source_tree.getroot().findall("context"):
            for message in context.findall("message"):
                translation = message.find("translation")

                if (
                    translation is not None
                    and translation.get("type") == "obsolete"
                ):
                    continue

                source = message.findtext("source") or ""

                if source.strip():
                    pending.append((message, source))

        output_tree = source_tree
    else:
        # 后续运行：以最新 source TS 为结构基础，
        # 把已有输出中的正常译文合并进来。
        pending = copy_existing_translations(
            source_tree,
            output_tree,
        )

        # 使用最新 source TS 的结构。
        source_root = source_tree.getroot()
        output_root = output_tree.getroot()

        output_root.clear()
        output_root.attrib.update(source_root.attrib)

        for child in source_root:
            output_root.append(child)

    await translate_pending(
        pending,
        app_key,
        app_secret,
        LANGUAGE_MAP[args.source_lang],
        LANGUAGE_MAP[args.to],
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)

    indent_xml(output_tree)
    output_tree.write(
        args.output,
        encoding="utf-8",
        xml_declaration=True,
    )

    print(f"\n完成：{args.output}")


if __name__ == "__main__":
    asyncio.run(main())
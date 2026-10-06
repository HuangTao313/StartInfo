import subprocess
import asyncio
import httpx
import time
import json
import hashlib
import sys
from pathlib import Path

from .base_lib import CURRENT_VERSION_JSON, is_internet, read_json
from .config import cfg
from .logger import log
from .paths import API_FILE_PATH, CACHE_FOLDER_PATH, VERSION_CACHE_FILE_PATH

api_data = read_json(API_FILE_PATH)

# 非 Windows 平台点击"立即更新"时跳转的 GitHub Releases 页面地址（可在 api.json 中配置）
GITHUB_RELEASES_URL: str = api_data.get('update_source', {}).get(
    'github_releases', 'https://github.com/HuangTao313/StartInfo/releases/latest')


class DownloadCancelled(Exception):
    """用户取消下载时由 download_file_async 内部抛出，仅作控制流使用"""


# ==================== 保留你原有的函数 ====================
def get_version_file() -> bool:
    """
    【使用场景】启动更新流程前，获取远程最新版本元数据
    【输入】无（自动从 API_FILE_PATH 读取加密URL）
    【输出】bool - True=成功下载并保存到 VERSION_CACHE_FILE_PATH（含 get_time 字段）
    【注意】
      - 会自动创建 VERSION_CACHE_FILE_PATH 的父目录
      - 失败时记录详细错误日志
    """
    try:
        if 'update_source' not in api_data:
            log.error("更新器-API配置中缺少[update_source]字段")
            return False

        # 如果使用GitHub镜像站，就拼接前缀
        if cfg.update_source.value == 'github_mirror':
            url = api_data['update_source']['github_mirror_prefix'] + api_data['update_source']['github']

        else:
            url = api_data['update_source'][cfg.update_source.value]

    except Exception as e:
        log.error(f"更新器-解密更新URL失败: {e}")
        return False

    try:
        # 修复点：创建的是父目录（json/），不是 version.json 文件本身
        VERSION_CACHE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    except Exception as e:
        log.error(f"更新器-创建版本目录失败: {e}")
        return False

    try:
        log.debug(f'更新器-获取远程版本文件: {url}')
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            existing_data = response.json()
            existing_data['get_time'] = int(time.time())
            # 记录本次使用的更新源，供缓存判断是否需要换源重新获取
            existing_data['update_source'] = cfg.update_source.value
            with open(VERSION_CACHE_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)
        log.info(f"更新器-已成功获取版本文件: {VERSION_CACHE_FILE_PATH}")
        return True
    except Exception as e:
        log.error(f"更新器-获取版本文件失败: {e}")
        return False


# ==================== 核心工具函数 ====================
def verify_sha256(file_path: Path, expected_sha256: str) -> bool:
    """
    【使用场景】下载文件后校验完整性
    【输入】
        file_path: Path - 待校验文件路径
        expected_sha256: str - 预期SHA256值（小写）
    【输出】bool - True=校验通过
    【注意】大文件分块计算，避免内存溢出
    """
    if not file_path.exists():
        log.error(f"更新器-文件不存在: {file_path}")
        return False
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        actual = sha256.hexdigest().lower()
        if actual == expected_sha256.lower():
            log.info(f"更新器-SHA256校验通过: {file_path.name}")
            return True
        else:
            log.error(f"更新器-SHA256校验失败! 期望: {expected_sha256}, 实际: {actual}")
            return False
    except Exception as e:
        log.error(f"更新器-SHA256校验异常: {e}")
        return False

# ==================== 下载模块 ====================
async def download_file_async(url: str, filename: str, progress_callback=None,
                              cancel_check=None) -> Path | None:
    """
    【使用场景】异步下载完整更新安装程序
    【输入】
        url: str - 下载链接
        filename: str - 保存文件名（不含路径）
        progress_callback: Callable[[int, int], None] - 进度回调(downloaded, total)，每次写入数据块后调用
        cancel_check: Callable[[], bool] - 每次写入数据块前调用，返回 True 时中止下载并删除残缺文件
    【输出】Path | None - 成功返回完整路径，失败或被取消返回None
    【注意】
      - 自动创建 CACHE_FOLDER_PATH
      - 使用 httpx.AsyncClient 流式下载（内存友好，不阻塞 UI）
      - 进度回调在事件循环主线程内执行，可直接更新 Qt 控件
    """
    CACHE_FOLDER_PATH.mkdir(parents=True, exist_ok=True)
    output_path = CACHE_FOLDER_PATH / filename

    log.debug(f'更新器-下载开始: {filename}')

    # 请求超时设置
    timeout = httpx.Timeout(
        connect=30.0,  # 连接超时 30秒
        read=300.0,    # 读取超时 5分钟
        write=300.0,
        pool=300.0,
    )

    log.debug(f'下载url:{url}')

    try:
        # follow_redirects: 跟随 302 重定向（如 GitHub releases 的 /latest/download/ 链接）
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()

                # 获取文件总大小（用于进度计算）
                total_size = int(resp.headers.get('content-length', 0))

                downloaded = 0
                with open(output_path, 'wb') as f:
                    async for chunk in resp.aiter_bytes(chunk_size=8192):  # 8KB/块
                        if cancel_check and cancel_check():
                            raise DownloadCancelled

                        f.write(chunk)
                        downloaded += len(chunk)

                        # 汇报下载进度
                        if progress_callback:
                            progress_callback(downloaded, total_size)

                log.info(f'更新器-下载完成: {filename} ({downloaded} bytes)')
                return output_path

    except DownloadCancelled:
        log.info(f'更新器-下载已取消: {filename}')
    except httpx.TimeoutException:
        log.error(f"更新器-下载超时 (300秒): {filename}")
    except httpx.HTTPError as e:
        log.error(f"更新器-HTTP下载错误: {e}")
    except Exception as e:
        log.error(f"更新器-下载异常: {str(e)}")

    # 下载失败，清理残缺文件
    if output_path.exists():
        try:
            output_path.unlink()
        except:
            pass

    return None

# ==================== 完整更新模块 ====================
def launch_installer(installer_path: Path) -> bool:
    """
    【使用场景】启动完整安装程序（静默安装），不退出当前进程
    【输入】installer_path: Path - Inno Setup 安装程序路径 (.exe)
    【输出】bool - 是否成功启动
    【注意】
      - 调用方须先关闭 UI 再调用本函数，启动后自行优雅退出进程
        （Inno 的 /CLOSEAPPLICATIONS 会兜底关闭残留进程）
    """
    if not installer_path.exists():
        log.critical(f"更新器-安装程序不存在: {installer_path}")
        return False

    log.info(f"更新器-启动完整安装程序: {installer_path.name}")
    try:
        subprocess.Popen(['start', '', str(installer_path)], shell=True)
        log.info("更新器-安装程序已启动")
        return True
    except Exception as e:
        log.critical(f"更新器-启动安装程序失败: {e}")
        return False


def apply_full_update(installer_path: Path) -> None:
    """
    【使用场景】启动完整安装程序（用于更新更新器自身或重大重构）并立即退出当前进程
    【输入】installer_path: Path - Inno Setup 安装程序路径 (.exe)
    【输出】无（函数内直接退出进程）
    【关键行为】
      1. 启动静默安装（/VERYSILENT /SUPPRESSMSGBOXES）
      2. 自动关闭关联应用（/CLOSEAPPLICATIONS）
      3. 安装完成后自动启动主程序（需Inno脚本配置 [Run]）
      4. 立即退出当前更新器进程（释放文件锁）
    【注意】
      - 调用后进程终止，后续代码不会执行
      - UI 场景请勿直接调用：先用 launch_installer() 并自行关闭窗口后优雅退出，
        避免事件循环运行中被 sys.exit 强杀（退出码 0xC0000409）
      - 确保 installer_path 是有效 Inno Setup 安装包
    """
    sys.exit(0 if launch_installer(installer_path) else 1)

# ==================== 检查更新决策 ====================
def check_update() -> tuple[bool, dict]:
    """
    【使用场景】判断是否需要更新 + 返回更新策略
    【输入】无（自动读取 VERSION_CACHE_FILE_PATH 和 CURRENT_VERSION_JSON）
    【输出】(need_update: bool, update_info: dict)
        update_info 包含: type, url, sha256, [changelog], [reason]
    """
    # 读取本地版本
    current_ver = CURRENT_VERSION_JSON.get('version', '0.0.0')
    current_ts = CURRENT_VERSION_JSON.get('release_timestamp', 0)

    # 读取远程版本
    if not VERSION_CACHE_FILE_PATH.exists():
        log.error("更新器-远程版本文件不存在，请先调用 get_version_file()")
        return False, {}

    try:
        remote = read_json(VERSION_CACHE_FILE_PATH)
        remote_ts = remote.get('release_timestamp', 0)
        remote_ver = remote.get('version', '')
    except Exception as e:
        log.error(f"更新器-解析远程版本文件失败: {e}")
        return False, {}

    # 版本比较
    log.debug(f'更新器-检查更新: 当前版本={current_ver}, 远程版本={remote_ver}')
    if remote_ts <= current_ts:
        log.info(f"更新器-已是最新版本(当前: {current_ver}, 远程: {remote_ver})")
        return False, {}

    log.info(f"更新器-发现新版本! 当前: {current_ver} → 远程: {remote_ver}")

    # 决策：完整更新（服务端强制 或 常规新版本）
    reason = '服务端强制完整更新' if remote.get('force_full_update', False) else f'当前版本 {current_ver} 可升级到 {remote_ver}'
    return True, _build_update_info(remote, 'full', reason)


def _build_update_info(remote: dict, update_type: str, reason: str) -> dict:
    """【内部函数】构建完整更新的更新信息"""
    # 延迟导入：core.ui.dialogs 依赖本模块，顶层导入 tr 会造成循环导入
    from .ui.app import tr

    pkg = remote.get('full_package', {})

    # 如果使用GitHub镜像站，就拼接前缀
    if cfg.update_source.value == 'github_mirror':
        url = api_data['update_source']['github_mirror_prefix'] + pkg.get('url', '')

    else:
        url = pkg.get('url', '')

    return {
        'version': remote.get('version', tr('版本号获取失败')),
        'release_date': remote.get('release_date', tr('日期获取失败')),
        'changelog': remote.get('changelog', tr('更新日志获取失败')),
        'type': update_type,
        'url': url,
        'sha256': pkg.get('sha256', ''),
        'reason': reason,
    }

async def download_and_verify_async(update_info: dict, progress_callback=None,
                                    cancel_check=None) -> tuple[Path | None, str]:
    """
    【异步流程】下载 → 校验（不启动安装，由调用方决定启动时机）
    返回: (安装包路径, 错误信息)；失败时路径为 None
    """
    # 延迟导入：core.ui.dialogs 依赖本模块，顶层导入 tr 会造成循环导入
    from .ui.app import tr

    # 下载
    log.info('更新器-准备完整更新，正在下载...')
    update_file_path = await download_file_async(
        update_info['url'], filename='setup.exe', progress_callback=progress_callback,
        cancel_check=cancel_check)
    if not update_file_path:
        return None, tr('下载更新包时出错，请稍后重试。')

    # 校验（放入线程池，避免阻塞 UI）
    if not await asyncio.to_thread(verify_sha256, update_file_path, update_info['sha256']):
        return None, tr('更新包校验失败，文件可能已损坏。')

    return update_file_path, ''

async def perform_update_async(update_info: dict, progress_callback=None,
                               cancel_check=None) -> tuple[bool, str]:
    """
    【异步流程】下载 → 校验 → 应用安装程序
    返回: (是否成功, 错误信息)；成功时内部会启动安装程序并退出当前进程
    """
    installer_path, error_msg = await download_and_verify_async(
        update_info, progress_callback=progress_callback, cancel_check=cancel_check)
    if installer_path is None:
        return False, error_msg

    # 应用（此函数会启动安装程序并退出当前进程）
    apply_full_update(installer_path)
    return True, ''

async def check_update_logic(force_refresh: bool = False) -> tuple[bool, dict, str | None]:
    """
    【核心逻辑】仅检查更新，不触发任何控制台或 UI 弹窗
    返回: (是否有更新, 更新信息字典, 错误信息)
        错误信息为 None 表示检查正常完成（可能没有更新）
        错误信息非 None 表示检查失败，调用方应提示出错而不是"已是最新版本"
    :param force_refresh: True 时跳过缓存，强制从当前更新源重新获取版本文件
    """
    # 延迟导入：core.ui.dialogs 依赖本模块，顶层导入 tr 会造成循环导入
    from .ui.app import tr

    log.debug(f'更新器-开始检查更新 (force_refresh={force_refresh})')
    try:
        # 0. 联网检查提前：断网时直接给出准确提示，
        #    避免先尝试拉取失败后报出误导性的"获取版本信息失败"；
        #    探测移入线程池，避免阻塞事件循环/UI
        if not await asyncio.to_thread(is_internet):
            return False, {}, tr('无法连接网络，检查更新失败')

        # 1. 版本文件维护逻辑
        need_fetch = force_refresh or not VERSION_CACHE_FILE_PATH.exists()
        if not need_fetch:
            version_data = read_json(VERSION_CACHE_FILE_PATH)
            cache_expired = int(time.time()) - version_data.get('get_time', 0) >= 600
            # 缓存是旧更新源获取的，切换更新源后必须重新获取
            source_changed = version_data.get('update_source') != cfg.update_source.value
            need_fetch = cache_expired or source_changed
            if source_changed:
                log.info(
                    f"更新器-更新源已切换"
                    f"（{version_data.get('update_source')} → {cfg.update_source.value}），重新获取版本文件"
                )

        if need_fetch:
            if not await asyncio.to_thread(get_version_file):
                log.warning("更新器-静默检查失败：无法获取远程版本")
                return False, {}, tr(
                    '获取版本信息失败（更新源: {source}），请检查网络或更新源配置'
                ).format(source=cfg.update_source.value)

        # 2. 比对版本
        need_update, update_info = check_update()  # 调用你原有的比对函数
        return need_update, update_info, None
    except Exception as e:
        log.error(f"静默检查异常: {e}")
        return False, {}, tr('检查更新异常: {error}').format(error=e)
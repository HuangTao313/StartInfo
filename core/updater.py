import subprocess
import asyncio
import httpx
import time
import json
import hashlib
import sys
from pathlib import Path
from . import ht_lib as lib
from . import ui
from .config import cfg

# ==================== 路径定义 ====================
VERSION_PATH: Path = lib.MAIN_PATH / 'data' / 'json' / 'version.json'  # 远程版本缓存
CURRENT_VERSION_PATH: Path = lib.CURRENT_VERSION_PATH  # 本地已安装版本记录
log = lib.log


# ==================== 保留你原有的函数 ====================
def get_version_file() -> bool:
    """
    【使用场景】启动更新流程前，获取远程最新版本元数据
    【输入】无（自动从 lib.API_FILE_PATH 读取加密URL）
    【输出】bool - True=成功下载并保存到 VERSION_PATH（含 get_time 字段）
    【注意】
      - 会自动创建 VERSION_PATH 的父目录
      - 失败时记录详细错误日志
    """
    try:
        api_data = lib.read_json(lib.API_FILE_PATH)
        if 'update_source' not in api_data:
            log.error("更新器-API配置中缺少[update_source]字段")
            return False
        url = api_data['update_source'][cfg.update_source.value]

    except Exception as e:
        log.error(f"更新器-解密更新URL失败: {e}")
        return False

    try:
        # 修复点：创建的是父目录（json/），不是 version.json 文件本身
        VERSION_PATH.parent.mkdir(parents=True, exist_ok=True)

    except Exception as e:
        log.error(f"更新器-创建版本目录失败: {e}")
        return False

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            existing_data = response.json()
            existing_data['get_time'] = int(time.time())
            with open(VERSION_PATH, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)
        log.info(f"更新器-已成功获取版本文件: {VERSION_PATH}")
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
def download_file(url: str, filename: str, show_progress: bool = True) -> Path | None:
    """
    【使用场景】下载完整更新安装程序
    【输入】
        url: str - 下载链接
        filename: str - 保存文件名（不含路径）
        show_progress: bool - 是否显示控制台进度条（默认True）
    【输出】Path | None - 成功返回完整路径，失败返回None
    【注意】
      - 自动创建 lib.DOWNLOAD_PATH
      - 使用 httpx 流式下载（内存友好）
      - 支持实时控制台进度条
      - 返回 Path 对象便于后续操作
    """
    lib.DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
    output_path = lib.DOWNLOAD_PATH / filename

    # 请求超时设置
    timeout = httpx.Timeout(
        connect=30.0,  # 连接超时 30秒
        read=300.0,    # 读取超时 5分钟
        write=300.0,
        pool=300.0,
    )

    try:
        with httpx.Client(timeout=timeout) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()

                # 获取文件总大小（用于进度计算）
                total_size = int(resp.headers.get('content-length', 0))

                downloaded = 0
                with open(output_path, 'wb') as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):  # 8KB/块
                        f.write(chunk)
                        downloaded += len(chunk)

                        # 显示进度条
                        if show_progress and total_size > 0:
                            percent = min(100, int(downloaded / total_size * 100))
                            _print_progress_bar(percent, downloaded, total_size)

                # 下载完成，清理进度行
                if show_progress:
                    print()  # 换行

                log.info(f'更新器-下载完成: {filename} ({downloaded} bytes)')
                return output_path

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


def _print_progress_bar(percent: int, downloaded: int, total: int):
    """
    【私有函数】打印控制台进度条
    【输入】percent: 0-100, downloaded: 已下载字节数, total: 总字节数
    【输出】无（直接打印到控制台）
    【格式】[████████████████████████████████████████] 100% (45.6MB / 45.6MB)
    """
    bar_length = 40  # 进度条长度
    filled_length = int(bar_length * percent // 100)

    # 构造进度条字符
    bar = '█' * filled_length + '-' * (bar_length - filled_length)

    # 格式化文件大小（B → MB/KB）
    def format_bytes(size: int) -> str:
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        else:
            return f"{size / (1024 * 1024):.1f}MB"

    # 打印进度（覆盖上一行）
    print(f"\r[{bar}] {percent:3d}% ({format_bytes(downloaded)} / {format_bytes(total)})", end='', flush=True)

# ==================== 完整更新模块 ====================
def apply_full_update(installer_path: Path) -> None:
    """
    【使用场景】启动完整安装程序（用于更新更新器自身或重大重构）
    【输入】installer_path: Path - Inno Setup 安装程序路径 (.exe)
    【输出】无（函数内直接退出进程）
    【关键行为】
      1. 启动静默安装（/VERYSILENT /SUPPRESSMSGBOXES）
      2. 自动关闭关联应用（/CLOSEAPPLICATIONS）
      3. 安装完成后自动启动主程序（需Inno脚本配置 [Run]）
      4. 立即退出当前更新器进程（释放文件锁）
    【注意】
      - 调用后进程终止，后续代码不会执行
      - 确保 installer_path 是有效 Inno Setup 安装包
    """
    if not installer_path.exists():
        log.critical(f"更新器-安装程序不存在: {installer_path}")
        sys.exit(1)

    log.info(f"更新器-启动完整安装程序: {installer_path.name}")
    try:
        subprocess.Popen(['start', '', str(installer_path)], shell=True)
        log.info("更新器-安装程序已启动，更新器即将退出")
        sys.exit(0)  # ⚠️ 关键：立即释放文件锁
    except Exception as e:
        log.critical(f"更新器-启动安装程序失败: {e}")
        sys.exit(1)


# ==================== 检查更新决策 ====================
def check_update() -> tuple[bool, dict]:
    """
    【使用场景】判断是否需要更新 + 返回更新策略
    【输入】无（自动读取 VERSION_PATH 和 lib.CURRENT_VERSION_JSON）
    【输出】(need_update: bool, update_info: dict)
        update_info 包含: type, url, sha256, [changelog], [reason]
    """
    # 读取本地版本
    current_ver = lib.CURRENT_VERSION_JSON.get('version', '0.0.0')
    current_ts = lib.CURRENT_VERSION_JSON.get('release_timestamp', 0)

    # 读取远程版本
    if not VERSION_PATH.exists():
        log.error("更新器-远程版本文件不存在，请先调用 get_version_file()")
        return False, {}

    try:
        remote = lib.read_json(VERSION_PATH)
        remote_ts = remote.get('release_timestamp', 0)
        remote_ver = remote.get('version', '')
    except Exception as e:
        log.error(f"更新器-解析远程版本文件失败: {e}")
        return False, {}

    # 版本比较
    if remote_ts <= current_ts:
        log.info(f"更新器-已是最新版本(当前: {current_ver}, 远程: {remote_ver})")
        return False, {}

    log.info(f"更新器-发现新版本! 当前: {current_ver} → 远程: {remote_ver}")

    # 决策：完整更新（服务端强制 或 常规新版本）
    reason = '服务端强制完整更新' if remote.get('force_full_update', False) else f'当前版本 {current_ver} 可升级到 {remote_ver}'
    return True, _build_update_info(remote, 'full', reason)


def _build_update_info(remote: dict, update_type: str, reason: str) -> dict:
    """【内部函数】构建完整更新的更新信息"""
    pkg = remote.get('full_package', {})

    return {
        'version': remote.get('version', '版本号获取失败'),
        'release_date': remote.get('release_date', '日期获取失败'),
        'changelog': remote.get('changelog', '更新日志获取失败'),
        'type': update_type,
        'url': pkg.get('url', ''),
        'sha256': pkg.get('sha256', ''),
        'reason': reason,
    }


def perform_update(update_info: dict) -> None:
    """执行完整更新流程（下载 → 校验 → 应用安装程序）"""
    # 下载
    log.info('更新器-准备完整更新，正在下载...')
    update_file_path = download_file(update_info['url'], filename='StartInfo.exe')
    if not update_file_path:
        ui.dialog('更新失败', '下载更新包时出错，请稍后重试。')
        return

    # 校验
    if not verify_sha256(update_file_path, update_info['sha256']):
        ui.dialog('更新失败', '更新包校验失败，文件可能已损坏。')
        return

    # 应用（此函数会启动安装程序并退出当前进程）
    apply_full_update(update_file_path)

async def check_update_logic() -> tuple[bool, dict, str | None]:
    """
    【核心逻辑】仅检查更新，不触发任何控制台或 UI 弹窗
    返回: (是否有更新, 更新信息字典, 错误信息)
        错误信息为 None 表示检查正常完成（可能没有更新）
        错误信息非 None 表示检查失败，调用方应提示出错而不是"已是最新版本"
    """
    try:
        # 1. 版本文件维护逻辑
        if not VERSION_PATH.exists():
            if not await asyncio.to_thread(get_version_file):
                return False, {}, f"获取版本信息失败（更新源: {cfg.update_source.value}），请检查网络或更新源配置"
        else:
            version_data = lib.read_json(VERSION_PATH)
            # 过期检查（1小时）
            if int(time.time()) - version_data.get('get_time', 0) >= 3600:
                if not await asyncio.to_thread(get_version_file):
                    log.warning("更新器-静默检查失败：无法获取远程版本")
                    return False, {}, f"获取版本信息失败（更新源: {cfg.update_source.value}），请检查网络或更新源配置"

        # 2. 联网并比对
        if not lib.is_internet():
            return False, {}, "无法连接网络，检查更新失败"

        need_update, update_info = check_update()  # 调用你原有的比对函数
        return need_update, update_info, None
    except Exception as e:
        log.error(f"静默检查异常: {e}")
        return False, {}, f"检查更新异常: {e}"


def run_update_process(update_info: dict) -> None:
    """
    【执行逻辑】执行下载替换（窗口已关闭，同步即可）。
    """
    perform_update(update_info)


# ==========================================
# 兼容层：适配旧版设置和直接运行
# ==========================================
def start_updater() -> None:
    """
    旧版入口：包含检查逻辑和弹窗确认
    """
    loop = asyncio.get_event_loop()
    need_update, update_info, error_msg = loop.run_until_complete(check_update_logic())

    if error_msg:
        ui.dialog(lib.TITLE, error_msg)
    elif need_update:
        text = f"发现新版本：{update_info.get('version', '未知')}\n\n更新内容：\n{update_info.get('changelog', '暂无')}"
        if ui.dialog('更新器', text, ['立即更新', '取消更新']):
            run_update_process(update_info)
        else:
            log.info('更新器-用户取消更新')
            lib.restart_program('--settings')
    else:
        log.info('更新器-已是最新版本')
        ui.dialog(lib.TITLE, '更新器-已是最新版本')


if __name__ == '__main__':
    # 初始化UI
    ui.app_manager.init_app()
    start_updater()
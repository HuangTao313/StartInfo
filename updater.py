import subprocess
import zipfile
import aiohttp
import asyncio
import aiofiles
import time
import json
import hashlib
import shutil
import sys
from pathlib import Path
import core.ht_lib as lib
import core.ui as ui

# ==================== 路径定义 ====================
VERSION_PATH: Path = lib.MAIN_PATH / 'data' / 'json' / 'version.json'  # 远程版本缓存
CURRENT_VERSION_PATH: Path = lib.CURRENT_VERSION_PATH  # 本地已安装版本记录
DOWNLOAD_PATH: Path = lib.MAIN_PATH / 'data' / 'download'
log = lib.log


# ==================== 保留你原有的函数 ====================
async def get_version_file() -> bool:
    """
    【使用场景】启动更新流程前，获取远程最新版本元数据
    【输入】无（自动从 lib.API_PATH 读取加密URL）
    【输出】bool - True=成功下载并保存到 VERSION_PATH（含 get_time 字段）
    【注意】
      - 会自动创建 VERSION_PATH 的父目录
      - 失败时记录详细错误日志
      - 保留你原有的解密逻辑和错误处理
    """
    try:
        api_data = lib.read_json(lib.API_PATH)
        if 'check_update_url' not in api_data:
            log.error("更新器-API配置中缺少check_update_url字段")
            return False
        url = lib.decrypt(api_data['check_update_url'])
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
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                content = await response.read()
                existing_data = json.loads(content.decode('utf-8'))
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
        log.error(f"文件不存在: {file_path}")
        return False
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        actual = sha256.hexdigest().lower()
        if actual == expected_sha256.lower():
            log.info(f"SHA256校验通过: {file_path.name}")
            return True
        else:
            log.error(f"SHA256校验失败! 期望: {expected_sha256}, 实际: {actual}")
            return False
    except Exception as e:
        log.error(f"SHA256校验异常: {e}")
        return False


# ==================== 下载模块（aria2） ====================
async def download_file(url: str, filename: str, show_progress: bool = True) -> Path | None:
    """
    【使用场景】下载更新包（增量包/安装程序）
    【输入】
        url: str - 下载链接
        filename: str - 保存文件名（不含路径）
        show_progress: bool - 是否显示控制台进度条（默认True）
    【输出】Path | None - 成功返回完整路径，失败返回None
    【注意】
      - 自动创建 DOWNLOAD_PATH
      - 使用 aiohttp 流式下载（内存友好）
      - 支持实时控制台进度条
      - 返回 Path 对象便于后续操作
    """
    DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
    output_path = DOWNLOAD_PATH / filename

    # 请求超时设置
    timeout = aiohttp.ClientTimeout(
        total=300,  # 总超时 5分钟
        connect=30  # 连接超时 30秒
    )

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                resp.raise_for_status()

                # 获取文件总大小（用于进度计算）
                total_size = int(resp.headers.get('content-length', 0))

                downloaded = 0
                async with aiofiles.open(output_path, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(8192):  # 8KB/块
                        await f.write(chunk)
                        downloaded += len(chunk)

                        # 显示进度条
                        if show_progress and total_size > 0:
                            percent = min(100, int(downloaded / total_size * 100))
                            _print_progress_bar(percent, downloaded, total_size)

                # 下载完成，清理进度行
                if show_progress:
                    print()  # 换行

                log.info(f'下载器-下载完成: {filename} ({downloaded} bytes)')
                return output_path

    except asyncio.TimeoutError:
        log.error(f"下载超时 (300秒): {filename}")
    except aiohttp.ClientError as e:
        log.error(f"HTTP下载错误: {e}")
    except Exception as e:
        log.error(f"下载异常: {str(e)}")

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

# ==================== 增量更新模块 ====================
def apply_incremental_update(zip_path: Path, delete_list_filename: str = "delete.json") -> bool:
    """
    【使用场景】应用增量更新包（解压→删旧文件→覆盖→清理）
    【输入】
        zip_path: Path - 增量包路径
        delete_list_filename: str - 包内删除列表文件名（默认"delete.json"）
    【输出】bool - True=更新成功
    【流程】
      1. 解压到临时目录（自动处理中文路径）
      2. 读取 delete.json → 删除 MAIN_PATH 下对应文件/目录
      3. 复制临时目录中其他文件到 MAIN_PATH（覆盖）
      4. 清理临时目录 + delete.json
    【注意】
      - delete.json 格式: ["相对路径1", "目录/"]（目录以/结尾）
      - 跳过复制 delete.json 本身
      - 严格保留目录结构
    """
    temp_dir = DOWNLOAD_PATH / "update_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # === 步骤1: 解压到临时目录（复用你的中文修复逻辑）===
        if not unzip_to_temp(zip_path, temp_dir):
            return False

        # === 步骤2: 处理删除列表 ===
        delete_file = temp_dir / delete_list_filename
        if delete_file.exists():
            try:
                delete_list = lib.read_json(delete_file)
                deleted_count = 0
                for rel_path in delete_list:
                    target = lib.MAIN_PATH / rel_path.strip()
                    if target.exists():
                        try:
                            if target.is_dir():
                                shutil.rmtree(target)
                            else:
                                target.unlink()
                            deleted_count += 1
                        except Exception as e:
                            log.warning(f"删除失败 {rel_path}: {e}")
                log.info(f"根据 {delete_list_filename} 删除 {deleted_count} 项")
                delete_file.unlink()  # 立即清理，避免被复制
            except Exception as e:
                log.error(f"处理删除列表失败: {e}")
                return False

        # === 步骤3: 覆盖主程序目录（跳过 delete.json）===
        copied_count = 0
        for src_item in temp_dir.rglob('*'):
            if not src_item.is_file() or src_item.name == delete_list_filename:
                continue
            # 计算相对路径
            rel_path = src_item.relative_to(temp_dir)
            dest_path = lib.MAIN_PATH / rel_path

            # 确保目标目录存在
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # 覆盖文件（处理文件锁定）
            try:
                if dest_path.exists():
                    dest_path.unlink()
                shutil.copy2(src_item, dest_path)
                copied_count += 1
            except PermissionError:
                # 文件被占用（如 update.exe 正在运行）→ 标记待重启生效
                pending_path = dest_path.with_suffix(dest_path.suffix + '.pending')
                shutil.copy2(src_item, pending_path)
                log.warning(f"文件被占用，标记待重启生效: {dest_path.name}")
            except Exception as e:
                log.error(f"覆盖文件失败 {rel_path}: {e}")
                return False

        log.info(f"增量更新完成: 覆盖 {copied_count} 个文件")

        return True

    except Exception as e:
        log.error(f"应用增量更新异常: {e}")
        return False
    finally:
        # 清理临时目录
        if temp_dir.exists():
            try:
                shutil.rmtree(DOWNLOAD_PATH)
            except Exception as e:
                log.warning(f"清理临时目录失败: {e}")


def unzip_to_temp(zip_path: Path, extract_to: Path) -> bool:
    """
    【内部函数】安全解压ZIP到临时目录（专为增量更新设计）
    【输入】
        zip_path: Path - ZIP文件路径
        extract_to: Path - 目标目录
    【输出】bool - True=解压成功
    【特点】
      - 修复中文文件名（CP437→GBK/UTF-8）
      - 跳过目录条目
      - 详细错误日志
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file in zip_ref.namelist():
                # 修复中文路径
                try:
                    fixed_name = file.encode('cp437').decode('gbk', errors='strict')
                except:
                    try:
                        fixed_name = file.encode('cp437').decode('utf-8', errors='strict')
                    except:
                        fixed_name = file  # 保留原始

                # 跳过目录
                if fixed_name.endswith('/') or fixed_name.endswith('\\'):
                    continue

                target_path = extract_to / fixed_name
                target_path.parent.mkdir(parents=True, exist_ok=True)

                with zip_ref.open(file) as source, open(target_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
        log.info(f"解压成功: {len(zip_ref.namelist())} 项 → {extract_to}")
        return True
    except Exception as e:
        log.error(f"解压失败: {e}")
        return False


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
        log.critical(f"安装程序不存在: {installer_path}")
        sys.exit(1)

    log.info(f"启动完整安装程序: {installer_path.name}")
    try:
        subprocess.Popen(['start', '', str(installer_path)], shell=True)
        log.info("安装程序已启动，更新器即将退出")
        sys.exit(0)  # ⚠️ 关键：立即释放文件锁
    except Exception as e:
        log.critical(f"启动安装程序失败: {e}")
        sys.exit(1)


# ==================== 检查更新决策 ====================
def check_update() -> tuple[bool, dict]:
    """
    【使用场景】判断是否需要更新 + 返回更新策略
    【输入】无（自动读取 VERSION_PATH 和 lib.CURRENT_VERSION_JSON）
    【输出】(need_update: bool, update_info: dict)
        update_info 包含: type, url, sha256, [changelog], [reason], [delete_list]
    """
    # 读取本地版本
    current_ver = lib.CURRENT_VERSION_JSON.get('version', '0.0.0')
    current_ts = lib.CURRENT_VERSION_JSON.get('release_timestamp', 0)

    # 读取远程版本
    if not VERSION_PATH.exists():
        log.error("远程版本文件不存在，请先调用 get_version_file()")
        return False, {}

    try:
        remote = lib.read_json(VERSION_PATH)
        remote_ts = remote.get('release_timestamp', 0)
        remote_ver = remote.get('version', '')
    except Exception as e:
        log.error(f"解析远程版本文件失败: {e}")
        return False, {}

    # 版本比较
    if remote_ts <= current_ts:
        log.info(f"已是最新版 (当前: {current_ver}, 远程: {remote_ver})")
        return False, {}

    log.info(f"发现新版本! 当前: {current_ver} → 远程: {remote_ver}")

    # 决策分支
    if remote.get('force_full_update', False):
        return True, _build_update_info(remote, 'full', '服务端强制完整更新')

    # 尝试增量更新
    incremental_pkg = remote.get('incremental_packages', {}).get(current_ver)
    if incremental_pkg:
        return True, _build_update_info(remote, 'incremental', f'支持 {current_ver} → {remote_ver} 增量更新',
                                        incremental_pkg)

    # 降级完整更新
    return True, _build_update_info(remote, 'full', f'当前版本 {current_ver} 无增量包，使用完整更新')


def _build_update_info(remote: dict, update_type: str, reason: str, pkg: dict = None) -> dict:
    """【内部函数】构建统一的更新信息"""
    if pkg is None:  # 完整更新
        pkg = remote.get('full_package', {})

    return {
        'version': remote.get('version', '版本号获取失败'),
        'changelog': remote.get('changelog', '更新日志获取失败'),
        'type': update_type,
        'url': pkg.get('url', ''),
        'sha256': pkg.get('sha256', ''),
        'reason': reason,
        **({'delete_list': pkg.get('delete_list', 'delete.json')} if update_type == 'incremental' else {})
    }


async def perform_update(update_info: dict) -> None:
    """执行完整的更新流程（下载 → 校验 → 应用）"""
    update_type_en = update_info.get('type', '')
    file_name = 'update_package.zip' if update_type_en == 'incremental' else 'StartInfo.exe'

    # 下载
    log.info(f'准备{"增量" if update_type_en == "incremental" else "完整"}更新，正在下载...')
    update_file_path = await download_file(update_info['url'], filename=file_name)
    if not update_file_path:
        ui.dialog('更新失败', '下载更新包时出错，请稍后重试。')
        return

    # 校验
    if not verify_sha256(update_file_path, update_info['sha256']):
        ui.dialog('更新失败', '更新包校验失败，文件可能已损坏。')
        return

    # 应用
    if update_type_en == 'incremental':
        if apply_incremental_update(update_file_path):
            ui.dialog('更新成功', f'程序已更新至最新版本{update_info.get('version','版本号获取失败')}')
            subprocess.Popen([lib.EXE_PATH, "--update"])

            ui.app_manager.quit()
            sys.exit()
        else:
            ui.dialog('更新失败', '增量更新过程中出现错误。')
    else:
        apply_full_update(update_file_path)  # 此函数会直接退出进程

if __name__ == '__main__':
    try:
        # 初始化UI
        ui.app_manager.init_app()
        # 检查version.json是否存在
        if not VERSION_PATH.exists():
            if not asyncio.run(get_version_file()):
                error_text = '无法获取远程版本信息，请检查网络连接'
                log.error(error_text)
                ui.dialog('获取版本信息失败', error_text)

        else:
            # 存在，检查版本文件是否过期(过期时间：1小时)
            version_data = lib.read_json(VERSION_PATH)
            if int(time.time()) - version_data.get('get_time', 0) >= 3600:
                if not asyncio.run(get_version_file()):
                    error_text = '无法获取远程版本信息，请检查网络连接'
                    log.error(error_text)
                    ui.dialog('获取版本信息失败', error_text)

        # 检查联网状态
        if lib.is_internet():
            # 检查更新
            need_update, update_info = check_update()
            # 如果需要更新
            if need_update:
                text = f'''发现新版本：{update_info.get("version", "未知")}

更新内容：
{update_info.get("changelog", "暂无更新日志")}'''

                if not ui.dialog('更新器', text, ['立即更新', '取消更新']):
                    log.info('用户取消更新')
                    ui.app_manager.quit()
                    sys.exit()

                # 执行更新（逻辑已抽离）
                asyncio.run(perform_update(update_info))



    except Exception as e:
        log.error(str(e))
        ui.error_dialog(str(e))
        ui.app_manager.quit()
        sys.exit()

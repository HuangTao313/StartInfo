from . import ht_lib as lib

# 日志
log = lib.log

# 创建快捷方式
def create_shortcut() -> bool:
    """
    创建快捷方式并移动到启动文件夹
    """
    try:
        # 如果系统是Windows
        if lib.system == 'Windows':
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(lib.SHORTCUT_PATH))
            shortcut.Targetpath = str(lib.EXE_PATH)
            shortcut.Arguments = '--startup'
            shortcut.WorkingDirectory = str(lib.MAIN_PATH)
            shortcut.save()
            log.info(f'快捷方式已创建并移动到启动文件夹: {lib.SHORTCUT_PATH}')
            return True

        #codex神力
        # 66 我这玩意登录不了 收不到手机验证码（ 我一直用的ds（
        # 如果系统是MacOS（暂时不会整Linux 所以直接else了
        # 启动项要带 --startup 参数启动 为了区分开机自启和手动启动 这样开机次数组件才能正常计数 emmm 启动时检测有没有带有这个参数 有就+1
        # 每天自动重置为1
        # 我想记录的是开机的次数（ 不是打开这个软件的次数） 手动开就不要+1
        # 只有5分钟了）（
        # 可以的
        else:
            pass


    except Exception as e:
        log.error(f'创建快捷方式失败: {str(e)}')
        return False


# 检查开机启动项是否存在
def is_shortcut_exist() -> bool:
    """
    检测指定的 .exe 文件是否已经添加到开机启动项
    :return: 如果存在返回 True，否则返回 False
    """
    # 如果系统是MacOS
    if lib.system == 'Windows':
        if lib.WIN_STARTUP_PATH.exists():
            # 检查快捷方式的目标路径是否与指定的目标路径一致
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(lib.SHORTCUT_PATH))
            if shortcut.Targetpath == str(lib.EXE_PATH):
                log.info(f'快捷方式已存在，且目标路径正确: {lib.SHORTCUT_PATH}')
                return True

            else:
                log.info(f'快捷方式已存在，但目标路径不匹配: {lib.SHORTCUT_PATH}')
                return False

        else:
            log.info(f'快捷方式不存在: {lib.SHORTCUT_PATH}')
            return False

    # 如果系统是MacOS
    else:
        # 暂时留空
        pass
    #话说我们不用写Linux的判断吧

# 删除开机启动项
def remove_shortcut() -> bool:
    """
    删除开机启动项中的快捷方式
    """
    try:
        # 如果系统是MacOS
        if lib.system == 'Windows':
            if lib.SHORTCUT_PATH.exists():
                lib.SHORTCUT_PATH.unlink(missing_ok = True)
                log.info(f'快捷方式已删除: {lib.SHORTCUT_PATH}')

            else:
                log.info(f'快捷方式不存在: {lib.SHORTCUT_PATH}')
            return True

        # 如果系统是MacOS
        else:
            # 暂时留空
            pass

    except Exception as e:
        log.error(f'删除快捷方式时出错: {e}')
        return False
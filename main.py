import argparse
import os
import sys
import threading
import queue
import tkinter as tk
from pathlib import Path
import ctypes

from data_manager import DataManager
from counter import KeyCounter
from listener import InputListener
from tray_app import TrayApp
from settings_window import SettingsWindow
from stats_window import StatsWindow

def get_app_dir():
    """返回应用数据目录，打包后与 exe 同级，开发时与 main.py 同级"""
    if getattr(sys, 'frozen', False):
        # 打包后，使用 exe 所在目录
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent

BASE_DIR = get_app_dir()
DATA_DIR = BASE_DIR / 'data'

def get_default_icon():
    """返回默认图标路径，支持 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        return str(Path(sys._MEIPASS) / 'icon.ico')
    return str(BASE_DIR / 'icon.ico')

# ---------- DPI 感知设置（解决 4K 模糊） ----------
def set_dpi_aware():
    if os.name != 'nt':
        return
    try:
        # 使用 PerMonitorV2 最高级 DPI 感知
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

# ---------- 注册表自启动管理 ----------
def is_frozen():
    return getattr(sys, 'frozen', False)

def get_exe_path():
    if is_frozen():
        return sys.executable
    return sys.argv[0]

def add_to_startup():
    if os.name != 'nt':
        return
    import winreg
    key = winreg.HKEY_CURRENT_USER
    subkey = r'Software\Microsoft\Windows\CurrentVersion\Run'
    try:
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as regkey:
            winreg.SetValueEx(regkey, 'KeyMouseCounter', 0, winreg.REG_SZ, get_exe_path())
    except Exception as e:
        print(f"添加开机启动失败: {e}")

def remove_from_startup():
    if os.name != 'nt':
        return
    import winreg
    key = winreg.HKEY_CURRENT_USER
    subkey = r'Software\Microsoft\Windows\CurrentVersion\Run'
    try:
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as regkey:
            winreg.DeleteValue(regkey, 'KeyMouseCounter')
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"移除开机启动失败: {e}")

def is_startup_enabled():
    if os.name != 'nt':
        return False
    import winreg
    key = winreg.HKEY_CURRENT_USER
    subkey = r'Software\Microsoft\Windows\CurrentVersion\Run'
    try:
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_READ) as regkey:
            value, _ = winreg.QueryValueEx(regkey, 'KeyMouseCounter')
            return value == get_exe_path()
    except (FileNotFoundError, OSError):
        return False

def set_startup_callback(enable):
    if enable:
        add_to_startup()
    else:
        remove_from_startup()

# ---------- 主函数 ----------
def main():
    parser = argparse.ArgumentParser(description="键盘鼠标按键计数器")
    parser.add_argument("--console", action="store_true", help="启用调试日志")
    parser.add_argument("--icon", type=str, default=None, help="托盘图标路径")
    parser.add_argument("--auto-start", action="store_true", help="设置开机自启动并退出")
    args = parser.parse_args()

    if args.auto_start:
        add_to_startup()
        print("已设置开机自启动")
        return

    # 设置 DPI 感知，必须在创建任何窗口之前
    set_dpi_aware()

    icon_path = args.icon if args.icon else get_default_icon()
    if not os.path.isfile(icon_path):
        icon_path = None

    data_manager = DataManager(str(DATA_DIR))
    counter = KeyCounter(data_manager)
    listener = InputListener(counter, debug=args.console)
    listener.start()

    stop_event = threading.Event()
    command_queue = queue.Queue()

    def auto_save_loop():
        while not stop_event.is_set():
            stop_event.wait(30)
            if stop_event.is_set():
                break
            try:
                counter.check_date_change()
                data = counter.get_save_data()
                data_manager.save_all(data['today'], data['total'])
                settings = data_manager.load_settings()
                data_manager.cleanup_old_data(settings.get('retention_days', 0))
            except Exception as e:
                print(f"自动保存出错: {e}")

    save_thread = threading.Thread(target=auto_save_loop, daemon=True)
    save_thread.start()

    def on_exit():
        print("正在退出，保存最终数据...")
        stop_event.set()
        listener.stop()
        try:
            counter.check_date_change()
            data = counter.get_save_data()
            data_manager.save_all(data['today'], data['total'])
        except Exception as e:
            print(f"退出保存出错: {e}")
        root.quit()

    # 托盘线程
    def tray_thread():
        tray = TrayApp(command_queue, icon_path)
        tray.run()

    threading.Thread(target=tray_thread, daemon=True).start()

    # 主线程 Tkinter 根窗口（隐藏，用于处理消息循环）
    root = tk.Tk()
    root.withdraw()

    # 设置根窗口图标（影响子窗口任务栏图标）
    if icon_path:
        try:
            img = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, img)
        except:
            pass

    settings_win = None
    stats_win = None

    def save_latest_data():
        counter.check_date_change()
        data = counter.get_save_data()
        data_manager.save_all(data['today'], data['total'])

    def process_queue():
        nonlocal settings_win, stats_win
        try:
            while True:
                cmd = command_queue.get_nowait()
                if cmd == 'settings':
                    if settings_win is None or not settings_win.win.winfo_exists():
                        settings_win = SettingsWindow(
                            root, data_manager, on_settings_close,
                            is_startup_enabled, set_startup_callback,
                            icon_path
                        )
                elif cmd == 'stats':
                    # 打开窗口前先保存一次（保持原有逻辑）
                    try:
                        save_latest_data()
                    except Exception as e:
                        print(f"统计前保存出错: {e}")
                    try:
                        if stats_win is None or not stats_win.win.winfo_exists():
                            stats_win = StatsWindow(
                                root, data_manager,
                                data_manager.load_settings(),
                                data_manager.get_available_dates,
                                on_stats_close,
                                icon_path,
                                save_callback=save_latest_data      # 传入刷新回调
                            )
                    except Exception as e:
                        print(f"打开统计界面出错: {e}")
                elif cmd == 'exit':
                    on_exit()
                    return
        except queue.Empty:
            pass
        root.after(200, process_queue)

    def on_settings_close():
        nonlocal settings_win
        settings_win = None

    def on_stats_close():
        nonlocal stats_win
        stats_win = None

    root.after(200, process_queue)
    root.mainloop()


if __name__ == '__main__':
    main()
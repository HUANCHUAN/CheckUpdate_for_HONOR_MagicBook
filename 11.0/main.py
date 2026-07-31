import sys, os, json
import ctypes
from ctypes import wintypes
import certifi
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from datetime import datetime

import main_normal
import main_transparency

# 设置TLS证书路径，解决打包后的TLS错误
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

plugin_path = os.path.join(os.path.dirname(sys.argv[0]), "PySide6", "plugins", "platforms")
if os.path.exists(plugin_path):
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

def resource_path(relative_path: str) -> str:
    """获取资源文件的绝对路径（兼容PyInstaller打包后）"""
    if hasattr(sys, "_MEIPASS"):  # PyInstaller 打包后的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def init_config():
    """初始化配置文件，如果不存在则创建默认配置"""
    config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'HonorUpdateChecker')
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "config.json")

    if not os.path.exists(config_path):
        default_config = {
            "preferred_mode": "glass",
            "last_updated": datetime.now().isoformat()
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)

    return config_path

def main():
    # 确保配置文件存在
    config_path = init_config()

    # 默认模式
    preferred_mode = "glass"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            preferred_mode = json.load(f).get("preferred_mode", "glass")
    except Exception:
        pass

    # 启动应用
    app = QApplication(sys.argv)
    app.setFont(QFont("HONOR Sans CN", 10))

    # 设置应用标识，帮助第三方任务栏识别应用
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HonorUpdateChecker")
    except Exception:
        pass

    # 设置应用图标（Qt级别，影响原生任务栏）
    icon_path_png = resource_path("resources/icon.png")
    if os.path.exists(icon_path_png):
        app.setWindowIcon(QIcon(icon_path_png))

    if preferred_mode == "glass":
        window = main_transparency.GlassWindow()
    else:
        window = main_normal.MainWindow()

    window.show()

    def set_window_class_icon():
        try:
            user32 = ctypes.windll.user32

            user32.LoadImageW.argtypes = [
                wintypes.HINSTANCE,
                wintypes.LPCWSTR,
                wintypes.UINT,
                wintypes.INT,
                wintypes.INT,
                wintypes.UINT
            ]
            user32.LoadImageW.restype = wintypes.HANDLE

            user32.SendMessageW.argtypes = [
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM
            ]
            user32.SendMessageW.restype = wintypes.LPARAM

            user32.SetClassLongPtrW.argtypes = [
                wintypes.HWND,
                ctypes.c_int,
                wintypes.LONG_PTR
            ]
            user32.SetClassLongPtrW.restype = wintypes.LONG_PTR

            hwnd = int(window.winId())
            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1
            IMAGE_ICON = 1
            LR_LOADFROMFILE = 0x00000010
            GCLP_HICON = -14
            GCLP_HICONSM = -34

            icon_path_ico = resource_path("resources/icon.ico")
            if os.path.exists(icon_path_ico):
                hicon_big = user32.LoadImageW(
                    0, icon_path_ico, IMAGE_ICON, 256, 256, LR_LOADFROMFILE
                )
                hicon_small = user32.LoadImageW(
                    0, icon_path_ico, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
                )

                if hicon_big:
                    user32.SetClassLongPtrW(hwnd, GCLP_HICON, hicon_big)
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                if hicon_small:
                    user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, hicon_small)
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)

                if hicon_big or hicon_small:
                    user32.UpdateWindow(hwnd)
        except Exception as e:
            pass

    from PySide6.QtCore import QTimer
    QTimer.singleShot(100, set_window_class_icon)
    QTimer.singleShot(500, set_window_class_icon)
    QTimer.singleShot(1000, set_window_class_icon)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
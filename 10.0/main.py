# HUANCHUAN with Copilot by Trae  版本号：10.0.0

import sys, os, json
import certifi
from PySide6 import QtCore
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
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
    config_path = os.path.join(os.path.dirname(sys.argv[0]), "config.json")

    if not os.path.exists(config_path):
        default_config = {
            "preferred_mode": "normal",   # 默认启动普通模式
            "last_updated": datetime.now().isoformat()
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)

    return config_path

def main():
    # 确保配置文件存在
    config_path = init_config()

    # 默认模式
    preferred_mode = "normal"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            preferred_mode = json.load(f).get("preferred_mode", "normal")
    except Exception:
        pass

    # 启动应用
    app = QApplication(sys.argv)
    app.setFont(QFont("HONOR Sans CN", 10))

    if preferred_mode == "glass":
        window = main_transparency.GlassWindow()
    else:
        window = main_normal.MainWindow()

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":

    main()

# HUANCHUAN with Copilot by Trae  版本号：11.0.0.22
import json
import subprocess
import sys
import os
import re
import xml.etree.ElementTree as ET
import winreg
import requests
import threading
import time
from typing import Tuple, Optional, List
from datetime import datetime
import ctypes
from ctypes import wintypes
import certifi

# 设置TLS证书路径，解决打包后的TLS错误
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from bs4 import BeautifulSoup
from PySide6.QtCore import (
    Qt, QObject, Signal, QRect,
    QPropertyAnimation, QUrl, QPoint, QTimer, QEasingCurve
)
from PySide6.QtGui import (
    QFont, QIcon, QColor, QPixmap, QDesktopServices
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QDialog,
    QScrollArea, QProgressBar, QMessageBox, QToolButton,
    QGraphicsDropShadowEffect, QStyle, QLineEdit, QMenu, QSizePolicy
)
from BlurWindow.blurWindow import GlobalBlur

from update_checker import check_for_update, UpdateAvailableDialog

# ===== 常量定义 =====
APP_NAME = "荣耀软件更新检查器"
APP_VERSION = "11.0.0.22"
COPYRIGHT_YEAR = f"2025-{datetime.now().year}"

# 应用名称映射
service_names = {
    "pc_manager": "荣耀电脑管家",
    "honor_workstation": "荣耀超级工作台",
    "yoyo_assistant": "荣耀 YOYO 助理",
    "yoyo_claw": "荣耀 YOYO Claw",
    "magic_animation": "荣耀 Magic 视界"
}

# 服务安装路径和版本获取方式
installed_versions_config = {
    "pc_manager": {
        "type": "xml",
        "path": r"C:\\Program Files\\HONOR\\PCManager\\config\\product_adapter_version.xml"
    },
    "honor_workstation": {
        "type": "registry",
        "path": r"SOFTWARE\\HONOR\\Hihonornote",
        "value_name": "HonorWorkStationVersion"
    },
    "yoyo_assistant": {
        "type": "xml",
        "path": r"C:\\Program Files\\HONOR\\HNMagicAI\\config\\product_adapter_version.xml"
    },
    "yoyo_claw": {
        "type": "registry",
        "path": r"SOFTWARE\\HONOR\\MagicClaw",
        "value_name": "MagicClawVersion"
    },
    "magic_animation": {
        "type": "registry",
        "path": r"SOFTWARE\\HONOR\\MagicAnimation",
        "value_name": "MagicAnimationVersion"
    }
}

# 官网页面配置
website_config = {
    "pc_manager": {
        "url": "https://www.honor.com/cn/tech/pc-manager/",
        "selector": ("p", "path")
    },
    "honor_workstation": {
        "url": "https://www.honor.com/cn/tech/honor-workstation/",
        "selector": ("div", "btn-text")
    },
    "yoyo_assistant": {
        "url": "https://www.honor.com/cn/tech/pc-yoyo-assistant-2/",
        "selector": ("p", "path")
    },
    "yoyo_claw": {
        "url": "https://www.honor.com/cn/tech/yoyo-claw/",
        "selector": ("div", "version-tag")
    },
    "magic_animation": {
        "url": "https://www.honor.com/cn/tech/magic-vision/",
        "selector": ("div", "version-info")
    }
}

# ===== 工具函数 =====
def get_local_version(xml_path: str) -> Optional[str]:
    """从XML文件中获取本地版本号"""
    if os.path.exists(xml_path):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            version_elem = root.find(".//version")
            if version_elem is not None:
                return version_elem.text.strip()
        except Exception as e:
            return f"读取版本失败: {e}"
    return None

def get_registry_version(path: str, value_name: str) -> Optional[str]:
    """从Windows注册表中获取版本号"""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        value, _ = winreg.QueryValueEx(key, value_name)
        winreg.CloseKey(key)
        return value.strip()
    except Exception:
        return None

def parse_sp_version(sp_str: str) -> int:
    """解析SP补丁版本号，返回整数（如SP6返回6）"""
    if not sp_str:
        return 0
    match = re.search(r'SP(\d+)', sp_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0

def clean_version(v: str, remove_patch: bool = True) -> str:
    """清理版本字符串，移除多余信息"""
    v = v.replace("Version", "").replace("版本", "").strip()
    v = v.replace("：", "").replace(":", "").strip()
    if remove_patch:
        v = re.sub(r"\(.*?\)", "", v).strip()
    return v

def parse_version(v: str) -> Tuple[Tuple[int, ...], int]:
    """解析版本字符串，返回(主版本元组, SP补丁版本号)"""
    v = v.replace("Version", "").replace("版本", "").strip()
    v = v.replace(" (", "(").strip()
    v = re.sub(r"\(SP(\d+)[^)]*\)", r"(SP\1)", v)
    
    main_part = re.sub(r"\(.*?\)", "", v).strip()
    sp_part = re.search(r"\((.*?)\)", v)
    
    main_tuple = ()
    try:
        main_tuple = tuple(int(x) for x in main_part.split(".") if x.isdigit())
    except ValueError:
        main_tuple = (0,)
    
    sp_version = parse_sp_version(sp_part.group(1) if sp_part else "")
    return main_tuple, sp_version

def format_version_display(version_text: str) -> str:
    """将版本号格式化为前端展示形式：XX.X.X.XX (SPX)
    
    移除 HONOR、C233 等多余字样，仅保留主版本号与 SP 补丁号，
    不影响后端检查逻辑。
    """
    if not version_text or not isinstance(version_text, str):
        return "未知"
    
    text = version_text.strip()
    
    # 提取四段式主版本号，如 18.0.0.1
    main_match = re.search(r'\b\d+\.\d+\.\d+\.\d+\b', text)
    if not main_match:
        # 退而求其次，匹配任意数字分段版本号
        main_match = re.search(r'\b\d+(?:\.\d+)+\b', text)
        if not main_match:
            return text
    
    main_version = main_match.group(0)
    
    # 提取 SP 补丁版本（兼容括号内前缀，如 C233SP2）
    # 仅当括号内明确包含 SP 标识时才显示补丁号，避免将 C233 等版本编号误判为 SP 补丁号
    sp_match = re.search(r'\([^)]*SP\s*(\d+)[^)]*\)', text, re.IGNORECASE)
    if sp_match:
        return f"{main_version} (SP{sp_match.group(1)})"

    return main_version

def get_network_error_message(error: Exception) -> str:
    """将网络请求异常转换为中文提示信息，避免向前端展示英文错误"""
    if isinstance(error, requests.exceptions.Timeout):
        return "检查失败: 请求超时，请检查网络连接"
    if isinstance(error, requests.exceptions.ConnectionError):
        return "检查失败: 网络连接错误，请检查网络是否正常"
    if isinstance(error, requests.exceptions.HTTPError):
        status_code = error.response.status_code if error.response is not None else "?"
        return f"检查失败: 服务器错误({status_code})"
    return f"检查失败: {str(error)[:30]}..."

def resource_path(relative_path: str) -> str:
    """获取资源文件的绝对路径（兼容PyInstaller打包后）"""
    if hasattr(sys, "_MEIPASS"):  # PyInstaller 打包后的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_config_path():
    """获取配置文件的绝对路径（使用APPDATA目录，用户有写入权限）"""
    config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'HonorUpdateChecker')
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.json")

# ===== 主题管理器 =====
class ThemeManager:
    """主题管理器 - 负责检测和应用系统主题"""
    
    def __init__(self):
        self.is_dark_mode = self._check_system_theme()
    
    def _check_system_theme(self) -> bool:
        """检查系统是否使用深色主题"""
        try:
            # 检查Windows注册表
            if sys.platform == 'win32':
                # Windows 10/11 的深色模式设置
                key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize'
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
                value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
                winreg.CloseKey(key)
                # 返回 False 表示深色模式，因为值为0时是深色模式
                return value == 0
        except Exception:
            pass
        # 默认返回浅色模式
        return False
    
    def get_style_sheet(self) -> str:
        """获取当前主题的样式表"""
        if self.is_dark_mode:
            return self._get_dark_style_sheet()
        else:
            return self._get_light_style_sheet()
    
    def _get_dark_style_sheet(self) -> str:
        """获取深色主题样式表"""
        return """
            /* 主窗口样式 */
            QWidget {
                background-color: #1e1e1e;
                color: #f3f3f3;
            }
            
            /* 卡片样式 */
            QFrame {
                background-color: #2d2d2d;
                border-radius: 12px;
            }
            
            /* 按钮样式 */
            QPushButton {
                background-color: #3773e8;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4285f4;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #aaa;
            }
            
            /* 标签样式 */
            QLabel {
                color: #f3f3f3;
            }
            
            /* 进度条样式 */
            QProgressBar {
                background-color: #3d3d3d;
                border-radius: 10px;
                text-align: center;
                color: #f3f3f3;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                          stop:0 rgba(55, 115, 232, 0.8), stop:1 rgba(66, 133, 244, 0.8));
                border-radius: 10px;
            }
        """
    
    def _get_light_style_sheet(self) -> str:
        """获取浅色主题样式表"""
        return """
            /* 主窗口样式 */
            QWidget {
                background-color: #f8f9fa;
                color: #212529;
            }
            
            /* 卡片样式 */
            QFrame {
                background-color: #ffffff;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            }
            
            /* 按钮样式 */
            QPushButton {
                background-color: #3773e8;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4285f4;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
            
            /* 标签样式 */
            QLabel {
                color: #212529;
            }
            
            /* 进度条样式 */
            QProgressBar {
                background-color: #e9ecef;
                border-radius: 10px;
                text-align: center;
                color: #212529;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                          stop:0 rgba(55, 115, 232, 0.8), stop:1 rgba(66, 133, 244, 0.8));
                border-radius: 10px;
            }
        """

# ===== 工作线程通信对象 =====
class WorkerBridge(QObject):
    """用于工作线程与UI线程通信的桥梁"""
    update_progress = Signal(int, str)
    update_result = Signal(str, dict)
    check_complete = Signal()
    show_message = Signal(str, str, int)
    show_self_update = Signal(dict)

# ===== 可复制标签（中文右键菜单）=====
class CopyableLabel(QLabel):
    """可复制标签，提供中文右键菜单"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)

    def contextMenuEvent(self, event):
        selected = self.selectedText()
        # 未选择内容时不弹出右键菜单
        if not selected:
            return

        menu = QMenu(self)
        copy_action = menu.addAction("复制")
        select_all_action = menu.addAction("全选")

        action = menu.exec(event.globalPos())
        if action == copy_action:
            QApplication.clipboard().setText(selected)
        elif action == select_all_action:
            self.setSelection(0, len(self.text()))

# ===== 自定义进度条（通透模式，带平滑动画）=====
class GlassProgressBar(QProgressBar):
    """通透模式进度条，带平滑动画"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setTextVisible(True)

        # 平滑动画
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(400)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        # 通透模式专用样式
        self.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                text-align: center;
                color: white;
                font-size: 12px;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                          stop:0 rgba(55, 115, 232, 0.8), stop:1 rgba(66, 133, 244, 0.8));
                border-radius: 10px;
            }
        """)

    def set_value_animated(self, value):
        """以动画方式设置进度值"""
        self.animation.stop()
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(value)
        self.animation.start()

# ===== 自定义卡片组件 =====
class SoftwareCard(QFrame):
    """软件信息卡片组件 - 通透模式专用样式"""
    def __init__(self, software_key: str, name: str, icon_path: str, parent=None):
        super().__init__(parent)
        self.software_key = software_key
        self.name = name
        self.icon_path = icon_path

        # 保留原始版本号，供调试模式使用（前端展示会另行格式化）
        self.raw_local_version = ""
        self.raw_online_version = ""

        # 紧凑模式标志（True=新版紧凑，False=原版大卡片）
        self.is_compact = True

        # 设置卡片样式 - 通透模式专用
        self.setObjectName("SoftwareCard")
        self.setStyleSheet("QFrame#SoftwareCard { margin: 8px; }")

        # 设置尺寸策略为水平扩展，确保双列布局中卡片始终填满列宽，
        # 避免逐个加载卡片时因可见卡片数量变化导致的位置抖动
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 15))
        self.setGraphicsEffect(shadow)

        # 初始化动画
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(500)

        # 默认设置为半透明，等待数据加载后显示
        self.setWindowOpacity(0.7)

        # 创建布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(6)

        # 创建顶部信息区
        self._create_header_section()

        # 创建版本信息区
        self._create_version_section()

        # 创建状态区
        self._create_status_section()

        # 初始设置卡片样式 - 必须在创建所有标签后调用
        self.update_card_theme()

    def set_compact_mode(self, is_compact: bool):
        """设置卡片紧凑模式（紧凑=新版小卡片，经典=原版大卡片）"""
        self.is_compact = is_compact
        # 调整图标大小
        if is_compact:
            self.icon_label.setFixedSize(40, 40)
            name_font = QFont("HONOR Sans CN", 13, QFont.Bold)
        else:
            self.icon_label.setFixedSize(64, 64)
            name_font = QFont("HONOR Sans CN", 16, QFont.Bold)
        self.icon_label.setScaledContents(True)
        name_font.setStyleStrategy(QFont.PreferAntialias)
        self.name_label.setFont(name_font)
        # 重新加载图标（setFixedSize 后需重设 pixmap）
        if self.icon_path and os.path.exists(self.icon_path):
            self.icon_label.setPixmap(QPixmap(self.icon_path))
        # 重新应用主题（更新 padding 和字号）
        self.update_card_theme()
        # 重新应用状态样式
        if hasattr(self, 'status_type'):
            local_version = getattr(self, 'raw_local_version', '')
            online_version = getattr(self, 'raw_online_version', '')
            status = self.status_label.text()
            status_type = self.status_type
            download_url = getattr(self, 'download_url', '')
            self.update_info(local_version, online_version, status, status_type, download_url)

    def _create_header_section(self):
        """创建卡片顶部信息区"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # 软件图标
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(40, 40)
        self.icon_label.setScaledContents(True)

        # 尝试加载图标 - 确保路径正确处理
        icon_path = self.icon_path
        if icon_path and os.path.exists(icon_path):
            self.icon_label.setPixmap(QPixmap(icon_path))

        # 软件名称
        self.name_label = QLabel(self.name)
        name_font = QFont("HONOR Sans CN", 13, QFont.Bold)
        name_font.setStyleStrategy(QFont.PreferAntialias)
        self.name_label.setFont(name_font)
        self.name_label.setStyleSheet("color: white;")

        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()

        self.main_layout.addLayout(header_layout)
    
    def _create_version_section(self):
        """创建版本信息区"""
        version_layout = QGridLayout()
        version_layout.setSpacing(4)
        version_layout.setColumnStretch(1, 1)
        # 整体向右偏移
        version_layout.setContentsMargins(2, 0, 0, 0)

        # 本地版本
        self.local_version_label = QLabel("本地版本:")
        self.local_version_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 11px;")

        self.local_version_value = CopyableLabel("加载中...")
        self.local_version_value.setStyleSheet("color: white; font-size: 11px;")

        # 官网版本
        self.online_version_label = QLabel("官网版本:")
        self.online_version_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 11px;")

        self.online_version_value = CopyableLabel("加载中...")
        self.online_version_value.setStyleSheet("color: white; font-size: 11px;")

        # 添加到布局
        version_layout.addWidget(self.local_version_label, 0, 0)
        version_layout.addWidget(self.local_version_value, 0, 1)
        version_layout.addWidget(self.online_version_label, 1, 0)
        version_layout.addWidget(self.online_version_value, 1, 1)

        self.main_layout.addLayout(version_layout)
    
    def _create_status_section(self):
        """创建状态显示区"""
        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)

        # 状态标签
        self.status_label = QLabel("正在检查...")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumWidth(80)

        # 更新链接按钮
        self.download_button = QPushButton("更新链接")
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(55, 115, 232, 0.8);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 3px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(66, 133, 244, 1);
            }
            QPushButton:disabled {
                background-color: rgba(173, 181, 189, 0.5);
                color: rgba(255, 255, 255, 0.6);
            }
        """)
        self.download_button.setVisible(False)

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.download_button)

        self.main_layout.addLayout(status_layout)
    
    def update_card_theme(self):
        """更新卡片样式 - 通透模式专用"""
        # 根据紧凑模式决定 padding 和字号
        if self.is_compact:
            padding_value = "18px"
            label_font_size = "11px"
        else:
            # 单列模式：上下 18px，左右 20px
            padding_value = "18px 20px"
            label_font_size = "13px"

        # 通透模式专用样式
        card_style = f"""
            QFrame#SoftwareCard {{
                background-color: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 17px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                padding: {padding_value};
            }}
            QFrame#SoftwareCard:disabled {{
                opacity: 0.7;
            }}
        """

        # 更新卡片样式
        self.setStyleSheet(card_style)

        # 更新文本颜色
        text_color = "white"
        info_color = "rgba(255, 255, 255, 0.8)"

        # 更新名称标签颜色
        self.name_label.setStyleSheet(f"color: {text_color}; background-color: transparent;")

        # 更新版本标签颜色
        for label in [self.local_version_value, self.online_version_value]:
            label.setStyleSheet(f"color: {text_color}; background-color: transparent; font-size: {label_font_size};")

        # 更新版本区"本地:""官网:"标签字号
        for label in [self.local_version_label, self.online_version_label]:
            label.setStyleSheet(f"color: {info_color}; font-size: {label_font_size};")
    
    def fade_in(self):
        """淡入动画"""
        self.fade_animation.setStartValue(self.windowOpacity())
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
    
    def update_info(self, local_version: str, online_version: str, status: str,
                   status_type: str, download_url: str = ""):
        """更新卡片信息"""
        # 保留原始版本号，供调试模式使用
        self.raw_local_version = local_version or ""
        self.raw_online_version = online_version or ""

        # 更新版本信息（前端展示使用格式化后的简洁版本）
        self.local_version_value.setText(format_version_display(local_version))
        self.online_version_value.setText(format_version_display(online_version))

        # 更新状态标签
        self.status_label.setText(status)

        # 保存状态类型和下载链接，用于主题/布局变化时重新应用样式
        self.status_type = status_type
        self.download_url = download_url

        # 根据紧凑模式决定状态标签样式参数
        if self.is_compact:
            status_padding = "3px 8px"
            status_radius = "12px"
            status_font_size = "11px"
            button_padding = "3px 8px"
            button_radius = "12px"
            button_font_size = "11px"
        else:
            status_padding = "4px 12px"
            status_radius = "16px"
            status_font_size = "12px"
            button_padding = "4px 12px"
            button_radius = "16px"
            button_font_size = "12px"

        # 根据状态类型设置样式 - 通透模式专用
        if status_type == "up_to_date":
            self.status_label.setStyleSheet(f"""
                QLabel#StatusLabel {{
                    background-color: rgba(45, 62, 54, 0.8);
                    color: rgba(146, 208, 80, 1);
                    padding: {status_padding};
                    border-radius: {status_radius};
                    font-size: {status_font_size};
                    font-weight: 500;
                }}
            """)
            self.download_button.setVisible(False)
        elif status_type == "update_available":
            self.status_label.setStyleSheet(f"""
                QLabel#StatusLabel {{
                    background-color: rgba(62, 54, 45, 0.8);
                    color: rgba(255, 193, 7, 1);
                    padding: {status_padding};
                    border-radius: {status_radius};
                    font-size: {status_font_size};
                    font-weight: 500;
                }}
            """)
            if download_url:
                self.download_button.setVisible(True)
                self.download_button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(55, 115, 232, 0.8);
                        color: white;
                        border: none;
                        border-radius: {button_radius};
                        padding: {button_padding};
                        font-size: {button_font_size};
                    }}
                    QPushButton:hover {{
                        background-color: rgba(66, 133, 244, 1);
                    }}
                """)
                self.download_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(download_url)))
        elif status_type == "error":
            self.status_label.setStyleSheet(f"""
                QLabel#StatusLabel {{
                    background-color: rgba(62, 45, 45, 0.8);
                    color: rgba(255, 107, 107, 1);
                    padding: {status_padding};
                    border-radius: {status_radius};
                    font-size: {status_font_size};
                    font-weight: 500;
                }}
            """)
            self.download_button.setVisible(False)
        elif status_type == "higher_version":
            self.status_label.setStyleSheet(f"""
                QLabel#StatusLabel {{
                    background-color: rgba(45, 54, 62, 0.8);
                    color: rgba(119, 191, 249, 1);
                    padding: {status_padding};
                    border-radius: {status_radius};
                    font-size: {status_font_size};
                    font-weight: 500;
                }}
            """)
            if download_url:
                self.download_button.setVisible(True)
                self.download_button.setText("官网链接")
                self.download_button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(55, 115, 232, 0.8);
                        color: white;
                        border: none;
                        border-radius: {button_radius};
                        padding: {button_padding};
                        font-size: {button_font_size};
                    }}
                    QPushButton:hover {{
                        background-color: rgba(66, 133, 244, 1);
                    }}
                """)
                self.download_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(download_url)))

        # 显示完整内容的动画
        self.fade_in()

# ===== 关于对话框 =====
class AboutDialog(QDialog):
    """关于对话框 - 支持深色/浅色主题"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于荣耀软件更新检查器")
        self.setModal(True)
        self.setFixedSize(340, 290)
        self.parent_window = parent
        # 初始化点击计数器
        self.click_count = 0
        
        # 初始化主题管理器引用
        self.theme_manager = None
        if parent and hasattr(parent, 'theme_manager'):
            self.theme_manager = parent.theme_manager
        
        self.init_ui()
    
    def init_ui(self):
        # 创建布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 15, 20, 15)
        self.main_layout.setSpacing(8)
        
        # 应用图标
        self.icon_label = QLabel()
        icon_path = resource_path("resources/icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            self.icon_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        # 标题
        self.title_label = QLabel(APP_NAME)
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # 版本号 - 添加点击事件
        self.version_label = QLabel(f"版本 {APP_VERSION}")
        self.version_label.setObjectName("VersionLabel")
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.mousePressEvent = self.on_version_clicked
        self.version_label.setCursor(Qt.PointingHandCursor)
        
        # 版权信息
        self.copyright_label = QLabel(f"Copyright © {COPYRIGHT_YEAR} HUANCHUAN")
        self.copyright_label.setAlignment(Qt.AlignCenter)
        
        # 反馈信息
        self.feedback_label = QLabel("反馈/建议：请使用 QQ 联系 HUANCHUAN")
        self.feedback_label.setAlignment(Qt.AlignCenter)

        # 检查更新按钮
        self.check_update_button = QPushButton("检查更新")
        self.check_update_button.setCursor(Qt.PointingHandCursor)
        self.check_update_button.setFixedHeight(32)
        self.check_update_button.clicked.connect(self.on_check_update_clicked)

        # 添加到布局
        self.main_layout.addWidget(self.icon_label)
        self.main_layout.addWidget(self.title_label)
        self.main_layout.addWidget(self.version_label)
        self.main_layout.addWidget(self.check_update_button)
        self.main_layout.addWidget(self.copyright_label)
        self.main_layout.addWidget(self.feedback_label)
    
    def set_windows_title_bar_color(self, hex_color):
        """设置Windows窗口标题栏颜色和文字颜色"""
        try:
            # 转换十六进制颜色到RGB
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # 定义Windows API
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            HWND = self.winId()
            dwmapi = ctypes.WinDLL('dwmapi')
            
            # 设置标题栏背景颜色
            color_value = wintypes.DWORD((b << 16) | (g << 8) | r)
            dwmapi.DwmSetWindowAttribute(
                HWND, 
                DWMWA_CAPTION_COLOR, 
                ctypes.byref(color_value), 
                ctypes.sizeof(color_value)
            )
            
            # 判断是否为深色背景，如果是则设置文字为白色
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if brightness < 128:
                text_color = wintypes.DWORD(0xFFFFFF)  # 白色
                dwmapi.DwmSetWindowAttribute(
                    HWND, 
                    DWMWA_TEXT_COLOR, 
                    ctypes.byref(text_color), 
                    ctypes.sizeof(text_color)
                )
        except Exception as e:
            # 忽略错误，确保程序正常运行
            pass
    
    def showEvent(self, event):
        """显示事件 - 应用主题样式"""
        super().showEvent(event)
        
        # 检查是否有主题管理器并应用深色主题样式
        if self.theme_manager and self.theme_manager.is_dark_mode:
            self.setStyleSheet("""
                QDialog {
                    background-color: #2d2d2d;
                    border-radius: 12px;
                }
                QLabel {
                    color: #f3f3f3;
                    font-size: 13px;
                }
                QLabel#TitleLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #ffffff;
                }
                QLabel#VersionLabel {
                    font-size: 14px;
                    color: #4285f4;
                }
                QPushButton {
                    background-color: #3773e8;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 0 16px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4285f4;
                }
                QPushButton:disabled {
                    background-color: #404040;
                    color: #6c757d;
                }
            """)
            # 设置标题栏颜色为深色主题背景色
            self.set_windows_title_bar_color("#2d2d2d")
        else:
            # 浅色主题样式
            self.setStyleSheet("""
                QDialog {
                    background-color: #f3f3f3;
                    border-radius: 12px;
                }
                QLabel {
                    color: #495057;
                    font-size: 13px;
                }
                QLabel#TitleLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #495057;
                }
                QLabel#VersionLabel {
                    font-size: 14px;
                    color: #4285f4;
                }
                QPushButton {
                    background-color: #3773e8;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 0 16px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4285f4;
                }
                QPushButton:disabled {
                    background-color: #adb5bd;
                    color: #6c757d;
                }
            """)
            # 设置标题栏颜色为浅色主题背景色
            self.set_windows_title_bar_color("#f3f3f3")
    
    def on_version_clicked(self, event):
        """版本号点击事件处理 - 连续点击7次打开版本修改对话框"""
        self.click_count += 1
        
        # 连续点击7次，打开版本修改对话框
        if self.click_count == 7:
            self.click_count = 0  # 重置计数器
            self.open_version_edit_dialog()
        elif self.click_count > 7:
            self.click_count = 0  # 防止无限累加
    
    def open_version_edit_dialog(self):
        """打开版本修改对话框"""
        if hasattr(self.parent_window, 'open_manual_version_dialog'):
            result = self.parent_window.open_manual_version_dialog()
            # 保存成功后关闭关于对话框
            if result == QDialog.Accepted:
                self.accept()

    def on_check_update_clicked(self):
        """检查更新按钮点击事件"""
        if hasattr(self.parent_window, 'manual_check_self_update'):
            # 禁用按钮并显示检查中状态
            self.check_update_button.setEnabled(False)
            self.check_update_button.setText("检查中...")
            # 调用主窗口的检查方法，传入自身引用以便检查完成后关闭
            self.parent_window.manual_check_self_update(self)

# ===== 手动版本修改对话框 =====
class ManualVersionDialog(QDialog):
    """手动版本修改对话框类 - 调试模式，支持深色/浅色主题"""
    
    def __init__(self, parent=None, current_versions=None):
        super().__init__(parent)
        self.setWindowTitle("调试模式 - 手动修改版本号")
        self.setModal(True)
        self.setMinimumSize(360, 330)
        
        # 初始化主题管理器引用
        self.theme_manager = None
        if parent and hasattr(parent, 'theme_manager'):
            self.theme_manager = parent.theme_manager
        
        self.current_versions = current_versions or {}
        self.version_inputs = {}
        
        self.init_ui()
    
    def init_ui(self):
        # 创建布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 20)
        self.main_layout.setSpacing(14)
        
        # 标题
        title_label = QLabel("手动修改应用版本号 (调试模式)")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-weight: bold;")
        self.main_layout.addWidget(title_label)
        
        # 版本输入框
        for app_key, app_name in service_names.items():
            input_layout = QHBoxLayout()
            input_layout.setSpacing(8)
            
            label = QLabel(f"{app_name}:")
            
            # 创建输入框并设置当前版本
            current_version = self.current_versions.get(app_key, "") if self.current_versions else ""
            line_edit = QLineEdit(current_version)
            line_edit.setPlaceholderText("请输入版本号")
            
            self.version_inputs[app_key] = line_edit
            
            input_layout.addWidget(label)
            input_layout.addWidget(line_edit)
            
            self.main_layout.addLayout(input_layout)
        
        # 提示信息
        tip_label = QLabel("注意：修改后需要重新检查更新才能生效")
        tip_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        tip_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(tip_label)
        
        # 底部按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.reset_button = QPushButton("还原本地")
        self.reset_button.setFixedSize(90, 32)
        self.reset_button.clicked.connect(self.reset_to_local_versions)
        
        self.save_button = QPushButton("保存")
        self.save_button.setFixedSize(80, 32)
        self.save_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFixedSize(80, 32)
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.save_button)
        
        self.main_layout.addLayout(buttons_layout)
        
        self.adjustSize()
    
    def get_versions(self):
        """获取用户输入的版本号"""
        return {
            app_key: line_edit.text().strip()
            for app_key, line_edit in self.version_inputs.items()
        }
        
    def reset_to_local_versions(self):
        """还原为本地检测的版本号"""
        if hasattr(self.parent(), 'software_cards'):
            for app_key, line_edit in self.version_inputs.items():
                # 重新检测本地版本号（不使用手动设置的版本）
                local_version = self._get_local_version_directly(app_key)
                line_edit.setText(local_version or "")
            
            # 显示还原成功的提示
            if hasattr(self.parent(), 'show_message'):
                self.parent().show_message(
                    "还原成功",
                    "已成功还原为本地检测的版本号。",
                    QMessageBox.Information
                )
    
    def _get_local_version_directly(self, app_key: str) -> str:
        """直接获取本地版本号（不依赖手动设置）"""
        if app_key in installed_versions_config:
            config = installed_versions_config[app_key]
            try:
                if config["type"] == "xml":
                    return get_local_version(config["path"])
                elif config["type"] == "registry":
                    return get_registry_version(config["path"], config["value_name"])
            except Exception:
                return "检测失败"
        return "配置不存在"
    
    def set_windows_title_bar_color(self, hex_color):
        """设置Windows窗口标题栏颜色和文字颜色"""
        try:
            # 转换十六进制颜色到RGB
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # 定义Windows API
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            HWND = self.winId()
            dwmapi = ctypes.WinDLL('dwmapi')
            
            # 设置标题栏背景颜色
            color_value = wintypes.DWORD((b << 16) | (g << 8) | r)
            dwmapi.DwmSetWindowAttribute(
                HWND, 
                DWMWA_CAPTION_COLOR, 
                ctypes.byref(color_value), 
                ctypes.sizeof(color_value)
            )
            
            # 判断是否为深色背景，如果是则设置文字为白色
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if brightness < 128:
                text_color = wintypes.DWORD(0xFFFFFF)  # 白色
                dwmapi.DwmSetWindowAttribute(
                    HWND, 
                    DWMWA_TEXT_COLOR, 
                    ctypes.byref(text_color), 
                    ctypes.sizeof(text_color)
                )
        except Exception as e:
            # 忽略错误，确保程序正常运行
            pass
    
    def showEvent(self, event):
        """显示事件 - 应用主题样式"""
        super().showEvent(event)
        
        # 检查是否有主题管理器并应用深色主题样式
        if self.theme_manager and self.theme_manager.is_dark_mode:
            self.setStyleSheet("""
                QDialog {
                    background-color: #2d2d2d;
                    border-radius: 12px;
                }
                QLabel {
                    color: #f3f3f3;
                    font-size: 13px;
                }
                QLabel[style*="font-weight: bold"] {
                    color: #ffffff;
                }
                QLabel[style*="color: #6c757d"] {
                    color: #adb5bd;
                }
                QLineEdit {
                    background-color: #3d3d3d;
                    border: 1px solid #4d4d4d;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 13px;
                    color: #f3f3f3;
                }
                QPushButton {
                    background-color: #3773e8;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4285f4;
                }
            """)
            # 设置标题栏颜色为深色主题背景色
            self.set_windows_title_bar_color("#2d2d2d")
        else:
            # 浅色主题样式
            self.setStyleSheet("""
                QDialog {
                    background-color: #f3f3f3;
                    border-radius: 12px;
                }
                QLabel {
                    color: #495057;
                    font-size: 13px;
                }
                QLabel[style*="font-weight: bold"] {
                    color: #212529;
                }
                QLabel[style*="color: #6c757d"] {
                    color: #6c757d;
                }
                QLineEdit {
                    background-color: white;
                    border: 1px solid #ced4da;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 13px;
                    color: #212529;
                }
                QPushButton {
                    background-color: #3773e8;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4285f4;
                }
            """)
            # 设置标题栏颜色为浅色主题背景色
            self.set_windows_title_bar_color("#f3f3f3")

# ===== 通透模式窗口类 =====
class GlassWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # 初始化手动版本号字典
        self.manual_versions = {}
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager()
        
        # 设置窗口标题
        self.setWindowTitle(f"Update Checker for HONOR MagicBook")
        
        # 设置窗口图标
        icon_path = resource_path("resources/icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 完全透明背景 + 系统毛玻璃（保留原有通透模式效果）
        self.setAttribute(Qt.WA_TranslucentBackground)
        GlobalBlur(self.winId(), Dark=False, Acrylic=False, QWidget=self)  # 示例，参数名以你的库为准
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        
        # 设置整体窗口透明度（0.0 ~ 1.0）
        self.setWindowOpacity(0.995)  # 保持原有设置
        
        # 存储状态
        self.running = False
        self.manual_versions = {}

        # 加载卡片布局配置（classic 原版单列 / compact 新版双列）
        self.card_layout_mode = "compact"
        try:
            config_path = get_config_path()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as config_file:
                    config_data = json.load(config_file)
                    self.card_layout_mode = config_data.get('card_layout', 'compact')
        except Exception:
            pass

        # 根据布局模式设置窗口尺寸
        if self.card_layout_mode == "classic":
            self.setMinimumSize(390, 725)
            self.resize(390, 725)
        else:
            self.setMinimumSize(620, 585)
            self.resize(620, 585)
        
        # 窗口居中显示
        screen_geometry = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x_position = (screen_geometry.width() - window_geometry.width()) // 2
        y_position = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x_position, y_position)
        
        # 加载图标路径
        self.icon_files = {
            "pc_manager": resource_path("resources/pc_manager.png"),
            "honor_workstation": resource_path("resources/honor_workstation.png"),
            "yoyo_assistant": resource_path("resources/yoyo_assistant.png"),
            "yoyo_claw": resource_path("resources/yoyo_claw.png"),
            "magic_animation": resource_path("resources/magic_animation.png")
        }
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(16)
        
        # 创建标题区域
        self._create_title()
        
        # 创建进度条区域
        self._create_progress_bar()
        
        # 创建结果显示区域
        self._create_results_area()
        
        # 创建按钮区域
        self._create_buttons()
        
        # 创建线程通信桥
        self.worker_bridge = WorkerBridge()
        self.worker_bridge.update_progress.connect(self.update_progress)
        self.worker_bridge.update_result.connect(self.update_card_result)
        self.worker_bridge.check_complete.connect(self.on_check_complete)
        self.worker_bridge.show_message.connect(self.show_message)
        self.worker_bridge.show_self_update.connect(self.on_self_update_result)

        # 自动开始检查更新
        self.run_check()

        # 启动后延迟 3 秒静默检查应用自身更新（每天最多一次）
        QTimer.singleShot(3000, self.auto_check_self_update)
        
        # 设置窗口标题栏颜色为指定颜色
        # 从窗口左侧1像素从客户区顶部下1像素的位置取色
        self.update_title_bar_color()
        
        # 设置定时器，定期更新标题栏颜色
        self.color_update_timer = QTimer(self)
        self.color_update_timer.timeout.connect(self.update_title_bar_color)
        self.color_update_timer.start(800)  # 800毫秒更新一次（调慢避免拖动卡顿）
        
        # 设置主题检测定时器
        self.theme_timer = QTimer(self)
        self.theme_timer.setInterval(1000)  # 每秒检查一次主题变化
        self.theme_timer.timeout.connect(self.check_system_theme_change)
        self.theme_timer.start()
    
    def update_title_bar_color(self):
        """更新标题栏颜色
        
        此方法会重新获取窗口颜色并应用到标题栏，用于定时更新
        或手动触发颜色更新
        """
        try:
            color = self.get_pixel_color_at_position(1, 1)
            self.set_windows_title_bar_color(color)
        except Exception as e:
            # 更新失败时不影响程序运行
            pass
    
    def _create_title(self):
        """创建标题区域"""
        title_frame = QFrame()
        title_frame.setStyleSheet("background-color: transparent;")
        
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)
        
        # 标题
        title_label = QLabel(APP_NAME)
        title_font = QFont("HONOR Sans CN", 18, QFont.Bold)
        title_font.setStyleStrategy(QFont.PreferAntialias)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white;")
        
        # 切换到普通模式按钮
        self.normal_mode_button = QToolButton()
        self.normal_mode_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.normal_mode_button.setToolTip("关闭通透模式")
        self.normal_mode_button.setFixedSize(32, 32)
        self.normal_mode_button.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 16px;
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.normal_mode_button.clicked.connect(self.switch_to_normal_mode)

        # 卡片布局切换按钮
        self.layout_switch_button = QToolButton()
        self.layout_switch_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogListView))
        self.layout_switch_button.setToolTip("切换卡片布局（）")
        self.layout_switch_button.setFixedSize(32, 32)
        self.layout_switch_button.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 16px;
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.layout_switch_button.clicked.connect(self.toggle_card_layout)
        
        # 关于按钮
        self.about_button = QToolButton()
        self.about_button.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        self.about_button.setToolTip("关于")
        self.about_button.setFixedSize(32, 32)
        self.about_button.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 16px;
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.about_button.clicked.connect(self.open_about)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.layout_switch_button)
        title_layout.addWidget(self.normal_mode_button)
        title_layout.addWidget(self.about_button)
        
        self.main_layout.addWidget(title_frame)
    
    def _create_progress_bar(self):
        """创建进度条区域"""
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("ProgressFrame")
        self.progress_frame.setStyleSheet("""
            QFrame#ProgressFrame {
                background-color: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                padding: 16px;
                margin-top: 0;
            }
        """)
        
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        
        # 进度条标签
        self.progress_label = QLabel("准备检查更新...")
        self.progress_label.setStyleSheet("color: white;")
        
        # 进度条
        self.progress_bar = GlassProgressBar()
        
        # 添加到布局
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        # 默认隐藏进度条区域
        self.progress_frame.setVisible(False)
        
        self.main_layout.addWidget(self.progress_frame)
    
    def _create_results_area(self):
        """创建结果显示区域"""
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # 滚动区域内容
        scroll_content = QWidget()
        self.results_layout = QVBoxLayout(scroll_content)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(8)
        
        # 添加占位符
        self.placeholder_label = QLabel("点击下方按钮开始检查更新")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.6);
            font-size: 14px;
            padding: 40px;
        """)
        self.results_layout.addWidget(self.placeholder_label)

        # 创建软件卡片（对象本身，布局由 rebuild_cards_layout 决定）
        self.software_cards = {}
        for key, name in service_names.items():
            card = SoftwareCard(key, name, self.icon_files.get(key, ""))
            card.setVisible(False)
            self.software_cards[key] = card

        # 根据当前模式创建卡片容器布局
        self.rebuild_cards_layout()

        self.results_layout.addStretch()

        # 设置滚动区域内容
        self.scroll_area.setWidget(scroll_content)

        self.main_layout.addWidget(self.scroll_area, 1)

    def rebuild_cards_layout(self):
        """根据 card_layout_mode 重建卡片容器布局
        compact: 双列网格布局（新版）
        classic: 单列布局（原版）
        """
        # 如果已存在旧容器，记录可见性并移除
        container_visible = False
        if hasattr(self, 'cards_container') and self.cards_container is not None:
            container_visible = self.cards_container.isVisible()
            self.results_layout.removeWidget(self.cards_container)
            self.cards_container.deleteLater()

        # 根据模式切换卡片的紧凑/经典样式
        is_compact = (self.card_layout_mode == "compact")
        for card in self.software_cards.values():
            card.set_compact_mode(is_compact)

        # 创建新容器
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background-color: transparent;")

        if self.card_layout_mode == "classic":
            # 原版单列布局，卡片间距比双列稍大
            self.cards_layout = QVBoxLayout(self.cards_container)
            self.cards_layout.setContentsMargins(0, 0, 0, 0)
            self.cards_layout.setSpacing(10)
            for key in service_names.keys():
                self.cards_layout.addWidget(self.software_cards[key])
        else:
            # 新版双列网格布局
            self.cards_layout = QGridLayout(self.cards_container)
            self.cards_layout.setContentsMargins(4, 4, 4, 4)
            self.cards_layout.setSpacing(8)
            self.cards_layout.setColumnStretch(0, 1)
            self.cards_layout.setColumnStretch(1, 1)
            # 设置两列最小宽度相同，避免卡片逐个显示时因可见卡片数量变化
            # 导致某列最小宽度为0而引发列宽重算和卡片位置抖动
            # 双列布局最小窗口宽度620px，减去边距和间距后每列约302px，取280px为安全下限
            self.cards_layout.setColumnMinimumWidth(0, 280)
            self.cards_layout.setColumnMinimumWidth(1, 280)
            for index, key in enumerate(service_names.keys()):
                row = index // 2
                col = index % 2
                self.cards_layout.addWidget(self.software_cards[key], row, col)

        self.cards_container.setVisible(container_visible)
        # 插入到占位符之后
        insert_index = self.results_layout.indexOf(self.placeholder_label) + 1
        self.results_layout.insertWidget(insert_index, self.cards_container)

    def toggle_card_layout(self):
        """切换卡片布局模式（原版/新版）"""
        if self.card_layout_mode == "compact":
            self.card_layout_mode = "classic"
            tip_text = "已切换为原版单列布局"
            target_min = (390, 725)
            target_size = (390, 725)
        else:
            self.card_layout_mode = "compact"
            tip_text = "已切换为新版双列布局"
            target_min = (620, 585)
            target_size = (620, 585)

        # 先设置新的最小尺寸
        self.setMinimumSize(*target_min)

        # 窗口大小切换动画
        self._resize_animation = QPropertyAnimation(self, b"geometry")
        self._resize_animation.setDuration(300)
        self._resize_animation.setEasingCurve(QEasingCurve.InOutCubic)
        current_geo = self.geometry()
        target_geo = QRect(current_geo.x(), current_geo.y(), target_size[0], target_size[1])
        self._resize_animation.setStartValue(current_geo)
        self._resize_animation.setEndValue(target_geo)
        self._resize_animation.start()

        self.rebuild_cards_layout()
        self.save_card_layout_config()
        self.show_message("布局已切换", tip_text, QMessageBox.Information)

    def save_card_layout_config(self):
        """保存卡片布局配置到 config.json"""
        try:
            config_path = get_config_path()
            config_data = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as config_file:
                    config_data = json.load(config_file)
            config_data['card_layout'] = self.card_layout_mode
            config_data['last_updated'] = datetime.now().isoformat()
            with open(config_path, 'w', encoding='utf-8') as config_file:
                json.dump(config_data, config_file, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def save_preferred_mode_config(self, mode: str):
        """保存 preferred_mode 到 config.json，同时保留 card_layout 等现有配置"""
        try:
            config_path = get_config_path()
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            config_data = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as config_file:
                    config_data = json.load(config_file)
            config_data['preferred_mode'] = mode
            config_data['last_updated'] = datetime.now().isoformat()
            with open(config_path, 'w', encoding='utf-8') as config_file:
                json.dump(config_data, config_file, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _create_buttons(self):
        """创建按钮区域"""
        buttons_frame = QFrame()
        buttons_frame.setStyleSheet("background-color: transparent;")
        
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(16)
        
        # 检查更新按钮
        self.check_button = QPushButton("检查更新")
        self.check_button.setFixedHeight(34)
        self.check_button.setMinimumWidth(120)
        self.check_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                          stop:0 rgba(55, 115, 232, 0.8), stop:1 rgba(66, 133, 244, 0.8));
                color: white;
                border: none;
                border-radius: 17px;
                font-size: 13px;
                font-weight: 500;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                          stop:0 rgba(66, 133, 244, 1), stop:1 rgba(77, 143, 245, 1));
            }
            QPushButton:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                          stop:0 rgba(44, 102, 212, 1), stop:1 rgba(55, 115, 232, 1));
            }
            QPushButton:disabled {
                background: rgba(173, 181, 189, 0.5);
                color: rgba(255, 255, 255, 0.6);
            }
        """)
        self.check_button.clicked.connect(self.run_check)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.check_button)
        buttons_layout.addStretch()
        
        self.main_layout.addWidget(buttons_frame)
    
    def check_system_theme_change(self):
        """检查系统主题变化并更新UI"""
        new_is_dark_mode = self.theme_manager._check_system_theme()
        if new_is_dark_mode != self.theme_manager.is_dark_mode:
            # 更新主题模式
            self.theme_manager.is_dark_mode = new_is_dark_mode
            
            # 更新所有软件卡片的主题
            for card in self.software_cards.values():
                if hasattr(card, 'update_card_theme'):
                    card.update_card_theme()
                # 重新应用状态标签样式
                if hasattr(card, 'status_type') and hasattr(card, 'update_info'):
                    # 使用现有数据重新调用update_info（使用原始版本号，避免重复格式化）
                    local_version = getattr(card, 'raw_local_version', '') if hasattr(card, 'local_version_value') else ''
                    online_version = getattr(card, 'raw_online_version', '') if hasattr(card, 'online_version_value') else ''
                    status = card.status_label.text()
                    status_type = getattr(card, 'status_type', 'up_to_date')
                    download_url = getattr(card, 'download_url', '')
                    card.update_info(local_version, online_version, status, status_type, download_url)
    
    def run_check(self):
        """运行更新检查"""
        if self.running:
            return
        
        self.running = True
        self.check_button.setEnabled(False)
        self.check_button.setText("正在检查...")
        
        # 显示进度条区域，初始值设为 10%，避免低百分比时圆角渲染异常
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(10)
        
        # 隐藏占位符，显示卡片容器
        self.placeholder_label.setVisible(False)
        self.cards_container.setVisible(True)
        
        # 检查所有服务
        selected_services = list(service_names.keys())
        
        # 创建工作线程
        t = threading.Thread(
            target=self.check_task,
            args=(selected_services,),
            daemon=True
        )
        t.start()
    
    def update_progress(self, value: int, message: str):
        """更新进度条"""
        self.progress_bar.set_value_animated(value)
        self.progress_label.setText(message)
    
    def update_card_result(self, service_key: str, result: dict):
        """更新卡片显示结果"""
        if service_key in self.software_cards:
            card = self.software_cards[service_key]
            card.setVisible(True)
            card.update_info(
                result.get("local_version", ""),
                result.get("online_version", ""),
                result.get("status", ""),
                result.get("status_type", ""),
                result.get("download_url", "")
            )
    
    def open_about(self):
        """打开关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec()
        
    def open_manual_version_dialog(self):
        """打开手动版本修改对话框

        返回:
            QDialog.Accepted 或 QDialog.Rejected，供调用方（如关于对话框）
            判断是否需要在保存成功后关闭自身
        """
        # 获取当前卡片中的版本号作为初始值
        current_versions = {}

        # 检查是否已经有手动设置的版本号
        if self.manual_versions:
            current_versions = self.manual_versions
        else:
            # 尝试从现有卡片中获取版本号（优先使用原始版本号，调试模式显示实际值）
            for app_key in service_names.keys():
                if app_key in self.software_cards:
                    card = self.software_cards[app_key]
                    raw_version = getattr(card, 'raw_local_version', '')
                    current_versions[app_key] = raw_version if raw_version else card.local_version_value.text()

        # 创建并显示对话框
        dialog = ManualVersionDialog(self, current_versions)

        result = dialog.exec()
        if result == QDialog.Accepted:
            # 保存用户输入的版本号
            self.manual_versions = dialog.get_versions()

            # 自动开始检查更新
            self.run_check()
        return result
    
    def on_check_complete(self):
        """检查完成后的处理"""
        self.running = False
        self.check_button.setEnabled(True)
        self.check_button.setText("检查更新")

        # 隐藏进度条
        self.progress_frame.setVisible(False)

    # ===== 应用自身更新检查 =====
    def _read_config(self) -> dict:
        """读取 config.json"""
        try:
            config_path = get_config_path()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as config_file:
                    return json.load(config_file)
        except Exception:
            pass
        return {}

    def _save_config(self, updates: dict):
        """合并写入 config.json（保留现有字段）"""
        try:
            config_path = get_config_path()
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            config_data = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as config_file:
                    config_data = json.load(config_file)
            config_data.update(updates)
            config_data['last_updated'] = datetime.now().isoformat()
            with open(config_path, 'w', encoding='utf-8') as config_file:
                json.dump(config_data, config_file, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def auto_check_self_update(self):
        """启动时静默检查应用自身更新（每天最多一次）"""
        config_data = self._read_config()
        last_check_date = config_data.get("last_self_check_date", "")
        today = datetime.now().strftime("%Y-%m-%d")
        if last_check_date == today:
            return
        # 记录今天已检查
        self._save_config({"last_self_check_date": today})
        # 后台线程执行检查
        threading.Thread(target=self._self_update_task, args=(False,), daemon=True).start()

    def manual_check_self_update(self, about_dialog=None):
        """关于对话框中手动触发检查（忽略每日一次限制）

        参数:
            about_dialog: 调用此方法的关于对话框引用，检查完成后会关闭它
        """
        self._pending_about_dialog = about_dialog
        threading.Thread(target=self._self_update_task, args=(True,), daemon=True).start()

    def _self_update_task(self, is_manual: bool):
        """后台检查应用自身更新的线程任务"""
        result = check_for_update(APP_VERSION)
        # 标记本次检查是否为手动触发（供 UI 侧决定是否弹出"已是最新版本"提示）
        result["is_manual"] = is_manual
        # 通过信号回 UI 线程
        self.worker_bridge.show_self_update.emit(result)

    def on_self_update_result(self, result: dict):
        """处理自身更新检查结果"""
        is_manual = result.get("is_manual", False)

        # 若来自手动检查，先关闭关于对话框
        if is_manual and hasattr(self, "_pending_about_dialog") and self._pending_about_dialog is not None:
            try:
                self._pending_about_dialog.reject()
            except Exception:
                pass
            self._pending_about_dialog = None

        if result.get("error"):
            # 仅手动检查时提示错误，自动检查静默忽略
            if is_manual:
                self.show_message("检查更新", result["error"], QMessageBox.Warning)
            return

        if result.get("has_update"):
            icon_path = resource_path("resources/icon.png")
            dialog = UpdateAvailableDialog(
                self, result, APP_VERSION,
                self.theme_manager, icon_path
            )
            dialog.exec()
        else:
            # 无更新：自动检查静默，仅手动检查时提示"已是最新版本"
            if is_manual:
                self.show_message(
                    "检查更新",
                    f"当前已是最新版本（{APP_VERSION}）",
                    QMessageBox.Information
                )

    def show_message(self, title: str, message: str, icon_type: int):
        """显示消息对话框 - 适配深色/浅色主题"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon_type)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # 应用主题样式
        if self.theme_manager.is_dark_mode:
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2d2d2d;
                    color: #f3f3f3;
                }
                QPushButton {
                    background-color: #3773e8;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                }
            """)
            # 设置标题栏颜色为深色主题背景色
            self._set_message_box_title_bar_color(msg_box, "#2d2d2d")
        else:
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #f3f3f3;
                    color: #495057;
                }
                QPushButton {
                    background-color: #3773e8;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                }
            """)
            # 设置标题栏颜色为浅色主题背景色
            self._set_message_box_title_bar_color(msg_box, "#f3f3f3")
        
        msg_box.exec()
    
    def get_pixel_color_at_position(self, x, y):
        """获取窗口客户区顶部背景颜色，用于设置标题栏颜色
        
        取色点集中在标题栏下方的客户区顶部，排除边缘和可能的文字/按钮干扰，
        通过聚类得到最贴近实际背景的主色调。
        """
        try:
            # 客户区左上角在屏幕上的位置（mapToGlobal(QPoint(0,0)) 已在标题栏下方）
            screen_pos = self.mapToGlobal(QPoint(0, 0))
            window_width = self.width()
            
            if window_width <= 0:
                return "#2d2d2d"
            
            # 横向均匀分布，避开左右 5% 边缘（避免边框/阴影影响）
            percent_positions = [0.05, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 0.95]
            # 纵向在客户区顶部取多行，紧贴标题栏下方
            y_offsets = [2, 4, 6, 8]
            
            colors = []
            screen = QApplication.primaryScreen()
            for percent in percent_positions:
                current_x = int(window_width * percent)
                for y_offset in y_offsets:
                    screen_x = screen_pos.x() + current_x
                    screen_y = screen_pos.y() + y_offset
                    pixmap = screen.grabWindow(0, screen_x, screen_y, 1, 1)
                    image = pixmap.toImage()
                    color = image.pixelColor(0, 0)
                    colors.append((color.red(), color.green(), color.blue()))
            
            if not colors:
                return "#2d2d2d"
            
            # 颜色聚类：找出最相近的颜色组，排除文字/按钮等异常点
            def color_distance(c1, c2):
                return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2) ** 0.5
            
            similarity_threshold = 25
            clusters = []
            for color in colors:
                added_to_cluster = False
                for cluster in clusters:
                    if color_distance(color, cluster[0]) < similarity_threshold:
                        cluster.append(color)
                        added_to_cluster = True
                        break
                if not added_to_cluster:
                    clusters.append([color])
            
            if not clusters:
                return "#2d2d2d"
            
            # 取最大聚类作为主背景色
            largest_cluster = max(clusters, key=len)
            
            # 如果主聚类样本过少，说明颜色分散，回退到默认深色
            if len(largest_cluster) < len(colors) * 0.3:
                return "#2d2d2d"
            
            avg_r = sum(c[0] for c in largest_cluster) // len(largest_cluster)
            avg_g = sum(c[1] for c in largest_cluster) // len(largest_cluster)
            avg_b = sum(c[2] for c in largest_cluster) // len(largest_cluster)
            
            # 轻微提亮以补偿 DWM 标题栏与实际半透明背景的视觉差异
            r = min(255, avg_r + 2)
            g = min(255, avg_g + 2)
            b = min(255, avg_b + 2)
            
            # 确保RGB值在有效范围内
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            # 如果取色失败，返回默认颜色
            return "#2d2d2d"  # 深色主题背景色调淡版
    
    def set_windows_title_bar_color(self, hex_color):
        """设置窗口标题栏颜色"""
        try:
            # 转换十六进制颜色到RGB
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # 定义Windows API
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            HWND = self.winId()
            dwmapi = ctypes.WinDLL('dwmapi')
            
            # 设置标题栏背景颜色
            color_value = wintypes.DWORD((b << 16) | (g << 8) | r)
            dwmapi.DwmSetWindowAttribute(
                HWND, 
                DWMWA_CAPTION_COLOR, 
                ctypes.byref(color_value), 
                ctypes.sizeof(color_value)
            )
            
            # 判断是否为深色背景，如果是则设置文字为白色
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if brightness < 128:
                text_color = wintypes.DWORD(0xFFFFFF)  # 白色
                dwmapi.DwmSetWindowAttribute(
                    HWND, 
                    DWMWA_TEXT_COLOR, 
                    ctypes.byref(text_color), 
                    ctypes.sizeof(text_color)
                )
        except Exception as e:
            # 忽略错误，确保程序正常运行
            pass
    
    def _set_message_box_title_bar_color(self, msg_box, hex_color):
        """设置消息对话框的标题栏颜色"""
        try:
            # 转换十六进制颜色到RGB
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # 定义Windows API
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            HWND = msg_box.winId()
            dwmapi = ctypes.WinDLL('dwmapi')
            
            # 设置标题栏背景颜色
            color_value = wintypes.DWORD((b << 16) | (g << 8) | r)
            dwmapi.DwmSetWindowAttribute(
                HWND, 
                DWMWA_CAPTION_COLOR, 
                ctypes.byref(color_value), 
                ctypes.sizeof(color_value)
            )
            
            # 判断是否为深色背景，如果是则设置文字为白色
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if brightness < 128:
                text_color = wintypes.DWORD(0xFFFFFF)  # 白色
                dwmapi.DwmSetWindowAttribute(
                    HWND, 
                    DWMWA_TEXT_COLOR, 
                    ctypes.byref(text_color), 
                    ctypes.sizeof(text_color)
                )
        except Exception as e:
            # 忽略错误，确保程序正常运行
            pass

    def switch_to_normal_mode(self):
        """切换到普通模式，修改配置文件并重启应用"""
        # 显示确认对话框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认切换")
        msg_box.setText("确定要切换到普通模式吗？\n切换后将关闭当前窗口并重启应用。")
        # 添加原生提示图标
        msg_box.setIcon(QMessageBox.Question)
        # 设置按钮文本为中文
        yes_button = msg_box.addButton("确认切换", QMessageBox.AcceptRole)
        no_button = msg_box.addButton("取消", QMessageBox.RejectRole)
        msg_box.setDefaultButton(no_button)
        
        # 应用主题样式
        if self.theme_manager.is_dark_mode:
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2d2d2d;
                    color: #f3f3f3;
                }
                QPushButton {
                    background-color: #3773e8;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                }
            """)
            # 设置标题栏颜色为深色主题背景色
            self._set_message_box_title_bar_color(msg_box, "#2d2d2d")
        else:
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #f3f3f3;
                    color: #495057;
                }
                QPushButton {
                    background-color: #3773e8;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                }
            """)
            # 设置标题栏颜色为浅色主题背景色
            self._set_message_box_title_bar_color(msg_box, "#f3f3f3")
        
        msg_box.exec()
        # 检查哪个按钮被点击
        if msg_box.clickedButton() == yes_button:
            try:
                # 保存用户配置 - 保留 card_layout 等现有配置
                self.save_preferred_mode_config("normal")

                # 重启自己（无论是 main.py 还是打包后的 main.exe）
                if getattr(sys, 'frozen', False):
                    # 打包后直接运行exe
                    subprocess.Popen([sys.executable])
                else:
                    # 开发环境
                    app_path = os.path.abspath(sys.argv[0])
                    subprocess.Popen([sys.executable, app_path])

                # 关闭当前窗口
                self.close()
            except Exception as e:
                self.show_message("错误", f"无法切换到普通模式: {str(e)}", QMessageBox.Critical)
    
    def check_task(self, services: List[str]):
        """更新检查的具体任务"""
        # 先获取所有本地版本
        installed_versions = {}

        # 更新进度
        total_services = len(services)
        # 进度分配：起始保留 10% 以保证进度条圆角正常渲染，
        # 剩余 90% 按软件数量平分，分为3个阶段
        # 阶段1（开始）：20% 检查本地版本
        # 阶段2（请求官网）：60% 请求并解析
        # 阶段3（完成）：20% 发送结果

        for i, key in enumerate(services):
            # 当前软件的进度区间
            base_progress = 10 + (i / total_services) * 90
            span = 90 / total_services

            # 阶段1：开始检查，获取本地版本
            self.worker_bridge.update_progress.emit(
                int(base_progress + span * 0.1),
                f"正在检查 {service_names[key]}..."
            )

            try:
                # 优先使用手动设置的版本号（如果有）
                if key in self.manual_versions and self.manual_versions[key]:
                    local_version = self.manual_versions[key]
                else:
                    # 获取本地版本
                    if key in installed_versions_config:
                        config = installed_versions_config[key]
                        if config["type"] == "xml":
                            local_version = get_local_version(config["path"])
                        elif config["type"] == "registry":
                            local_version = get_registry_version(config["path"], config["value_name"])
                        else:
                            local_version = None
                    else:
                        local_version = None

                installed_versions[key] = local_version

                # 阶段2：请求官网页面获取最新版本
                self.worker_bridge.update_progress.emit(
                    int(base_progress + span * 0.3),
                    f"正在获取 {service_names[key]} 官网版本..."
                )

                # 请求官网页面获取最新版本
                if key in website_config:
                    info = website_config[key]
                    res = requests.get(info["url"], timeout=10)
                    res.raise_for_status()

                    res.encoding = 'utf-8'

                    soup = BeautifulSoup(res.text, "html.parser")
                    tag, cls = info["selector"]
                    element = soup.find(tag, class_=cls)

                    if element:
                        latest_version_text = element.get_text(strip=True)
                        version_display = clean_version(latest_version_text.split("|")[0], remove_patch=False)

                        online_main, online_sp = parse_version(version_display)
                        local_main, local_sp = parse_version(local_version or "")

                        if not local_version:
                            status = f"未获取到本地版本"
                            status_type = "error"
                        elif online_main > local_main or (online_main == local_main and online_sp > local_sp):
                            status = f"有新版本可用！"
                            status_type = "update_available"
                        elif online_main == local_main and online_sp == local_sp:
                            status = "已是最新版本"
                            status_type = "up_to_date"
                        else:
                            status = "本地版本高于官网版本"
                            status_type = "higher_version"

                        # 发送结果到UI线程
                        self.worker_bridge.update_result.emit(key, {
                            "local_version": local_version,
                            "online_version": version_display,
                            "status": status,
                            "status_type": status_type,
                            "download_url": info["url"]
                        })
                    else:
                        # 未找到版本信息
                        self.worker_bridge.update_result.emit(key, {
                            "local_version": local_version,
                            "online_version": "未找到",
                            "status": "未找到官网版本",
                            "status_type": "error",
                            "download_url": info["url"]
                        })
                else:
                    # 配置不存在
                    self.worker_bridge.update_result.emit(key, {
                        "local_version": local_version,
                        "online_version": "配置不存在",
                        "status": "配置错误",
                        "status_type": "error",
                        "download_url": ""
                    })

            except Exception as e:
                # 发生错误
                self.worker_bridge.update_result.emit(key, {
                    "local_version": installed_versions.get(key, ""),
                    "online_version": "获取失败",
                    "status": get_network_error_message(e),
                    "status_type": "error",
                    "download_url": website_config.get(key, {}).get("url", "")
                })

            # 阶段3：当前软件检查完成
            self.worker_bridge.update_progress.emit(
                int(base_progress + span * 0.95),
                f"{service_names[key]} 检查完成"
            )

            # 短暂延迟，避免请求过快
            time.sleep(0.3)

        # 平滑更新进度为100%
        self.worker_bridge.update_progress.emit(100, "检查完成")

        # 通知UI线程检查完成
        self.worker_bridge.check_complete.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont("HONOR Sans CN", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    
    w = GlassWindow()
    w.show()
    sys.exit(app.exec())
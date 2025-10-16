# HUANCHUAN with Copilot by Trae  版本号：10.0.0
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
    Qt, QObject, Signal,
    QPropertyAnimation, QUrl, QPoint, QTimer
)
from PySide6.QtGui import (
    QFont, QIcon, QColor, QPixmap, QDesktopServices
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QDialog,
    QScrollArea, QProgressBar, QMessageBox, QToolButton,
    QGraphicsDropShadowEffect, QStyle, QLineEdit
)
from BlurWindow.blurWindow import GlobalBlur

# ===== 常量定义 =====
APP_NAME = "荣耀软件更新检查器"
APP_VERSION = "10.0.0"
COPYRIGHT_YEAR = "2025"

# 应用名称映射
service_names = {
    "pc_manager": "荣耀电脑管家",
    "honor_workstation": "荣耀超级工作台",
    "yoyo_assistant": "荣耀 YOYO 助理"
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
    except Exception as e:
        return f"读取版本失败: {e}"

def version_tuple(v: str) -> Tuple[int, ...]:
    """将版本字符串转换为元组，用于比较版本号"""
    try:
        return tuple(int(x) for x in v.strip().split(".") if x.isdigit())
    except ValueError:
        return (0,)

def clean_version(v: str, remove_patch: bool = True) -> str:
    """清理版本字符串，移除多余信息"""
    v = v.replace("Version", "").replace("版本", "").strip()
    if remove_patch:
        v = re.sub(r"\(.*?\)", "", v).strip()
    return v

def resource_path(relative_path: str) -> str:
    """获取资源文件的绝对路径（兼容PyInstaller打包后）"""
    if hasattr(sys, "_MEIPASS"):  # PyInstaller 打包后的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_config_path():
    """获取配置文件的绝对路径（统一使用sys.argv[0]）"""
    return os.path.join(os.path.dirname(sys.argv[0]), "config.json")

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

# ===== 自定义卡片组件 =====
class SoftwareCard(QFrame):
    """软件信息卡片组件 - 通透模式专用样式"""
    def __init__(self, software_key: str, name: str, icon_path: str, parent=None):
        super().__init__(parent)
        self.software_key = software_key
        self.name = name
        self.icon_path = icon_path
        
        # 设置卡片样式 - 通透模式专用
        self.setObjectName("SoftwareCard")
        self.setStyleSheet("QFrame#SoftwareCard { margin: 8px; }")
        
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
        self.main_layout.setSpacing(12)
        
        # 创建顶部信息区
        self._create_header_section()
        
        # 创建版本信息区
        self._create_version_section()
        
        # 创建状态区
        self._create_status_section()
        
        # 初始设置卡片样式 - 必须在创建所有标签后调用
        self.update_card_theme()
    
    def _create_header_section(self):
        """创建卡片顶部信息区"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        # 软件图标
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(64, 64)
        self.icon_label.setScaledContents(True)
        
        # 尝试加载图标 - 确保路径正确处理
        icon_path = self.icon_path
        if icon_path and os.path.exists(icon_path):
            self.icon_label.setPixmap(QPixmap(icon_path))
        
        # 软件名称
        self.name_label = QLabel(self.name)
        name_font = QFont("HONOR Sans CN", 16, QFont.Bold)
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
        version_layout.setSpacing(6)
        version_layout.setColumnStretch(1, 1)
        
        # 本地版本
        local_version_label = QLabel("本地版本:")
        local_version_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        
        self.local_version_value = QLabel("加载中...")
        self.local_version_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.local_version_value.setStyleSheet("color: white;")
        
        # 官网版本
        online_version_label = QLabel("官网版本:")
        online_version_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        
        self.online_version_value = QLabel("加载中...")
        self.online_version_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.online_version_value.setStyleSheet("color: white;")
        
        # 添加到布局
        version_layout.addWidget(local_version_label, 0, 0)
        version_layout.addWidget(self.local_version_value, 0, 1)
        version_layout.addWidget(online_version_label, 1, 0)
        version_layout.addWidget(self.online_version_value, 1, 1)
        
        self.main_layout.addLayout(version_layout)
    
    def _create_status_section(self):
        """创建状态显示区"""
        status_layout = QHBoxLayout()
        status_layout.setSpacing(12)
        
        # 状态标签
        self.status_label = QLabel("正在检查...")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumWidth(120)
        
        # 更新链接按钮
        self.download_button = QPushButton("更新链接")
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(55, 115, 232, 0.8);
                color: white;
                border: none;
                border-radius: 16px;
                padding: 6px 16px;
                font-size: 12px;
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
        # 通透模式专用样式
        card_style = """
            QFrame#SoftwareCard {
                background-color: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                padding: 20px;
            }
            QFrame#SoftwareCard:disabled {
                opacity: 0.7;
            }
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
            label.setStyleSheet(f"color: {text_color}; background-color: transparent;")
    
    def fade_in(self):
        """淡入动画"""
        self.fade_animation.setStartValue(self.windowOpacity())
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
    
    def update_info(self, local_version: str, online_version: str, status: str,
                   status_type: str, download_url: str = ""):
        """更新卡片信息"""
        # 更新版本信息
        self.local_version_value.setText(local_version or "未知")
        self.online_version_value.setText(online_version or "未知")
        
        # 更新状态标签
        self.status_label.setText(status)
        
        # 根据状态类型设置样式 - 通透模式专用
        if status_type == "up_to_date":
            self.status_label.setStyleSheet("""
                QLabel#StatusLabel {
                    background-color: rgba(45, 62, 54, 0.8);
                    color: rgba(146, 208, 80, 1);
                    padding: 4px 12px;
                    border-radius: 16px;
                    font-weight: 500;
                }
            """)
            self.download_button.setVisible(False)
        elif status_type == "update_available":
            self.status_label.setStyleSheet("""
                QLabel#StatusLabel {
                    background-color: rgba(62, 54, 45, 0.8);
                    color: rgba(255, 193, 7, 1);
                    padding: 4px 12px;
                    border-radius: 16px;
                    font-weight: 500;
                }
            """)
            if download_url:
                self.download_button.setVisible(True)
                self.download_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(download_url)))
        elif status_type == "error":
            self.status_label.setStyleSheet("""
                QLabel#StatusLabel {
                    background-color: rgba(62, 45, 45, 0.8);
                    color: rgba(255, 107, 107, 1);
                    padding: 4px 12px;
                    border-radius: 16px;
                    font-weight: 500;
                }
            """)
            self.download_button.setVisible(False)
        elif status_type == "higher_version":
            self.status_label.setStyleSheet("""
                QLabel#StatusLabel {
                    background-color: rgba(45, 54, 62, 0.8);
                    color: rgba(119, 191, 249, 1);
                    padding: 4px 12px;
                    border-radius: 16px;
                    font-weight: 500;
                }
            """)
            if download_url:
                self.download_button.setVisible(True)
                self.download_button.setText("官网链接")
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
        self.setFixedSize(340, 240)
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
        
        # 添加到布局
        self.main_layout.addWidget(self.icon_label)
        self.main_layout.addWidget(self.title_label)
        self.main_layout.addWidget(self.version_label)
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
            self.parent_window.open_manual_version_dialog()

# ===== 手动版本修改对话框 =====
class ManualVersionDialog(QDialog):
    """手动版本修改对话框类 - 调试模式，支持深色/浅色主题"""
    
    def __init__(self, parent=None, current_versions=None):
        super().__init__(parent)
        self.setWindowTitle("调试模式 - 手动修改版本号")
        self.setModal(True)
        self.setFixedSize(360, 280)
        
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
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(12)
        
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
        self.reset_button.setFixedWidth(90)
        self.reset_button.clicked.connect(self.reset_to_local_versions)
        
        self.save_button = QPushButton("保存")
        self.save_button.setFixedWidth(80)
        self.save_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFixedWidth(80)
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.save_button)
        
        self.main_layout.addLayout(buttons_layout)
    
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
        
        # 设置窗口标题、大小和最小大小
        self.setWindowTitle(f"Update Checker for HONOR MagicBook")
        self.resize(400, 740)
        self.setMinimumSize(400, 740)
        
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
        
        # 加载图标路径
        self.icon_files = {
            "pc_manager": resource_path("resources/pc_manager.png"),
            "honor_workstation": resource_path("resources/honor_workstation.png"),
            "yoyo_assistant": resource_path("resources/yoyo_assistant.png")
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
        
        # 自动开始检查更新
        self.run_check()
        
        # 设置窗口标题栏颜色为指定颜色
        # 从窗口左侧1像素从客户区顶部下1像素的位置取色
        self.update_title_bar_color()
        
        # 设置定时器，定期更新标题栏颜色（每500毫秒）
        self.color_update_timer = QTimer(self)
        self.color_update_timer.timeout.connect(self.update_title_bar_color)
        self.color_update_timer.start(300)  # 300毫秒更新一次
        
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
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
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
        
        # 创建软件卡片
        self.software_cards = {}
        for key, name in service_names.items():
            card = SoftwareCard(key, name, self.icon_files.get(key, ""))
            card.setVisible(False)
            self.software_cards[key] = card
            self.results_layout.addWidget(card)
        
        self.results_layout.addStretch()
        
        # 设置滚动区域内容
        self.scroll_area.setWidget(scroll_content)
        
        self.main_layout.addWidget(self.scroll_area, 1)
    
    def _create_buttons(self):
        """创建按钮区域"""
        buttons_frame = QFrame()
        buttons_frame.setStyleSheet("background-color: transparent;")
        
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(16)
        
        # 检查更新按钮
        self.check_button = QPushButton("检查更新")
        self.check_button.setFixedHeight(40)
        self.check_button.setMinimumWidth(160)
        self.check_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                          stop:0 rgba(55, 115, 232, 0.8), stop:1 rgba(66, 133, 244, 0.8));
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 16px;
                font-weight: 500;
                padding: 0 24px;
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
                    # 使用现有数据重新调用update_info
                    card.update_info(
                        getattr(card, 'local_version', ''),
                        getattr(card, 'online_version', ''),
                        getattr(card, 'status', ''),
                        getattr(card, 'status_type', ''),
                        getattr(card, 'download_url', '')
                    )
    
    def run_check(self):
        """运行更新检查"""
        if self.running:
            return
        
        self.running = True
        self.check_button.setEnabled(False)
        self.check_button.setText("正在检查...")
        
        # 显示进度条区域
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 隐藏占位符，显示所有选中的卡片
        self.placeholder_label.setVisible(False)
        
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
        self.progress_bar.setValue(value)
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
        """打开手动版本修改对话框"""
        # 获取当前卡片中的版本号作为初始值
        current_versions = {}
        
        # 检查是否已经有手动设置的版本号
        if self.manual_versions:
            current_versions = self.manual_versions
        else:
            # 尝试从现有卡片中获取版本号
            for app_key in service_names.keys():
                if app_key in self.software_cards:
                    card = self.software_cards[app_key]
                    current_versions[app_key] = card.local_version_value.text()
        
        # 创建并显示对话框
        dialog = ManualVersionDialog(self, current_versions)
        
        if dialog.exec() == QDialog.Accepted:
            # 保存用户输入的版本号
            self.manual_versions = dialog.get_versions()
            
            # 显示保存成功的消息
            self.show_message(
                "设置成功",
                "已成功设置手动版本号。\n请点击'检查更新'按钮查看效果。",
                QMessageBox.Information
            )
    
    def on_check_complete(self):
        """检查完成后的处理"""
        self.running = False
        self.check_button.setEnabled(True)
        self.check_button.setText("检查更新")
        
        # 隐藏进度条
        self.progress_frame.setVisible(False)
    
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
        """获取窗口内指定位置的像素颜色并进行智能调整
        
        Args:
            x: 窗口左侧的水平偏移像素（从左边缘计算）
            y: 客户区垂直偏移像素（从标题栏下方开始计算）
        """
        try:
            # 获取窗口在屏幕上的位置
            screen_pos = self.mapToGlobal(QPoint(0, 0))
            
            # 计算客户区在屏幕上的位置（需要考虑标题栏高度）
            title_bar_height = self.frameGeometry().height() - self.geometry().height()
            
            # 获取窗口宽度
            window_width = self.width()
            
            # 定义多个取色点的百分比位置（横向）
            percent_positions = [0.01, 0.25, 0.5, 0.75, 0.99]  # 1%, 25%, 50%, 75%, 99%
            colors = []
            
            # 遍历所有取色点获取颜色
            for percent in percent_positions:
                # 计算当前取色点的x坐标
                current_x = int(window_width * percent)
                
                # 计算实际屏幕坐标
                screen_x = screen_pos.x() + current_x
                screen_y = screen_pos.y() + title_bar_height + 1  # 纵向固定为1像素
                
                # 获取屏幕截图
                screen = QApplication.primaryScreen()
                pixmap = screen.grabWindow(0, screen_x, screen_y, 1, 1)  # 获取指定像素
                
                # 获取像素颜色
                image = pixmap.toImage()
                color = image.pixelColor(0, 0)
                
                # 保存RGB值
                colors.append((color.red(), color.green(), color.blue()))
            
            # 颜色聚类：找出最相近的颜色组
            # 使用简单的聚类方法，计算颜色之间的欧氏距离
            def color_distance(c1, c2):
                return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2) ** 0.5
            
            # 设定颜色相似度阈值
            similarity_threshold = 20
            
            # 聚类结果
            clusters = []
            
            # 对每个颜色进行聚类
            for color in colors:
                # 查找是否可以加入现有聚类
                added_to_cluster = False
                for cluster in clusters:
                    # 计算与聚类中第一个颜色的距离（简化处理）
                    if color_distance(color, cluster[0]) < similarity_threshold:
                        cluster.append(color)
                        added_to_cluster = True
                        break
                
                # 如果没有找到合适的聚类，创建新聚类
                if not added_to_cluster:
                    clusters.append([color])
            
            # 找出最大的聚类
            if clusters:
                largest_cluster = max(clusters, key=len)
                
                # 计算最大聚类的平均颜色
                avg_r = sum(c[0] for c in largest_cluster) // len(largest_cluster)
                avg_g = sum(c[1] for c in largest_cluster) // len(largest_cluster)
                avg_b = sum(c[2] for c in largest_cluster) // len(largest_cluster)
            else:
                # 如果聚类失败，使用第一个取色点
                avg_r, avg_g, avg_b = colors[0] if colors else (45, 45, 45)  # 默认颜色
            
            # 智能颜色调整逻辑
            # 1. 对于白色(ffffff)，调整为bebebe
            if avg_r == 255 and avg_g == 255 and avg_b == 255:
                r = 215
                g = 215
                b = 215
            # 2. 对于深色，根据亮度进行调整
            elif avg_r < 50 and avg_g < 50 and avg_b < 50:  # 非常暗的颜色
                # 1e1f22(30,31,34) -> 222222(34,34,34)
                # 1a1b1d(26,27,29) -> 1c1d1f(28,29,31)
                # 基于亮度增加RGB值
                avg_brightness = (avg_r + avg_g + avg_b) // 3
                if avg_brightness < 30:  # 极暗
                    r = min(255, avg_r + 3)
                    g = min(255, avg_g + 2)
                    b = min(255, avg_b + 3)
                else:  # 一般暗
                    r = min(255, avg_r + 2)
                    g = min(255, avg_g + 2)
                    b = min(255, avg_b + 2)
            # 3. 对于蓝色系深色(如091c3a)
            elif avg_r < 30 and avg_g < 50 and avg_b > 50:
                # 091c3a(9,28,58) -> 0c1e3d(12,30,61)
                r = min(255, avg_r + 3)
                g = min(255, avg_g + 2)
                b = min(255, avg_b + 3)
            else:
                # 其他情况使用平均颜色
                r, g, b = avg_r, avg_g, avg_b
            
            # 确保RGB值在有效范围内
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception as e:
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
                # 保存用户配置 - 使用json文件存储偏好设置
                config_path = get_config_path()
                # 确保目录存在
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                config = {
                    "preferred_mode": "normal",
                    "last_updated": datetime.now().isoformat()
                }
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                # 重启自己（无论是 main.py 还是打包后的 main.exe）
                # 使用os.path.abspath确保获取完整路径
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
        
        for i, key in enumerate(services):
            # 更新进度
            progress_value = int((i / total_services) * 70)  # 留30%给后续处理
            self.worker_bridge.update_progress.emit(
                progress_value,
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
                
                # 请求官网页面获取最新版本
                if key in website_config:
                    info = website_config[key]
                    res = requests.get(info["url"], timeout=10)
                    res.raise_for_status()
                    
                    soup = BeautifulSoup(res.text, "html.parser")
                    tag, cls = info["selector"]
                    element = soup.find(tag, class_=cls)
                    
                    if element:
                        latest_version_text = element.get_text(strip=True)
                        version_display = clean_version(latest_version_text.split("|")[0], remove_patch=False)
                        version_compare = clean_version(version_display, remove_patch=True)
                        
                        local_ver_compare = clean_version(local_version or "", remove_patch=True)
                        
                        # 版本比较
                        if not local_version:
                            status = f"未获取到本地版本"
                            status_type = "error"
                        elif version_tuple(local_ver_compare) == version_tuple(version_compare):
                            status = "已是最新版本"
                            status_type = "up_to_date"
                        elif version_tuple(local_ver_compare) < version_tuple(version_compare):
                            status = f"有新版本可用！"
                            status_type = "update_available"
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
                    "status": f"检查失败: {str(e)[:30]}...",
                    "status_type": "error",
                    "download_url": website_config.get(key, {}).get("url", "")
                })
            
            # 短暂延迟，避免请求过快
            time.sleep(0.5)
        
        # 更新进度为100%
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
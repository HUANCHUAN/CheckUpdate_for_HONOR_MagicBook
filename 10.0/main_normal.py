# HUANCHUAN with Copilot by Trae  版本号：10.0.0
import json
import subprocess
from datetime import datetime
import sys
import os
import re
import xml.etree.ElementTree as ET
import winreg
import requests
import threading
import time
from typing import Tuple, Optional, List
import ctypes
from ctypes import wintypes
import certifi

# 设置TLS证书路径，解决打包后的TLS错误
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from bs4 import BeautifulSoup
from PySide6.QtCore import (
    Qt, QObject, Signal, QRect,
    QEasingCurve, QPropertyAnimation, QUrl, QTimer
)
from PySide6.QtGui import (
    QFont, QIcon, QColor, QPixmap, QDesktopServices
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QDialog,
    QScrollArea, QProgressBar,QMessageBox, QToolButton,
    QGraphicsDropShadowEffect, QStyle, QLineEdit
)

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

# ===== 主题管理 =====
class ThemeManager:
    """主题管理类，负责处理应用程序的主题切换"""
    def __init__(self):
        self.is_dark_mode = False
        self.load_system_theme()
        
    def load_system_theme(self):
        """加载系统主题设置"""
        try:
            # 尝试从Windows注册表获取系统主题设置
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            self.is_dark_mode = value == 0
        except:
            # 默认使用浅色主题
            self.is_dark_mode = False
    
    def toggle_theme(self):
        """切换主题模式"""
        self.is_dark_mode = not self.is_dark_mode
        return self.is_dark_mode
    
    def get_style_sheet(self) -> str:
        """获取当前主题的样式表"""
        if self.is_dark_mode:
            return self._get_dark_style_sheet()
        else:
            return self._get_light_style_sheet()
    
    def _get_light_style_sheet(self) -> str:
        """获取浅色主题样式表"""
        return """
            /* 主窗口样式 */
            MainWindow {
                background-color: #f3f3f3;
                color: #212529;
            }
            
            /* 卡片样式 */
            .Card {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e9ecef;
                padding: 16px;
                margin: 8px;
            }
            
            /* 按钮样式 */
            .PrimaryButton {
                background-color: #3773e8;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: 500;
            }
            .PrimaryButton:hover {
                background-color: #4285f4;
            }
            .PrimaryButton:pressed {
                background-color: #2c66d4;
            }
            
            /* 状态标签样式 */
            .StatusLabel {
                font-weight: 500;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
            }
            
            /* 信息文本样式 */
            .InfoText {
                color: #6c757d;
                font-size: 12px;
            }
        """
    
    def _get_dark_style_sheet(self) -> str:
        """获取深色主题样式表"""
        return """
            /* 主窗口样式 */
            MainWindow {
                background-color: #1e1e1e;
                color: #f3f3f3;
            }
            
            /* 卡片样式 */
            .Card {
                background-color: #2d2d2d;
                border-radius: 12px;
                border: 1px solid #404040;
                padding: 16px;
                margin: 8px;
            }
            
            /* 按钮样式 */
            .PrimaryButton {
                background-color: #3773e8;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: 500;
            }
            .PrimaryButton:hover {
                background-color: #4285f4;
            }
            .PrimaryButton:pressed {
                background-color: #2c66d4;
            }
            
            /* 状态标签样式 */
            .StatusLabel {
                font-weight: 500;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
            }
            
            /* 信息文本样式 */
            .InfoText {
                color: #adb5bd;
                font-size: 12px;
            }
        """

# ===== 工作线程通信对象 =====
class WorkerBridge(QObject):
    """用于工作线程与UI线程通信的桥梁"""
    update_progress = Signal(int, str)
    update_result = Signal(str, dict)
    check_complete = Signal()
    show_message = Signal(str, str, int)

# ===== 自定义渐变按钮 =====
class GradientButton(QPushButton):
    """自定义渐变按钮"""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(40)
        self.setMinimumWidth(120)
        self.setCursor(Qt.PointingHandCursor)
        
        # 设置基础样式
        self.update_styles()
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)
    
    def update_styles(self):
        """更新按钮样式"""
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                           stop:0 #3773e8, stop:1 #4285f4);
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 16px;
                font-weight: 500;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                           stop:0 #4285f4, stop:1 #4d8ff5);
            }
            QPushButton:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                           stop:0 #2c66d4, stop:1 #3773e8);
            }
            QPushButton:disabled {
                background: #adb5bd;
                color: #6c757d;
            }
        """)
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self.animate_scale(1.05)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.animate_scale(1.0)
        super().leaveEvent(event)
    
    def animate_scale(self, target_scale: float):
        """缩放动画"""
        animation = QPropertyAnimation(self, b"geometry")
        animation.setDuration(200)
        animation.setEasingCurve(QEasingCurve.OutQuad)
        
        rect = self.geometry()
        center = rect.center()
        
        animation.setStartValue(rect)
        
        new_width = int(rect.width() * target_scale)
        new_height = int(rect.height() * target_scale)
        
        new_rect = QRect(0, 0, new_width, new_height)
        new_rect.moveCenter(center)
        
        animation.setEndValue(new_rect)
        animation.start()

# ===== 自定义卡片组件 =====
class SoftwareCard(QFrame):
    """软件信息卡片组件"""
    def __init__(self, software_key: str, name: str, icon_path: str, parent=None):
        super().__init__(parent)
        self.software_key = software_key
        self.name = name
        self.icon_path = icon_path
        
        # 现在卡片样式通过主题管理系统在update_card_theme方法中设置
        self.setObjectName("SoftwareCard")
        self.setStyleSheet("QFrame#SoftwareCard { margin: 8px; }")
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 15))
        self.setGraphicsEffect(shadow)
        
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
        
        # 初始化动画
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(500)
        
    def update_card_theme(self, is_dark_mode: bool):
        """根据主题更新卡片样式"""
        if is_dark_mode:
            # 深色模式样式
            card_style = """
                QFrame#SoftwareCard {
                    background-color: #2d2d2d;
                    border-radius: 16px;
                    border: 1px solid #404040;
                    padding: 20px;
                }
                QFrame#SoftwareCard:disabled {
                    opacity: 0.7;
                }
            """
            text_color = "#f3f3f3"
            info_color = "#adb5bd"
        else:
            # 浅色模式样式 - 优化版本
            card_style = """
                QFrame#SoftwareCard {
                    background-color: white;
                    border-radius: 16px;
                    border: 1px solid #e9ecef;
                    padding: 20px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
                    transition: all 0.3s ease;
                }
                QFrame#SoftwareCard:hover {
                    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
                    border-color: #dee2e6;
                }
                QFrame#SoftwareCard:disabled {
                    opacity: 0.7;
                }
            """
            text_color = "#495057"
            info_color = "#6c757d"
        
        # 更新卡片样式
        self.setStyleSheet(card_style)
        
        # 更新文本颜色，确保文字不透明
        self.name_label.setStyleSheet(f"color: {text_color}; background-color: transparent;")
        
        # 更新版本标签颜色，确保文字不透明
        for label in [self.local_version_value, self.online_version_value]:
            label.setStyleSheet(f"color: {text_color}; background-color: transparent;")
        
        # 更新状态标签颜色（如果已经设置了状态），确保背景和文字都不透明
        current_status = self.status_label.text()
        if "已是最新版本" in current_status:
            self.status_label.setStyleSheet(f"""
                QLabel#StatusLabel {{
                    background-color: rgba(45, 62, 54, 1.0);
                    color: rgba(146, 208, 80, 1.0);
                    border-radius: 12px;
                    padding: 4px 8px;
                    font-size: 12px;
                }}
            """)
        elif "有更新可用" in current_status:
            self.status_label.setStyleSheet(f"""
                QLabel#StatusLabel {{
                    background-color: rgba(62, 54, 45, 1.0);
                    color: rgba(255, 193, 7, 1.0);
                    border-radius: 12px;
                    padding: 4px 8px;
                    font-size: 12px;
                }}
            """)
        elif "检查失败" in current_status:
            self.status_label.setStyleSheet(f"""
                QLabel#StatusLabel {{
                    background-color: rgba(62, 45, 45, 1.0);
                    color: rgba(255, 107, 107, 1.0);
                    border-radius: 12px;
                    padding: 4px 8px;
                    font-size: 12px;
                }}
            """)
        elif "未知" in current_status:
            self.status_label.setStyleSheet(f"""
                QLabel#StatusLabel {{
                    background-color: #2d2d3e;
                    color: #adb5bd;
                    border-radius: 12px;
                    padding: 4px 8px;
                    font-size: 12px;
                }}
            """)
        
        # 默认设置为半透明，等待数据加载后显示
        self.setWindowOpacity(0.7)
    
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
        local_version_label.setStyleSheet("color: #6c757d;")
        
        self.local_version_value = QLabel("加载中...")
        self.local_version_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        # 官网版本
        online_version_label = QLabel("官网版本:")
        online_version_label.setStyleSheet("color: #6c757d;")
        
        self.online_version_value = QLabel("加载中...")
        self.online_version_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
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
                background-color: #3773e8;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 6px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4285f4;
            }
            QPushButton:disabled {
                background-color: #adb5bd;
                color: #6c757d;
            }
        """)
        self.download_button.setVisible(False)
        
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.download_button)
        
        self.main_layout.addLayout(status_layout)
    
    def update_info(self, local_version: str, online_version: str, status: str, 
                   status_type: str, download_url: str = ""):
        """更新卡片信息"""
        # 更新版本信息
        self.local_version_value.setText(local_version or "未知")
        self.online_version_value.setText(online_version or "未知")
        
        # 更新状态标签
        self.status_label.setText(status)
        
        # 保存状态类型，用于主题变化时重新应用样式
        self.status_type = status_type
        
        # 根据状态类型设置样式
        if status_type == "up_to_date":
            self.status_label.setStyleSheet("""
                QLabel#StatusLabel {
                    background-color: #d4edda;
                    color: #155724;
                    padding: 4px 12px;
                    border-radius: 16px;
                    font-weight: 500;
                }
            """)
            self.download_button.setVisible(False)
        elif status_type == "update_available":
            self.status_label.setStyleSheet("""
                QLabel#StatusLabel {
                    background-color: #fff3cd;
                    color: #856404;
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
                    background-color: #f8d7da;
                    color: #721c24;
                    padding: 4px 12px;
                    border-radius: 16px;
                    font-weight: 500;
                }
            """)
            self.download_button.setVisible(False)
        elif status_type == "higher_version":
            self.status_label.setStyleSheet("""
                QLabel#StatusLabel {
                    background-color: #d1ecf1;
                    color: #0c5460;
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
    
    def fade_in(self):
        """淡入动画"""
        self.fade_animation.setStartValue(self.windowOpacity())
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

# ===== 自定义进度条 =====
class CustomProgressBar(QProgressBar):
    """自定义进度条"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setTextVisible(True)
        
        # 设置样式
        self.setStyleSheet("""
            QProgressBar {
                background-color: #e9ecef;
                border-radius: 10px;
                text-align: center;
                color: #495057;
                font-size: 12px;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #3773e8, stop:1 #4285f4);
                border-radius: 10px;
            }
        """)

# ===== 关于对话框 =====
class AboutDialog(QDialog):
    """关于对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于荣耀软件更新检查器")
        self.setModal(True)
        self.setFixedSize(340, 240)
        
        # 记录点击次数
        self.click_count = 0
        self.parent_window = parent
        
        # 设置窗口样式（默认浅色主题）
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
            }
            QLabel#VersionLabel {
                font-size: 14px;
                color: #3773e8;
            }
        """)
        
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
            import ctypes
            from ctypes import wintypes
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
        
        # 检查父窗口是否有主题管理器并应用深色主题样式
        if hasattr(self.parent(), 'theme_manager'):
            theme_manager = self.parent().theme_manager
            if theme_manager.is_dark_mode:
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
                # 设置标题栏颜色为浅色主题背景色
                self.set_windows_title_bar_color("#f3f3f3")
        else:
            # 默认设置为浅色主题标题栏颜色
            self.set_windows_title_bar_color("#f3f3f3")
    
    def on_version_clicked(self, event):
        """版本号点击事件处理"""
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

# ===== 手动版本输入对话框 =====
class ManualVersionDialog(QDialog):
    """手动输入版本号对话框"""
    def __init__(self, parent=None, current_versions=None):
        super().__init__(parent)
        self.setWindowTitle("调试模式 - 手动修改版本号")
        self.setModal(True)
        self.setFixedSize(360, 280)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f3f3f3;
                border-radius: 12px;
            }
            QLabel {
                color: #495057;
                font-size: 13px;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
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
        self.version_inputs = {}
        
        for app_key, app_name in service_names.items():
            input_layout = QHBoxLayout()
            input_layout.setSpacing(8)
            
            label = QLabel(f"{app_name}:")
            
            # 创建输入框并设置当前版本
            current_version = current_versions.get(app_key, "") if current_versions else ""
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
        
        # 检查父窗口是否有主题管理器并应用深色主题样式
        if hasattr(self.parent(), 'theme_manager'):
            theme_manager = self.parent().theme_manager
            if theme_manager.is_dark_mode:
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
                # 设置标题栏颜色为浅色主题背景色
                self.set_windows_title_bar_color("#f3f3f3")
        else:
            # 默认设置为浅色主题标题栏颜色
            self.set_windows_title_bar_color("#f3f3f3")

# ===== 主窗口类 =====
class MainWindow(QWidget):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        # 设置主题管理器
        self.theme_manager = ThemeManager()
        
        # 初始化样式表
        self.style_sheet = ""
        
        # 设置窗口属性
        self.setWindowTitle(f"Update Checker for HONOR MagicBook")
        self.setMinimumSize(400, 740)
        
        # 设置窗口图标
        icon_path = resource_path("resources/icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 创建定时器用于检测系统主题变化
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.check_system_theme_change)
        self.theme_timer.start(1000)  # 每秒检查一次主题变化
        
        # 加载图标路径
        self.icon_files = {
            "pc_manager": resource_path("resources/pc_manager.png"),
            "honor_workstation": resource_path("resources/honor_workstation.png"),
            "yoyo_assistant": resource_path("resources/yoyo_assistant.png")
        }
        
        # 初始化状态
        self.running = False
        self.auto_check_enabled = True
        self.check_interval = 3  # 默认每周检查
        
        # 存储手动设置的版本号
        self.manual_versions = {}
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(16)
        
        # 创建顶部区域
        self._create_header()
        
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
        
        # 应用主题
        self.apply_theme()
        
        # 如果启用了自动检查，就开始检查
        if self.auto_check_enabled:
            self.run_check()
    
    def _create_header(self):
        """创建窗口顶部区域"""
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: transparent;")
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        
        # 标题和版本
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        
        title_label = QLabel(APP_NAME)
        title_font = QFont("HONOR Sans CN", 18, QFont.Bold)
        title_font.setStyleStrategy(QFont.PreferAntialias)
        title_label.setFont(title_font)
        

        version_font = QFont("HONOR Sans CN", 10)
        version_font.setStyleStrategy(QFont.PreferAntialias)
        
        title_layout.addWidget(title_label)

        
        # 右侧按钮
        right_layout = QHBoxLayout()
        right_layout.setSpacing(8)
        
        # 通透模式按钮
        self.glass_mode_button = QToolButton()
        # 使用齿轮设置图标
        self.glass_mode_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.glass_mode_button.setToolTip("通透模式")
        self.glass_mode_button.setFixedSize(32, 32)
        self.glass_mode_button.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 16px;
                background-color: transparent;
                color: #495057;
            }
            QToolButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.glass_mode_button.clicked.connect(self.open_glass_mode)
        
        # 关于按钮
        self.about_button = QToolButton()
        self.about_button.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        self.about_button.setToolTip("关于")
        self.about_button.setFixedSize(32, 32)
        self.about_button.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 16px;
                background-color: transparent;
                color: #495057;
            }
            QToolButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.about_button.clicked.connect(self.open_about)
        
        right_layout.addWidget(self.glass_mode_button)
        right_layout.addWidget(self.about_button)
        
        # 添加到主布局
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addLayout(right_layout)
        
        self.main_layout.addWidget(header_frame)
    
    def _create_progress_bar(self):
        """创建进度条区域"""
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("ProgressFrame")
        self.progress_frame.setStyleSheet("""
            QFrame#ProgressFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e9ecef;
                padding: 16px;
                margin-top: 0;
            }
        """)
        
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        
        # 进度条标签
        self.progress_label = QLabel("准备检查更新...")
        self.progress_label.setStyleSheet("color: #495057;")
        
        # 进度条
        self.progress_bar = CustomProgressBar()
        
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
        
        # 初始设置简单样式，具体样式在apply_theme中设置
        
        # 滚动区域内容
        scroll_content = QWidget()
        self.results_layout = QVBoxLayout(scroll_content)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(8)
        
        # 添加占位符
        self.placeholder_label = QLabel("点击下方按钮开始检查更新")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("""
            color: #adb5bd;
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
        self.check_button = GradientButton("检查更新")
        self.check_button.setFixedHeight(40)
        self.check_button.setMinimumWidth(160)
        self.check_button.clicked.connect(self.run_check)
        
        # 全部展开按钮（默认隐藏）
        self.expand_button = QPushButton("全部展开")
        self.expand_button.setFixedHeight(40)
        self.expand_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 20px;
                padding: 0 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f3f3f3;
            }
        """)
        self.expand_button.setVisible(False)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.check_button)
        buttons_layout.addWidget(self.expand_button)
        buttons_layout.addStretch()
        
        self.main_layout.addWidget(buttons_frame)
    
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
            
            # 判断是否为深色背景，设置文字颜色
            # 计算颜色亮度 (0-255)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            
            # 根据背景亮度设置文字颜色
            if brightness < 128:
                text_color = wintypes.DWORD(0xFFFFFF)  # 白色
            else:
                text_color = wintypes.DWORD(0x000000)  # 黑色
            
            dwmapi.DwmSetWindowAttribute(
                HWND, 
                DWMWA_TEXT_COLOR, 
                ctypes.byref(text_color), 
                ctypes.sizeof(text_color)
            )
        except Exception as e:
            # 忽略错误，确保程序正常运行
            pass
    
    def apply_theme(self):
        """应用当前主题"""
        # 保存当前样式表
        self.style_sheet = self.theme_manager.get_style_sheet()
        
        # 应用全局样式表
        self.setStyleSheet(self.style_sheet)
        
        # 设置窗口背景色和标题栏颜色（保持一致）
        if self.theme_manager.is_dark_mode:
            bg_color = "#1e1e1e"
        else:
            bg_color = "#f3f3f3"
        
        # 设置窗口背景色
        self.setStyleSheet(self.styleSheet() + f"""
            MainWindow {{
                background-color: {bg_color};
            }}
        """)
        
        # 设置Windows标题栏颜色以匹配窗口背景
        self.set_windows_title_bar_color(bg_color)
        
        # 更新组件样式
        self._update_components_style()
    
    def check_system_theme_change(self):
        """检查系统主题是否发生变化"""
        try:
            # 保存当前主题状态
            old_is_dark_mode = self.theme_manager.is_dark_mode
            
            # 重新加载系统主题设置
            self.theme_manager.load_system_theme()
            
            # 如果主题发生变化，重新应用主题
            if old_is_dark_mode != self.theme_manager.is_dark_mode:
                self.apply_theme()
                
                # 遍历所有软件卡片，更新它们的主题
                for card in self.software_cards.values():
                    card.update_card_theme(self.theme_manager.is_dark_mode)
                    # 如果卡片可见且已显示信息，重新应用状态标签样式
                    if card.isVisible() and hasattr(card, 'status_label') and hasattr(card, 'status_type'):
                        # 获取当前状态信息
                        local_version = card.local_version_value.text() if hasattr(card, 'local_version_value') else ''
                        online_version = card.online_version_value.text() if hasattr(card, 'online_version_value') else ''
                        status = card.status_label.text()
                        status_type = getattr(card, 'status_type', 'up_to_date')
                        # 重新应用状态标签样式
                        card.update_info(local_version, online_version, status, status_type)
        except Exception:
            # 忽略错误，确保程序正常运行
            pass
            
    def _update_components_style(self):
        """更新各个组件的样式"""
        # 选项框样式
        if self.theme_manager.is_dark_mode:
            frame_bg_color = "#2d2d2d"
            frame_border_color = "#404040"
        else:
            frame_bg_color = "white"
            frame_border_color = "#e9ecef"
        # 普通模式下的样式
        options_style = f""
        options_style += f"    background-color: {frame_bg_color};\n"
        options_style += "    border-radius: 12px;\n"
        options_style += f"    border: 1px solid {frame_border_color};\n"
        options_style += "    padding: 16px;\n"
        
        # 进度框样式
        progress_style = options_style
        # 使用字符串拼接避免大括号冲突
        progress_sheet = "QFrame#ProgressFrame { " + progress_style + " margin-top: 0; }"
        self.findChild(QFrame, "ProgressFrame").setStyleSheet(progress_sheet)
        
        # 更新文字颜色
        text_color = "#495057" if not self.theme_manager.is_dark_mode else "#f3f3f3"
        info_color = "#6c757d" if not self.theme_manager.is_dark_mode else "#adb5bd"
        
        # 使用字符串拼接替代f-string以避免语法冲突
        self.progress_label.setStyleSheet("color: " + text_color + ";")
        self.placeholder_label.setStyleSheet("color: " + info_color + "; font-size: 14px; padding: 40px;")
        
        # 更新软件卡片样式
        for card in self.software_cards.values():
            card.update_card_theme(self.theme_manager.is_dark_mode)
        
        # 更新下载按钮样式
        border_color = "#dee2e6" if not self.theme_manager.is_dark_mode else "#404040"
        bg_color = "white" if not self.theme_manager.is_dark_mode else "#2d2d2d"
        hover_color = "#f3f3f3" if not self.theme_manager.is_dark_mode else "#3a3a3a"
        
        # 构建样式表字符串
        style_sheet = ""
        style_sheet += "QPushButton {\n"
        style_sheet += "    background-color: " + bg_color + ";\n"
        style_sheet += "    color: " + text_color + ";\n"
        style_sheet += "    border: 1px solid " + border_color + ";\n"
        style_sheet += "    border-radius: 20px;\n"
        style_sheet += "    padding: 0 16px;\n"
        style_sheet += "    font-size: 13px;\n"
        style_sheet += "}\n"
        style_sheet += "QPushButton:hover {\n"
        style_sheet += "    background-color: " + hover_color + ";\n"
        style_sheet += "}"
        
        self.expand_button.setStyleSheet(style_sheet)
        
        # 更新滚动条样式（隐藏滚动条）
        if not self.theme_manager.is_dark_mode:
            # 浅色模式滚动条样式 - 隐藏滚动条
            scrollbar_style = """
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    width: 0px;
                    background-color: transparent;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background-color: transparent;
                    width: 0px;
                }
                QScrollBar::add-line:vertical,
                QScrollBar::sub-line:vertical {
                    height: 0px;
                    subcontrol-origin: margin;
                }
            """
        else:
            # 深色模式滚动条样式 - 隐藏滚动条
            scrollbar_style = """
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    width: 0px;
                    background-color: transparent;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background-color: transparent;
                    width: 0px;
                }
                QScrollBar::add-line:vertical,
                QScrollBar::sub-line:vertical {
                    height: 0px;
                    subcontrol-origin: margin;
                }
            """
        
        self.scroll_area.setStyleSheet(scrollbar_style)

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
    
    def on_check_complete(self):
        """检查完成后的处理"""
        self.running = False
        self.check_button.setEnabled(True)
        self.check_button.setText("检查更新")
        
        # 隐藏进度条
        self.progress_frame.setVisible(False)

    def switch_to_glass_mode(self):
        """切换到通透模式，修改配置文件并重启应用"""
        # 显示确认对话框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认切换")
        msg_box.setText("确定要切换到通透模式吗？\n切换后将关闭当前窗口并重启应用。")
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
                    "preferred_mode": "glass",
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
                self.show_message("错误", f"无法切换到通透模式: {str(e)}", QMessageBox.Critical)

    def open_glass_mode(self):
        """打开通透模式窗口，添加确认对话框并保存配置"""
        # 显示确认对话框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认切换")
        msg_box.setText("确定要切换到通透模式吗？\n切换后将关闭当前窗口并重启应用。")
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
                    "preferred_mode": "glass",
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
                self.show_message("错误", f"无法切换到通透模式: {str(e)}", QMessageBox.Critical)
    
    def show_message(self, title: str, message: str, icon_type: int):
        """显示消息对话框"""
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
            # 设置标题栏颜色为浅色主题背景色
            self._set_message_box_title_bar_color(msg_box, "#f3f3f3")
        
        msg_box.exec()
    
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

# ===== 主函数 =====
def main():
    """应用程序入口"""
    import json
    import sys  # 确保sys在函数内部可用
    
    # 检查用户配置，决定启动哪种模式
    config_path = get_config_path()
    preferred_mode = 'normal'  # 默认普通模式
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                preferred_mode = config.get('preferred_mode', 'normal')
        except Exception:
            # 配置文件读取失败，使用默认值
            preferred_mode = 'normal'
    
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont("HONOR Sans CN", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    
    # 根据用户偏好启动相应模式
    if preferred_mode == 'glass':
        # 直接启动通透模式
        import subprocess
        try:
            subprocess.Popen([sys.executable, 'main_transparency.py'])
            # 不显示普通窗口，直接退出
            return
        except Exception:
            # 如果通透模式启动失败，回退到普通模式
            pass
    
    # 创建并显示主窗口（普通模式）
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
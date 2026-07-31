# update_checker.py
# 应用自身更新检查模块
# 通过 GitHub 仓库托管的 version.json 获取最新版本信息
# 优先直连 raw.githubusercontent.com（实时同步，无长缓存），
# jsDelivr CDN 作为国内网络不佳时的回退
import os
import json
import time
import ctypes
from ctypes import wintypes
from datetime import datetime
from typing import Optional, Dict, Tuple

import requests
import certifi

# 设置 TLS 证书路径，解决打包后的 TLS 错误
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QFont, QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QApplication
)

# ===== 配置（GitHub 仓库地址）=====
# 主地址：直连 GitHub raw（实时同步仓库内容，无长缓存问题）
UPDATE_CHECK_URL = "https://raw.githubusercontent.com/HUANCHUAN/CheckUpdate_for_HONOR_MagicBook/main/version.json"
# 备用地址：jsDelivr CDN（国内有节点，但分支引用缓存更新较慢，作为回退）
UPDATE_CHECK_URL_FALLBACK = "https://cdn.jsdelivr.net/gh/HUANCHUAN/CheckUpdate_for_HONOR_MagicBook@main/version.json"
REQUEST_TIMEOUT = 10  # 秒


def _build_cache_busting_url(base_url: str) -> str:
    """为 URL 添加时间戳查询参数，避免任何中间层（代理、CDN）缓存。

    raw.githubusercontent.com 本身实时返回仓库内容，但用户所在网络
    可能有透明代理缓存，加时间戳可彻底绕过。
    """
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}_t={int(time.time())}"


# ===== 版本比较工具 =====
def parse_version_tuple(version_str: str) -> Tuple[int, ...]:
    """将版本号字符串解析为整数元组，便于比较。

    例如 '11.0.0.17' -> (11, 0, 0, 17)
    非数字段按 0 处理，空字符串返回 (0,)。
    """
    if not version_str:
        return (0,)
    parts = []
    for segment in version_str.strip().split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0,)


def compare_versions(current: str, latest: str) -> int:
    """比较两个版本号。

    返回:
        1  表示 latest > current（有更新可用）
        0  表示两者相同
        -1 表示 current > latest（当前版本更高）
    """
    current_tuple = parse_version_tuple(current)
    latest_tuple = parse_version_tuple(latest)
    # 补齐长度使其一致
    max_length = max(len(current_tuple), len(latest_tuple))
    current_tuple = current_tuple + (0,) * (max_length - len(current_tuple))
    latest_tuple = latest_tuple + (0,) * (max_length - len(latest_tuple))
    if latest_tuple > current_tuple:
        return 1
    elif latest_tuple == current_tuple:
        return 0
    else:
        return -1


# ===== 远程获取 =====
def fetch_latest_version() -> Optional[Dict]:
    """拉取远程 version.json。

    优先直连 raw.githubusercontent.com（实时同步仓库内容），
    失败则回退到 jsDelivr CDN（国内网络不佳时使用）。
    所有请求添加时间戳查询参数，避免中间代理/CDN缓存。
    返回解析后的 dict，或 None（全部失败时）。
    """
    for base_url in (UPDATE_CHECK_URL, UPDATE_CHECK_URL_FALLBACK):
        try:
            url = _build_cache_busting_url(base_url)
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            # 校验必要字段
            if "version" in data:
                return data
        except Exception:
            continue
    return None


# ===== 检查入口（纯逻辑，无 UI）=====
def check_for_update(current_version: str) -> Dict:
    """检查应用自身是否有新版本。

    参数:
        current_version: 当前应用版本号，如 "11.0.0.17"

    返回字典结构:
        {
            "has_update": bool,          # 是否有更新
            "latest_version": str,       # 最新版本号
            "release_notes": str,        # 更新日志
            "download_url": str,         # 下载页面链接
            "release_date": str,         # 发布日期
            "error": str                 # 错误信息（无错误为空字符串）
        }
    """
    result = {
        "has_update": False,
        "latest_version": "",
        "release_notes": "",
        "download_url": "",
        "release_date": "",
        "error": ""
    }

    latest_info = fetch_latest_version()
    if latest_info is None:
        result["error"] = "无法获取版本信息，请检查网络连接"
        return result

    latest_version = latest_info.get("version", "")
    result["latest_version"] = latest_version
    result["release_notes"] = latest_info.get("release_notes", "")
    result["download_url"] = latest_info.get(
        "download_url",
        "https://github.com/HUANCHUAN/CheckUpdate_for_HONOR_MagicBook/releases/latest"
    )
    result["release_date"] = latest_info.get("release_date", "")

    if not latest_version:
        result["error"] = "版本信息格式错误"
        return result

    comparison = compare_versions(current_version, latest_version)
    result["has_update"] = (comparison == 1)
    return result


# ===== 更新可用对话框（带主题适配）=====
class UpdateAvailableDialog(QDialog):
    """发现新版本时弹出的对话框。

    通过传入 theme_manager 适配深色/浅色模式（与现有对话框主题模式一致）。
    包含: 应用图标、当前版本→最新版本、更新日志(可滚动)、"前往下载"按钮。
    """
    def __init__(self, parent, update_info: Dict, current_version: str,
                 theme_manager=None, icon_path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("发现新版本")
        self.setModal(True)
        self.setFixedSize(380, 420)

        self.update_info = update_info
        self.current_version = current_version
        self.theme_manager = theme_manager
        self.icon_path = icon_path

        # 判断是否深色模式
        self.is_dark_mode = False
        if theme_manager and hasattr(theme_manager, "is_dark_mode"):
            self.is_dark_mode = theme_manager.is_dark_mode

        self._init_ui()
        self._apply_theme()

    def _init_ui(self):
        """初始化界面"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(12)

        # 顶部图标
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        if self.icon_path and os.path.exists(self.icon_path):
            pixmap = QPixmap(self.icon_path)
            self.icon_label.setPixmap(
                pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        # 标题
        self.title_label = QLabel("发现新版本！")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("HONOR Sans CN", 15, QFont.Bold)
        title_font.setStyleStrategy(QFont.PreferAntialias)
        self.title_label.setFont(title_font)

        # 版本对比
        latest_version = self.update_info.get("latest_version", "")
        self.version_label = QLabel(
            f"当前 {self.current_version}  →  最新 {latest_version}"
        )
        self.version_label.setObjectName("VersionLabel")
        self.version_label.setAlignment(Qt.AlignCenter)
        version_font = QFont("HONOR Sans CN", 11)
        version_font.setStyleStrategy(QFont.PreferAntialias)
        self.version_label.setFont(version_font)

        # 发布日期
        release_date = self.update_info.get("release_date", "")
        if release_date:
            self.date_label = QLabel(f"发布日期：{release_date}")
            self.date_label.setAlignment(Qt.AlignCenter)
            self.date_label.setObjectName("DateLabel")
        else:
            self.date_label = QLabel("")
            self.date_label.setObjectName("DateLabel")

        # 更新日志（可滚动）
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(160)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(12, 10, 12, 10)
        scroll_layout.setSpacing(4)

        self.notes_label = QLabel(self.update_info.get("release_notes", "暂无更新日志"))
        self.notes_label.setObjectName("NotesLabel")
        self.notes_label.setWordWrap(True)
        self.notes_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        notes_font = QFont("HONOR Sans CN", 10)
        notes_font.setStyleStrategy(QFont.PreferAntialias)
        self.notes_label.setFont(notes_font)

        scroll_layout.addWidget(self.notes_label)
        scroll_layout.addStretch()
        self.scroll_area.setWidget(scroll_content)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.later_button = QPushButton("以后再说")
        self.later_button.setFixedHeight(34)
        self.later_button.setCursor(Qt.PointingHandCursor)
        self.later_button.clicked.connect(self.reject)

        self.download_button = QPushButton("前往下载")
        self.download_button.setFixedHeight(34)
        self.download_button.setMinimumWidth(120)
        self.download_button.setCursor(Qt.PointingHandCursor)
        self.download_button.clicked.connect(self._on_download_clicked)

        button_layout.addStretch()
        button_layout.addWidget(self.later_button)
        button_layout.addWidget(self.download_button)

        # 组装
        self.main_layout.addWidget(self.icon_label)
        self.main_layout.addWidget(self.title_label)
        self.main_layout.addWidget(self.version_label)
        self.main_layout.addWidget(self.date_label)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addLayout(button_layout)

    def _apply_theme(self):
        """根据主题应用样式"""
        if self.is_dark_mode:
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
                    color: #ffffff;
                }
                QLabel#VersionLabel {
                    color: #4285f4;
                }
                QLabel#DateLabel {
                    color: #adb5bd;
                    font-size: 11px;
                }
                QScrollArea {
                    background-color: #1e1e1e;
                    border: 1px solid #404040;
                    border-radius: 6px;
                }
                QLabel#NotesLabel {
                    color: #d3d3d3;
                    background-color: transparent;
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
                QPushButton#later_button {
                    background-color: #3d3d3d;
                    color: #f3f3f3;
                    border: 1px solid #4d4d4d;
                }
                QPushButton#later_button:hover {
                    background-color: #4a4a4a;
                }
            """)
            self.later_button.setObjectName("later_button")
            self._set_windows_title_bar_color("#2d2d2d")
        else:
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
                    color: #212529;
                }
                QLabel#VersionLabel {
                    color: #3773e8;
                }
                QLabel#DateLabel {
                    color: #6c757d;
                    font-size: 11px;
                }
                QScrollArea {
                    background-color: #ffffff;
                    border: 1px solid #e9ecef;
                    border-radius: 6px;
                }
                QLabel#NotesLabel {
                    color: #495057;
                    background-color: transparent;
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
                QPushButton#later_button {
                    background-color: #ffffff;
                    color: #495057;
                    border: 1px solid #dee2e6;
                }
                QPushButton#later_button:hover {
                    background-color: #f3f3f3;
                }
            """)
            self.later_button.setObjectName("later_button")
            self._set_windows_title_bar_color("#f3f3f3")

    def _set_windows_title_bar_color(self, hex_color: str):
        """设置 Windows 窗口标题栏颜色和文字颜色"""
        try:
            hex_color = hex_color.lstrip('#')
            red = int(hex_color[0:2], 16)
            green = int(hex_color[2:4], 16)
            blue = int(hex_color[4:6], 16)

            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            hwnd = self.winId()
            dwmapi = ctypes.WinDLL('dwmapi')

            color_value = wintypes.DWORD((blue << 16) | (green << 8) | red)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_CAPTION_COLOR,
                ctypes.byref(color_value),
                ctypes.sizeof(color_value)
            )

            brightness = (red * 299 + green * 587 + blue * 114) / 1000
            if brightness < 128:
                text_color = wintypes.DWORD(0xFFFFFF)
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_TEXT_COLOR,
                    ctypes.byref(text_color),
                    ctypes.sizeof(text_color)
                )
        except Exception:
            pass

    def _on_download_clicked(self):
        """点击前往下载按钮，在浏览器打开下载页面"""
        download_url = self.update_info.get("download_url", "")
        if download_url:
            QDesktopServices.openUrl(QUrl(download_url))
        self.accept()

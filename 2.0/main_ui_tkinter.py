# HUANCHUAN with Copilot  版本号：2.0.0
# 说明：此版本不会识别补丁包版本。一般官网发布版本已合入最新补丁，识别补丁包版本意义不大，且容易造成bug
# 实测荣耀 MagicBook Pro 16 使用完全正常，如有 bug 可以 QQ 搜索 HUANCHUAN 联系反馈，谢谢！
# 此为开源项目，允许分发，但请作出一定说明，谢谢！

import os
import re
import winreg
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import tkinter as tk
import threading

# ===== 原有逻辑部分 =====
names = {
    "pc_manager": "荣耀电脑管家",
    "honor_workstation": "荣耀超级工作台",
    "yoyo_assistant": "荣耀 YOYO 助理"
}

def get_local_version(xml_path):
    if os.path.exists(xml_path):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            version_elem = root.find(".//version")
            if version_elem is not None:
                return version_elem.text.strip()
        except Exception as e:
            return f"读取版本号失败: {e}"
    return None

def get_registry_version(path, value_name):
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        value, _ = winreg.QueryValueEx(key, value_name)
        winreg.CloseKey(key)
        return value.strip()
    except Exception as e:
        return f"读取版本号失败: {e}"

installed_versions = {
    "pc_manager": get_local_version(r"C:\Program Files\HONOR\PCManager\config\product_adapter_version.xml"),
    "honor_workstation": get_registry_version(r"SOFTWARE\HONOR\Hihonornote", "HonorWorkStationVersion"),
    "yoyo_assistant": get_local_version(r"C:\Program Files\HONOR\HNMagicAI\config\product_adapter_version.xml")
}

pages = {
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

def version_tuple(v):
    return tuple(int(x) for x in v.strip().split(".") if x.isdigit())

def clean_version(v, remove_patch=True):
    v = v.replace("Version", "").replace("版本", "").strip()
    if remove_patch:
        v = re.sub(r"\(.*?\)", "", v).strip()
    return v

# ===== UI部分 =====
anim_running = False
anim_index = 0
anim_texts = ["检测中.", "检测中..", "检测中..."]

def safe_ui_append(text):
    def _append():
        output_box.config(state="normal")  # 临时启用编辑
        output_box.insert(tk.END, text)
        output_box.config(state="disabled")  # 再禁用
    root.after(0, _append)

def animate_button():
    global anim_index
    if anim_running:
        check_btn.config(text=anim_texts[anim_index])
        anim_index = (anim_index + 1) % len(anim_texts)
        root.after(500, animate_button)

def check_task():
    root.after(0, lambda: (
        output_box.config(state="normal"),
        output_box.delete(1.0, tk.END),
        output_box.insert(tk.END, "🔛 程序开始运行啦！\n\n"),
        output_box.config(state="disabled")
    ))

    for key, info in pages.items():
        try:
            res = requests.get(info["url"], timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            tag, cls = info["selector"]
            element = soup.find(tag, class_=cls)

            if not element:
                safe_ui_append(f"[{key}] 未找到 {names[key]} 的版本号元素\n\n")
                continue

            latest_version_text = element.get_text(strip=True)
            version_display = clean_version(latest_version_text.split("|")[0], remove_patch=False)
            version_compare = clean_version(version_display, remove_patch=True)

            local_ver = installed_versions.get(key, "")
            local_ver_compare = clean_version(local_ver or "", remove_patch=True)

            safe_ui_append(f"[{key}] 本地版本：{local_ver or '未知'} 官网版本：{version_display}\n")

            if not local_ver:
                safe_ui_append(f"⚠️ 未获取到 {names[key]} 的本地版本号，官网最新版本是 {version_display}\n🔗 {info['url']}\n\n")
                continue

            if version_tuple(local_ver_compare) == version_tuple(version_compare):
                safe_ui_append(f"✅ {names[key]} 已是最新版本\n\n")
            elif version_tuple(local_ver_compare) < version_tuple(version_compare):
                safe_ui_append(f"⚠️ {names[key]} 有新版本！ {local_ver} -> {version_display}\n🔗 {info['url']}\n\n")
            else:
                safe_ui_append(f"ℹ️ 当前本地安装的 {names[key]} 版本高于官网版本，或为测试版\n🔗 {info['url']}\n\n")

        except Exception as e:
            safe_ui_append(f"[{key}] 检查更新失败: {e}\n\n")

    def finish_ui():
        global anim_running
        anim_running = False
        check_btn.config(text="开始检测", state="normal")
    root.after(0, finish_ui)

def run_check():
    global anim_running
    if anim_running:
        return
    anim_running = True
    check_btn.config(state="disabled")
    animate_button()
    threading.Thread(target=check_task, daemon=True).start()

# ===== 创建窗口 =====
root = tk.Tk()
root.title("Update Checker for HONOR MagicBook")
root.geometry("600x380")
root.configure(bg="#ffffff")
root.resizable(False, False)

# 输出框
common_border = {
    "bd": 0,
    "relief": "solid",
    "highlightthickness": 1,
    "highlightbackground": "#666666",
    "highlightcolor": "#666666"

}

output_box = tk.Text(root,
                     wrap=tk.WORD,
                     font=("Microsoft YaHei", 10),
                     state="disabled",
                     bg="#ffffff",
                     **common_border)
output_box.place(x=20, y=20, width=560, height=320)

# 检查按钮
check_btn = tk.Button(root, text="开始检测", command=run_check, bg="#4CAF50", fg="white", relief="flat", font=("Microsoft YaHei", 10))
check_btn.place(x=250, y=347, width=100, height=25)


root.mainloop()

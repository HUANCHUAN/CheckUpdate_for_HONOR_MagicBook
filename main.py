# HUANCHUAN with Copilot
# 说明：此版本忽略识别补丁包版本。一般官网发布版本已合入最新补丁，识别补丁包版本意义不大，且容易造成bug
# 实测荣耀 MagicBook Pro 16 使用完全正常，如有 bug 可以 QQ 搜索 HUANCHUAN 联系反馈，谢谢！

import os
import re
import msvcrt
import winreg
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# 中文名称映射
names = {
    "pc_manager": "荣耀电脑管家",
    "honor_workstation": "荣耀超级工作台",
    "yoyo_assistant": "荣耀 YOYO 助理"
}

# 读取版本号（XML）
def get_local_version(xml_path):
    if os.path.exists(xml_path):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            version_elem = root.find(".//version")
            if version_elem is not None:
                return version_elem.text.strip()
        except Exception as e:
            print(f"读取版本号失败: {e}")
    return None

# 读取版本号（注册表）
def get_registry_version(path, value_name):
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        value, _ = winreg.QueryValueEx(key, value_name)
        winreg.CloseKey(key)
        return value.strip()
    except Exception as e:
        print(f"读取版本号失败: {e}")
        return None

# 本地版本号
installed_versions = {
    "pc_manager": get_local_version(r"C:\Program Files\HONOR\PCManager\config\product_adapter_version.xml"),
    "honor_workstation": get_registry_version(r"SOFTWARE\HONOR\Hihonornote", "HonorWorkStationVersion"),
    "yoyo_assistant": get_local_version(r"C:\Program Files\HONOR\HNMagicAI\config\product_adapter_version.xml")
}

# 官网页面与定位器
pages = {
    "pc_manager": {
        "url": "https://www.honor.com/cn/tech/pc-manager/",
        "selector": ("p", "path")  # class=path
    },
    "honor_workstation": {
        "url": "https://www.honor.com/cn/tech/honor-workstation/",
        "selector": ("div", "btn-text")  # class=btn-text
    },
    "yoyo_assistant": {
        "url": "https://www.honor.com/cn/tech/pc-yoyo-assistant-2/",
        "selector": ("p", "path")  # class=path
    }
}

# 版本号比较方法
def version_tuple(v):
    return tuple(int(x) for x in v.strip().split(".") if x.isdigit())

# 清理版本号（去掉前缀和补丁包）
def clean_version(v, remove_patch=True):
    v = v.replace("Version", "").replace("版本", "").strip()
    if remove_patch:
        v = re.sub(r"\(.*?\)", "", v).strip()
    return v

print("\n🔛 程序开始运行啦！\n")

# 主循环
for key, info in pages.items():
    try:
        res = requests.get(info["url"], timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        tag, cls = info["selector"]
        element = soup.find(tag, class_=cls)

        if not element:
            print(f"[{key}] 未找到 {names[key]} 的版本号元素\n")
            continue

        latest_version_text = element.get_text(strip=True)

        # 显示用版本（保留补丁包）
        version_display = clean_version(latest_version_text.split("|")[0], remove_patch=False)

        # 比较用版本（去掉补丁包）
        version_compare = clean_version(version_display, remove_patch=True)

        # 本地版本（去掉补丁包）
        local_ver = installed_versions.get(key, "")
        local_ver_compare = clean_version(local_ver or "", remove_patch=True)

        print(f"[{key}] 本地版本：{local_ver or '未知'} 官网版本：{version_display}")

        if not local_ver:
            print(f"⚠️ 未获取到 {names[key]} 的本地版本号，官网最新版本是 {version_display}")
            print(f"🔗 官网链接: {info['url']}\n")
            continue

        if version_tuple(local_ver_compare) == version_tuple(version_compare):
            print(f"✅ {names[key]} 已是最新版本\n")
        elif version_tuple(local_ver_compare) < version_tuple(version_compare):
            print(f"⚠️ {names[key]} 有新版本！ {local_ver} -> {version_display}")
            print(f"🔗 下载链接: {info['url']}\n")
        else:
            print(f"ℹ️ 当前本地安装的 {names[key]} 版本高于官网版本，或为测试版，")
            print(f"🔗 官网链接: {info['url']}\n")

    except Exception as e:
        print(f"[{key}] 检查更新失败: {e}\n")

print("按任意键退出...（注：按下 Ctrl+C 不会退出）") # 如直接使用 IDE 运行，建议删除以下代码或运行后手动停止
while True:
    key = msvcrt.getch()
    break

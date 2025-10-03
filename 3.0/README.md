# CheckUpdate_for_HONOR_MagicBook 3.0.0

## 📌 简介
这是一个基于 **Python + PySide6** 框架开发的 Windows 桌面工具，用于检测部分新款 HONOR MagicBook 中预装的以下三款应用的更新情况：
- 荣耀电脑管家
- 荣耀超级工作台
- 荣耀 YOYO 助理

本工具会自动读取本地安装版本，与荣耀官网最新版本进行对比，并提示是否需要更新。

---

## ✨ 功能特点
- 自动获取三款应用的本地版本与官网最新版本
- 对比版本号并提示更新情况
- 提供官网下载链接
- 界面更精美

---

## 📥 下载与运行
1. 前往 Release 页面下载最新的压缩包，在3.0的文件夹中有 `CheckUpdate_for_HONOR_MagicBook 3.0.0.exe` 文件
2. 双击运行即可（无需额外安装 Python）
3. 如果运行提示缺少运行库，请安装 [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/zh-cn/cpp/windows/latest-supported-vc-redist)

---

## 🖼 使用示例
🔛 程序开始运行啦！  

[pc_manager] 本地版本：20.0.0.31(SP5C233) 官网版本：20.0.0.31 (SP5)  
✅ 荣耀电脑管家 已是最新版本  

[honor_workstation] 本地版本：5.5.1.42(SP4) 官网版本：5.5.1.48  
⚠️ 荣耀超级工作台 有新版本！ 5.5.1.42(SP4) -> 5.5.1.48  
🔗 下载链接: https://www.honor.com/cn/tech/honor-workstation/  

[yoyo_assistant] 本地版本：10.0.1.16(SP2) 官网版本：9.0.2.42 (SP10)  
ℹ️ 荣耀 YOYO 助理 当前本地安装版本或为测试版，版本高于官网版本  
🔗 官网链接: https://www.honor.com/cn/tech/pc-yoyo-assistant-2/  

---

## ⚠️ 注意事项
- 本工具仅适配部分 HONOR MagicBook 机型，其他电脑可能无法正常使用
- 需要联网才能获取官网版本信息，否则显示报错信息
- 如果官网页面结构变化，可能会导致检测失败，请联系作者适配
- `.exe` 文件可能会被杀毒软件误报，请自行判断是否信任

---

## 📄 许可证
本工具仅供学习和交流使用，禁止用于商业用途。

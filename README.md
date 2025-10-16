# CheckUpdate_for_HONOR_MagicBook

## 📌 项目简介
**CheckUpdate_for_HONOR_MagicBook** 是由 Copilot 与 HUANCHUAN 共创的工具，使用 Python 开发，用于检测部分新款 HONOR MagicBook 的以下三款应用的更新情况：
- 荣耀电脑管家
- 荣耀超级工作台
- 荣耀 YOYO 助理

此工具会自动读取以上三款应用的本地安装版本，与荣耀官网最新版本进行对比，并提示是否需要更新，帮助用户快速获取最新版本信息。

---

## 📜 项目背景
用户使用 HONOR MagicBook 需要手动检查部分预装软件工具的更新。本项目旨在提供一个自动化检测工具，减少人工操作，提高更新效率。

---

## ✨ 功能特点
- 自动获取三款目标应用的本地版本与官网最新版本
- 对比版本号并提示更新情况
- 提供官网下载链接
- 轻量、易用、可扩展性强
- 支持命令行版（1.0）和桌面版（2.0）

---

## 📦 版本演进
| 版本 | 框架 | 特点 |
|------|------|------|
| **0.0.x** | 纯 Python 命令行 | 未公开，此版本通过 Selenium 实现，目前已弃项，转为 1.0 版本 |
| **1.0.x** | 纯 Python 命令行 | 已公开，无 UI，直接在终端输出检测结果，依赖少，运行快 |
| **2.0.x** | Tkinter 桌面版 | 已公开，轻量 GUI，直接下载打开 .exe 文件即可运行 |
| **3.0.x** | PySide 桌面版 | 已公开，支持 Windows 深色模式，仿照官方设计|
| **10.0.x** | PySide 桌面版 | 已公开，卡片化设计，类 MagicOS 10 通透模式 |

> 1. 各版本的详细 README 位于对应版本文件夹中。
> 2. 以上已公开版本若无明显问题将不再更新。  
> 3. 如需体验 Beta 版本请 QQ 联系 HUANCHUAN 获取。

---

## 📥 下载与运行
### 方式一：直接运行 `.exe`（推荐不熟悉编程的用户使用，仅限2.0及以上版本）
1. 前往 [Releases](../../releases) 页面下载最新版本的压缩包，运行里面的 `.exe` 文件
2. 双击运行即可（无需安装 Python）
3. 如果运行提示缺少运行库，请安装 [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/zh-cn/cpp/windows/latest-supported-vc-redist)
4. 若提示 Windows 已保护你的电脑，点击 **更多信息 > 仍要运行** 即可

### 方式二：源码运行（欢迎开发者寻找问题）
1. 克隆仓库：
   ```bash
   git clone https://github.com/HUANCHUAN/CheckUpdate_for_HONOR_MagicBook.git
   cd CheckUpdate_for_HONOR_MagicBook
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
3. 运行：
   ```bash
   python main.py

## 🖼 使用示例（不同版本略有差异，请以实际为准）

**1.0-2.0：**  

🔛 程序开始运行啦！  

[pc_manager] 本地版本：20.0.0.31(SP5C233) 官网版本：20.0.0.31 (SP5)  
✅ 荣耀电脑管家 已是最新版本  

[honor_workstation] 本地版本：5.5.1.42(SP4) 官网版本：5.5.1.48  
⚠️ 荣耀超级工作台 有新版本！ 5.5.1.42(SP4) -> 5.5.1.48  
🔗 下载链接: https://www.honor.com/cn/tech/honor-workstation/  

[yoyo_assistant] 本地版本：10.0.1.16(SP2) 官网版本：9.0.2.42 (SP10)  
ℹ️ 荣耀 YOYO 助理 当前本地安装版本或为测试版，版本高于官网版本  
🔗 官网链接: https://www.honor.com/cn/tech/pc-yoyo-assistant-2/  


**3.0：**

<img width="64" height="64" alt="pc_manager" src="https://github.com/user-attachments/assets/10ee0a39-c3e8-4c9e-b431-a4ab9dfadafb" />  

荣耀电脑管家  
当前版本：20.0.0.31(SP5C233)  
官网版本：20.0.0.31 (SP5)  
✅已是最新版本  

<img width="64" height="64" alt="honor_workstation" src="https://github.com/user-attachments/assets/c818ea1d-6e99-4ff4-b9ad-49c8978c7f55"/>  

荣耀超级工作台  
当前版本：5.5.1.42(SP4)  
官网版本：5.5.1.48  
⚠️荣耀超级工作台有新版本！5.5.1.42(SP4) -> 5.5.1.48  
[下载链接](https://www.honor.com/cn/tech/honor-workstation/)  

<img width="64" height="64" alt="yoyo_assistant" src="https://github.com/user-attachments/assets/602c3da6-2e92-4f74-a049-27fd262cb91e"/>  

荣耀 YOYO 助理  
当前版本：10.0.1.16(SP2)   
官网版本：9.0.2.42 (SP10)  
ℹ️当前版本高于官网版本，或为测试版  
[官网链接](https://www.honor.com/cn/tech/pc-yoyo-assistant-2/)  

<img width="371" height="639.5" alt="image" src="https://github.com/user-attachments/assets/67a7cf52-466d-4747-bed5-4962e413356f"/>  

## 📂 项目结构
CheckUpdate_for_HONOR_MagicBook/  
├── 1.0/ ------------ # Python 命令行版  
├── 2.0/ ------------ # Tkinter 桌面版  
├── 3.0/ ------------ # PySide6 桌面版 
├── 10.0/ ----------- # PySide6 桌面版 
├── README.md ------- # 项目总说明（当前文件）  
└── LICENSE --------- # 开源许可证  

## 📄 许可证
本项目采用 MIT License 开源协议，允许自由使用、修改和分发，但需保留版权声明。此外，本项目仅供学习和交流使用，禁止用于商业用途。

## 🤝 特别鸣谢
- Copilot 提供代码辅助与优化
- HUANCHUAN 负责项目设计与测试

## ⚠️ 注意事项
- 本工具仅适配部分 HONOR MagicBook 机型，其他电脑可能无法正常使用
- 需要联网才能获取官网版本信息
- 如果官网页面结构变化，可能会导致检测失败，请 QQ 联系 HUANCHUAN 做适配处理
- .exe 文件可能会被杀毒软件误报，请自行判断是否信任
- 若提示以下内容，点击**更多信息 > 仍要运行**即可  
<img width="436" height="408" alt="Windows 已保护你的电脑" src="https://github.com/user-attachments/assets/8f98381d-959c-46ef-aaa7-371ba1400945" />

# CheckUpdate_for_HONOR_MagicBook

这是 Copilot 与 HUANCHUAN 共创的 Python 工具，用于检测部分新款 HONOR MagicBook 的荣耀电脑管家、荣耀超级工作台、荣耀 YOYO 助理等三款应用的更新，帮助用户快速获取官网是否有新版本可用。

## ✨ 功能特点
- 自动获取三款目标应用的本地最新版本信息
- 对比本地版本与官网最新版本
- 提示是否需要更新
- 轻量、易用、可扩展

## 📝 使用示例
[pc_manager] 本地版本：20.0.0.31(SP5C233) 官网版本：20.0.0.31 (SP5)
✅ 荣耀电脑管家 已是最新版本

[honor_workstation] 本地版本：5.5.1.42(SP4) 官网版本：5.5.1.48
⚠️ 荣耀超级工作台 有新版本！ 5.5.1.42(SP4) -> 5.5.1.48 /n
🔗 下载链接: https://www.honor.com/cn/tech/honor-workstation/

[yoyo_assistant] 本地版本：10.0.1.16(SP2) 官网版本：9.0.2.42 (SP10)
ℹ️ 荣耀 YOYO 助理 当前本地安装版本或为测试版，版本高于官网版本
🔗 官网链接: https://www.honor.com/cn/tech/pc-yoyo-assistant-2/

## 📦 环境要求
- Python 3.8 及以上版本（推荐3.12、3.13，测试无问题）
- Windows 11 系统（为部分新款 HONOR MagicBook 适配，其他品牌电脑可能无法正常使用）
- 网络连接（用于获取最新版本信息）

## 🔧 安装与运行
1. **克隆仓库**
   ```bash
   git clone https://github.com/HUANCHUAN/CheckUpdate_for_HONOR_MagicBook.git
   cd CheckUpdate_for_HONOR_MagicBook
4. **安装依赖**
   ```bash
   pip install -r requirements.txt
4. **运行程序**
   ```bash
   python main.py

## 📂 项目结构
CheckUpdate_for_HONOR_MagicBook/
├── main.py              # 主程序入口
├── requirements.txt     # 依赖列表
├── README.md            # 项目说明
└── LICENSE              # 开源许可证

## 📄 许可证
本项目采用 MIT License 开源协议，允许自由使用、修改和分发，但需保留版权声明。

## 🤝 特别鸣谢
Copilot 提供代码辅助，部分代码由其编写、优化。

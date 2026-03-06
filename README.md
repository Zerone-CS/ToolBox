# 🐛 Worm - 命令行文件快传工具

[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 通过邮件快速发送文件或目录的轻量级命令行工具

## 💡 为什么需要 Worm？

### 传统文件传输的痛点

**场景 1：深夜修 Bug，需要把服务器日志发给同事**
```bash
# 传统方式：
# 1. scp 下载到本地（记不住参数，Google 一下）
# 2. 打开邮箱客户端或网页
# 3. 新建邮件，填写收件人、主题
# 4. 点击附件按钮，浏览文件
# 5. 等待上传，点击发送
# 耗时：3-5 分钟 😫

# 使用 Worm：
worm /var/log/app.log colleague@company.com
# 耗时：5 秒 ✨
```

**场景 2：在 Linux 服务器上，想把项目代码发给自己**
```bash
# 传统方式：
# - scp？参数太复杂，本地 IP 是多少来着？
# - 网盘？服务器没装客户端，网页版又被防火墙拦了
# - U 盘？这是云服务器，没有 USB 接口...
# 最后：算了，手动复制粘贴到邮件正文吧（格式全乱了）😭

# 使用 Worm：
worm ./my_project myemail@gmail.com
# 自动打包 ZIP，直接发送，完美！✨
```

**场景 3：客户催要文档，你在咖啡厅用手机热点办公**
```bash
# 传统方式：
# - 网盘上传？4G 信号不稳定，上传到 50% 断了，重新来...
# - 微信传文件？文件太大，压缩画质还被压缩
# - QQ？手机上没装，下载要 200MB
# 10 分钟过去了，客户发来：？？？😰

# 使用 Worm：
worm ./proposal.pdf client@company.com
# 邮件发送稳定可靠，断点续传，客户秒收 ✨
```

**场景 4：公司内网环境，外部工具全被禁**
```bash
# 被禁用的工具：
# ❌ 百度网盘 - 禁止访问外部网盘
# ❌ 微信/QQ - 禁止安装即时通讯工具
# ❌ GitHub - 代码托管平台被墙
# ✅ 邮件 - 唯一可用的通信方式

# 但是...
# 手动发邮件：打开 Outlook → 等待加载 → 新建邮件 → ...
# 每天要发 10+ 次文件，崩溃！😤

# 使用 Worm：
worm ./report.xlsx manager@company.com
# 命令行直接发送，效率提升 10 倍 ✨
```

### Worm 的价值

| 对比项 | 传统方式 | Worm |
|--------|---------|------|
| 操作步骤 | 5-8 步 | 1 步 |
| 耗时 | 2-5 分钟 | 5-10 秒 |
| 学习成本 | 需要学习各种工具 | 一行命令 |
| 跨平台 | 不同系统不同工具 | 统一方案 |
| 内网可用 | 大部分工具被禁 | ✅ 邮件畅通 |
| 自动化 | 难以集成到脚本 | ✅ 完美支持 |

**一行命令，解决所有文件传输烦恼！**

## ✨ 特性

- 🚀 **极简使用** - 一行命令即可发送文件
- 📦 **智能打包** - 自动将目录打包为 ZIP 文件
- 🔒 **安全可靠** - 支持 SSL/TLS 加密传输
- 🌐 **广泛兼容** - 支持 QQ、163、Gmail 等主流邮箱
- 📊 **友好提示** - 自动计算文件大小并显示进度
- ⚡ **轻量无依赖** - 仅使用 Python 标准库

## 📦 安装

### 方式一：直接使用

```bash
# 克隆仓库
git clone https://github.com/yourusername/worm.git
cd worm

# 添加执行权限
chmod +x worm.py

# 创建软链接（可选，方便全局使用）
sudo ln -s $(pwd)/worm.py /usr/local/bin/worm
```

### 方式二：复制到系统路径

```bash
# 复制到系统路径
sudo cp worm.py /usr/local/bin/worm
sudo chmod +x /usr/local/bin/worm
```

## ⚙️ 配置

首次使用前需要配置邮箱 SMTP 信息：

```bash
# 复制配置文件模板
cp worm.conf.example worm.conf

# 编辑配置文件
vim worm.conf  # 或使用你喜欢的编辑器
```

配置文件支持三个位置（按优先级排序）：
1. `~/.config/worm/worm.conf`
2. `~/.worm.conf`
3. `程序同目录/worm.conf`

### 配置示例

#### QQ 邮箱

```ini
[smtp]
smtp_host = smtp.qq.com
smtp_port = 465
smtp_user = your_qq_number@qq.com
smtp_pass = 你的QQ邮箱授权码
sender_name = 文件快传
```

> 💡 **获取 QQ 邮箱授权码**：登录 QQ 邮箱 → 设置 → 账户 → POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务 → 开启 SMTP 服务 → 生成授权码

#### 163 邮箱

```ini
[smtp]
smtp_host = smtp.163.com
smtp_port = 465
smtp_user = your_account@163.com
smtp_pass = 你的163邮箱授权码
sender_name = 文件快传
```

#### Gmail

```ini
[smtp]
smtp_host = smtp.gmail.com
smtp_port = 465
smtp_user = your_account@gmail.com
smtp_pass = 你的应用专用密码
sender_name = File Transfer
```

> 💡 **获取 Gmail 应用专用密码**：Google 账户 → 安全性 → 两步验证 → 应用专用密码

## 🚀 使用方法

### 基本语法

```bash
worm <文件或目录路径> <目标邮箱>
```

### 使用示例

```bash
# 发送单个文件
worm ./report.pdf zhangsan@qq.com

# 发送目录（自动打包为 ZIP）
worm ./project_dir admin@163.com

# 发送日志文件
worm /var/log/app.log support@gmail.com

# 使用绝对路径
worm ~/Documents/presentation.pptx colleague@company.com
```

### 输出示例

```bash
$ worm ./report.pdf zhangsan@qq.com
📤 正在发送 report.pdf → zhangsan@qq.com ...
✅ 发送成功！

$ worm ./my_project zhangsan@qq.com
📦 正在打包目录 my_project/ ...
📤 正在发送 my_project.zip → zhangsan@qq.com ...
✅ 发送成功！
```

## 📋 功能说明

### 文件大小限制

- 最大附件大小：**50 MB**
- 超过限制会自动拒绝发送并提示

### 目录处理

- 自动将目录打包为 ZIP 文件
- 保留原始目录名称
- 发送完成后自动清理临时文件

### 错误处理

- ✅ 路径不存在检测
- ✅ 文件权限检查
- ✅ 邮箱格式验证
- ✅ SMTP 认证错误提示
- ✅ 网络异常处理

## 🔧 技术细节

### 系统要求

- Python 3.6+
- 标准库（无需额外安装依赖）

### 支持的 SMTP 端口

- **465** - SSL 加密（推荐）
- **587** - STARTTLS 加密

### 邮件格式

- 使用 MIME 多部分格式
- 自动检测文件类型
- Base64 编码附件
- UTF-8 编码邮件正文

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### 代码规范

- 遵循 PEP 8 编码规范
- 添加必要的注释和文档字符串
- 保持代码简洁和可读性

## 📝 常见问题

### Q: 为什么发送失败提示 "SMTP 认证失败"？

A: 请检查：
- 是否使用了**授权码**而非登录密码
- 是否已在邮箱设置中开启 SMTP 服务
- 配置文件中的邮箱地址和授权码是否正确

### Q: 支持哪些邮箱服务？

A: 理论上支持所有提供 SMTP 服务的邮箱，常见的包括：
- QQ 邮箱
- 163/126 邮箱
- Gmail
- Outlook/Hotmail
- 企业邮箱

### Q: 可以发送多个文件吗？

A: 当前版本仅支持单个文件或目录。如需发送多个文件，建议：
- 将文件放入同一目录后发送该目录
- 或多次执行命令

### Q: 为什么有 50 MB 的大小限制？

A: 大多数邮箱服务商对附件大小有限制（通常 25-50 MB）。超过此大小建议使用其他文件传输方式（如网盘、FTP 等）。

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件
---

⭐ 如果这个项目对你有帮助，欢迎 Star 支持！

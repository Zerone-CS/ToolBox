# NPU Container Manager

[English](#english) | [中文](#中文)

---

## English

### Overview

NPU Container Manager is a command-line tool for managing Docker containers with Huawei Ascend NPU devices. It provides an interactive interface to create, manage, and monitor containers optimized for Ascend NPU workloads.

### Features

- 🚀 **Interactive Container Creation**: Step-by-step wizard for creating NPU-enabled containers
- 🎯 **NPU Device Management**: Automatic detection and selection of available NPU devices
- 🐳 **Docker Integration**: Seamless integration with Docker for container lifecycle management
- 📦 **Image Management**: Support for pulling and managing Ascend-optimized images
- 🔧 **Custom Configuration**: Flexible volume mounting and shared memory configuration
- 📊 **Container Monitoring**: View container status, logs, and resource usage
- 🛡️ **Conflict Resolution**: Intelligent handling of container name conflicts

### Prerequisites

- Python 3.6+
- Docker installed and running
- Huawei Ascend NPU drivers (optional, for NPU functionality)
- Linux/Unix operating system

### Installation

#### Method 1: Direct Execution

```bash
# Clone the repository
git clone https://github.com/yourusername/npu-manager.git
cd npu-manager

# Make the script executable
chmod +x npu_container_manager.py

# Run the tool
python3 npu_container_manager.py
```

#### Method 2: Install as Package

```bash
# Clone the repository
git clone https://github.com/yourusername/npu-manager.git
cd npu-manager

# Install using pip
pip install -e .

# Run the tool
npu-manager
```

### Usage

#### Main Menu

When you run the tool, you'll see an interactive menu:

```
=== NPU Container Manager ===
1. Create new container
2. List all containers
3. Start container
4. Stop container
5. Restart container
6. Enter container
7. View container logs
8. Delete container
0. Exit
```

#### Creating a Container

1. Select option `1` from the main menu
2. Choose or pull a Docker image
3. Select NPU devices to use
4. Configure volume mounts (optional)
5. Set shared memory size
6. Provide a container name
7. Review and confirm the configuration

The tool will generate a startup script and create the container automatically.

#### Managing Containers

- **List containers**: View all containers with their status
- **Start/Stop/Restart**: Control container lifecycle
- **Enter container**: Open an interactive bash session
- **View logs**: Check container output and errors
- **Delete container**: Remove containers with confirmation

### Configuration

Default settings can be modified in the `NPUContainerManager` class:

```python
DEFAULT_IMAGE = "quay.io/ascend/vllm-ascend:main"
DEFAULT_SHM_SIZE = "16g"
SCRIPT_OUTPUT_DIR = Path.home() / "npu_container_scripts"
```

### Generated Scripts

Container startup scripts are saved to `~/npu_container_scripts/` for reference and reuse.

### Troubleshooting

**Docker not found**:
- Ensure Docker is installed: `docker --version`
- Check Docker service is running: `sudo systemctl status docker`

**NPU devices not detected**:
- Verify Ascend drivers are installed: `npu-smi info`
- Check device permissions: `ls -l /dev/davinci*`

**Container creation fails**:
- Check Docker logs: `docker logs <container_name>`
- Verify image compatibility with your NPU model

### Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Acknowledgments

- Built for Huawei Ascend NPU ecosystem
- Supports CANN, MindSpore, and vLLM frameworks

---

## 中文

### 概述

NPU Container Manager 是一个用于管理华为昇腾 NPU 设备 Docker 容器的命令行工具。它提供了交互式界面来创建、管理和监控针对昇腾 NPU 工作负载优化的容器。

### 功能特性

- 🚀 **交互式容器创建**：分步向导式创建支持 NPU 的容器
- 🎯 **NPU 设备管理**：自动检测和选择可用的 NPU 设备
- 🐳 **Docker 集成**：与 Docker 无缝集成，管理容器生命周期
- 📦 **镜像管理**：支持拉取和管理昇腾优化镜像
- 🔧 **自定义配置**：灵活的卷挂载和共享内存配置
- 📊 **容器监控**：查看容器状态、日志和资源使用情况
- 🛡️ **冲突解决**：智能处理容器名称冲突

### 系统要求

- Python 3.6+
- 已安装并运行的 Docker
- 华为昇腾 NPU 驱动（可选，用于 NPU 功能）
- Linux/Unix 操作系统

### 安装方法

#### 方法一：直接执行

```bash
# 克隆仓库
git clone https://github.com/yourusername/npu-manager.git
cd npu-manager

# 添加执行权限
chmod +x npu_container_manager.py

# 运行工具
python3 npu_container_manager.py
```

#### 方法二：安装为包

```bash
# 克隆仓库
git clone https://github.com/yourusername/npu-manager.git
cd npu-manager

# 使用 pip 安装
pip install -e .

# 运行工具
npu-manager
```

### 使用说明

#### 主菜单

运行工具后，您将看到交互式菜单：

```
=== NPU 容器管理器 ===
1. 创建新容器
2. 列出所有容器
3. 启动容器
4. 停止容器
5. 重启容器
6. 进入容器
7. 查看容器日志
8. 删除容器
0. 退出
```

#### 创建容器

1. 从主菜单选择选项 `1`
2. 选择或拉取 Docker 镜像
3. 选择要使用的 NPU 设备
4. 配置卷挂载（可选）
5. 设置共享内存大小
6. 提供容器名称
7. 审查并确认配置

工具将自动生成启动脚本并创建容器。

#### 管理容器

- **列出容器**：查看所有容器及其状态
- **启动/停止/重启**：控制容器生命周期
- **进入容器**：打开交互式 bash 会话
- **查看日志**：检查容器输出和错误
- **删除容器**：确认后删除容器

### 配置说明

可以在 `NPUContainerManager` 类中修改默认设置：

```python
DEFAULT_IMAGE = "quay.io/ascend/vllm-ascend:main"
DEFAULT_SHM_SIZE = "16g"
SCRIPT_OUTPUT_DIR = Path.home() / "npu_container_scripts"
```

### 生成的脚本

容器启动脚本保存在 `~/npu_container_scripts/` 目录中，供参考和重用。

### 故障排除

**找不到 Docker**：
- 确保已安装 Docker：`docker --version`
- 检查 Docker 服务是否运行：`sudo systemctl status docker`

**未检测到 NPU 设备**：
- 验证昇腾驱动已安装：`npu-smi info`
- 检查设备权限：`ls -l /dev/davinci*`

**容器创建失败**：
- 查看 Docker 日志：`docker logs <容器名称>`
- 验证镜像与您的 NPU 型号兼容

### 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细指南。

### 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

### 致谢

- 为华为昇腾 NPU 生态系统构建
- 支持 CANN、MindSpore 和 vLLM 框架

# Contributing to NPU Container Manager

[English](#english) | [中文](#中文)

---

## English

Thank you for your interest in contributing to NPU Container Manager! This document provides guidelines for contributing to the project.

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints and experiences

### How to Contribute

#### Reporting Bugs

Before creating a bug report:
1. Check the existing issues to avoid duplicates
2. Collect relevant information (OS, Python version, Docker version, error messages)

When creating a bug report, include:
- Clear and descriptive title
- Steps to reproduce the issue
- Expected vs actual behavior
- Environment details
- Error messages and logs

#### Suggesting Enhancements

Enhancement suggestions are welcome! Please:
1. Check if the feature has already been suggested
2. Provide a clear use case
3. Explain why this enhancement would be useful
4. Consider implementation complexity

#### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow coding standards**:
   - Use type hints for function parameters and return values
   - Follow PEP 8 style guidelines
   - Keep functions focused and single-purpose (SOLID principles)
   - Avoid code duplication (DRY principle)
   - Write clear, self-documenting code (KISS principle)
3. **Test your changes**:
   - Ensure existing functionality still works
   - Test with different Docker images and NPU configurations
   - Verify error handling works correctly
4. **Update documentation**:
   - Update README.md if adding new features
   - Add docstrings to new functions
   - Update comments for modified code
5. **Commit messages**:
   - Use clear, descriptive commit messages
   - Reference issue numbers when applicable
   - Follow conventional commit format (optional but appreciated)

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/npu-manager.git
cd npu-manager

# Create a virtual environment (optional)
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt

# Make your changes
# ...

# Test your changes
python3 npu_container_manager.py
```

### Coding Standards

- **SOLID Principles**: Single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion
- **KISS**: Keep it simple - prefer straightforward solutions
- **DRY**: Don't repeat yourself - extract common functionality
- **YAGNI**: You aren't gonna need it - implement only what's needed now

### Testing Guidelines

- Test on Linux systems with Docker installed
- Test with and without NPU devices available
- Verify error messages are clear and helpful
- Test edge cases (empty inputs, invalid selections, etc.)

### Questions?

Feel free to open an issue for questions or discussions about contributing.

---

## 中文

感谢您对 NPU Container Manager 项目的贡献兴趣！本文档提供了项目贡献指南。

### 行为准则

- 尊重和包容他人
- 欢迎新人并帮助他们入门
- 专注于建设性反馈
- 尊重不同的观点和经验

### 如何贡献

#### 报告错误

创建错误报告前：
1. 检查现有问题以避免重复
2. 收集相关信息（操作系统、Python 版本、Docker 版本、错误消息）

创建错误报告时，请包含：
- 清晰描述性的标题
- 重现问题的步骤
- 预期行为与实际行为对比
- 环境详细信息
- 错误消息和日志

#### 建议改进

欢迎提出改进建议！请：
1. 检查该功能是否已被建议
2. 提供清晰的使用场景
3. 解释为什么这个改进有用
4. 考虑实现复杂度

#### 拉取请求

1. **Fork 仓库**并从 `main` 分支创建您的分支
2. **遵循编码标准**：
   - 为函数参数和返回值使用类型提示
   - 遵循 PEP 8 风格指南
   - 保持函数专注和单一职责（SOLID 原则）
   - 避免代码重复（DRY 原则）
   - 编写清晰、自文档化的代码（KISS 原则）
3. **测试您的更改**：
   - 确保现有功能仍然正常工作
   - 使用不同的 Docker 镜像和 NPU 配置进行测试
   - 验证错误处理正确工作
4. **更新文档**：
   - 如果添加新功能，更新 README.md
   - 为新函数添加文档字符串
   - 更新修改代码的注释
5. **提交消息**：
   - 使用清晰、描述性的提交消息
   - 在适用时引用问题编号
   - 遵循常规提交格式（可选但建议）

### 开发环境设置

```bash
# 克隆您的 fork
git clone https://github.com/yourusername/npu-manager.git
cd npu-manager

# 创建虚拟环境（可选）
python3 -m venv venv
source venv/bin/activate

# 安装开发依赖
pip install -r requirements.txt

# 进行更改
# ...

# 测试您的更改
python3 npu_container_manager.py
```

### 编码标准

- **SOLID 原则**：单一职责、开闭原则、里氏替换、接口隔离、依赖倒置
- **KISS**：保持简单 - 优先选择直接的解决方案
- **DRY**：不要重复自己 - 提取公共功能
- **YAGNI**：你不会需要它 - 只实现当前需要的功能

### 测试指南

- 在安装了 Docker 的 Linux 系统上测试
- 在有和没有 NPU 设备的情况下测试
- 验证错误消息清晰且有帮助
- 测试边缘情况（空输入、无效选择等）

### 有问题？

欢迎开启 issue 讨论贡献相关的问题。

# CLAUDE.md - OpsKit 项目开发指南

本文件为 Claude Code AI 提供 OpsKit 项目的完整开发指导。所有代码使用英文编写。

## 项目概述

OpsKit 是一个统一的运维工具管理平台，旨在解决运维工具分散管理、依赖复杂、配置混乱等问题。

### 核心特性
- **统一管理**: 通过 `opskit` 命令统一访问所有工具
- **自动依赖**: 运行时自动检测和安装 Python/系统依赖
- **Git 原生**: 基于 Git 的版本管理和更新机制
- **配置分离**: 用户配置与代码分离，避免更新冲突
- **跨平台**: 支持 macOS 和主流 Linux 发行版
- **AI 友好**: 每个工具包含 CLAUDE.md 支持 AI 开发

### 技术架构
- **主语言**: Python 3.7+ (核心服务)
- **工具语言**: Python + Shell Script
- **配置格式**: YAML
- **存储**: SQLite (轻量级 KV 存储)
- **平台支持**: macOS + Ubuntu/CentOS/Arch/SUSE

## 项目结构

```
~/.opskit/                          # Git 仓库根目录
├── CLAUDE.md                       # 本文件 - AI 开发指南
├── README.md                       # 用户文档
├── TODO.md                         # 开发进度管理
├── .gitignore                      # Git 忽略规则
├── requirements.txt                # 核心依赖
├── setup.py                        # 安装脚本
├── opskit                          # 主执行文件 (Python)
├── core/                           # 核心服务模块
│   ├── __init__.py
│   ├── cli.py                      # 交互式命令行
│   ├── plugin_manager.py           # 工具发现和管理
│   ├── dependency_manager.py       # 自动依赖安装
│   ├── config_manager.py           # 配置管理
│   └── platform_utils.py           # 平台工具
├── tools/                          # 工具插件目录
│   ├── database/                   # 数据库工具类
│   │   └── mysql-sync/
│   │       ├── CLAUDE.md           # 工具级开发指南
│   │       ├── main.py             # 主程序
│   │       ├── requirements.txt    # 依赖列表
│   │       └── resources/          # 外部资源 (Git 忽略)
│   ├── network/                    # 网络工具类
│   ├── system/                     # 系统工具类
│   └── monitoring/                 # 监控工具类
├── common/                         # 公共库
│   ├── python/                     # Python 公共库
│   │   ├── __init__.py
│   │   ├── logger.py               # 统一日志管理
│   │   ├── storage.py              # KV/SQLite 存储
│   │   └── utils.py                # 通用工具函数
│   └── shell/                      # Shell 公共库
│       ├── common.sh               # Shell 公共函数
│       └── logger.sh               # Shell 日志函数
├── config/                         # 配置模板
│   ├── opskit.yaml.template        # 主配置模板
│   └── tools.yaml                  # 工具注册表
├── data/                           # 用户数据 (Git 忽略)
│   ├── opskit.yaml                 # 用户主配置
│   └── storage.db                  # SQLite 数据库
├── cache/                          # 缓存目录 (Git 忽略)
│   ├── venvs/                      # Python 虚拟环境
│   ├── downloads/                  # 下载缓存
│   └── pip_cache/                  # Pip 缓存
└── logs/                           # 日志文件 (Git 忽略)
```

## 核心组件架构

### 1. 主执行文件 (`opskit`)
- **职责**: 程序入口点，命令行参数解析
- **特点**: 可执行的 Python 脚本，添加到系统 PATH
- **功能**: 工具启动器、系统状态检查、更新管理

### 2. CLI 模块 (`core/cli.py`)
- **职责**: 交互式命令行界面
- **功能**:
  - 工具浏览和搜索 (分类/模糊匹配)
  - 工具详情展示 (描述/依赖/配置)
  - 配置管理界面
  - 系统状态显示

### 3. 插件管理器 (`core/plugin_manager.py`)
- **职责**: 工具发现、注册和生命周期管理
- **功能**:
  - 自动扫描 `tools/` 目录
  - 解析工具元数据 (CLAUDE.md, requirements.txt)
  - 工具分类和索引
  - 工具状态管理

### 4. 依赖管理器 (`core/dependency_manager.py`)
- **职责**: 自动依赖检测和安装
- **功能**:
  - Python 依赖: 虚拟环境管理 + pip 安装
  - 系统依赖: 包管理器检测 + 安装提示
  - 依赖缓存和版本管理
  - 外部资源下载

### 5. 配置管理器 (`core/config_manager.py`)
- **职责**: 配置文件管理和持久化
- **功能**:
  - 配置模板系统
  - 用户配置存储
  - 配置验证和默认值
  - 配置导入导出

### 6. 平台工具 (`core/platform_utils.py`)
- **职责**: 跨平台兼容性处理
- **功能**:
  - 系统信息检测 (OS/发行版/架构)
  - 包管理器检测和适配
  - 系统命令执行
  - 路径和环境变量处理

## 工具开发规范

### 标准工具结构
每个工具必须包含以下文件：
```
tools/category/tool-name/
├── CLAUDE.md           # 工具开发指南 (必需)
├── main.py 或 main.sh  # 主程序文件 (必需)
├── requirements.txt    # Python 依赖 (Python 工具必需)
├── config.yaml.template # 配置模板 (可选)
└── resources/          # 外部资源目录 (Git 忽略, 可选)
```

### CLAUDE.md 模板
每个工具的 CLAUDE.md 应包含：
```markdown
# 工具名称

## 功能描述
简要描述工具的用途和核心功能

## 技术架构
- 实现语言: Python/Shell
- 核心依赖: 列出主要依赖
- 系统要求: OS/软件要求

## 配置项
列出所有配置项及其说明

## 开发指南
- 代码结构说明
- 关键功能实现
- 错误处理策略
- 测试方法

## 使用示例
提供典型使用场景的示例
```

### 公共库使用

**Python 工具**:
```python
# 导入公共库
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../common/python'))

from logger import get_logger
from storage import get_storage
from utils import load_config

# 使用统一日志
logger = get_logger(__name__)
logger.info("工具启动")

# 使用 KV 存储
storage = get_storage("tool_name")
storage.set("key", "value")

# 加载配置
config = load_config("tool_name")
```

**Shell 工具**:
```bash
#!/bin/bash

# 导入公共库
source "$(dirname "$0")/../../../common/shell/common.sh"
source "$(dirname "$0")/../../../common/shell/logger.sh"

# 使用统一日志
log_info "工具启动"

# 检查依赖
check_command "mysql" "请安装 MySQL 客户端"
```

## 开发流程

### 新工具开发流程
1. **创建目录结构**: `tools/category/tool-name/`
2. **编写 CLAUDE.md**: 按模板编写工具文档
3. **实现主程序**: main.py 或 main.sh
4. **添加依赖声明**: requirements.txt (Python 工具)
5. **集成公共库**: 使用统一日志和存储
6. **本地测试**: 确保工具正常运行
7. **注册工具**: 更新 config/tools.yaml

### Git 工作流
- **开发**: 在功能分支开发新工具
- **测试**: 在多个平台测试兼容性
- **合并**: 通过 PR 合并到主分支
- **发布**: 打标签发布新版本

## 依赖管理策略

### Python 依赖管理
```python
def ensure_python_dependencies(tool_path):
    """为工具创建虚拟环境并安装依赖"""
    venv_path = f"cache/venvs/{tool_name}"
    requirements_file = f"{tool_path}/requirements.txt"
    
    # 创建虚拟环境
    if not os.path.exists(venv_path):
        subprocess.run([sys.executable, "-m", "venv", venv_path])
    
    # 安装依赖
    if os.path.exists(requirements_file):
        pip_path = f"{venv_path}/bin/pip"
        subprocess.run([pip_path, "install", "-r", requirements_file])
```

### 系统依赖管理
```python
PACKAGE_MANAGERS = {
    "darwin": ["brew", "port"],      # macOS
    "ubuntu": ["apt", "apt-get"],    # Ubuntu
    "centos": ["yum", "dnf"],        # CentOS/RHEL
    "arch": ["pacman"],              # Arch Linux
    "opensuse": ["zypper"],          # openSUSE
}

def install_system_dependency(package_name):
    """根据系统自动选择包管理器安装依赖"""
    os_type = detect_os()
    managers = PACKAGE_MANAGERS.get(os_type, [])
    
    for manager in managers:
        if command_exists(manager):
            return install_with_manager(manager, package_name)
    
    # 如果没有找到包管理器，提供手动安装指导
    provide_manual_installation_guide(package_name)
```

## 数据分离架构

### Git 友好设计
OpsKit 采用数据分离架构，确保用户数据与代码库分离：

**核心原则**:
- 用户数据存储在 `data/` 目录 (Git 忽略)
- 缓存文件存储在 `cache/` 目录 (Git 忽略)  
- 日志文件存储在 `logs/` 目录 (Git 忽略)
- 其他所有文件均为 Git 跟踪的代码库

**优势**:
- **无冲突更新**: 用户可以安全地执行 `git pull` 更新
- **数据保护**: 用户配置和存储不会被版本更新覆盖
- **清洁分离**: 代码、配置、缓存、日志完全分离

### 目录职责划分
```yaml
data/:           # 用户持久化数据 (Git 忽略)
  - opskit.yaml  # 主配置文件
  - storage.db   # SQLite 数据库
  - *.yaml       # 工具配置文件 (按需)

cache/:          # 临时缓存数据 (Git 忽略)
  - venvs/       # Python 虚拟环境
  - downloads/   # 下载缓存
  - pip_cache/   # Pip 缓存

logs/:           # 日志文件 (Git 忽略)
  - opskit.log   # 主应用日志

其他目录:        # Git 跟踪的代码库
  - core/        # 核心模块
  - tools/       # 工具定义
  - config/      # 配置模板
  - common/      # 公共库
```

## 配置管理系统

### 配置层次结构
1. **全局配置**: `data/opskit.yaml`
2. **工具配置**: `data/tool-name.yaml` (按需创建)
3. **默认配置**: `config/*.yaml.template`

### 配置文件格式
```yaml
# opskit.yaml
general:
  default_editor: vim
  auto_update: true
  confirm_destructive: true

display:
  show_colors: true
  page_size: 20
  show_descriptions: true

logging:
  file_enabled: false          # 默认关闭文件日志
  console_level: INFO
  file_level: DEBUG
  max_files: 5
  max_size: 10MB

tools: {}

platforms:
  preferred_package_manager: auto  # auto, brew, apt, yum, etc.

paths:
  cache_dir: cache                  # 默认为相对于项目根目录的 cache 文件夹
  logs_dir: logs                    # 默认为相对于项目根目录的 logs 文件夹
  
  # 路径规则:
  # - 相对路径: 基于 OpsKit 项目根目录
  # - 绝对路径: 直接使用指定路径
  # - 工具临时目录: 自动在 cache_dir/tools/ 下创建
```

## 错误处理和日志

### 统一错误处理
```python
class OpsKitError(Exception):
    """OpsKit 基础异常类"""
    pass

class DependencyError(OpsKitError):
    """依赖相关错误"""
    pass

class ConfigError(OpsKitError):
    """配置相关错误"""
    pass

class ToolError(OpsKitError):
    """工具执行错误"""
    pass
```

### 日志管理
- **级别**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **格式**: 时间戳 + 级别 + 模块 + 消息
- **输出**: 控制台 + 日志文件 (logs/)
- **轮转**: 按日期或大小轮转日志文件

## 测试策略

### 单元测试
- 每个核心模块都需要单元测试
- 使用 pytest 框架
- 测试覆盖率要求 >80%

### 集成测试
- 工具端到端测试
- 依赖安装测试
- 配置管理测试
- 跨平台兼容性测试

### 平台测试矩阵
- **macOS**: Intel + Apple Silicon
- **Ubuntu**: 20.04, 22.04
- **CentOS**: 7, 8
- **Arch Linux**: 最新版

## 性能要求

### 响应时间
- CLI 启动: <2s
- 工具列表加载: <1s
- 依赖检查: <5s
- 依赖安装: 取决于网络和包大小

### 资源占用
- 内存使用: <100MB (不包含工具运行)
- 磁盘空间: 核心 <50MB，缓存按需
- CPU 使用: 空闲时 <1%

## 安全考虑

### 配置安全
- 敏感信息加密存储
- 配置文件权限控制 (600)
- 避免在日志中记录敏感信息

### 依赖安全
- 验证下载文件完整性
- 使用官方源安装依赖
- 定期检查依赖漏洞

### 执行安全
- 输入验证和清理
- 避免命令注入
- 最小权限原则

## 扩展指南

### 添加新的工具类别
1. 在 `tools/` 下创建新目录
2. 更新 `config/tools.yaml`
3. 在 CLI 中添加类别显示

### 添加新的平台支持
1. 在 `platform_utils.py` 中添加检测逻辑
2. 在 `PACKAGE_MANAGERS` 中添加包管理器
3. 测试新平台的兼容性

### 添加新的配置选项
1. 在配置模板中添加新选项
2. 更新配置验证逻辑
3. 在相关模块中使用新配置

## 常见问题解决

### 依赖安装失败
1. 检查网络连接
2. 检查包管理器可用性
3. 查看详细错误日志
4. 手动安装问题依赖

### 工具无法启动
1. 检查工具结构完整性
2. 验证依赖是否正确安装
3. 检查配置文件格式
4. 查看工具专用日志

### 配置不生效
1. 检查配置文件路径
2. 验证 YAML 语法
3. 确认配置优先级
4. 重启 opskit 服务
# CLAUDE.md - OpsKit 项目开发指南

本文件为 Claude Code AI 提供 OpsKit 项目的完整开发指导。所有代码使用英文编写。

## 项目概述

OpsKit 是一个统一的运维工具管理平台，旨在解决运维工具分散管理、依赖复杂、配置混乱等问题。

### 核心特性
- **统一管理**: 通过 `opskit` 命令统一访问所有工具
- **共享环境**: 单个共享虚拟环境，减少资源占用
- **按需依赖**: 工具依赖按需安装，智能缓存管理
- **Git 原生**: 基于 Git 的版本管理和更新机制
- **配置分离**: 用户配置与代码分离，避免更新冲突
- **跨平台**: 支持 macOS 和主流 Linux 发行版
- **AI 友好**: 每个工具包含 CLAUDE.md 支持 AI 开发

### 技术架构
- **主语言**: Python 3.7+ (核心服务)
- **工具语言**: Python + Shell Script
- **配置格式**: Environment Variables + YAML
- **存储**: SQLite (轻量级 KV 存储)
- **依赖管理**: 共享虚拟环境 + 按需工具环境
- **平台支持**: macOS + Ubuntu/CentOS/Arch/SUSE

## 项目结构

```
~/.opskit/                          # Git 仓库根目录
├── CLAUDE.md                       # 本文件 - AI 开发指南
├── README.md                       # 用户文档
├── TODO.md                         # 开发进度管理
├── Makefile                        # 构建和管理脚本
├── requirements.txt                # 核心依赖列表
├── setup.py                        # 安装脚本
├── .venv/                          # 共享虚拟环境 (Git 忽略)
├── bin/                            # 可执行文件目录
│   └── opskit                      # 主执行文件
├── core/                           # 核心服务模块
│   ├── __init__.py
│   ├── cli.py                      # 交互式命令行界面
│   ├── dependency_manager.py       # 依赖管理和安装
│   ├── env.py                      # 环境变量管理
│   ├── env_manager.py              # 环境管理器
│   └── platform_utils.py           # 平台工具和检测
├── tools/                          # 工具插件目录
│   ├── database/                   # 数据库工具类
│   │   └── mysql-sync/
│   │       ├── CLAUDE.md           # 工具级开发指南
│   │       ├── main.py             # 主程序
│   │       └── requirements.txt    # 依赖列表
│   ├── network/                    # 网络工具类
│   │   └── port-scanner/
│   │       ├── CLAUDE.md
│   │       └── main.sh             # Shell 脚本工具
│   ├── system/                     # 系统工具类
│   │   ├── disk-usage/
│   │   │   ├── CLAUDE.md
│   │   │   └── main.sh
│   │   └── system-info/
│   │       ├── CLAUDE.md
│   │       └── main.py
│   └── cloudnative/                # 云原生工具类
│       └── k8s-resource-copy/
│           ├── CLAUDE.md
│           ├── main.py
│           └── requirements.txt
├── common/                         # 公共库
│   ├── python/                     # Python 公共库
│   │   ├── __init__.py
│   │   ├── logger.py               # 统一日志管理
│   │   ├── storage.py              # KV/SQLite 存储
│   │   └── utils.py                # 通用工具函数
│   └── shell/                      # Shell 公共库
│       ├── logger.sh               # Shell 日志函数
│       ├── storage.sh              # Shell 存储函数
│       └── utils.sh                # Shell 通用函数
├── config/                         # 配置和工具注册
│   ├── dependencies.yaml           # 依赖配置
│   └── tools.yaml                  # 工具注册表
├── docs/                           # 文档目录
│   ├── python-tool-development.md  # Python 工具开发指南
│   └── shell-tool-development.md   # Shell 工具开发指南
├── data/                           # 用户数据 (Git 忽略)
│   └── storage.db                  # SQLite 数据库
├── cache/                          # 缓存目录 (Git 忽略)
│   ├── downloads/                  # 下载缓存
│   ├── pip_cache/                  # Pip 缓存
│   ├── requirements/               # 工具依赖缓存
│   ├── storage.db                  # 缓存数据库
│   ├── tools/                      # 工具临时目录
│   └── venvs/                      # 工具特定虚拟环境
└── logs/                           # 日志文件 (Git 忽略)
```

## 核心组件架构

### 1. 主执行文件 (`bin/opskit`)
- **职责**: 程序入口点，命令行参数解析和路由
- **特点**: Python 脚本，使用共享虚拟环境 shebang
- **功能**: 命令分发、参数处理、错误处理、版本管理

### 2. CLI 模块 (`core/cli.py`)
- **职责**: 交互式命令行界面和工具运行
- **功能**:
  - 交互模式 - 工具浏览和选择
  - 工具列表 - 按分类显示所有工具
  - 工具搜索 - 模糊匹配和描述搜索
  - 工具运行 - 依赖检查和工具执行
  - 配置管理 - 工具配置界面
  - 系统状态 - 健康检查和诊断

### 3. 依赖管理器 (`core/dependency_manager.py`)
- **职责**: 共享环境和按需依赖管理
- **功能**:
  - 共享虚拟环境管理 (.venv/)
  - 工具特定依赖安装 (cache/venvs/)
  - 依赖缓存和复用 (cache/requirements/)
  - 系统依赖检测和安装提示
  - 外部资源下载和管理

### 4. 环境管理器 (`core/env.py`)
- **职责**: 环境变量和配置管理
- **特性**: 基于 python-dotenv 的现代配置管理
- **功能**:
  - 环境变量加载 (data/.env)
  - 配置属性访问 (env.cache_dir, env.log_level)
  - 工具临时目录创建
  - 配置摘要和状态

### 5. 环境管理器扩展 (`core/env_manager.py`)
- **职责**: 高级环境管理功能
- **功能**: 环境变量管理、工具环境隔离、配置验证

### 6. 平台工具 (`core/platform_utils.py`)
- **职责**: 跨平台兼容性和系统检测
- **功能**:
  - 操作系统和发行版检测
  - 包管理器自动识别
  - 系统命令执行和路径处理
  - 平台特定逻辑适配

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
sys.path.insert(0, os.path.join(os.environ['OPSKIT_BASE_PATH'], 'common/python'))

from logger import get_logger
from storage import get_storage

# 使用统一日志
logger = get_logger(__name__)
logger.info("工具启动")

# 使用 KV 存储
storage = get_storage("tool_name")
storage.set("key", "value")

```

**Shell 工具**:
```bash
#!/bin/bash

# 导入公共库
source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
source "${OPSKIT_BASE_PATH}/common/shell/utils.sh"

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

### 共享虚拟环境架构
OpsKit 采用混合依赖管理策略：

**1. 共享虚拟环境 (.venv/)**:
- 安装 OpsKit 核心依赖 (requirements.txt)
- 所有工具共享基础包 (PyYAML, click, rich 等)
- 减少磁盘空间占用和安装时间

**2. 工具特定环境 (cache/venvs/tool-name/)**:
- 工具有特殊依赖时创建独立环境
- 避免依赖冲突和版本兼容问题
- 按需创建，智能缓存复用

### Python 依赖管理实现
```python
def ensure_tool_dependencies(tool_name: str, tool_path: str):
    """智能依赖管理 - 共享环境优先，按需隔离"""
    requirements_file = Path(tool_path) / "requirements.txt"
    
    if not requirements_file.exists():
        # 无依赖文件，使用共享环境
        return str(OPSKIT_ROOT / ".venv" / "bin" / "python")
    
    # 检查是否需要独立环境
    if tool_needs_isolation(tool_name, requirements_file):
        # 创建工具特定虚拟环境
        venv_path = CACHE_DIR / "venvs" / tool_name
        create_tool_venv(venv_path, requirements_file)
        return str(venv_path / "bin" / "python")
    else:
        # 安装到共享环境
        install_to_shared_venv(requirements_file)
        return str(OPSKIT_ROOT / ".venv" / "bin" / "python")
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
  - .env         # 全局变量文件
  - storage.db   # SQLite 数据库

cache/:          # 临时缓存数据 (Git 忽略)
  - venvs/       # Python 虚拟环境
  - downloads/   # 下载缓存
  - pip_cache/   # Pip 缓存
  - tools/       # 工具临时目录

logs/:           # 日志文件 (Git 忽略)
  - opskit.log   # 主应用日志

其他目录:        # Git 跟踪的代码库
  - core/        # 核心模块
  - tools/       # 工具定义
  - config/      # 配置模板
  - common/      # 公共库
```

## 配置管理系统

### 现代环境变量架构
OpsKit 使用 python-dotenv 实现现代化配置管理：

**配置层次结构**:
1. **环境变量文件**: `data/.env` (用户自定义配置)
2. **系统环境变量**: `OPSKIT_*` 前缀的环境变量
3. **默认配置**: 硬编码在 `core/env.py` 中的默认值
4. **存储数据库**: `data/storage.db` (运行时状态和缓存)

### 环境变量配置格式
```bash
# data/.env - 用户配置文件
OPSKIT_VERSION=0.1.0
OPSKIT_AUTHOR="OpsKit Development Team"

# 路径配置
OPSKIT_PATHS_CACHE_DIR=cache           # 缓存目录 (相对或绝对路径)
OPSKIT_PATHS_LOGS_DIR=logs             # 日志目录 (相对或绝对路径)

# 日志配置
OPSKIT_LOGGING_CONSOLE_LEVEL=INFO      # 控制台日志级别
OPSKIT_LOGGING_FILE_ENABLED=false     # 文件日志开关
OPSKIT_LOGGING_FILE_LEVEL=DEBUG       # 文件日志级别
OPSKIT_LOGGING_CONSOLE_SIMPLE_FORMAT=true  # 简化控制台格式
OPSKIT_LOGGING_MAX_FILES=5            # 日志文件保留数量
OPSKIT_LOGGING_MAX_SIZE=10MB          # 单个日志文件大小

# 工具配置示例
MYSQL_SYNC_DEFAULT_HOST=localhost
MYSQL_SYNC_DEFAULT_PORT=3306
K8S_RESOURCE_COPY_DEFAULT_NAMESPACE=default
```

### 配置访问接口
```python
from core.env import env

# 通过属性访问配置
print(env.cache_dir)      # 缓存目录路径
print(env.logs_dir)       # 日志目录路径
print(env.log_level)      # 日志级别
print(env.version)        # OpsKit 版本

# 工具临时目录
temp_dir = get_tool_temp_dir("mysql-sync")

# 工具特定环境变量
tool_env = load_tool_env("/path/to/tool")
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

## 测试命令

### 初始化和设置
```bash
# 运行设置脚本创建共享虚拟环境
python3 setup.py

# 设置环境变量 (添加到 ~/.bashrc 或 ~/.zshrc)
export OPSKIT_BASE_PATH="/home/user/.opskit"
export PATH="$OPSKIT_BASE_PATH/bin:$PATH"
```

### 核心功能测试
```bash
# 测试工具列表 (使用共享虚拟环境)
opskit list

# 测试交互模式
opskit

# 测试工具搜索
opskit search mysql

# 测试系统状态
opskit status

# 测试版本信息
opskit version
```

### 依赖管理测试
```bash
# 测试共享环境工具
opskit run system-info    # 使用共享虚拟环境

# 测试按需依赖安装
opskit run mysql-sync     # 自动安装工具特定依赖
opskit run k8s-resource-copy  # 创建独立虚拟环境

# 测试 Shell 工具 (无 Python 依赖)
opskit run port-scanner   # 直接运行 Shell 脚本
opskit run disk-usage     # 系统工具调用
```

### 工具特定测试
```bash
# 数据库工具
opskit run mysql-sync         # MySQL 同步工具

# 网络工具  
opskit run port-scanner       # 端口扫描

# 系统工具
opskit run disk-usage         # 磁盘分析
opskit run system-info        # 系统信息

# 云原生工具
opskit run k8s-resource-copy  # Kubernetes 资源复制
```

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
1. 在 `core/env.py` 中添加新的配置属性
2. 更新环境变量前缀规则 (OPSKIT_*)
3. 在 `data/.env` 示例中添加配置说明
4. 在相关模块中使用 `env.new_option` 访问

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
- refact memery , some core libs have been removed and refacted, directory has been changed a lot
- opskit环境变量访问应该使用env.py，不能直接读取data/.env
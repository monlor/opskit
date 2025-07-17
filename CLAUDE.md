# OpsKit - Remote Operations Toolkit

## 项目概述

OpsKit是一个轻量级的远程运维工具包，现已使用Go语言重新实现，提供动态工具加载、交互式菜单操作和智能依赖管理。

## 快速安装

### 一键安装（推荐）

```bash
# 安装最新版本
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash

# 安装指定版本
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash -s -- --version=v1.0.0

# 强制重新安装
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash -s -- --force
```

### 手动安装

1. 下载安装脚本：
```bash
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh -o install.sh
chmod +x install.sh
```

2. 运行安装：
```bash
# 查看帮助
./install.sh --help

# 安装最新版本
./install.sh

# 安装指定版本
./install.sh --version=v1.0.0

# 开启调试模式
./install.sh --debug --version=v1.0.0
```

### 支持的系统

- **操作系统**: Linux, macOS, Windows
- **架构**: amd64, arm64, 386, arm

安装脚本会自动检测您的操作系统和架构，下载对应的二进制文件。

**核心理念**: 
- 动态工具加载，主程序轻量化
- 模块化设计，工具独立维护
- 智能依赖管理，用户确认安装
- 安全操作，多重确认机制
- 多语言脚本支持（Shell、Python、Go、Binary）

## 架构设计

### 主要组件

1. **main.go** - 主入口程序
   - 负责初始化和配置加载
   - 启动CLI命令行界面
   - 管理全局配置和环境变量

2. **cmd/root.go** - 根命令和动态命令加载
   - 基于Cobra框架的CLI界面
   - 动态从配置文件生成子命令
   - 版本信息和帮助系统

3. **internal/config/** - 配置管理
   - 工具配置加载和解析
   - 依赖配置管理
   - 版本控制和更新策略

4. **internal/executor/** - 工具执行器
   - 支持多种脚本类型执行
   - 文件查找和下载机制
   - 参数构建和环境变量传递

5. **internal/dynamic/** - 动态命令生成
   - 从JSON配置生成Cobra命令
   - 参数验证和标志处理
   - 子命令路由和执行

6. **tools/tools.json** - 工具配置
   - 工具元信息和依赖列表
   - 动态菜单生成依据
   - 支持多种脚本类型定义

7. **tools/dependencies.json** - 依赖配置
   - 简化配置：相同包名用`"package"`
   - 特殊配置：不同包名用`"packages"`对象
   - 支持多包管理器（brew、apt、yum、dnf等）

### 工具模块

- **mysql-sync.sh** - MySQL数据库同步
  - 支持数据库间完整同步
  - 连接测试和信息显示
  - 强制确认机制（输入"CONFIRM"）
  
- **s3-sync.sh** - S3存储同步
  - 支持S3与本地双向同步
  - AWS凭证检查和配置
  - 干运行预览功能

- **test-python.py** - Python工具示例
  - 展示Python脚本集成
  - 支持命令行参数处理
  - 环境变量传递

## 技术实现

### 版本管理系统

1. **文件加载优先级**：
   - 优先级1：当前目录本地文件（开发模式）
   - 优先级2：缓存文件（如果无需更新）
   - 优先级3：远程下载

2. **版本控制策略**：
   - **main版本**：默认自动更新，可通过`OPSKIT_NO_AUTO_UPDATE=1`禁用
   - **release版本**：不自动更新，保持稳定性
   - **更新间隔**：main版本默认1小时检查更新，可通过`OPSKIT_UPDATE_INTERVAL`调整

3. **缓存机制**：
   - 按版本分目录存储：`$OPSKIT_DIR/tools/$OPSKIT_RELEASE/`
   - 文件年龄检查：基于修改时间判断是否需要更新
   - 跨平台兼容：支持macOS和Linux的stat命令格式

### 多语言脚本支持

1. **Shell脚本** (`type: "shell"`)
   - 使用bash执行
   - 支持所有Shell功能
   - 环境变量自动传递

2. **Python脚本** (`type: "python"`)
   - 使用python3执行
   - 支持命令行参数处理
   - 环境变量传递

3. **Go程序** (`type: "go"`)
   - 使用`go run`执行源码
   - 支持编译后的二进制文件
   - 高性能工具开发

4. **二进制文件** (`type: "binary"`)
   - 直接执行二进制文件
   - 跨平台兼容性
   - 最佳性能

### 动态命令生成

1. **JSON配置驱动**：
   - 工具定义在`tools.json`中
   - 支持子命令和参数定义
   - 动态生成Cobra命令

2. **简化设计原则**：
   - JSON配置不定义脚本具体参数
   - 主程序只负责执行脚本
   - 参数由脚本自己处理

### 配置格式

**工具配置示例**：
```json
{
  "id": "mysql-sync",
  "name": "MySQL Database Sync",
  "description": "Synchronize MySQL databases with safety checks",
  "file": "mysql-sync.sh",
  "type": "shell",
  "dependencies": ["mysql"],
  "category": "database",
  "version": "1.0.0",
  "commands": [
    {
      "name": "sync",
      "description": "Synchronize databases"
    },
    {
      "name": "check",
      "description": "Test database connections"
    }
  ]
}
```

**依赖配置示例**：
```json
{
  "curl": {
    "package": "curl"
  },
  "mysql": {
    "packages": {
      "brew": "mysql-client",
      "apt": "mysql-client", 
      "yum": "mysql"
    }
  }
}
```

### 安全机制

- **依赖安装确认**：用户必须确认才能安装软件
- **危险操作确认**：MySQL同步等操作需要输入"CONFIRM"
- **详细信息显示**：操作前显示源和目标详细信息
- **参数过滤**：全局参数不会传递给工具脚本

## 开发指南

### 添加新工具

1. **创建工具脚本** (`tools/your-tool.sh`)：
   ```bash
   #!/bin/bash
   set -euo pipefail
   
   # 工具脚本自己处理参数
   command=$1
   shift
   
   case "$command" in
     "sync")
       echo "Syncing with args: $@"
       ;;
     "test")
       echo "Testing with args: $@"
       ;;
     *)
       echo "Unknown command: $command"
       exit 1
       ;;
   esac
   ```

2. **更新工具配置** (`tools/tools.json`)：
   ```json
   {
     "id": "your-tool",
     "name": "Your Tool Name", 
     "description": "Tool description",
     "file": "your-tool.sh",
     "type": "shell",
     "dependencies": ["required-command"],
     "category": "category",
     "version": "1.0.0",
     "commands": [
       {
         "name": "sync",
         "description": "Synchronize data"
       },
       {
         "name": "test",
         "description": "Test connections"
       }
     ]
   }
   ```

3. **添加依赖配置** (`tools/dependencies.json`)：
   ```json
   {
     "new-dependency": {
       "description": "Description",
       "check": "command-to-check",
       "package": "package-name"
     }
   }
   ```

### 构建和测试

**构建项目**：
```bash
./build.sh
```

**运行测试**：
```bash
go test ./... -v
```

**运行特定测试**：
```bash
go test ./internal/config -v
go test ./internal/executor -v
go test ./internal/dynamic -v
```

**集成测试**：
```bash
go test -v -timeout 30s
```

## 环境变量

- `OPSKIT_DIR` - 工作目录（默认：`$HOME/.opskit`）
- `OPSKIT_DEBUG` - 调试模式（设置为`1`启用）
- `OPSKIT_RELEASE` - 版本跟踪（默认：`main`，可设置为具体release版本如`v1.0.0`）
- `OPSKIT_NO_AUTO_UPDATE` - 禁用main版本自动更新（设置为`1`禁用）
- `OPSKIT_UPDATE_INTERVAL` - 更新间隔小时数（默认：`1`小时）
- `GITHUB_REPO` - 自定义仓库地址（用于开发测试）

## 使用场景

### 二进制使用
```bash
# 查看帮助
./opskit --help

# 列出工具
./opskit list

# 执行工具
./opskit mysql-sync sync source_db target_db --dry-run
./opskit s3-sync upload local_dir s3://bucket/path --exclude "*.tmp"
./opskit test-python test --verbose
```

### 开发调试
```bash
# 启用调试模式
export OPSKIT_DEBUG=1
./opskit --debug mysql-sync sync source target

# 使用本地配置
./opskit mysql-sync --help
```

### 版本管理使用

**使用特定release版本**：
```bash
export OPSKIT_RELEASE=v1.0.0
./opskit --version-info
```

**禁用自动更新**：
```bash
export OPSKIT_NO_AUTO_UPDATE=1
./opskit --version-info
```

**查看版本信息**：
```bash
./opskit --version-info
```

## 故障排除

### 常见问题

1. **构建失败**：确保Go 1.21+已安装
2. **依赖缺失**：运行`go mod tidy`
3. **测试失败**：确保没有网络限制
4. **工具执行失败**：检查脚本权限和依赖

### 调试技巧

1. **启用调试模式**：`export OPSKIT_DEBUG=1`
2. **查看详细日志**：`./opskit --debug command`
3. **测试配置加载**：`./opskit list`
4. **检查工具文件**：确保工具脚本存在且可执行

## 项目状态

### ✅ 已完成功能
- 动态工具架构
- Go语言重新实现
- 多语言脚本支持（Shell、Python、Go、Binary）
- 智能依赖管理
- 版本管理系统
- 优先本地文件加载
- main版本自动更新
- release版本稳定性
- 完整测试套件（18个测试用例）
- 多平台构建支持
- 动态命令生成
- 配置驱动架构

### 📋 测试覆盖
- 配置管理测试
- 执行器功能测试
- 动态命令生成测试
- 集成测试
- 多平台构建测试

### 🚀 技术特性
- 基于Cobra的CLI框架
- 模块化Go包结构
- JSON配置驱动
- 动态命令路由
- 智能文件查找
- 环境变量传递
- 错误处理机制

## 下一步计划

- 添加更多运维工具（Redis同步、文件备份等）
- 增强错误处理和重试机制
- 添加配置文件验证
- 支持工具版本管理
- 增加使用统计和日志
- 支持插件系统
- 添加交互式菜单模式
- 完善文档和示例
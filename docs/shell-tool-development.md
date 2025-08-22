# Shell 工具开发指南

本文档提供了在 OpsKit 框架中开发 Shell 工具的环境变量规范。

## 目录

1. [工具结构标准](#工具结构标准)
2. [环境变量规范](#环境变量规范)
3. [工具模板](#工具模板)

## 工具结构标准

每个 Shell 工具必须遵循以下目录结构：

```
tools/category/tool-name/
├── CLAUDE.md           # 工具开发指南 (必需)
├── main.sh             # 主程序文件 (必需)
└── .env               # 环境变量配置 (可选)
```

### 文件说明

- **CLAUDE.md**: 工具的开发指南，包含功能描述、架构说明、配置项等
- **main.sh**: 主程序文件，包含工具的核心逻辑，必须是可执行文件
- **.env**: 环境变量配置文件（如果工具需要默认配置）

## 环境变量规范

### OpsKit 自动注入的环境变量

OpsKit 框架会自动为 Shell 工具注入以下环境变量：

**核心环境变量（只读）**：
- `OPSKIT_BASE_PATH`: OpsKit 安装根目录
- `OPSKIT_TOOL_TEMP_DIR`: 工具专属临时目录
- `OPSKIT_WORKING_DIR`: 用户当前工作目录
- `TOOL_NAME`: 工具显示名称
- `TOOL_VERSION`: 工具版本号

**使用示例**：
```bash
#!/bin/bash

# 获取 OpsKit 注入的环境变量
BASE_PATH="${OPSKIT_BASE_PATH}"
TEMP_DIR="${OPSKIT_TOOL_TEMP_DIR}"
WORKING_DIR="${OPSKIT_WORKING_DIR}"
TOOL_NAME="${TOOL_NAME}"
TOOL_VERSION="${TOOL_VERSION}"

# 创建临时目录
mkdir -p "$TEMP_DIR"
```

## 推荐的工具函数使用

### 使用 OpsKit 通用工具函数

**推荐方式** - 直接使用基础的Shell功能和环境变量：

```bash
#!/bin/bash

# 直接使用环境变量，避免复杂依赖
# 简单的环境变量获取函数
get_env_var() {
    local var_name="$1"
    local default_value="$2"
    echo "${!var_name:-$default_value}"
}
```

**重要**: Shell工具不要使用复杂的fallback，保持简单直接。

### 避免复杂依赖

**不推荐** - 避免依赖已移除的复杂库：
```bash
# ❌ 这些库已被移除，不要使用
source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
source "${OPSKIT_BASE_PATH}/common/shell/interactive.sh"
source "${OPSKIT_BASE_PATH}/common/shell/storage.sh"
```

**推荐** - 直接使用 echo 输出：
```bash
# ✅ 直接使用 echo 输出，参考 mysql-sync 和 port-scanner 工具
echo "🔍 正在检查依赖..."
echo "✅ 操作成功完成"
echo "❌ 操作失败"
echo "⚠️  警告信息"
```

# 获取工具特定配置（从 .env 文件或环境变量）
TIMEOUT="${TIMEOUT:-30}"
DEBUG="${DEBUG:-false}"
MAX_RETRIES="${MAX_RETRIES:-3}"
```

### .env 文件格式

工具可以包含一个可选的 `.env` 文件来定义默认配置：

```bash
# .env 文件示例
TIMEOUT=30
DEBUG=false
MAX_RETRIES=3
HOST=localhost
USE_COLORS=true
```

### 配置读取最佳实践

```bash
#!/bin/bash

# 读取配置，支持默认值
TIMEOUT="${TIMEOUT:-30}"
DEBUG="${DEBUG:-false}"
MAX_RETRIES="${MAX_RETRIES:-3}"
HOST="${HOST:-localhost}"

# 类型转换函数（可选实现）
to_bool() {
    case "${1,,}" in
        true|yes|1|on) echo "true" ;;
        *) echo "false" ;;
    esac
}

to_int() {
    if [[ "$1" =~ ^[0-9]+$ ]]; then
        echo "$1"
    else
        echo "$2"  # 默认值
    fi
}

# 使用示例
DEBUG=$(to_bool "$DEBUG")
TIMEOUT=$(to_int "$TIMEOUT" "30")
```

### 临时文件管理

使用工具专属临时目录：

```bash
# 使用工具专属临时目录
if [[ -n "${OPSKIT_TOOL_TEMP_DIR}" ]]; then
    temp_file="${OPSKIT_TOOL_TEMP_DIR}/my_temp_file.txt"
    echo "Temporary data" > "$temp_file"
    echo "Created temp file: $temp_file"
fi
```


## 工具模板

```bash
#!/bin/bash

# My Tool - Shell Implementation
# Description of what this tool does

set -euo pipefail  # Enable strict mode

# Tool metadata from OpsKit environment
readonly TOOL_NAME="${TOOL_NAME:-My Tool}"
readonly TOOL_VERSION="${TOOL_VERSION:-1.0.0}"
readonly BASE_PATH="${OPSKIT_BASE_PATH:-}"
readonly TEMP_DIR="${OPSKIT_TOOL_TEMP_DIR:-}"
readonly WORKING_DIR="${OPSKIT_WORKING_DIR:-$(pwd)}"

# Tool-specific configuration from environment variables
TIMEOUT="${TIMEOUT:-30}"
DEBUG="${DEBUG:-false}"
MAX_RETRIES="${MAX_RETRIES:-3}"
HOST="${HOST:-localhost}"

# Convert string values to appropriate types
case "${DEBUG,,}" in
    true|yes|1|on) DEBUG=true ;;
    *) DEBUG=false ;;
esac

if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
    TIMEOUT=30
fi

if ! [[ "$MAX_RETRIES" =~ ^[0-9]+$ ]]; then
    MAX_RETRIES=3
fi

# Main tool operation - implement your logic here
main() {
    echo "Starting $TOOL_NAME v$TOOL_VERSION"
    
    # Example: Use temporary directory
    if [[ -n "$TEMP_DIR" ]]; then
        echo "Using temp directory: $TEMP_DIR"
    fi
    
    # Example: Access user's working directory
    echo "User working directory: $WORKING_DIR"
    
    # Your tool logic goes here
    echo "Tool execution completed"
}

# Run main function with all arguments
main "$@"
```

## 总结

### Shell 工具开发要点

**OpsKit 提供的环境变量**：
- `OPSKIT_BASE_PATH`: OpsKit 框架根目录
- `OPSKIT_TOOL_TEMP_DIR`: 工具专属临时目录
- `OPSKIT_WORKING_DIR`: 用户当前工作目录
- `TOOL_NAME`: 工具显示名称
- `TOOL_VERSION`: 工具版本号

**工具开发自由度**：
- 工具可以自行决定实现哪些功能（日志、用户交互、错误处理等）
- 工具可以自行选择依赖和实现方式
- 工具可以自定义配置项和命令行参数
- OpsKit 仅提供基础的环境变量注入，不强制任何实现模式

**文件结构**：
- `CLAUDE.md`（必需）- 工具开发指南
- `main.sh`（必需，可执行）- 主程序文件
- `.env`（可选）- 默认配置文件
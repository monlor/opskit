# Shell 工具开发指南

本文档提供了在 OpsKit 框架中开发 Shell 工具的关键规则和特定要求。

## 目录

1. [工具结构标准](#工具结构标准)
2. [OpsKit 特定规则](#opskit-特定规则)
3. [公共库集成](#公共库集成)
4. [配置管理](#配置管理)
5. [工具模板](#工具模板)

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

## OpsKit 特定规则

### ✅ 必须遵循的规则

**1. 公共库导入模式**
```bash
#!/bin/bash

# Source OpsKit common shell libraries
source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
source "${OPSKIT_BASE_PATH}/common/shell/utils.sh"
source "${OPSKIT_BASE_PATH}/common/shell/storage.sh"  # 如果需要存储功能
source "${OPSKIT_BASE_PATH}/common/shell/interactive.sh"  # 如果需要交互功能
```

**2. 使用 OpsKit 环境变量**
```bash
# OPSKIT_BASE_PATH - OpsKit 安装根目录
# OPSKIT_TOOL_NAME - 当前工具名称 (由框架注入)
# OPSKIT_TOOL_TEMP_DIR - 工具专属临时目录
# TOOL_NAME - 工具显示名称 (由框架注入)
# TOOL_VERSION - 工具版本 (由框架注入)
```

**3. 配置读取规范**
```bash
# 使用 get_env_var() 函数获取配置，支持类型转换
TIMEOUT=$(get_env_var "TIMEOUT" "30" "int")
DEBUG=$(get_env_var "DEBUG" "false" "bool")
HOST=$(get_env_var "HOST" "localhost" "str")
MAX_RETRIES=$(get_env_var "MAX_RETRIES" "3" "int")
```

**4. 工具生命周期管理**
```bash
main() {
    # 工具启动
    tool_start "$TOOL_NAME"
    
    # 主要逻辑
    step_start "Checking dependencies"
    # ... 依赖检查逻辑
    step_complete "Checking dependencies"
    
    step_start "Performing main operation"
    # ... 主要操作逻辑
    step_complete "Performing main operation"
    
    # 工具完成
    tool_complete "$TOOL_NAME"
}
```

**5. 标准化的文件头**
```bash
#!/bin/bash

# Tool Name
# Brief description of what the tool does

# Load OpsKit common shell libraries
source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
source "${OPSKIT_BASE_PATH}/common/shell/utils.sh"
```

### ❌ 禁止的做法

**1. 不要手动设置 OPSKIT_BASE_PATH**
```bash
# ❌ 错误
export OPSKIT_BASE_PATH="/path/to/opskit"

# ✅ 正确 - 使用环境变量（由框架自动设置）
source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
```

**2. 不要定义版本号或工具名**
```bash
# ❌ 错误
TOOL_NAME="My Tool"
TOOL_VERSION="1.0.0"

# ✅ 正确 - 使用框架注入的变量
tool_start "$TOOL_NAME"
```

**3. 不要使用 echo 进行日志输出**
```bash
# ❌ 错误
echo "INFO: Starting operation"
echo "ERROR: Operation failed"

# ✅ 正确
log_info "Starting operation"
log_error "Operation failed"
```

**4. 不要使用相对路径导入公共库**
```bash
# ❌ 错误
source "../../../common/shell/logger.sh"

# ✅ 正确
source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
```

## 公共库集成

### 日志系统 (logger.sh)

#### 基本日志函数
```bash
log_debug "Debug message"      # 调试信息
log_info "Information"         # 一般信息  
log_warn "Warning message"     # 警告信息
log_error "Error occurred"     # 错误信息
log_fatal "Critical error"     # 致命错误
```

#### 工具生命周期函数
```bash
tool_start "tool-name"         # 工具开始
tool_complete "tool-name"      # 工具完成
tool_error "tool-name" "error" # 工具出错
```

#### 步骤进度函数
```bash
step_start "Checking system"   # 步骤开始
step_complete "System ready"   # 步骤完成
step_error "Check failed" "reason"  # 步骤失败
```

#### 系统操作函数
```bash
dependency_check "curl" "found"          # 依赖检查
config_loaded "/path/to/config"          # 配置加载
network_operation "GET" "api.example.com" "success"  # 网络操作
file_operation "read" "/tmp/file" "success"           # 文件操作
```

#### 工具函数
```bash
die "Fatal error occurred" 1              # 错误退出
success_exit "Operation completed"        # 成功退出
```

### 工具函数库 (utils.sh)

#### 环境变量处理
```bash
# 获取环境变量并进行类型转换
get_env_var "KEY" "default_value" "type"

# 类型支持: str, int, bool, float
TIMEOUT=$(get_env_var "TIMEOUT" "30" "int")
DEBUG=$(get_env_var "DEBUG" "false" "bool")
RATE=$(get_env_var "RATE" "1.5" "float")
```

#### 命令和依赖检查
```bash
# 检查命令是否存在
if command_exists "curl"; then
    log_info "curl is available"
fi

# 检查单个命令并显示提示
check_command "mysql" "Please install MySQL client"

# 检查多个命令
check_commands "curl" "jq" "grep"
```

#### 文件和目录操作
```bash
# 确保目录存在
ensure_dir "/tmp/myapp" "755"

# 获取文件大小
size=$(get_file_size "/path/to/file")

# 创建安全文件名
safe_name=$(safe_filename "my file name.txt")  # 返回: my_file_name.txt
```

#### 字符串处理
```bash
# 去除首尾空格
clean_text=$(trim "  hello world  ")

# 检查字符串是否为空
if is_empty "$var"; then
    log_warn "Variable is empty"
fi

# 检查是否为数字
if is_numeric "$input"; then
    log_info "Valid number: $input"
fi
```

#### 时间和日期
```bash
# 获取时间戳
timestamp=$(get_timestamp)

# 获取 ISO 格式时间戳
iso_time=$(get_iso_timestamp)

# 计算时间差
start_time=$(get_timestamp)
# ... 执行操作
end_time=$(get_timestamp)
duration=$(time_diff "$start_time" "$end_time")
log_info "Operation took $duration"
```

### 交互式组件 (interactive.sh)

#### 用户输入和确认
```bash
# 获取用户输入（带验证）
username=$(get_user_input "Enter username" "admin" true "validate_username")

# 用户确认
if confirm "Continue with operation?" true; then
    log_info "User confirmed"
fi

# 从列表中选择
selected=$(select_from_list "Choose option:" "option1,option2,option3")

# 删除确认
if delete_confirmation "connection" "test-db"; then
    log_info "User confirmed deletion"
fi
```

#### 内置验证器
```bash
# 邮箱验证
email=$(get_user_input "Enter email" "" true "validate_email")

# IP 地址验证
ip_addr=$(get_user_input "Enter IP address" "127.0.0.1" true "validate_ip")

# 端口验证
port=$(get_user_input "Enter port" "3306" true "validate_port")

# 自定义验证器
validate_username() {
    [[ "$1" =~ ^[a-zA-Z][a-zA-Z0-9_]{2,19}$ ]]
}
username=$(get_user_input "Enter username" "" true "validate_username")
```

#### 系统信息
```bash
# 检测操作系统
os=$(detect_os)  # 返回: macos, linux, windows, unknown

# 检查是否在交互模式
if is_interactive; then
    log_info "Running in interactive mode"
fi

# 获取终端宽度
width=$(get_terminal_width)
```

#### 进程管理
```bash
# 带超时运行命令
run_with_timeout "10" "curl" "-s" "http://example.com"
```

#### 工具信息显示
```bash
# 显示工具信息横幅
show_tool_info "$TOOL_NAME" "$TOOL_VERSION" "Tool description"
```

### 存储系统 (storage.sh)

#### 基本存储操作
```bash
# 获取存储命名空间
storage=$(get_storage "my-tool")

# 存储键值对
storage_set "my-tool" "server_host" "localhost"

# 获取值
host=$(storage_get "my-tool" "server_host" "127.0.0.1")

# 检查键是否存在
if storage_exists "my-tool" "server_host"; then
    log_info "Host configuration found"
fi

# 删除键
storage_delete "my-tool" "old_setting"

# 列出所有键
storage_keys "my-tool"

# 清空命名空间
count=$(storage_clear "my-tool")
log_info "Cleared $count entries"

# 获取键数量
size=$(storage_size "my-tool")
```

#### 工具配置存储
```bash
# 存储工具配置
store_tool_config "mysql-sync" "default_db" "production"

# 获取工具配置
db=$(get_tool_config "mysql-sync" "default_db" "test")
```

#### 执行结果存储
```bash
# 存储执行结果
execution_id=$(date +%s)
store_execution_result "backup-tool" "$execution_id" "success"

# 获取执行结果
result=$(get_execution_result "backup-tool" "$execution_id" "unknown")
```

## 配置管理

### 环境变量规范

#### OpsKit 系统环境变量

**框架注入的变量（只读）**:
- `OPSKIT_BASE_PATH`: OpsKit 安装根目录
- `OPSKIT_TOOL_NAME`: 当前工具内部名称（如：mysql-sync）
- `OPSKIT_TOOL_TEMP_DIR`: 工具专属临时目录
- `TOOL_NAME`: 工具显示名称（如：MySQL Sync Tool）
- `TOOL_VERSION`: 工具版本号（如：1.2.0）

#### 临时文件目录环境变量

**OPSKIT_TOOL_TEMP_DIR**

OpsKit 为每个工具提供一个独立的临时目录：

```bash
# 获取工具专属临时目录
temp_dir="${OPSKIT_TOOL_TEMP_DIR}"

# 在临时目录创建文件
if [[ -n "$temp_dir" ]]; then
    temp_file="$temp_dir/my_temp_file.txt"
    echo "Temporary data" > "$temp_file"
    log_info "Created temp file: $temp_file"
fi
```

**重要特点**：
- 每个工具运行时都有独立的临时目录
- 目录由 OpsKit 框架自动创建和管理  
- 目录路径通过 `OPSKIT_TOOL_TEMP_DIR` 环境变量提供
- 不保证目录在工具运行后自动清理
- 不要存储敏感或需要长期保存的数据

### .env 文件格式
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
# 使用 get_env_var() 函数，支持类型转换和默认值
TIMEOUT=$(get_env_var "TIMEOUT" "30" "int")
DEBUG=$(get_env_var "DEBUG" "false" "bool")
HOST=$(get_env_var "HOST" "localhost" "str")
MAX_RETRIES=$(get_env_var "MAX_RETRIES" "3" "int")
RATE_LIMIT=$(get_env_var "RATE_LIMIT" "1.0" "float")
```

## 工具模板

```bash
#!/bin/bash

# My Tool - Shell Implementation
# Description of what this tool does

# Load OpsKit common shell libraries
source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
source "${OPSKIT_BASE_PATH}/common/shell/utils.sh"
source "${OPSKIT_BASE_PATH}/common/shell/storage.sh"
source "${OPSKIT_BASE_PATH}/common/shell/interactive.sh"

# Tool configuration using environment variables
DEBUG=$(get_env_var "DEBUG" "false" "bool")
TIMEOUT=$(get_env_var "TIMEOUT" "30" "int")
MAX_RETRIES=$(get_env_var "MAX_RETRIES" "3" "int")
HOST=$(get_env_var "HOST" "localhost" "str")

# Initialize storage if needed
STORAGE_NAMESPACE="my-tool"

# Help function
show_help() {
    cat << EOF
Usage: $0 [options]

Description:
    Brief description of what this tool does

Options:
    -h, --help           Show this help message
    --host HOST          Target host (default: $HOST)
    --timeout SECONDS    Connection timeout (default: $TIMEOUT)

Environment Variables:
    DEBUG               Enable debug output (default: false)
    TIMEOUT             Operation timeout in seconds (default: 30)
    MAX_RETRIES         Maximum retry attempts (default: 3)
    HOST                Target host (default: localhost)

Examples:
    $0 --host example.com --timeout 60
    DEBUG=true $0 --host localhost
    
EOF
}

# Dependency checks
check_dependencies() {
    step_start "Checking system dependencies"
    
    # Check required system commands
    local required_commands=("curl" "jq")
    
    if ! check_commands "${required_commands[@]}"; then
        step_error "Dependency check failed" "Missing required commands"
        return 1
    fi
    
    step_complete "All dependencies are available"
    return 0
}

# Validate configuration
validate_config() {
    step_start "Validating configuration"
    
    # Validate host
    if is_empty "$HOST"; then
        step_error "Configuration validation" "Host cannot be empty"
        return 1
    fi
    
    # Validate timeout
    if ! is_numeric "$TIMEOUT" || [[ $TIMEOUT -lt 1 ]]; then
        step_error "Configuration validation" "Timeout must be a positive number"
        return 1
    fi
    
    # Log configuration if debug enabled
    if [[ "$DEBUG" == "true" ]]; then
        log_debug "Configuration loaded:"
        log_debug "  HOST=$HOST"
        log_debug "  TIMEOUT=$TIMEOUT"
        log_debug "  MAX_RETRIES=$MAX_RETRIES"
        log_debug "  TEMP_DIR=${OPSKIT_TOOL_TEMP_DIR}"
    fi
    
    step_complete "Configuration is valid"
    return 0
}

# Main tool operation
perform_main_operation() {
    step_start "Performing main operation"
    
    local attempt=1
    local success=false
    
    while [[ $attempt -le $MAX_RETRIES ]] && [[ "$success" != "true" ]]; do
        log_info "Attempt $attempt of $MAX_RETRIES"
        
        # Simulate main operation with timeout
        if run_with_timeout "$TIMEOUT" curl -s "http://$HOST" >/dev/null; then
            log_info "✅ Operation successful"
            success=true
            
            # Store result in storage
            execution_id=$(get_timestamp)
            store_execution_result "$OPSKIT_TOOL_NAME" "$execution_id" "success"
            
        else
            log_warn "⚠️  Attempt $attempt failed"
            ((attempt++))
            
            if [[ $attempt -le $MAX_RETRIES ]]; then
                log_info "Retrying in 2 seconds..."
                sleep 2
            fi
        fi
    done
    
    if [[ "$success" == "true" ]]; then
        step_complete "Main operation completed successfully"
        return 0
    else
        step_error "Main operation" "Failed after $MAX_RETRIES attempts"
        return 1
    fi
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --host)
                HOST="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Main function
main() {
    # Start tool execution
    tool_start "$TOOL_NAME"
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Check dependencies
    if ! check_dependencies; then
        tool_error "$TOOL_NAME" "Dependency check failed"
        exit 1
    fi
    
    # Validate configuration
    if ! validate_config; then
        tool_error "$TOOL_NAME" "Configuration validation failed"
        exit 1
    fi
    
    # Perform main operation
    if ! perform_main_operation; then
        tool_error "$TOOL_NAME" "Main operation failed"
        exit 1
    fi
    
    # Tool completed successfully
    tool_complete "$TOOL_NAME"
}

# Handle Ctrl+C gracefully
trap 'log_warn "Operation cancelled by user"; tool_error "$TOOL_NAME" "Cancelled"; exit 130' INT

# Run main function with all arguments
main "$@"
```

## 错误处理和调试

### 标准错误处理模式
```bash
# 设置错误处理
set -euo pipefail  # 可选：启用严格模式

# 捕获信号
trap 'cleanup; exit 130' INT TERM

cleanup() {
    log_info "Cleaning up temporary files"
    [[ -n "${temp_file:-}" ]] && rm -f "$temp_file"
}

# 错误检查模式
if ! command_that_might_fail; then
    log_error "Command failed"
    cleanup
    exit 1
fi

# 或使用 die 函数
command_that_might_fail || die "Command failed" 1
```

### 调试模式支持
```bash
# 启用调试模式
if [[ "$DEBUG" == "true" ]]; then
    set -x  # 启用命令跟踪
    log_debug "Debug mode enabled"
fi

# 调试日志
log_debug "Processing file: $filename"
log_debug "Current state: $state"
```

## 性能和最佳实践

### 高效的 Shell 编程
```bash
# 使用数组而不是字符串处理列表
declare -a files=()
files+=("file1.txt")
files+=("file2.txt")

# 避免不必要的子shell
count=0
while read -r line; do
    ((count++))
done < "$file"

# 使用内置命令
[[ -n "$var" ]]  # 而不是 test -n "$var"
```

### 并发处理
```bash
# 简单的并发任务
process_file() {
    local file="$1"
    log_debug "Processing $file"
    # 处理逻辑
}

# 并发执行
for file in "${files[@]}"; do
    process_file "$file" &
done
wait  # 等待所有后台任务完成
```

## 交互式组件参考

详细的交互式组件使用方法请参考：[交互式组件使用指南](interactive-components-guide.md)

该指南包含：
- Python 和 Shell 版本的完整 API 文档
- 使用示例和最佳实践
- 内置验证器说明
- 组件对比表

## 总结

### Shell 工具开发核心要点

**必须遵循**：
- 使用标准的公共库导入模式
- 使用 `get_env_var()` 获取配置，支持类型转换
- 使用交互式组件进行用户交互，不要自行实现输入/确认逻辑
- 不要定义工具名称和版本（由框架管理）
- 使用 OpsKit 的日志和存储系统
- 遵循工具生命周期管理

**公共库功能**：
- **logger.sh**: 统一日志系统、工具生命周期、步骤管理
- **utils.sh**: 环境变量处理、命令检查、文件操作、字符串处理、系统信息
- **storage.sh**: 键值存储、工具配置、执行结果存储
- **interactive.sh**: 用户交互组件、输入验证、选择列表、确认对话框

**环境变量**：
- `OPSKIT_BASE_PATH`: 框架根目录
- `OPSKIT_TOOL_NAME`: 工具内部名称
- `OPSKIT_TOOL_TEMP_DIR`: 工具临时目录
- `TOOL_NAME`: 工具显示名称
- `TOOL_VERSION`: 工具版本

**文件结构**：
- `CLAUDE.md`（必需）
- `main.sh`（必需，可执行）
- `.env`（可选配置）
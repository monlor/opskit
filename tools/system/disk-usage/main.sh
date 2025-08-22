#!/bin/bash

# Disk Usage Analysis Tool - OpsKit Version
# Displays disk usage information with configurable thresholds and formatting.
# All configuration is loaded from environment variables.

# 获取 OpsKit 环境变量
OPSKIT_TOOL_TEMP_DIR="${OPSKIT_TOOL_TEMP_DIR:-$(pwd)/.disk-usage-temp}"
OPSKIT_BASE_PATH="${OPSKIT_BASE_PATH:-$HOME/.opskit}"
OPSKIT_WORKING_DIR="${OPSKIT_WORKING_DIR:-$(pwd)}"
TOOL_NAME="${TOOL_NAME:-disk-usage}"
TOOL_VERSION="${TOOL_VERSION:-1.0.0}"

# 创建临时目录
mkdir -p "$OPSKIT_TOOL_TEMP_DIR"

# 无需额外的日志函数，直接使用 echo

# 获取环境变量的简单函数
get_env_var() {
    local var_name="$1"
    local default_value="$2"
    echo "${!var_name:-$default_value}"
}

# Load configuration from environment variables with defaults
SHOW_PERCENTAGE=$(get_env_var "SHOW_PERCENTAGE" "true")
SHOW_HUMAN_READABLE=$(get_env_var "SHOW_HUMAN_READABLE" "true")
SHOW_FILESYSTEM_TYPE=$(get_env_var "SHOW_FILESYSTEM_TYPE" "false")
SORT_BY_USAGE=$(get_env_var "SORT_BY_USAGE" "true")
WARNING_THRESHOLD=$(get_env_var "WARNING_THRESHOLD" "80")
CRITICAL_THRESHOLD=$(get_env_var "CRITICAL_THRESHOLD" "95")
ALERT_ON_THRESHOLD=$(get_env_var "ALERT_ON_THRESHOLD" "true")
OUTPUT_FORMAT=$(get_env_var "OUTPUT_FORMAT" "table")
SHOW_HEADER=$(get_env_var "SHOW_HEADER" "true")
MAX_ENTRIES=$(get_env_var "MAX_ENTRIES" "20")
TIMEOUT=$(get_env_var "TIMEOUT" "10")
EXCLUDE_TMPFS=$(get_env_var "EXCLUDE_TMPFS" "true")
EXCLUDE_PROC=$(get_env_var "EXCLUDE_PROC" "true")


get_disk_usage() {
    local df_options=""
    
    # Add human readable option if enabled
    if [[ "$SHOW_HUMAN_READABLE" == "true" ]]; then
        df_options="$df_options -h"
    fi
    
    # Add filesystem type if enabled
    if [[ "$SHOW_FILESYSTEM_TYPE" == "true" ]]; then
        df_options="$df_options -T"
    fi
    
    # Get disk usage data
    local df_output
    if ! df_output=$(timeout "$TIMEOUT" df $df_options 2>/dev/null); then
        echo "❌ 获取磁盘使用信息失败"
        return 1
    fi
    
    echo "$df_output"
}

parse_usage_percentage() {
    local line="$1"
    local usage_field
    
    if [[ "$SHOW_FILESYSTEM_TYPE" == "true" ]]; then
        # With filesystem type: filesystem type size used avail use% mount
        usage_field=$(echo "$line" | awk '{print $6}' | sed 's/%//')
    else
        # Without filesystem type: filesystem size used avail use% mount
        usage_field=$(echo "$line" | awk '{print $5}' | sed 's/%//')
    fi
    
    echo "$usage_field"
}

get_mount_point() {
    local line="$1"
    
    if [[ "$SHOW_FILESYSTEM_TYPE" == "true" ]]; then
        echo "$line" | awk '{print $7}'
    else
        echo "$line" | awk '{print $6}'
    fi
}

get_filesystem() {
    local line="$1"
    echo "$line" | awk '{print $1}'
}

check_thresholds() {
    local usage="$1"
    local mount="$2"
    
    if [[ "$ALERT_ON_THRESHOLD" != "true" ]]; then
        return 0
    fi
    
    if [[ -n "$usage" && "$usage" =~ ^[0-9]+$ ]]; then
        if [[ $usage -ge $CRITICAL_THRESHOLD ]]; then
            echo "❌ $mount 使用率 ${usage}% (危险)"
        elif [[ $usage -ge $WARNING_THRESHOLD ]]; then
            echo "⚠️  $mount 使用率 ${usage}% (警告)"
        fi
    fi
}

format_output() {
    local df_data="$1"
    
    case "$OUTPUT_FORMAT" in
        "json")
            format_json "$df_data"
            ;;
        "csv")
            format_csv "$df_data"
            ;;
        *)
            format_table "$df_data"
            ;;
    esac
}

format_table() {
    local df_data="$1"
    local line_count=0
    
    if [[ "$SHOW_HEADER" == "true" ]]; then
        echo ""
        echo "📊 文件系统使用报告"
        echo "-" * 50
        echo "$(echo "$df_data" | head -1)"
        echo "----------------------------------------"
    fi
    
    # Process each line (skip header)
    echo "$df_data" | tail -n +2 | while IFS= read -r line; do
        # Skip empty lines
        [[ -z "$line" ]] && continue
        
        # Filter out unwanted filesystems
        local filesystem
        filesystem=$(get_filesystem "$line")
        
        if [[ "$EXCLUDE_TMPFS" == "true" && "$filesystem" =~ tmpfs ]]; then
            continue
        fi
        
        if [[ "$EXCLUDE_PROC" == "true" && "$filesystem" =~ ^(proc|sys|dev) ]]; then
            continue
        fi
        
        # Check entry limit
        ((line_count++))
        if [[ $line_count -gt $MAX_ENTRIES ]]; then
            echo "... (显示前 $MAX_ENTRIES 条记录)"
            break
        fi
        
        local usage_percent
        usage_percent=$(parse_usage_percentage "$line")
        
        local mount_point
        mount_point=$(get_mount_point "$line")
        
        # Color code based on usage (simplified without color codes)
        local status=""
        if [[ -n "$usage_percent" && "$usage_percent" =~ ^[0-9]+$ ]]; then
            if [[ $usage_percent -ge $CRITICAL_THRESHOLD ]]; then
                status="🔴"
            elif [[ $usage_percent -ge $WARNING_THRESHOLD ]]; then
                status="🟡"
            else
                status="🟢"
            fi
        fi
        
        echo "${status} $line"
        
        # Check thresholds and alert
        check_thresholds "$usage_percent" "$mount_point"
    done
}

format_json() {
    local df_data="$1"
    local json_output="["
    local first=true
    
    echo "$df_data" | tail -n +2 | while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        
        local filesystem mount_point usage_percent
        filesystem=$(get_filesystem "$line")
        mount_point=$(get_mount_point "$line")
        usage_percent=$(parse_usage_percentage "$line")
        
        if [[ "$first" != "true" ]]; then
            json_output="$json_output,"
        fi
        first=false
        
        json_output="$json_output{\"filesystem\":\"$filesystem\",\"mount\":\"$mount_point\",\"usage\":$usage_percent}"
    done
    
    json_output="$json_output]"
    echo "$json_output"
}

format_csv() {
    local df_data="$1"
    
    if [[ "$SHOW_HEADER" == "true" ]]; then
        echo "Filesystem,Mount,Usage%"
    fi
    
    echo "$df_data" | tail -n +2 | while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        
        local filesystem mount_point usage_percent
        filesystem=$(get_filesystem "$line")
        mount_point=$(get_mount_point "$line")
        usage_percent=$(parse_usage_percentage "$line")
        
        echo "$filesystem,$mount_point,$usage_percent"
    done
}

main() {
    echo "📊 磁盘使用分析工具"
    echo "=" * 50
    echo "⚙️  工具版本: $TOOL_VERSION"
    echo "📂 临时目录: $OPSKIT_TOOL_TEMP_DIR"
    echo "📁 工作目录: $OPSKIT_WORKING_DIR"
    echo ""
    
    # Show configuration info
    echo "⚙️  配置信息"
    echo "-" * 30
    echo "🚨 警告阈值: ${WARNING_THRESHOLD}%"
    echo "💥 危险阈值: ${CRITICAL_THRESHOLD}%"
    echo "📋 输出格式: $OUTPUT_FORMAT"
    echo "⏱️  超时时间: ${TIMEOUT}s"
    echo "📏 人类可读: $SHOW_HUMAN_READABLE"
    echo "🚫 排除TmpFS: $EXCLUDE_TMPFS"
    echo ""
    
    # Get disk usage information
    echo "🔍 正在获取磁盘使用信息..."
    local disk_data
    if ! disk_data=$(get_disk_usage); then
        echo "❌ 获取磁盘使用数据失败"
        exit 1
    fi
    echo "✅ 磁盘使用数据获取成功"
    
    # Format and display output
    echo "📋 正在格式化并显示输出..."
    format_output "$disk_data"
    echo "✅ 输出格式化并显示完成"
    
    echo ""
    echo "✅ 磁盘使用分析完成"
}

# Handle help flag
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "📊 磁盘使用分析工具 - 帮助信息"
    echo "=" * 50
    echo "用法: $0 [选项]"
    echo ""
    echo "环境变量:"
    echo "  WARNING_THRESHOLD    - 警告阈值百分比 (默认: 80)"
    echo "  CRITICAL_THRESHOLD   - 危险阈值百分比 (默认: 95)"
    echo "  OUTPUT_FORMAT        - 输出格式: table, json, csv (默认: table)"
    echo "  SHOW_HEADER         - 显示表头 (默认: true)"
    echo "  MAX_ENTRIES         - 最大显示条数 (默认: 20)"
    echo "  TIMEOUT             - 命令超时秒数 (默认: 10)"
    echo ""
    echo "使用示例:"
    echo "  $0                              # 使用默认设置"
    echo "  WARNING_THRESHOLD=90 $0         # 自定义警告阈值"
    echo "  OUTPUT_FORMAT=json $0           # JSON格式输出"
    exit 0
fi

# Run main function with error handling
if ! main "$@"; then
    echo "❌ 磁盘使用分析失败"
    exit 1
fi
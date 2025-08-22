#!/bin/bash

# Port Scanner Tool - OpsKit Version
# Simple network port scanner with visual output

# 获取 OpsKit 环境变量
OPSKIT_TOOL_TEMP_DIR="${OPSKIT_TOOL_TEMP_DIR:-$(pwd)/.port-scanner-temp}"
OPSKIT_BASE_PATH="${OPSKIT_BASE_PATH:-$HOME/.opskit}"
OPSKIT_WORKING_DIR="${OPSKIT_WORKING_DIR:-$(pwd)}"
TOOL_NAME="${TOOL_NAME:-port-scanner}"
TOOL_VERSION="${TOOL_VERSION:-1.0.0}"

# 创建临时目录
mkdir -p "$OPSKIT_TOOL_TEMP_DIR"

# 日志函数
log_info() {
    echo "🔍 [INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_success() {
    echo "✅ [SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_warning() {
    echo "⚠️  [WARNING] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_error() {
    echo "❌ [ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

# Default configuration
DEFAULT_HOST="localhost"
DEFAULT_PORTS="1-1000"
DEFAULT_PROTOCOL="tcp"
DEFAULT_TIMEOUT="1"
DEFAULT_THREADS="100"

# Environment variables are loaded from .env via core/env automatically

# Configuration with environment variable support
HOST="${HOST:-$DEFAULT_HOST}"
PORTS="${PORTS:-$DEFAULT_PORTS}"
PROTOCOL="${PROTOCOL:-$DEFAULT_PROTOCOL}"
TIMEOUT="${TIMEOUT:-$DEFAULT_TIMEOUT}"
THREADS="${THREADS:-$DEFAULT_THREADS}"

# Arrays for results
declare -a open_ports=()
declare -a closed_ports=()

# Helper functions
usage() {
    echo "🔍 端口扫描工具 - 使用说明"
    echo "=" * 50
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --host HOST      目标主机 (默认: $DEFAULT_HOST)"
    echo "  -p, --ports RANGE    端口范围 (默认: $DEFAULT_PORTS)"
    echo "  -t, --timeout SEC    连接超时 (默认: $DEFAULT_TIMEOUT)"
    echo "  --help              显示此帮助"
    echo ""
    echo "示例:"
    echo "  $0 -h 192.168.1.1 -p 80,443,22"
    echo "  $0 -h localhost -p 1-65535"
    echo "  $0 --host example.com --ports 80,443,8080,3000"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--ports)
            PORTS="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            usage
            exit 1
            ;;
    esac
done

# Service mapping for common ports
get_service_name() {
    local port=$1
    case $port in
        21) echo "ftp" ;;
        22) echo "ssh" ;;
        23) echo "telnet" ;;
        25) echo "smtp" ;;
        53) echo "dns" ;;
        80) echo "http" ;;
        110) echo "pop3" ;;
        143) echo "imap" ;;
        443) echo "https" ;;
        993) echo "imaps" ;;
        995) echo "pop3s" ;;
        3306) echo "mysql" ;;
        5432) echo "postgresql" ;;
        6379) echo "redis" ;;
        27017) echo "mongodb" ;;
        *) echo "unknown" ;;
    esac
}

# Validate host
validate_host() {
    local host="$1"
    if [[ -z "$host" ]]; then
        log_error "主机地址不能为空"
        return 1
    fi
    
    # Try to resolve hostname
    if ! getent hosts "$host" >/dev/null 2>&1; then
        log_warning "无法解析主机名 '$host'，继续尝试"
    fi
    
    return 0
}

# Parse port range
parse_ports() {
    local port_spec="$1"
    local -a ports=()
    
    # Split by comma
    IFS=',' read -ra PORT_RANGES <<< "$port_spec"
    
    for range in "${PORT_RANGES[@]}"; do
        if [[ "$range" =~ ^[0-9]+$ ]]; then
            # Single port
            if [[ $range -ge 1 && $range -le 65535 ]]; then
                ports+=("$range")
            else
                log_error "无效端口: $range (必须是 1-65535)"
                return 1
            fi
        elif [[ "$range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            # Port range
            local start="${BASH_REMATCH[1]}"
            local end="${BASH_REMATCH[2]}"
            
            if [[ $start -ge 1 && $start -le 65535 && $end -ge 1 && $end -le 65535 && $start -le $end ]]; then
                for ((port=start; port<=end; port++)); do
                    ports+=("$port")
                done
            else
                log_error "无效端口范围: $range"
                return 1
            fi
        else
            log_error "无效端口格式: $range"
            return 1
        fi
    done
    
    # Remove duplicates and sort
    printf '%s\n' "${ports[@]}" | sort -n | uniq
}

# Test single port
test_port() {
    local host="$1"
    local port="$2"
    local timeout="$3"
    
    if timeout "$timeout" bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
        return 0  # Port is open
    else
        return 1  # Port is closed
    fi
}

# Scan ports with progress indication
scan_ports() {
    local host="$1"
    local port_list="$2"
    local -a ports_to_scan=()
    
    # Read ports from string parameter
    while IFS= read -r port; do
        [[ -n "$port" ]] && ports_to_scan+=("$port")
    done <<< "$port_list"
    
    local total=${#ports_to_scan[@]}
    local scanned=0
    local progress_step=$((total / 20))  # Show progress every 5%
    
    if [[ $progress_step -eq 0 ]]; then
        progress_step=1
    fi
    
    log_info "开始扫描 $host 端口 ${PORTS} ($PROTOCOL)"
    
    for port in "${ports_to_scan[@]}"; do
        ((scanned++))
        
        if test_port "$host" "$port" "$TIMEOUT"; then
            local service=$(get_service_name "$port")
            open_ports+=("$port:$service")
        else
            closed_ports+=("$port")
        fi
        
        # Show progress
        if [[ $((scanned % progress_step)) -eq 0 ]] || [[ $scanned -eq $total ]]; then
            local percentage=$((scanned * 100 / total))
            echo "⏳ 进度: $percentage% ($scanned/$total 个端口已扫描)"
        fi
    done
    
    log_success "扫描完成: ${#open_ports[@]} 个开放端口, ${#closed_ports[@]} 个关闭端口"
}

# Display results in visual format
display_results() {
    local host="$1"
    
    echo ""
    echo "🔍 $host 的端口扫描结果"
    echo "=" * 50
    
    if [[ ${#open_ports[@]} -gt 0 ]]; then
        echo ""
        echo "🟢 发现开放端口"
        echo "┌─────────┬─────────────┬─────────────────────────────────┐"
        echo "│  端口   │    状态     │            服务                 │"
        echo "├─────────┼─────────────┼─────────────────────────────────┤"
        
        for port_info in "${open_ports[@]}"; do
            local port="${port_info%:*}"
            local service="${port_info#*:}"
            printf "│  %-5s  │    开放     │  %-29s  │\n" "$port" "$service"
        done
        
        echo "└─────────┴─────────────┴─────────────────────────────────┘"
    else
        echo ""
        log_warning "🟡 在指定范围内未发现开放端口"
    fi
    
    # Summary
    local total_scanned=$((${#open_ports[@]} + ${#closed_ports[@]}))
    echo ""
    echo "📊 扫描统计"
    echo "-" * 30
    echo "🌐 主机: $host"
    echo "🔢 端口范围: $PORTS"
    echo "🔌 协议: $PROTOCOL"
    echo "📈 总扫描数: $total_scanned"
    echo "✅ 开放端口: ${#open_ports[@]}"
    echo "❌ 关闭端口: ${#closed_ports[@]}"
}

# Main execution
main() {
    echo "🔍 端口扫描工具"
    echo "=" * 50
    echo "⚙️  工具版本: $TOOL_VERSION"
    echo "📂 临时目录: $OPSKIT_TOOL_TEMP_DIR"
    echo "📁 工作目录: $OPSKIT_WORKING_DIR"
    echo ""
    
    # Validation phase
    log_info "检查系统要求"
    if ! command -v timeout >/dev/null 2>&1; then
        log_error "未找到 timeout 命令。请安装 coreutils。"
        exit 1
    fi
    log_success "系统要求检查完成"
    
    log_info "验证输入参数"
    if ! validate_host "$HOST"; then
        exit 1
    fi
    log_success "输入参数验证完成"
    
    # Parse and validate ports
    local port_list
    if ! port_list=$(parse_ports "$PORTS"); then
        exit 1
    fi
    
    # Scan phase
    log_info "开始端口扫描"
    scan_ports "$HOST" "$port_list"
    log_success "端口扫描完成"
    
    # Display results
    display_results "$HOST"
    
    echo ""
    log_success "✅ 端口扫描任务完成"
}

# Run main function with error handling
if ! main "$@"; then
    log_error "端口扫描失败"
    exit 1
fi
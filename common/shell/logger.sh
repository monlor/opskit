#!/bin/bash
# OpsKit Shell Specialized Logger Functions
# Provides concise logging interface

# Check if common library is already loaded
if [[ -z "${OPSKIT_SHELL_LIB_DIR:-}" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    source "$SCRIPT_DIR/common.sh"
fi

# ==================== Specialized Logging Functions ====================

# Tool startup log
tool_start() {
    local tool_name="$1"
    log_info "🚀 Starting tool: $tool_name"
}

# Tool completion log
tool_complete() {
    local tool_name="$1"
    local duration="${2:-}"
    
    if [[ -n "$duration" ]]; then
        log_info "✅ Tool $tool_name execution completed (duration: $duration)"
    else
        log_info "✅ Tool $tool_name execution completed"
    fi
}

# Tool failure log
tool_error() {
    local tool_name="$1"
    local error_msg="$2"
    log_error "❌ Tool $tool_name execution failed: $error_msg"
}

# Step start log
step_start() {
    local step_name="$1"
    log_info "📋 Starting: $step_name"
}

# Step completion log
step_complete() {
    local step_name="$1"
    log_info "✓ Completed: $step_name"
}

# Step failure log
step_error() {
    local step_name="$1"
    local error_msg="$2"
    log_error "✗ $step_name failed: $error_msg"
}

# Dependency check log
dependency_check() {
    local dep_name="$1"
    local status="$2"  # found/missing
    
    case "$status" in
        found)
            log_info "✓ Dependency check: $dep_name"
            ;;
        missing)
            log_warn "✗ Missing dependency: $dep_name"
            ;;
        *)
            log_debug "? Unknown dependency status: $dep_name"
            ;;
    esac
}

# Configuration loaded log
config_loaded() {
    local config_file="$1"
    log_debug "📄 Loaded config: $config_file"
}

# Network operation log
network_operation() {
    local operation="$1"
    local target="$2"
    local status="${3:-start}"
    
    case "$status" in
        start)
            log_info "🌐 $operation: $target"
            ;;
        success)
            log_info "✅ $operation succeeded: $target"
            ;;
        failed)
            log_error "❌ $operation failed: $target"
            ;;
    esac
}

# File operation log
file_operation() {
    local operation="$1"
    local file_path="$2"
    local status="${3:-start}"
    
    case "$status" in
        start)
            log_debug "📁 $operation: $file_path"
            ;;
        success)
            log_debug "✓ $operation succeeded: $file_path"
            ;;
        failed)
            log_error "✗ $operation failed: $file_path"
            ;;
    esac
}

# Installation operation log
install_operation() {
    local package="$1"
    local status="$2"  # start/success/failed
    
    case "$status" in
        start)
            log_info "📦 Installing: $package"
            ;;
        success)
            log_info "✅ Installation succeeded: $package"
            ;;
        failed)
            log_error "❌ Installation failed: $package"
            ;;
    esac
}

# ==================== Logging Functions with Time Tracking ====================

# Global variable to store start times
declare -A TIMER_START_TIMES

# Start timer
timer_start() {
    local timer_name="$1"
    TIMER_START_TIMES["$timer_name"]=$(get_timestamp)
    log_debug "⏱️  Started timer: $timer_name"
}

# Stop timer and record
timer_stop() {
    local timer_name="$1"
    local start_time="${TIMER_START_TIMES[$timer_name]:-}"
    
    if [[ -z "$start_time" ]]; then
        log_warn "Timer $timer_name was not started"
        return 1
    fi
    
    local end_time duration
    end_time=$(get_timestamp)
    duration=$(time_diff "$start_time" "$end_time")
    
    log_info "⏱️  $timer_name duration: $duration"
    
    # Clean up timer
    unset TIMER_START_TIMES["$timer_name"]
    
    echo "$duration"
}

# ==================== Structured Logging ====================

# JSON format logs (for parsing)
log_json() {
    local level="$1"
    local component="$2"
    local message="$3"
    local extra="${4:-{}}"
    
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    
    local log_entry
    log_entry=$(cat << EOF
{
    "timestamp": "$timestamp",
    "level": "$level",
    "component": "$component",
    "message": "$message",
    "extra": $extra
}
EOF
)
    
    # Output to structured log file
    if [[ -n "${OPSKIT_STRUCTURED_LOG:-}" ]]; then
        echo "$log_entry" >> "$OPSKIT_STRUCTURED_LOG"
    fi
    
    # Also output regular log
    _log "$level" "[$component] $message" "$NC"
}

# Structured error log
log_structured_error() {
    local component="$1"
    local error_code="$2"
    local error_msg="$3"
    local context="${4:-{}}"
    
    local extra
    extra=$(cat << EOF
{
    "error_code": "$error_code",
    "context": $context
}
EOF
)
    
    log_json "ERROR" "$component" "$error_msg" "$extra"
}

# ==================== Log Aggregation and Analysis ====================

# Analyze log statistics
analyze_logs() {
    local log_file="${1:-${OPSKIT_LOG_FILE}}"
    
    if [[ ! -f "$log_file" ]]; then
        log_error "Log file does not exist: $log_file"
        return 1
    fi
    
    echo "📊 Log analysis report: $log_file"
    echo "==============================="
    
    # Count logs by level
    echo "Log level statistics:"
    grep -o '\(DEBUG\|INFO\|WARN\|ERROR\|FATAL\):' "$log_file" | sort | uniq -c | while read count level; do
        printf "  %-8s: %s\n" "${level%:}" "$count"
    done
    
    # Recent errors
    echo -e "\nRecent errors (max 10):"
    grep 'ERROR\|FATAL' "$log_file" | tail -10 | while IFS= read -r line; do
        echo "  $line"
    done
    
    # File size
    echo -e "\nLog file size: $(get_file_size "$log_file")"
    
    # Time range
    local first_line last_line
    first_line=$(head -1 "$log_file")
    last_line=$(tail -1 "$log_file")
    
    if [[ -n "$first_line" && -n "$last_line" ]]; then
        echo "Time range: $(echo "$first_line" | cut -d']' -f1 | tr -d '[') to $(echo "$last_line" | cut -d']' -f1 | tr -d '[')"
    fi
}

# Clean up old logs
cleanup_logs() {
    local log_dir="${1:-${OPSKIT_ROOT_DIR}/logs}"
    local days_to_keep="${2:-30}"
    
    if [[ ! -d "$log_dir" ]]; then
        log_warn "Log directory does not exist: $log_dir"
        return 1
    fi
    
    log_info "Cleaning up log files older than $days_to_keep days"
    
    # Find and delete old log files
    find "$log_dir" -name "*.log" -type f -mtime +$days_to_keep -print0 | while IFS= read -r -d '' file; do
        log_debug "Deleting old log: $file"
        rm -f "$file"
    done
    
    log_info "Log cleanup completed"
}

# ==================== Utility Tools ====================

# Output colored banner
print_banner() {
    local text="$1"
    local color="${2:-$CYAN}"
    local width="${3:-60}"
    
    local padding=$(( (width - ${#text}) / 2 ))
    local border=$(printf '=%.0s' $(seq 1 $width))
    
    echo -e "${color}$border${NC}"
    printf "%s%*s%s%*s%s\n" "$color" $padding "" "$text" $padding "" "$NC"
    echo -e "${color}$border${NC}"
}

# Show tool information
show_tool_info() {
    local tool_name="$1"
    local version="${2:-unknown}"
    local description="${3:-No description}"
    
    print_banner "$tool_name v$version" "$BLUE"
    echo -e "${DIM}$description${NC}\n"
}

# Show step progress
show_step_progress() {
    local current="$1"
    local total="$2"
    local step_name="$3"
    
    local percentage=$((current * 100 / total))
    printf "${CYAN}[%2d/%2d] (%3d%%)${NC} %s\n" "$current" "$total" "$percentage" "$step_name"
}

# Error exit
die() {
    local message="$1"
    local exit_code="${2:-1}"
    
    log_fatal "$message"
    exit "$exit_code"
}

# Success exit
success_exit() {
    local message="${1:-Operation completed successfully}"
    
    log_info "🎉 $message"
    exit 0
}

# ==================== Debug Tools ====================

# Debug mode check
is_debug() {
    [[ "${OPSKIT_DEBUG:-0}" == "1" ]]
}

# Debug output
debug_var() {
    local var_name="$1"
    local var_value="${!var_name:-}"
    
    if is_debug; then
        log_debug "Variable $var_name = '$var_value'"
    fi
}

# Debug function call
debug_function() {
    local func_name="$1"
    shift
    local args=("$@")
    
    if is_debug; then
        log_debug "Calling function: $func_name(${args[*]})"
    fi
}

# If running this file directly, show available functions
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "OpsKit Shell Logger Function Library"
    echo "==================================="
    echo "Tool logging: tool_start, tool_complete, tool_error"
    echo "Step logging: step_start, step_complete, step_error"
    echo "Timer functions: timer_start, timer_stop"
    echo "Structured logging: log_json, log_structured_error"
    echo "Log analysis: analyze_logs, cleanup_logs"
    echo "Utility tools: print_banner, show_tool_info, die, success_exit"
fi
#!/bin/bash
# OpsKit Shell Logger Functions
# Provides unified logging interface using pure shell implementation

# Ensure OPSKIT_BASE_PATH is set
if [[ -z "${OPSKIT_BASE_PATH:-}" ]]; then
    # Get the OpsKit root directory (common/shell -> ../..)
    OPSKIT_BASE_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    export OPSKIT_BASE_PATH
fi

# ==================== Configuration ====================

# Configuration variables are injected by CLI, use defaults if not set

# Map log levels to numeric values for filtering
declare -A LOG_LEVELS=(
    ["DEBUG"]=10
    ["INFO"]=20
    ["WARNING"]=30
    ["ERROR"]=40
    ["CRITICAL"]=50
)

# Get logs directory - only create if file logging is enabled
_get_logs_dir() {
    local logs_dir="${OPSKIT_PATHS_LOGS_DIR:-logs}"
    if [[ ! "$logs_dir" = /* ]]; then
        logs_dir="${OPSKIT_BASE_PATH}/${logs_dir}"
    fi
    echo "$logs_dir"
}

# ==================== Core Logging Functions ====================

# Get current timestamp in ISO format
_get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Check if log level should be output
_should_log() {
    local level="$1"
    local current_log_level="${OPSKIT_LOGGING_CONSOLE_LEVEL:-INFO}"
    local current_level_value="${LOG_LEVELS[$current_log_level]:-20}"
    local message_level_value="${LOG_LEVELS[$level]:-20}"
    
    [[ $message_level_value -ge $current_level_value ]]
}

# Internal logging function using pure shell
_shell_log() {
    local level="$1"
    local message="$2"
    local tool_name="${3:-shell}"
    
    # Check if we should log this level
    if ! _should_log "$level"; then
        return 0
    fi
    
    local timestamp
    timestamp="$(_get_timestamp)"
    
    # Console output: simple format (just message)
    local console_message="$message"
    
    # Color codes for different levels
    local color_reset="\033[0m"
    local color_code=""
    case "$level" in
        DEBUG)   color_code="\033[36m" ;;  # Cyan
        INFO)    color_code="\033[32m" ;;  # Green
        WARNING) color_code="\033[33m" ;;  # Yellow
        ERROR)   color_code="\033[31m" ;;  # Red
        CRITICAL) color_code="\033[35m" ;; # Magenta
    esac
    
    # Output to console with color (simple format - just message)
    if [[ -t 2 ]]; then
        # Terminal supports colors
        echo -e "${color_code}${console_message}${color_reset}" >&2
    else
        # No color support
        echo "$console_message" >&2
    fi
    
    # Output to log file if enabled
    if [[ "${OPSKIT_LOGGING_FILE_ENABLED}" == "true" ]]; then
        local logs_dir
        logs_dir="$(_get_logs_dir)"
        mkdir -p "$logs_dir"
        local log_file="$logs_dir/opskit.log"
        local detailed_message="$timestamp $level [$tool_name] $message"
        echo "$detailed_message" >> "$log_file"
    fi
}

# Basic logging functions
log_debug() {
    _shell_log "DEBUG" "$1" "${OPSKIT_TOOL_NAME:-}"
}

log_info() {
    _shell_log "INFO" "$1" "${OPSKIT_TOOL_NAME:-}"
}

log_warn() {
    _shell_log "WARNING" "$1" "${OPSKIT_TOOL_NAME:-}"
}

log_warning() {
    log_warn "$1"
}

log_error() {
    _shell_log "ERROR" "$1" "${OPSKIT_TOOL_NAME:-}"
}

log_fatal() {
    _shell_log "CRITICAL" "$1" "${OPSKIT_TOOL_NAME:-}"
}

log_critical() {
    log_fatal "$1"
}

# ==================== Tool Lifecycle Functions ====================

# Tool startup log
tool_start() {
    local tool_name="$1"
    export OPSKIT_TOOL_NAME="$tool_name"
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

# ==================== Step Progress Functions ====================

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

# ==================== Dependency and System Functions ====================

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

# ==================== Utility Functions ====================

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

# Functions are available when this file is sourced
# No explicit exports needed since functions are defined in the current shell

# If running this file directly, show available functions
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "OpsKit Shell Logger Function Library"
    echo "==================================="
    echo "Basic logging: log_debug, log_info, log_warn, log_error, log_fatal"
    echo "Tool logging: tool_start, tool_complete, tool_error"
    echo "Step logging: step_start, step_complete, step_error"
    echo "System logging: dependency_check, config_loaded, network_operation, file_operation"
    echo "Utility functions: die, success_exit"
fi
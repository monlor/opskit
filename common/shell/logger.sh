#!/bin/bash
# OpsKit Shell Logger Functions
# Provides unified logging interface using Python backend

# Ensure OPSKIT_BASE_PATH is set
if [[ -z "${OPSKIT_BASE_PATH:-}" ]]; then
    # Get the OpsKit root directory (common/shell -> ../..)
    OPSKIT_BASE_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    export OPSKIT_BASE_PATH
fi

# ==================== Core Logging Functions ====================

# Internal logging function using Python backend
_python_log() {
    local level="$1"
    local message="$2"
    local tool_name="${3:-shell}"
    
    # Use Python logger for consistent logging - no fallbacks
    python3 -c "
import sys
sys.path.insert(0, '${OPSKIT_BASE_PATH}/common/python')
from logger import get_logger
logger = get_logger('shell', '$tool_name')
logger.${level,,}('$message')
"
}

# Basic logging functions
log_debug() {
    _python_log "DEBUG" "$1" "${OPSKIT_TOOL_NAME:-}"
}

log_info() {
    _python_log "INFO" "$1" "${OPSKIT_TOOL_NAME:-}"
}

log_warn() {
    _python_log "WARNING" "$1" "${OPSKIT_TOOL_NAME:-}"
}

log_warning() {
    log_warn "$1"
}

log_error() {
    _python_log "ERROR" "$1" "${OPSKIT_TOOL_NAME:-}"
}

log_fatal() {
    _python_log "CRITICAL" "$1" "${OPSKIT_TOOL_NAME:-}"
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

# Export all functions
export -f _python_log log_debug log_info log_warn log_warning log_error log_fatal log_critical
export -f tool_start tool_complete tool_error
export -f step_start step_complete step_error
export -f dependency_check config_loaded network_operation file_operation
export -f die success_exit

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
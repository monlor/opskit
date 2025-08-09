#!/bin/bash

# Disk Usage Analysis Tool
# Displays disk usage information with configurable thresholds and formatting.
# All configuration is loaded from environment variables.

# Load OpsKit common shell libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
source "${OPSKIT_BASE_PATH}/common/shell/utils.sh"

# Tool information will be injected by cli.py
# TOOL_NAME and TOOL_VERSION are provided by the framework

# Load configuration from environment variables with defaults using utils
SHOW_PERCENTAGE=$(get_env_var "SHOW_PERCENTAGE" "true" "bool")
SHOW_HUMAN_READABLE=$(get_env_var "SHOW_HUMAN_READABLE" "true" "bool")
SHOW_FILESYSTEM_TYPE=$(get_env_var "SHOW_FILESYSTEM_TYPE" "false" "bool")
SORT_BY_USAGE=$(get_env_var "SORT_BY_USAGE" "true" "bool")
WARNING_THRESHOLD=$(get_env_var "WARNING_THRESHOLD" "80" "int")
CRITICAL_THRESHOLD=$(get_env_var "CRITICAL_THRESHOLD" "95" "int")
ALERT_ON_THRESHOLD=$(get_env_var "ALERT_ON_THRESHOLD" "true" "bool")
OUTPUT_FORMAT=$(get_env_var "OUTPUT_FORMAT" "table" "str")
SHOW_HEADER=$(get_env_var "SHOW_HEADER" "true" "bool")
MAX_ENTRIES=$(get_env_var "MAX_ENTRIES" "20" "int")
TIMEOUT=$(get_env_var "TIMEOUT" "10" "int")
EXCLUDE_TMPFS=$(get_env_var "EXCLUDE_TMPFS" "true" "bool")
EXCLUDE_PROC=$(get_env_var "EXCLUDE_PROC" "true" "bool")

print_header() {
    show_tool_info "$TOOL_NAME" "$TOOL_VERSION" "Environment-based disk usage monitoring tool"
}

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
        step_error "get_disk_usage" "Failed to get disk usage information"
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
            log_error "CRITICAL: $mount is ${usage}% full"
        elif [[ $usage -ge $WARNING_THRESHOLD ]]; then
            log_warn "WARNING: $mount is ${usage}% full"
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
        echo -e "${BOLD}Filesystem Usage Report${NC}"
        echo -e "${BOLD}$(echo "$df_data" | head -1)${NC}"
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
            echo "... (showing first $MAX_ENTRIES entries)"
            break
        fi
        
        local usage_percent
        usage_percent=$(parse_usage_percentage "$line")
        
        local mount_point
        mount_point=$(get_mount_point "$line")
        
        # Color code based on usage
        local color=""
        if [[ -n "$usage_percent" && "$usage_percent" =~ ^[0-9]+$ ]]; then
            if [[ $usage_percent -ge $CRITICAL_THRESHOLD ]]; then
                color="$RED"
            elif [[ $usage_percent -ge $WARNING_THRESHOLD ]]; then
                color="$YELLOW"
            else
                color="$GREEN"
            fi
        fi
        
        echo -e "${color}$line${NC}"
        
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
    # Start tool execution
    tool_start "$TOOL_NAME"
    
    print_header
    
    # Debug output if enabled
    log_debug "Configuration loaded:"
    log_debug "  WARNING_THRESHOLD=$WARNING_THRESHOLD"
    log_debug "  CRITICAL_THRESHOLD=$CRITICAL_THRESHOLD"
    log_debug "  OUTPUT_FORMAT=$OUTPUT_FORMAT"
    log_debug "  TIMEOUT=$TIMEOUT"
    
    # Get disk usage information
    step_start "Getting disk usage information"
    local disk_data
    if ! disk_data=$(get_disk_usage); then
        tool_error "$TOOL_NAME" "Failed to get disk usage data"
        exit 1
    fi
    step_complete "Getting disk usage information"
    
    # Format and display output
    step_start "Formatting and displaying output"
    format_output "$disk_data"
    step_complete "Formatting and displaying output"
    
    # Tool completion
    tool_complete "$TOOL_NAME"
}

# Handle help flag
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Environment Variables:"
    echo "  WARNING_THRESHOLD    - Warning threshold percentage (default: 80)"
    echo "  CRITICAL_THRESHOLD   - Critical threshold percentage (default: 95)"
    echo "  OUTPUT_FORMAT        - Output format: table, json, csv (default: table)"
    echo "  USE_COLORS          - Enable colored output (default: true)"
    echo "  SHOW_HEADER         - Show table header (default: true)"
    echo "  MAX_ENTRIES         - Maximum entries to display (default: 20)"
    echo "  TIMEOUT             - Command timeout in seconds (default: 10)"
    echo "  DEBUG               - Enable debug output (default: false)"
    echo ""
    echo "Global overrides (using DISK_USAGE_ prefix):"
    echo "  DISK_USAGE_WARNING_THRESHOLD=90"
    echo "  DISK_USAGE_OUTPUT_FORMAT=json"
    echo ""
    exit 0
fi

# Run main function
main "$@"
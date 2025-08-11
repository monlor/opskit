#!/bin/bash
# OpsKit Shell Utility Functions
# Provides essential utility functions for shell tools

# Ensure OPSKIT_BASE_PATH is set
if [[ -z "${OPSKIT_BASE_PATH:-}" ]]; then
    # Get the OpsKit root directory (common/shell -> ../..)
    OPSKIT_BASE_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    export OPSKIT_BASE_PATH
fi

# ==================== Environment Variable Utilities ====================

# Get environment variable with type conversion
get_env_var() {
    local key="$1"
    local default="${2:-}"
    local var_type="${3:-str}"
    local value="${!key:-}"
    
    if [[ -z "$value" ]]; then
        echo "$default"
        return
    fi
    
    case "$var_type" in
        bool)
            case "$(echo "$value" | tr '[:upper:]' '[:lower:]')" in
                true|1|yes|on) echo "true" ;;
                *) echo "false" ;;
            esac
            ;;
        int)
            if [[ "$value" =~ ^-?[0-9]+$ ]]; then
                echo "$value"
            else
                echo "$default"
            fi
            ;;
        float)
            if [[ "$value" =~ ^-?[0-9]+.?[0-9]*$ ]]; then
                echo "$value"
            else
                echo "$default"
            fi
            ;;
        *)
            echo "$value"
            ;;
    esac
}

# ==================== Command and Dependency Utilities ====================

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check command and show installation hint if missing
check_command() {
    local cmd="$1"
    local hint="${2:-Please install $cmd}"
    
    if command_exists "$cmd"; then
        return 0
    else
        log_error "Command not found: $cmd"
        log_info "$hint"
        return 1
    fi
}

# Check multiple commands
check_commands() {
    local missing=()
    
    for cmd in "$@"; do
        if ! command_exists "$cmd"; then
            missing+=("$cmd")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing[*]}"
        return 1
    fi
    
    return 0
}

# Check required commands (alias for check_commands for backward compatibility)
check_required_commands() {
    check_commands "$@"
}

# ==================== File and Directory Utilities ====================

# Ensure directory exists
ensure_dir() {
    local dir="$1"
    local mode="${2:-755}"
    
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        chmod "$mode" "$dir"
        log_debug "Created directory: $dir"
    fi
}

# Get file size in human readable format
get_file_size() {
    local file="$1"
    
    if [[ ! -f "$file" ]]; then
        echo "0B"
        return 1
    fi
    
    if command_exists du; then
        du -h "$file" | cut -f1
    else
        ls -lh "$file" | awk '{print $5}'
    fi
}

# Create safe filename
safe_filename() {
    local filename="$1"
    echo "$filename" | tr '<>:"/\\|?*' '_' | tr -s '_'
}

# ==================== String Processing ====================

# Trim whitespace
trim() {
    local var="$1"
    # Remove leading whitespace
    var="${var#"${var%%[![:space:]]*}"}"
    # Remove trailing whitespace
    var="${var%"${var##*[![:space:]]}"}"
    echo "$var"
}

# Check if string is empty
is_empty() {
    [[ -z "$1" ]]
}

# Check if string is numeric
is_numeric() {
    [[ "$1" =~ ^-?[0-9]+\.?[0-9]*$ ]]
}

# ==================== Time and Date Utilities ====================

# Get timestamp
get_timestamp() {
    date +%s
}

# Get ISO timestamp
get_iso_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%S.%3NZ"
}

# Calculate time difference
time_diff() {
    local start_time="$1"
    local end_time="$2"
    local diff=$((end_time - start_time))
    
    if [[ $diff -lt 60 ]]; then
        echo "${diff}s"
    elif [[ $diff -lt 3600 ]]; then
        echo "$((diff / 60))m $((diff % 60))s"
    else
        echo "$((diff / 3600))h $(((diff % 3600) / 60))m"
    fi
}

# ==================== User Interaction ====================

# Ask yes/no question
ask_yes_no() {
    local question="$1"
    local default="${2:-n}"
    local response
    
    while true; do
        if [[ "$default" == "y" ]]; then
            echo -n "$question [Y/n]: "
        else
            echo -n "$question [y/N]: "
        fi
        
        read -r response
        response=$(trim "$(echo "$response" | tr '[:upper:]' '[:lower:]')")
        
        if [[ -z "$response" ]]; then
            response="$default"
        fi
        
        case "$response" in
            y|yes)
                return 0
                ;;
            n|no)
                return 1
                ;;
            *)
                echo "Please answer 'y' or 'n'"
                ;;
        esac
    done
}

# Get user input with validation
get_input() {
    local prompt="$1"
    local default="${2:-}"
    local validator="${3:-}"
    local max_attempts="${4:-3}"
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        local full_prompt="$prompt"
        if [[ -n "$default" ]]; then
            full_prompt+=" [$default]"
        fi
        full_prompt+=": "
        
        echo -n "$full_prompt"
        read -r user_input
        
        # Use default if empty
        if [[ -z "$user_input" && -n "$default" ]]; then
            user_input="$default"
        fi
        
        # Validate if validator provided
        if [[ -n "$validator" ]]; then
            if $validator "$user_input"; then
                echo "$user_input"
                return 0
            else
                echo "Invalid input. Please try again." >&2
            fi
        else
            echo "$user_input"
            return 0
        fi
        
        ((attempt++))
    done
    
    log_error "Failed to get valid input after $max_attempts attempts"
    return 1
}

# ==================== Debug and Logging Utilities ====================

# Check if debug mode is enabled
is_debug() {
    local debug_enabled
    debug_enabled=$(get_env_var "DEBUG" "false" "bool")
    [[ "$debug_enabled" == "true" ]]
}

# ==================== System Information ====================

# Detect operating system
detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*) echo "linux" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

# Check if running in interactive mode
is_interactive() {
    [[ -t 0 ]]
}

# Get terminal width
get_terminal_width() {
    if command_exists tput; then
        tput cols 2>/dev/null || echo "80"
    else
        echo "80"
    fi
}

# ==================== Process Management ====================

# Run command with timeout
run_with_timeout() {
    local timeout="$1"
    shift
    local command=("$@")
    
    timeout "$timeout" "${command[@]}" 2>/dev/null || {
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            log_error "Command timed out after ${timeout}s: ${command[*]}"
        else
            log_error "Command failed with exit code $exit_code: ${command[*]}"
        fi
        return $exit_code
    }
}

# ==================== Tool Information ====================

# Show tool information banner
show_tool_info() {
    local tool_name="$1"
    local version="${2:-unknown}"
    local description="${3:-No description}"
    
    local width=60
    local border=$(printf "=%.0s" $(seq 1 $width))
    local padding=$(( (width - ${#tool_name}) / 2 ))
    
    echo -e "${CYAN}$border${NC}"
    printf "%s%*s%s v%s%*s%s\n" "$CYAN" $padding "" "$tool_name" "$version" $padding "" "$NC"
    echo -e "${DIM}$description${NC}"
    echo -e "${CYAN}$border${NC}"
    echo
}

# ==================== Help Function ====================

show_utils_help() {
    cat << EOF
${BOLD}OpsKit Shell Utility Functions${NC}

${BOLD}Environment Variables:${NC}
  get_env_var <key> [default] [type]    - Get environment variable with type conversion

${BOLD}Command Utilities:${NC}
  command_exists <cmd>                  - Check if command exists
  check_command <cmd> [hint]            - Check command with installation hint
  check_commands <cmd1> <cmd2> ...      - Check multiple commands

${BOLD}File Utilities:${NC}
  ensure_dir <dir> [mode]               - Ensure directory exists
  get_file_size <file>                  - Get file size in human readable format
  safe_filename <name>                  - Create safe filename

${BOLD}String Processing:${NC}
  trim <string>                         - Trim whitespace
  is_empty <string>                     - Check if string is empty
  is_numeric <string>                   - Check if string is numeric

${BOLD}Time Utilities:${NC}
  get_timestamp                         - Get Unix timestamp
  get_iso_timestamp                     - Get ISO timestamp
  time_diff <start> <end>               - Calculate time difference

${BOLD}User Interaction:${NC}
  ask_yes_no <question> [default]       - Ask yes/no question
  get_input <prompt> [default] [validator] [attempts] - Get validated input

${BOLD}System Information:${NC}
  detect_os                             - Detect operating system
  is_interactive                        - Check if running interactively
  get_terminal_width                    - Get terminal width

${BOLD}Process Management:${NC}
  run_with_timeout <timeout> <command>  - Run command with timeout

${BOLD}Tool Information:${NC}
  show_tool_info <name> [version] [desc] - Show tool information banner
EOF
}

# ==================== Export Functions ====================

# Export all utility functions
export -f get_env_var
export -f command_exists check_command check_commands check_required_commands
export -f ensure_dir get_file_size safe_filename
export -f trim is_empty is_numeric
export -f get_timestamp get_iso_timestamp time_diff
export -f ask_yes_no get_input
export -f is_debug
export -f detect_os is_interactive get_terminal_width
export -f run_with_timeout
export -f show_tool_info
export -f show_utils_help

# If running this file directly, show available functions
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    show_utils_help
fi
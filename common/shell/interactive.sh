#!/bin/bash
# Interactive Components Library - Shell Implementation
#
# Provides core interactive UI components for OpsKit shell tools with same API as Python version:
# - User input with validation
# - Confirmation dialogs
# - Simple selection lists
# - Delete confirmations
# - Display helpers
#
# Usage: source "${OPSKIT_BASE_PATH}/common/shell/interactive.sh"

# Import logger if available
if [[ -n "${OPSKIT_BASE_PATH}" && -f "${OPSKIT_BASE_PATH}/common/shell/logger.sh" ]]; then
    source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
fi

# Color codes (if terminal supports colors)
if [[ -t 1 && $(tput colors) -ge 8 ]]; then
    readonly RED=$(tput setaf 1)
    readonly GREEN=$(tput setaf 2)
    readonly YELLOW=$(tput setaf 3)
    readonly BLUE=$(tput setaf 4)
    readonly CYAN=$(tput setaf 6)
    readonly WHITE=$(tput setaf 7)
    readonly BOLD=$(tput bold)
    readonly RESET=$(tput sgr0)
else
    readonly RED=""
    readonly GREEN=""
    readonly YELLOW=""
    readonly BLUE=""
    readonly CYAN=""
    readonly WHITE=""
    readonly BOLD=""
    readonly RESET=""
fi

# Global settings
INTERACTIVE_USE_COLORS="${INTERACTIVE_USE_COLORS:-true}"

# Utility function to check if colors should be used
use_colors() {
    [[ "$INTERACTIVE_USE_COLORS" == "true" && -n "$RED" ]]
}

# Enhanced logging functions matching Python API - use unified logger
info() {
    local message="$1"
    log_info "$message"
}

debug() {
    local message="$1"
    log_debug "$message"
}

warning() {
    local message="$1"
    log_warning "⚠️  $message"
}

error() {
    local message="$1"
    log_error "❌ $message"
}

critical() {
    local message="$1"
    log_critical "🚨 CRITICAL: $message"
}

section() {
    local title="$1"
    local width="${2:-80}"
    local separator=""
    
    # Create separator
    for ((i=0; i<width; i++)); do
        separator+="="
    done
    
    info ""
    info "$separator"
    info "🔄 $title"
    info "$separator"
}

subsection() {
    local title="$1"
    local width="${2:-60}"
    local separator=""
    
    # Create separator
    for ((i=0; i<width; i++)); do
        separator+="-"
    done
    
    info ""
    info "$separator"
    info "📋 $title"
    info "$separator"
}

step() {
    local step_num="$1"
    local total_steps="$2"
    local description="$3"
    info "[${step_num}/${total_steps}] 🔄 ${description}"
}

success() {
    local message="$1"
    log_info "✅ $message"
}

failure() {
    local message="$1"
    log_error "❌ $message"
}

warning_msg() {
    local message="$1"
    warning "$message"
}

progress() {
    local message="$1"
    info "📊 $message"
}

connection_test() {
    local host="$1"
    local port="$2"
    local result="$3"
    
    if [[ "$result" == "true" || "$result" == "0" ]]; then
        success "Connection to ${host}:${port} successful"
    else
        failure "Connection to ${host}:${port} failed"
    fi
}

operation_start() {
    local operation="$1"
    local details="$2"
    
    if [[ -n "$details" ]]; then
        info "🚀 Starting ${operation}: ${details}"
    else
        info "🚀 Starting ${operation}"
    fi
}

operation_complete() {
    local operation="$1"
    local duration="$2"
    
    if [[ -n "$duration" ]]; then
        success "${operation} completed (duration: ${duration}s)"
    else
        success "${operation} completed"
    fi
}

display_info() {
    local title="$1"
    shift
    local -a info_pairs=("$@")
    
    info ""
    info "📋 ${title}:"
    
    # Process key-value pairs
    local i=0
    while [[ $i -lt ${#info_pairs[@]} ]]; do
        local key="${info_pairs[$i]}"
        local value="${info_pairs[$((i+1))]}"
        info "   ${key}: ${value}"
        ((i+=2))
    done
}

display_list() {
    local title="$1"
    shift
    local -a items=("$@")
    local indent="  • "
    
    info ""
    info "📊 ${title} (${#items[@]} items):"
    
    local item
    for item in "${items[@]}"; do
        info "${indent}${item}"
    done
}

confirmation_required() {
    local message="$1"
    warning_msg "Confirmation required: ${message}"
}

user_cancelled() {
    local operation="${1:-operation}"
    info "👋 User cancelled ${operation}"
}

retry_attempt() {
    local attempt="$1"
    local max_attempts="$2"
    local operation="$3"
    warning_msg "Retry attempt ${attempt}/${max_attempts} for ${operation}"
}

cache_operation() {
    local operation="$1"
    local item="$2"
    debug "Cache ${operation}: ${item}"
}

# Core interactive functions matching Python API

# Function: confirm
# Interactive confirmation matching Python API
# Args:
#   $1: message - Confirmation message
#   $2: default - "true" or "false" (optional, default: false)
# Returns: 0 for yes, 1 for no
confirm() {
    local message="$1"
    local default="${2:-false}"
    local response=""
    local default_char="n"
    local other_char="y"
    local display_prompt=""
    
    confirmation_required "$message"
    
    if [[ "$default" == "true" ]]; then
        default_char="Y"
        other_char="n"
    fi
    
    display_prompt="${message} [${default_char}/${other_char}]: "
    
    # Add colors if enabled
    if use_colors; then
        display_prompt="${CYAN}${display_prompt}${RESET}"
    fi
    
    while true; do
        printf "%s" "$display_prompt" >&2
        read -r response
        
        # Handle Ctrl+C
        if [[ $? -ne 0 ]]; then
            echo "" >&2
            user_cancelled "confirmation"
            return 1
        fi
        
        # Convert to lowercase
        response=$(echo "$response" | tr '[:upper:]' '[:lower:]')
        
        # Handle empty response (use default)
        if [[ -z "$response" ]]; then
            if [[ "$default" == "true" ]]; then
                info "✅ User confirmed: $message"
                return 0
            else
                info "❌ User declined: $message"
                return 1
            fi
        fi
        
        # Check response
        case "$response" in
            y|yes|true|1)
                info "✅ User confirmed: $message"
                return 0
                ;;
            n|no|false|0)
                info "❌ User declined: $message"
                return 1
                ;;
            *)
                if use_colors; then
                    echo "${RED}Please enter yes or no${RESET}" >&2
                else
                    echo "Please enter yes or no" >&2
                fi
                ;;
        esac
    done
}

# Function: get_input
# Get user input matching Python API
# Args:
#   $1: prompt - Text to display as prompt
#   $2: default - Default value (optional)
#   $3: password - "true" for password input (optional, default: false)
#   $4: validator_function - Name of validation function (optional)
#   $5: error_message - Error message for validation (optional)
# Returns: User input via stdout
get_input() {
    local prompt="$1"
    local default="$2"
    local password="${3:-false}"
    local validator_function="$4"
    local error_message="${5:-Invalid input}"
    local user_input=""
    local display_prompt=""
    
    debug "Requesting input: $prompt"
    
    # Format prompt
    if [[ -n "$default" ]]; then
        display_prompt="${prompt} [${default}]: "
    else
        display_prompt="${prompt}: "
    fi
    
    # Add colors if enabled
    if use_colors; then
        display_prompt="${CYAN}${display_prompt}${RESET}"
    fi
    
    while true; do
        # Get input
        if [[ "$password" == "true" ]]; then
            printf "%s" "$display_prompt" >&2
            read -rs user_input
            echo "" >&2  # New line after hidden input
        else
            printf "%s" "$display_prompt" >&2
            read -r user_input
        fi
        
        # Handle Ctrl+C gracefully
        if [[ $? -ne 0 ]]; then
            echo "" >&2
            user_cancelled "input"
            return 1
        fi
        
        # Handle empty input
        if [[ -z "$user_input" ]]; then
            if [[ -n "$default" ]]; then
                echo "$default"
                debug "User input received for: $prompt"
                return 0
            else
                warning "Input is required"
                continue
            fi
        fi
        
        # Validate input if validator function provided
        if [[ -n "$validator_function" ]] && command -v "$validator_function" >/dev/null 2>&1; then
            if ! "$validator_function" "$user_input"; then
                warning "$error_message"
                continue
            fi
        fi
        
        echo "$user_input"
        debug "User input received for: $prompt"
        return 0
    done
}

# Function: delete_confirm
# Specialized confirmation for delete operations matching Python API
# Args:
#   $1: item_name - Name of item being deleted
#   $2: item_type - Type of item (optional, default: "item")
#   $3: force_typing - "true" to require typing confirmation (optional, default: false)
#   $4: confirmation_text - Text to type for confirmation (optional, default: "DELETE")
# Returns: 0 for confirmed, 1 for cancelled
delete_confirm() {
    local item_name="$1"
    local item_type="${2:-item}"
    local force_typing="${3:-false}"
    local confirmation_text="${4:-DELETE}"
    
    warning_msg "Delete confirmation requested for: $item_name"
    
    # Display warning
    if use_colors; then
        echo "" >&2
        echo "${RED}⚠️  WARNING: Destructive Operation${RESET}" >&2
        echo "You are about to delete ${item_type}: ${YELLOW}${item_name}${RESET}" >&2
        echo "${RED}This action cannot be undone!${RESET}" >&2
    else
        echo "" >&2
        echo "⚠️  WARNING: Destructive Operation" >&2
        echo "You are about to delete ${item_type}: ${item_name}" >&2
        echo "This action cannot be undone!" >&2
    fi
    
    if [[ "$force_typing" == "true" ]]; then
        # Require typing confirmation
        local typed_confirmation
        typed_confirmation=$(get_input "Type '${confirmation_text}' to confirm deletion" "" "false" "validate_delete_confirmation" "You must type '${confirmation_text}' exactly to confirm")
        if [[ $? -ne 0 ]]; then
            return 1
        fi
        
        local typed_upper=$(echo "$typed_confirmation" | tr '[:lower:]' '[:upper:]')
        local confirmation_upper=$(echo "$confirmation_text" | tr '[:lower:]' '[:upper:]')
        if [[ "$typed_upper" == "$confirmation_upper" ]]; then
            warning_msg "Delete confirmed for: $item_name"
            return 0
        else
            info "Delete cancelled for: $item_name"
            return 1
        fi
    else
        # Simple yes/no confirmation
        if confirm "Delete ${item_type} '${item_name}'?" "false"; then
            warning_msg "Delete confirmed for: $item_name"
            return 0
        else
            info "Delete cancelled for: $item_name"
            return 1
        fi
    fi
}

# Function: select_from_list
# Display a selection list and get user choice matching Python API
# Args:
#   $1: title - Title for the selection
#   $@: items - List of items to select from
# Returns: Selected index (0-based) via stdout, or exits on cancel
select_from_list() {
    local title="$1"
    shift
    local items=("$@")
    local selection=""
    local i
    
    info "List selection requested: $title (${#items[@]} items)"
    
    if [[ ${#items[@]} -eq 0 ]]; then
        warning "No items to select from"
        return 1
    fi
    
    # Display title
    if use_colors; then
        echo "" >&2
        echo "${CYAN}=== ${title} ===${RESET}" >&2
    else
        echo "" >&2
        echo "=== ${title} ===" >&2
    fi
    
    # Display items
    for i in "${!items[@]}"; do
        local display_num=$((i + 1))
        if use_colors; then
            printf "${YELLOW}%2d.${RESET} %s\n" "$display_num" "${items[$i]}" >&2
        else
            printf "%2d. %s\n" "$display_num" "${items[$i]}" >&2
        fi
    done
    
    # Show selection options
    if use_colors; then
        echo "${CYAN}" >&2
        echo "Enter the number of your choice, or 'cancel' to abort:" >&2
        echo "${RESET}" >&2
    else
        echo "" >&2
        echo "Enter the number of your choice, or 'cancel' to abort:" >&2
    fi
    
    while true; do
        printf "Your choice: " >&2
        read -r selection
        
        # Handle Ctrl+C
        if [[ $? -ne 0 ]]; then
            echo "" >&2
            info "User cancelled selection from: $title"
            return 1
        fi
        
        # Handle cancel
        local selection_lower=$(echo "$selection" | tr '[:upper:]' '[:lower:]')
        if [[ "$selection_lower" == "cancel" || "$selection_lower" == "c" || "$selection_lower" == "quit" || "$selection_lower" == "q" ]]; then
            info "User cancelled selection from: $title"
            return 1
        fi
        
        # Validate numeric input
        if [[ "$selection" =~ ^[0-9]+$ ]]; then
            local index=$((selection - 1))
            if [[ $index -ge 0 && $index -lt ${#items[@]} ]]; then
                echo "$index"
                info "User selected option $index from: $title"
                return 0
            fi
        fi
        
        # Invalid selection
        if use_colors; then
            echo "${RED}Please enter a number between 1 and ${#items[@]}${RESET}" >&2
        else
            echo "Please enter a number between 1 and ${#items[@]}" >&2
        fi
    done
}

# Validation helper functions
# These can be used with get_input as validator functions

# Validate non-empty string
validate_not_empty() {
    [[ -n "$1" ]]
}

# Validate numeric input
validate_numeric() {
    [[ "$1" =~ ^[0-9]+$ ]]
}

# Validate email format (basic)
validate_email() {
    [[ "$1" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]
}

# Validate IP address (basic)
validate_ip() {
    local ip="$1"
    local IFS='.'
    local parts=($ip)
    
    [[ ${#parts[@]} -eq 4 ]] || return 1
    
    local part
    for part in "${parts[@]}"; do
        [[ "$part" =~ ^[0-9]+$ ]] && [[ $part -ge 0 && $part -le 255 ]] || return 1
    done
    
    return 0
}

# Validate port number
validate_port() {
    local port="$1"
    [[ "$port" =~ ^[0-9]+$ ]] && [[ $port -ge 1 && $port -le 65535 ]]
}

# Validate delete confirmation text
validate_delete_confirmation() {
    local input="$1"
    local expected="${INTERACTIVE_DELETE_CONFIRMATION_TEXT:-DELETE}"
    local input_upper=$(echo "$input" | tr '[:lower:]' '[:upper:]')
    local expected_upper=$(echo "$expected" | tr '[:lower:]' '[:upper:]')
    [[ "$input_upper" == "$expected_upper" ]]
}

# Demo function (if script is run directly)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Interactive Components Demo (Shell)"
    echo "=================================="
    echo
    
    section "Interactive Components Test"
    
    # Test basic input
    name=$(get_input "Enter your name" "User")
    success "Hello, $name!"
    echo
    
    # Test confirmation
    if confirm "Continue with demo?" "true"; then
        success "Continuing..."
        
        # Test list selection
        items=("Option A" "Option B" "Option C")
        echo
        selection=$(select_from_list "Choose an option" "${items[@]}")
        if [[ $? -eq 0 ]]; then
            success "You selected: ${items[$selection]}"
        else
            info "Selection cancelled"
        fi
        echo
        
        # Test delete confirmation
        if delete_confirm "test_file.txt" "file" "false"; then
            success "File would be deleted"
        else
            info "Delete cancelled"
        fi
        echo
        
        success "Demo complete!"
    else
        info "Demo cancelled"
    fi
fi
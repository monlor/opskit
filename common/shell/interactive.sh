#!/bin/bash
# Interactive Components Library - Shell Implementation
#
# Provides common interactive UI components for OpsKit shell tools:
# - User input with validation
# - Confirmation dialogs
# - Simple selection lists
# - Delete confirmations
# - Progress indicators
#
# Usage: source "${OPSKIT_BASE_PATH}/common/shell/interactive.sh"

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

# Function: get_user_input
# Get user input with validation and optional features
# Args:
#   $1: prompt_text - Text to display as prompt
#   $2: default - Default value (optional)
#   $3: required - "true" or "false" (optional, default: true)
#   $4: validator_function - Name of validation function (optional)
# Returns: User input via stdout
get_user_input() {
    local prompt_text="$1"
    local default="$2"
    local required="${3:-true}"
    local validator_function="$4"
    local user_input=""
    local display_prompt=""
    
    # Format prompt
    if [[ -n "$default" ]]; then
        display_prompt="${prompt_text} [${default}]: "
    else
        display_prompt="${prompt_text}: "
    fi
    
    # Add colors if enabled
    if use_colors; then
        display_prompt="${CYAN}${display_prompt}${RESET}"
    fi
    
    while true; do
        # Get input
        printf "%s" "$display_prompt" >&2
        read -r user_input
        
        # Handle Ctrl+C gracefully
        if [[ $? -ne 0 ]]; then
            echo "" >&2
            echo "Operation cancelled by user" >&2
            return 1
        fi
        
        # Handle empty input
        if [[ -z "$user_input" ]]; then
            if [[ -n "$default" ]]; then
                echo "$default"
                return 0
            elif [[ "$required" != "true" ]]; then
                echo ""
                return 0
            else
                if use_colors; then
                    echo "${RED}Input is required${RESET}" >&2
                else
                    echo "Input is required" >&2
                fi
                continue
            fi
        fi
        
        # Validate input if validator function provided
        if [[ -n "$validator_function" ]] && command -v "$validator_function" >/dev/null 2>&1; then
            if ! "$validator_function" "$user_input"; then
                if use_colors; then
                    echo "${RED}Invalid input, please try again${RESET}" >&2
                else
                    echo "Invalid input, please try again" >&2
                fi
                continue
            fi
        fi
        
        echo "$user_input"
        return 0
    done
}

# Function: get_password_input
# Get password input (hidden)
# Args:
#   $1: prompt_text - Text to display as prompt
# Returns: Password via stdout
get_password_input() {
    local prompt_text="$1"
    local password=""
    local display_prompt="${prompt_text}: "
    
    # Add colors if enabled
    if use_colors; then
        display_prompt="${CYAN}${display_prompt}${RESET}"
    fi
    
    printf "%s" "$display_prompt" >&2
    read -rs password
    echo "" >&2  # New line after hidden input
    
    echo "$password"
}

# Function: confirm
# Show confirmation dialog
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
            echo "Operation cancelled by user" >&2
            return 1
        fi
        
        # Convert to lowercase
        response=$(echo "$response" | tr '[:upper:]' '[:lower:]')
        
        # Handle empty response (use default)
        if [[ -z "$response" ]]; then
            if [[ "$default" == "true" ]]; then
                return 0
            else
                return 1
            fi
        fi
        
        # Check response
        case "$response" in
            y|yes|true|1)
                return 0
                ;;
            n|no|false|0)
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

# Function: select_from_list
# Display a selection list and get user choice
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
    
    if [[ ${#items[@]} -eq 0 ]]; then
        if use_colors; then
            echo "${YELLOW}No items to select from${RESET}" >&2
        else
            echo "No items to select from" >&2
        fi
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
            echo "Selection cancelled by user" >&2
            return 1
        fi
        
        # Handle cancel
        local selection_lower=$(echo "$selection" | tr '[:upper:]' '[:lower:]')
        if [[ "$selection_lower" == "cancel" || "$selection_lower" == "c" || "$selection_lower" == "quit" || "$selection_lower" == "q" ]]; then
            return 1
        fi
        
        # Validate numeric input
        if [[ "$selection" =~ ^[0-9]+$ ]]; then
            local index=$((selection - 1))
            if [[ $index -ge 0 && $index -lt ${#items[@]} ]]; then
                echo "$index"
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

# Function: delete_confirmation
# Specialized confirmation for delete operations
# Args:
#   $1: item_name - Name of item being deleted
#   $2: item_type - Type of item (optional, default: "item")
#   $3: force_typing - "true" to require typing confirmation (optional, default: false)
# Returns: 0 for confirmed, 1 for cancelled
delete_confirmation() {
    local item_name="$1"
    local item_type="${2:-item}"
    local force_typing="${3:-false}"
    local confirmation_text="DELETE"
    
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
        typed_confirmation=$(get_user_input "Type '${confirmation_text}' to confirm deletion")
        if [[ $? -ne 0 ]]; then
            return 1
        fi
        
        local typed_upper=$(echo "$typed_confirmation" | tr '[:lower:]' '[:upper:]')
        if [[ "$typed_upper" == "$confirmation_text" ]]; then
            return 0
        else
            if use_colors; then
                echo "${RED}Confirmation text did not match${RESET}" >&2
            else
                echo "Confirmation text did not match" >&2
            fi
            return 1
        fi
    else
        # Simple yes/no confirmation
        confirm "Delete ${item_type} '${item_name}'?" "false"
        return $?
    fi
}

# Function: show_progress_bar
# Display a progress bar
# Args:
#   $1: current - Current progress value
#   $2: total - Total value for completion
#   $3: prefix - Text before progress bar (optional, default: "Progress")
#   $4: suffix - Text after progress bar (optional, default: "Complete")
show_progress_bar() {
    local current="$1"
    local total="$2"
    local prefix="${3:-Progress}"
    local suffix="${4:-Complete}"
    local length=50
    local fill="█"
    local empty="-"
    
    if [[ $total -eq 0 ]]; then
        return 0
    fi
    
    # Calculate progress
    local percent=$(( (current * 100) / total ))
    local filled_length=$(( (current * length) / total ))
    local empty_length=$(( length - filled_length ))
    
    # Build progress bar
    local bar=""
    local i
    
    # Add filled portion
    for (( i=0; i<filled_length; i++ )); do
        bar+="$fill"
    done
    
    # Add empty portion  
    for (( i=0; i<empty_length; i++ )); do
        bar+="$empty"
    done
    
    # Display progress bar
    if use_colors; then
        printf "\r%s |${GREEN}%s${RESET}| %3d%% %s" "$prefix" "$bar" "$percent" "$suffix" >&2
    else
        printf "\r%s |%s| %3d%% %s" "$prefix" "$bar" "$percent" "$suffix" >&2
    fi
}

# Function: show_spinner
# Show a simple spinner (call in loops)
# Args:
#   $1: message - Message to show with spinner (optional)
show_spinner() {
    local message="${1:-Processing}"
    local spinner_chars=("|" "/" "-" "\\")
    local char_index=$(( (SECONDS % 4) ))
    local spinner_char="${spinner_chars[$char_index]}"
    
    if use_colors; then
        printf "\r${CYAN}%s${RESET} %s" "$spinner_char" "$message" >&2
    else
        printf "\r%s %s" "$spinner_char" "$message" >&2
    fi
}

# Function: display_table
# Display data in a simple table format
# Args:
#   $1: title - Optional table title
#   $@: rows - Each argument is a row with columns separated by |
display_table() {
    local title=""
    local rows=()
    
    # Check if first argument is title (starts with uppercase)
    if [[ "$1" =~ ^[A-Z] ]] && [[ $# -gt 1 ]]; then
        title="$1"
        shift
    fi
    
    rows=("$@")
    
    if [[ ${#rows[@]} -eq 0 ]]; then
        if use_colors; then
            echo "${YELLOW}No data to display${RESET}" >&2
        else
            echo "No data to display" >&2
        fi
        return 0
    fi
    
    # Display title
    if [[ -n "$title" ]]; then
        if use_colors; then
            echo "" >&2
            echo "${CYAN}=== ${title} ===${RESET}" >&2
        else
            echo "" >&2
            echo "=== ${title} ===" >&2
        fi
    fi
    
    # Display rows (simple format)
    local row
    for row in "${rows[@]}"; do
        # Replace | with formatted separator
        local formatted_row=$(echo "$row" | sed 's/|/ | /g')
        echo "$formatted_row" >&2
    done
}

# Function: pause_for_input
# Pause execution until user presses Enter
# Args:
#   $1: message - Message to display (optional)
pause_for_input() {
    local message="${1:-Press Enter to continue...}"
    
    if use_colors; then
        printf "${CYAN}%s${RESET}" "$message" >&2
    else
        printf "%s" "$message" >&2
    fi
    
    read -r
}

# Function: show_menu
# Display a menu and get user selection
# Args:
#   $1: title - Menu title
#   $@: options - Menu options
# Returns: Selected index (0-based) via stdout
show_menu() {
    local title="$1"
    shift
    local options=("$@")
    
    while true; do
        # Display menu
        if use_colors; then
            echo "" >&2
            echo "${CYAN}=== ${title} ===${RESET}" >&2
        else
            echo "" >&2
            echo "=== ${title} ===" >&2
        fi
        
        local i
        for i in "${!options[@]}"; do
            local display_num=$((i + 1))
            if use_colors; then
                printf "${YELLOW}%2d.${RESET} %s\n" "$display_num" "${options[$i]}" >&2
            else
                printf "%2d. %s\n" "$display_num" "${options[$i]}" >&2
            fi
        done
        
        # Add quit option
        local quit_num=$((${#options[@]} + 1))
        if use_colors; then
            printf "${YELLOW}%2d.${RESET} Quit\n" "$quit_num" >&2
        else
            printf "%2d. Quit\n" "$quit_num" >&2
        fi
        
        # Get selection
        local selection
        selection=$(get_user_input "Your choice" "" "true")
        if [[ $? -ne 0 ]]; then
            return 1
        fi
        
        # Validate selection
        if [[ "$selection" =~ ^[0-9]+$ ]]; then
            if [[ $selection -eq $quit_num ]]; then
                return 1
            elif [[ $selection -ge 1 && $selection -le ${#options[@]} ]]; then
                echo $((selection - 1))
                return 0
            fi
        fi
        
        # Invalid selection
        if use_colors; then
            echo "${RED}Invalid selection. Please try again.${RESET}" >&2
        else
            echo "Invalid selection. Please try again." >&2
        fi
        echo "" >&2
    done
}

# Validation helper functions
# These can be used with get_user_input as validator functions

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

# Demo function (if script is run directly)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Interactive Components Demo (Shell)"
    echo "=================================="
    echo
    
    # Test basic input
    name=$(get_user_input "Enter your name" "User")
    echo "Hello, $name!"
    echo
    
    # Test confirmation
    if confirm "Continue with demo?" "true"; then
        echo "Continuing..."
        
        # Test list selection
        items=("Option A" "Option B" "Option C")
        echo
        selection=$(select_from_list "Choose an option" "${items[@]}")
        if [[ $? -eq 0 ]]; then
            echo "You selected: ${items[$selection]}"
        else
            echo "Selection cancelled"
        fi
        echo
        
        # Test delete confirmation
        if delete_confirmation "test_file.txt" "file" "false"; then
            echo "File would be deleted"
        else
            echo "Delete cancelled"
        fi
        echo
        
        # Test progress bar
        echo "Progress bar demo:"
        for i in {0..100}; do
            show_progress_bar $i 100 "Loading" "Done"
            sleep 0.02
        done
        echo
        echo "Demo complete!"
    else
        echo "Demo cancelled"
    fi
fi
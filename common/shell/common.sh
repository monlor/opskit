#!/bin/bash
# OpsKit Shell Common Library
# Cross-platform shell utility functions

# ==================== Basic Configuration ====================

# Set error handling
set -euo pipefail

# Get script directory
OPSKIT_SHELL_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPSKIT_ROOT_DIR="$(cd "${OPSKIT_SHELL_LIB_DIR}/../.." && pwd)"

# Color definitions
if [[ -t 1 ]] && [[ "${TERM:-}" != "dumb" ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    PURPLE='\033[0;35m'
    CYAN='\033[0;36m'
    WHITE='\033[1;37m'
    BOLD='\033[1m'
    DIM='\033[2m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    PURPLE=''
    CYAN=''
    WHITE=''
    BOLD=''
    DIM=''
    NC=''
fi

# Log levels
declare -A LOG_LEVELS=(
    ["DEBUG"]=0
    ["INFO"]=1
    ["WARN"]=2
    ["ERROR"]=3
    ["FATAL"]=4
)

# Current log level (default INFO)
CURRENT_LOG_LEVEL=${OPSKIT_LOG_LEVEL:-"INFO"}

# ==================== Platform Detection ====================

# Detect operating system
detect_os() {
    case "$(uname -s)" in
        Darwin*)
            echo "macos"
            ;;
        Linux*)
            echo "linux"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# Detect Linux distribution
detect_linux_distro() {
    if [[ "$(detect_os)" != "linux" ]]; then
        echo "unknown"
        return
    fi
    
    # Prefer /etc/os-release
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "${ID:-unknown}"
        return
    fi
    
    # Fallback detection methods
    if [[ -f /etc/debian_version ]]; then
        echo "debian"
    elif [[ -f /etc/redhat-release ]]; then
        if grep -q "CentOS" /etc/redhat-release; then
            echo "centos"
        else
            echo "rhel"
        fi
    elif [[ -f /etc/arch-release ]]; then
        echo "arch"
    elif [[ -f /etc/SuSE-release ]]; then
        echo "opensuse"
    else
        echo "unknown"
    fi
}

# Detect package manager
detect_package_manager() {
    local os_type
    os_type=$(detect_os)
    
    case "$os_type" in
        macos)
            if command -v brew >/dev/null 2>&1; then
                echo "brew"
            elif command -v port >/dev/null 2>&1; then
                echo "macports"
            else
                echo "none"
            fi
            ;;
        linux)
            if command -v apt-get >/dev/null 2>&1; then
                echo "apt"
            elif command -v dnf >/dev/null 2>&1; then
                echo "dnf"
            elif command -v yum >/dev/null 2>&1; then
                echo "yum"
            elif command -v pacman >/dev/null 2>&1; then
                echo "pacman"
            elif command -v zypper >/dev/null 2>&1; then
                echo "zypper"
            else
                echo "none"
            fi
            ;;
        *)
            echo "none"
            ;;
    esac
}

# ==================== Logging Functions ====================

# Internal logging function
_log() {
    local level="$1"
    local message="$2"
    local color="$3"
    local timestamp
    
    # Check log level
    if [[ ${LOG_LEVELS[$level]} -lt ${LOG_LEVELS[$CURRENT_LOG_LEVEL]} ]]; then
        return
    fi
    
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Output to console
    if [[ "${OPSKIT_LOG_CONSOLE:-1}" == "1" ]]; then
        echo -e "${color}[${timestamp}] ${level}: ${message}${NC}" >&2
    fi
    
    # Output to file (if configured)
    if [[ -n "${OPSKIT_LOG_FILE:-}" ]]; then
        echo "[${timestamp}] ${level}: ${message}" >> "${OPSKIT_LOG_FILE}"
    fi
}

# Public logging functions
log_debug() {
    _log "DEBUG" "$1" "$DIM"
}

log_info() {
    _log "INFO" "$1" "$GREEN"
}

log_warn() {
    _log "WARN" "$1" "$YELLOW"
}

log_error() {
    _log "ERROR" "$1" "$RED"
}

log_fatal() {
    _log "FATAL" "$1" "$BOLD$RED"
}

# Set log level
set_log_level() {
    local level="$1"
    if [[ -n "${LOG_LEVELS[$level]:-}" ]]; then
        CURRENT_LOG_LEVEL="$level"
    else
        log_error "Invalid log level: $level"
        return 1
    fi
}

# ==================== File and Directory Operations ====================

# Ensure directory exists
ensure_dir() {
    local dir_path="$1"
    if [[ ! -d "$dir_path" ]]; then
        mkdir -p "$dir_path"
        log_debug "Created directory: $dir_path"
    fi
}

# Safely remove file or directory
safe_remove() {
    local path="$1"
    if [[ -e "$path" ]]; then
        rm -rf "$path"
        log_debug "Removed: $path"
        return 0
    else
        log_warn "Path does not exist: $path"
        return 1
    fi
}

# Copy file safely
safe_copy() {
    local src="$1"
    local dst="$2"
    
    if [[ ! -e "$src" ]]; then
        log_error "Source file does not exist: $src"
        return 1
    fi
    
    # Ensure target directory exists
    ensure_dir "$(dirname "$dst")"
    
    cp "$src" "$dst"
    log_debug "Copied file: $src -> $dst"
}

# Move file safely
safe_move() {
    local src="$1"
    local dst="$2"
    
    if [[ ! -e "$src" ]]; then
        log_error "Source file does not exist: $src"
        return 1
    fi
    
    # Ensure target directory exists
    ensure_dir "$(dirname "$dst")"
    
    mv "$src" "$dst"
    log_debug "Moved file: $src -> $dst"
}

# Calculate file size (human readable format)
get_file_size() {
    local file_path="$1"
    
    if [[ ! -f "$file_path" ]]; then
        echo "0B"
        return 1
    fi
    
    local size
    if command -v numfmt >/dev/null 2>&1; then
        size=$(stat -c%s "$file_path" 2>/dev/null || stat -f%z "$file_path" 2>/dev/null)
        numfmt --to=iec-i --suffix=B "$size" 2>/dev/null || echo "${size}B"
    else
        # Simple size formatting
        local bytes
        bytes=$(stat -c%s "$file_path" 2>/dev/null || stat -f%z "$file_path" 2>/dev/null)
        
        if [[ $bytes -lt 1024 ]]; then
            echo "${bytes}B"
        elif [[ $bytes -lt 1048576 ]]; then
            echo "$((bytes / 1024))KB"
        elif [[ $bytes -lt 1073741824 ]]; then
            echo "$((bytes / 1048576))MB"
        else
            echo "$((bytes / 1073741824))GB"
        fi
    fi
}

# ==================== System Tools ====================

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if running as root
is_root() {
    [[ $EUID -eq 0 ]]
}

# Get system information
get_system_info() {
    local os_type distro package_manager
    os_type=$(detect_os)
    distro=$(detect_linux_distro)
    package_manager=$(detect_package_manager)
    
    cat << EOF
System Type: $os_type
Distribution: $distro
Package Manager: $package_manager
Architecture: $(uname -m)
Kernel Version: $(uname -r)
User: $(whoami)
Home Directory: $HOME
Shell: $SHELL
EOF
}

# Execute command and check result
run_command() {
    local cmd="$1"
    local description="${2:-Execute command}"
    local allow_fail="${3:-false}"
    
    log_debug "$description: $cmd"
    
    if eval "$cmd"; then
        log_debug "$description succeeded"
        return 0
    else
        local exit_code=$?
        if [[ "$allow_fail" == "true" ]]; then
            log_warn "$description failed (exit code: $exit_code)"
            return $exit_code
        else
            log_error "$description failed (exit code: $exit_code)"
            return $exit_code
        fi
    fi
}

# Execute command and get output
run_command_output() {
    local cmd="$1"
    local description="${2:-Execute command}"
    
    log_debug "$description: $cmd"
    eval "$cmd" 2>/dev/null
}

# ==================== Package Management ====================

# Install system package
install_package() {
    local package="$1"
    local pm
    pm=$(detect_package_manager)
    
    if [[ "$pm" == "none" ]]; then
        log_error "No supported package manager found"
        return 1
    fi
    
    log_info "Installing system package: $package (using $pm)"
    
    case "$pm" in
        brew)
            run_command "brew install '$package'" "Install $package"
            ;;
        macports)
            run_command "sudo port install '$package'" "Install $package"
            ;;
        apt)
            run_command "sudo apt-get update && sudo apt-get install -y '$package'" "Install $package"
            ;;
        dnf)
            run_command "sudo dnf install -y '$package'" "Install $package"
            ;;
        yum)
            run_command "sudo yum install -y '$package'" "Install $package"
            ;;
        pacman)
            run_command "sudo pacman -S --noconfirm '$package'" "Install $package"
            ;;
        zypper)
            run_command "sudo zypper install -y '$package'" "Install $package"
            ;;
        *)
            log_error "Unsupported package manager: $pm"
            return 1
            ;;
    esac
}

# Check if package is installed
is_package_installed() {
    local package="$1"
    local pm
    pm=$(detect_package_manager)
    
    case "$pm" in
        brew)
            brew list "$package" >/dev/null 2>&1
            ;;
        macports)
            port installed "$package" >/dev/null 2>&1
            ;;
        apt)
            dpkg -l "$package" >/dev/null 2>&1
            ;;
        dnf|yum)
            rpm -q "$package" >/dev/null 2>&1
            ;;
        pacman)
            pacman -Q "$package" >/dev/null 2>&1
            ;;
        zypper)
            zypper search --installed-only "$package" >/dev/null 2>&1
            ;;
        *)
            return 1
            ;;
    esac
}

# ==================== User Interaction ====================

# Ask user for confirmation
confirm() {
    local message="$1"
    local default="${2:-n}"
    local prompt
    
    case "$default" in
        y|Y|yes|YES)
            prompt="[Y/n]"
            ;;
        *)
            prompt="[y/N]"
            ;;
    esac
    
    echo -e -n "${CYAN}$message $prompt ${NC}"
    read -r response
    
    # If no input, use default
    if [[ -z "$response" ]]; then
        response="$default"
    fi
    
    case "$response" in
        y|Y|yes|YES|true|TRUE|1)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Show progress bar
show_progress() {
    local current="$1"
    local total="$2"
    local width="${3:-50}"
    local char="${4:-█}"
    
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "\r[%s%s] %d%% (%d/%d)" \
        "$(printf "%*s" $filled | tr ' ' "$char")" \
        "$(printf "%*s" $empty)" \
        "$percentage" "$current" "$total"
    
    if [[ $current -eq $total ]]; then
        echo
    fi
}

# Show selection menu
show_menu() {
    local title="$1"
    shift
    local options=("$@")
    
    echo -e "${BOLD}$title${NC}"
    echo "$(printf '=%.0s' {1..50})"
    
    for i in "${!options[@]}"; do
        echo -e "${CYAN}$((i + 1)).${NC} ${options[i]}"
    done
    
    echo -e -n "${CYAN}Please select (1-${#options[@]}): ${NC}"
}

# ==================== String Processing ====================

# Remove leading and trailing whitespace
trim() {
    local str="$1"
    # Remove leading whitespace
    str="${str#"${str%%[![:space:]]*}"}"
    # Remove trailing whitespace
    str="${str%"${str##*[![:space:]]}"}"
    echo "$str"
}

# Convert to lowercase
to_lowercase() {
    echo "$1" | tr '[:upper:]' '[:lower:]'
}

# Convert to uppercase
to_uppercase() {
    echo "$1" | tr '[:lower:]' '[:upper:]'
}

# Replace string
string_replace() {
    local str="$1"
    local search="$2"
    local replace="$3"
    echo "${str//$search/$replace}"
}

# Check if string contains substring
string_contains() {
    local str="$1"
    local substr="$2"
    [[ "$str" == *"$substr"* ]]
}

# ==================== Network Tools ====================

# Check internet connection
check_internet() {
    local host="${1:-8.8.8.8}"
    local timeout="${2:-5}"
    
    if command_exists ping; then
        ping -c 1 -W "$timeout" "$host" >/dev/null 2>&1
    elif command_exists curl; then
        curl --connect-timeout "$timeout" --silent "$host" >/dev/null 2>&1
    elif command_exists wget; then
        wget --timeout="$timeout" --spider "$host" >/dev/null 2>&1
    else
        log_error "Cannot check internet connection: missing ping, curl, or wget commands"
        return 1
    fi
}

# Download file
download_file() {
    local url="$1"
    local output_file="$2"
    local description="${3:-Download file}"
    
    log_info "$description: $url"
    
    # Ensure output directory exists
    ensure_dir "$(dirname "$output_file")"
    
    if command_exists curl; then
        run_command "curl -fsSL -o '$output_file' '$url'" "$description"
    elif command_exists wget; then
        run_command "wget -q -O '$output_file' '$url'" "$description"
    else
        log_error "Cannot download file: missing curl or wget commands"
        return 1
    fi
}

# ==================== Time Tools ====================

# Get timestamp
get_timestamp() {
    date +%s
}

# Format time
format_time() {
    local timestamp="${1:-$(get_timestamp)}"
    local format="${2:-%Y-%m-%d %H:%M:%S}"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        date -r "$timestamp" +"$format"
    else
        date -d "@$timestamp" +"$format"
    fi
}

# Calculate time difference
time_diff() {
    local start_time="$1"
    local end_time="${2:-$(get_timestamp)}"
    local diff=$((end_time - start_time))
    
    if [[ $diff -lt 60 ]]; then
        echo "${diff}s"
    elif [[ $diff -lt 3600 ]]; then
        echo "$((diff / 60))m$((diff % 60))s"
    else
        echo "$((diff / 3600))h$(((diff % 3600) / 60))m"
    fi
}

# ==================== Error Handling ====================

# Setup error handling traps
setup_error_handling() {
    trap 'handle_error $? $LINENO' ERR
    trap 'handle_exit' EXIT
    trap 'handle_interrupt' INT TERM
}

# Error handling function
handle_error() {
    local exit_code="$1"
    local line_no="$2"
    
    log_error "Error occurred at line $line_no (exit code: $exit_code)"
    
    # Optional: show call stack
    if [[ "${OPSKIT_DEBUG:-0}" == "1" ]]; then
        log_error "Call stack:"
        local frame=0
        while caller $frame; do
            ((frame++))
        done
    fi
    
    exit "$exit_code"
}

# Exit handling function
handle_exit() {
    log_debug "Script execution completed"
}

# Interrupt handling function
handle_interrupt() {
    log_info "Received interrupt signal, cleaning up..."
    exit 130
}

# ==================== Initialization ====================

# Initialization function (optional call)
opskit_init() {
    log_debug "Initializing OpsKit Shell environment"
    
    # Setup error handling
    if [[ "${OPSKIT_ERROR_HANDLING:-1}" == "1" ]]; then
        setup_error_handling
    fi
    
    # Setup log file
    if [[ -n "${OPSKIT_ROOT_DIR:-}" ]]; then
        ensure_dir "$OPSKIT_ROOT_DIR/logs"
        export OPSKIT_LOG_FILE="$OPSKIT_ROOT_DIR/logs/shell_$(date +%Y%m%d).log"
    fi
    
    log_info "OpsKit Shell environment initialization completed"
}

# Show help information
show_shell_help() {
    cat << EOF
${BOLD}OpsKit Shell Common Library${NC}

${BOLD}Platform Detection:${NC}
  detect_os                 - Detect operating system
  detect_linux_distro       - Detect Linux distribution
  detect_package_manager     - Detect package manager

${BOLD}Logging Functions:${NC}
  log_debug <msg>           - Debug log
  log_info <msg>            - Info log
  log_warn <msg>            - Warning log
  log_error <msg>           - Error log
  log_fatal <msg>           - Fatal log
  set_log_level <level>     - Set log level

${BOLD}File Operations:${NC}
  ensure_dir <path>         - Ensure directory exists
  safe_remove <path>        - Safe removal
  safe_copy <src> <dst>     - Safe copy
  safe_move <src> <dst>     - Safe move
  get_file_size <file>      - Get file size

${BOLD}System Tools:${NC}
  command_exists <cmd>      - Check command exists
  is_root                   - Check root privileges
  get_system_info           - Get system information
  run_command <cmd>         - Execute command

${BOLD}Package Management:${NC}
  install_package <pkg>     - Install system package
  is_package_installed <pkg> - Check package installation status

${BOLD}User Interaction:${NC}
  confirm <msg>             - Confirmation dialog
  show_progress <cur> <tot> - Show progress bar
  show_menu <title> <opts>  - Show selection menu

${BOLD}Environment Variables:${NC}
  OPSKIT_LOG_LEVEL         - Log level (DEBUG/INFO/WARN/ERROR/FATAL)
  OPSKIT_LOG_CONSOLE       - Console output (0/1)
  OPSKIT_LOG_FILE          - Log file path
  OPSKIT_DEBUG             - Debug mode (0/1)
  OPSKIT_ERROR_HANDLING    - Error handling (0/1)
EOF
}

# If running this script directly, show help
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    show_shell_help
fi
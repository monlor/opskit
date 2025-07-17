#!/bin/bash

# OpsKit Common Library
# Shared utilities for all OpsKit tools
# This file should be sourced by other tools

# Prevent multiple sourcing
if [ "${OPSKIT_COMMON_LOADED:-}" = "1" ]; then
    return 0
fi
export OPSKIT_COMMON_LOADED=1

# Colors for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export PURPLE='\033[0;35m'
export CYAN='\033[0;36m'
export WHITE='\033[1;37m'
export NC='\033[0m' # No Color

# Global variables
export OPSKIT_VERSION="${OPSKIT_VERSION:-1.0.0}"
export OPSKIT_DIR="${OPSKIT_DIR:-$HOME/.opskit}"
export OPSKIT_TOOLS_DIR="${OPSKIT_TOOLS_DIR:-$OPSKIT_DIR/tools}"
export GITHUB_REPO="${GITHUB_REPO:-https://raw.githubusercontent.com/monlor/opskit/main}"
export OPSKIT_RELEASE="${OPSKIT_RELEASE:-main}"

# Logging functions with timestamps and levels
log_message() {
    local level="$1"
    local color="$2"
    local message="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${color}[${timestamp}] [${level}]${NC} $message"
}

log_debug() {
    if [ "${OPSKIT_DEBUG:-}" = "1" ]; then
        log_message "DEBUG" "$CYAN" "$1"
    fi
}

log_info() {
    log_message "INFO" "$BLUE" "$1"
}

log_success() {
    log_message "SUCCESS" "$GREEN" "$1"
}

log_warning() {
    log_message "WARNING" "$YELLOW" "$1"
}

log_error() {
    log_message "ERROR" "$RED" "$1"
}

log_critical() {
    log_message "CRITICAL" "$PURPLE" "$1"
}

# Progress indicator
show_progress() {
    local message="$1"
    local delay="${2:-0.1}"
    
    echo -n "${message}..."
    for i in {1..3}; do
        sleep "$delay"
        echo -n "."
    done
    echo
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS and architecture
detect_system() {
    local os=""
    local arch=""
    
    case "$(uname -s)" in
        Darwin*) os="macos" ;;
        Linux*) os="linux" ;;
        *) 
            log_error "Unsupported operating system: $(uname -s)"
            return 1
        ;;
    esac
    
    case "$(uname -m)" in
        x86_64) arch="amd64" ;;
        arm64|aarch64) arch="arm64" ;;
        i386|i686) arch="386" ;;
        *)
            log_error "Unsupported architecture: $(uname -m)"
            return 1
        ;;
    esac
    
    echo "${os}_${arch}"
}

# Get package manager for current system
get_package_manager() {
    local system=$(detect_system)
    
    case "$system" in
        macos_*)
            if command_exists brew; then
                echo "brew"
            else
                echo "brew_missing"
            fi
        ;;
        linux_*)
            if command_exists apt-get; then
                echo "apt"
            elif command_exists yum; then
                echo "yum"
            elif command_exists dnf; then
                echo "dnf"
            elif command_exists pacman; then
                echo "pacman"
            elif command_exists zypper; then
                echo "zypper"
            else
                echo "unknown"
            fi
        ;;
        *)
            echo "unsupported"
        ;;
    esac
}

# Download file with retry and verification
download_file() {
    local url="$1"
    local output="$2"
    local max_retries="${3:-3}"
    local retry_delay="${4:-2}"
    
    log_debug "Downloading: $url -> $output"
    
    for attempt in $(seq 1 $max_retries); do
        log_debug "Download attempt $attempt/$max_retries"
        
        if curl -sSL --connect-timeout 10 --max-time 60 "$url" -o "$output" 2>/dev/null; then
            if [ -f "$output" ] && [ -s "$output" ]; then
                log_debug "Download successful"
                return 0
            else
                log_debug "Downloaded file is empty or missing"
            fi
        else
            log_debug "Download failed with curl error"
        fi
        
        if [ $attempt -lt $max_retries ]; then
            log_debug "Retrying in ${retry_delay} seconds..."
            sleep "$retry_delay"
        fi
    done
    
    log_error "Failed to download after $max_retries attempts: $url"
    return 1
}

# Load dependency configuration with version management
load_dependency_config() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local local_file="$script_dir/dependencies.json"
    local config_file="$OPSKIT_TOOLS_DIR/$OPSKIT_RELEASE/dependencies.json"
    local config_url
    
    # Construct remote URL based on version
    if [ "$OPSKIT_RELEASE" = "main" ]; then
        config_url="$GITHUB_REPO/tools/dependencies.json"
    else
        # For release versions, use release URL format
        local repo_base="${GITHUB_REPO%/main*}"
        if [[ "$GITHUB_REPO" == *"/main" ]]; then
            config_url="${repo_base}/${OPSKIT_RELEASE}/tools/dependencies.json"
        else
            config_url="${GITHUB_REPO%/*}/${OPSKIT_RELEASE}/tools/dependencies.json"
        fi
    fi
    
    # Create version directory
    mkdir -p "$(dirname "$config_file")"
    
    # Priority 1: Local file in current directory (for development)
    if [ -f "$local_file" ]; then
        log_debug "Using local dependency config: $local_file"
        echo "$local_file"
        return 0
    fi
    
    # Priority 2: Check if we need to update main version
    local should_update=false
    if [ "$OPSKIT_RELEASE" = "main" ] && [ "${OPSKIT_NO_AUTO_UPDATE:-}" != "1" ]; then
        should_update=true
    fi
    
    # Priority 3: Use cached file if exists and no update needed
    if [ -f "$config_file" ] && [ "$should_update" != "true" ]; then
        log_debug "Using cached dependency config: $config_file"
        echo "$config_file"
        return 0
    fi
    
    # Priority 4: Download from remote
    log_info "Loading dependency configuration (version: $OPSKIT_RELEASE)..."
    
    # Handle file:// URLs for local testing
    if [[ "$config_url" =~ ^file:// ]]; then
        local source_file="${config_url#file://}/tools/dependencies.json"
        if [ -f "$source_file" ]; then
            cp "$source_file" "$config_file"
            log_debug "Copied local dependency config: $source_file -> $config_file"
        else
            log_error "Local dependency config not found: $source_file"
            return 1
        fi
    else
        if ! download_file "$config_url" "$config_file"; then
            log_error "Failed to load dependency configuration"
            return 1
        fi
    fi
    
    echo "$config_file"
}

# Get dependency package name
get_package_name() {
    local dep="$1"
    local pkg_manager=$(get_package_manager)
    local config_file=$(load_dependency_config)
    
    if [ ! -f "$config_file" ]; then
        log_error "Dependency configuration not available"
        return 1
    fi
    
    local pkg_name=""
    
    # Try to parse JSON with jq if available, otherwise use basic parsing
    if command_exists jq; then
        # First try specific package manager in "packages" object
        pkg_name=$(jq -r ".dependencies.\"$dep\".packages.\"$pkg_manager\" // empty" "$config_file" 2>/dev/null)
        
        # If not found, try the default "package" field
        if [ -z "$pkg_name" ] || [ "$pkg_name" = "null" ] || [ "$pkg_name" = "empty" ]; then
            pkg_name=$(jq -r ".dependencies.\"$dep\".package // empty" "$config_file" 2>/dev/null)
        fi
    else
        # Basic JSON parsing - first try packages object
        pkg_name=$(grep -A 15 "\"$dep\"" "$config_file" | grep -A 10 '"packages"' | grep "\"$pkg_manager\"" | sed 's/.*"\([^"]*\)".*/\1/' | head -1)
        
        # If not found, try default package field
        if [ -z "$pkg_name" ]; then
            pkg_name=$(grep -A 5 "\"$dep\"" "$config_file" | grep '"package"' | sed 's/.*"\([^"]*\)".*/\1/' | head -1)
        fi
    fi
    
    echo "$pkg_name"
}

# Get dependency description
get_dependency_description() {
    local dep="$1"
    local config_file=$(load_dependency_config)
    
    if [ ! -f "$config_file" ]; then
        echo "Required dependency: $dep"
        return
    fi
    
    if command_exists jq; then
        jq -r ".dependencies.\"$dep\".description // \"Required dependency: $dep\"" "$config_file" 2>/dev/null
    else
        # Basic JSON parsing for description
        local desc=$(grep -A 5 "\"$dep\"" "$config_file" | grep '"description"' | sed 's/.*"\([^"]*\)".*/\1/' | head -1)
        echo "${desc:-Required dependency: $dep}"
    fi
}

# Build install command
build_install_command() {
    local pkg_name="$1"
    local pkg_manager="$2"
    
    case "$pkg_manager" in
        brew)
            echo "brew install $pkg_name"
        ;;
        apt)
            echo "sudo apt-get update && sudo apt-get install -y $pkg_name"
        ;;
        yum)
            echo "sudo yum install -y $pkg_name"
        ;;
        dnf)
            echo "sudo dnf install -y $pkg_name"
        ;;
        pacman)
            echo "sudo pacman -S $pkg_name"
        ;;
        zypper)
            echo "sudo zypper install $pkg_name"
        ;;
        *)
            echo "# Package manager '$pkg_manager' not supported"
            return 1
        ;;
    esac
}

# Check single dependency
check_dependency() {
    local dep="$1"
    local config_file=$(load_dependency_config)
    
    if [ ! -f "$config_file" ]; then
        return 1
    fi
    
    # Get the command to check
    local check_cmd=""
    if command_exists jq; then
        check_cmd=$(jq -r ".dependencies.\"$dep\".check // \"$dep\"" "$config_file" 2>/dev/null)
    else
        # Default to the dependency name as command
        check_cmd="$dep"
    fi
    
    # Special handling for common dependency aliases
    case "$dep" in
        mysql) check_cmd="mysql" ;;
        awscli) check_cmd="aws" ;;
        *) ;;
    esac
    
    command_exists "$check_cmd"
}

# Show manual installation instructions
show_manual_install_instructions() {
    local dep="$1"
    local pkg_manager="$2"
    local pkg_name="$3"
    local description="$4"
    
    echo
    echo "=== Manual Installation Required ==="
    echo "Dependency: $dep"
    echo "Description: $description"
    echo "Package Manager: $pkg_manager"
    echo
    
    if [ -n "$pkg_name" ] && [ "$pkg_name" != "null" ]; then
        local install_cmd=$(build_install_command "$pkg_name" "$pkg_manager")
        if [ -n "$install_cmd" ] && [ "$install_cmd" != "# Package manager '$pkg_manager' not supported" ]; then
            echo "Recommended installation command:"
            echo "  $install_cmd"
        else
            echo "Package name: $pkg_name"
            echo "Please install using your system's package manager."
        fi
    else
        echo "Please install '$dep' using your system's package manager:"
        case "$pkg_manager" in
            brew) echo "  brew install <package-name>" ;;
            apt) echo "  sudo apt-get install <package-name>" ;;
            yum) echo "  sudo yum install <package-name>" ;;
            dnf) echo "  sudo dnf install <package-name>" ;;
            pacman) echo "  sudo pacman -S <package-name>" ;;
            zypper) echo "  sudo zypper install <package-name>" ;;
            *) echo "  Use your system's package manager to install '$dep'" ;;
        esac
    fi
    
    echo
    echo "After installation, please run this script again."
    echo
}

# Install single dependency with user confirmation
install_dependency() {
    local dep="$1"
    local auto_confirm="${2:-false}"
    
    log_info "Processing dependency: $dep"
    
    # Check if already installed
    if check_dependency "$dep"; then
        log_success "Dependency '$dep' is already installed"
        return 0
    fi
    
    # Get dependency information
    local pkg_manager=$(get_package_manager)
    local pkg_name=$(get_package_name "$dep")
    local description=$(get_dependency_description "$dep")
    
    # Show installation details
    echo
    echo "=== Dependency Installation ==="
    echo "Dependency: $dep"
    echo "Description: $description"
    echo "Package Manager: $pkg_manager"
    if [ -n "$pkg_name" ] && [ "$pkg_name" != "null" ]; then
        echo "Package Name: $pkg_name"
    fi
    echo
    
    # Build install command if possible
    local install_cmd=""
    if [ -n "$pkg_name" ] && [ "$pkg_name" != "null" ]; then
        install_cmd=$(build_install_command "$pkg_name" "$pkg_manager")
    fi
    
    if [ -z "$install_cmd" ] || [ "$install_cmd" = "# Package manager '$pkg_manager' not supported" ]; then
        log_warning "Automatic installation not available for '$dep' on $pkg_manager"
        show_manual_install_instructions "$dep" "$pkg_manager" "$pkg_name" "$description"
        return 1
    fi
    
    # User confirmation
    if [ "$auto_confirm" != "true" ]; then
        log_warning "This will install '$dep' using your system package manager"
        echo "Install command: $install_cmd"
        echo
        read -p "Proceed with automatic installation? (y/N): " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Automatic installation declined"
            show_manual_install_instructions "$dep" "$pkg_manager" "$pkg_name" "$description"
            return 1
        fi
    fi
    
    # Handle package manager setup
    case "$pkg_manager" in
        brew_missing)
            log_info "Installing Homebrew first..."
            if ! /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; then
                log_error "Failed to install Homebrew"
                show_manual_install_instructions "$dep" "brew" "$pkg_name" "$description"
                return 1
            fi
            pkg_manager="brew"
            install_cmd=$(build_install_command "$pkg_name" "$pkg_manager")
        ;;
        apt)
            log_info "Updating package list..."
            if ! sudo apt-get update >/dev/null 2>&1; then
                log_warning "Failed to update package list, proceeding anyway..."
            fi
        ;;
        yum|dnf)
            log_info "Updating package cache..."
            sudo $pkg_manager check-update >/dev/null 2>&1 || true
        ;;
    esac
    
    # Execute installation
    log_info "Installing $dep..."
    if eval "$install_cmd"; then
        # Verify installation
        if check_dependency "$dep"; then
            log_success "Successfully installed: $dep"
            return 0
        else
            log_error "Installation completed but dependency check failed: $dep"
            show_manual_install_instructions "$dep" "$pkg_manager" "$pkg_name" "$description"
            return 1
        fi
    else
        log_error "Failed to install: $dep"
        show_manual_install_instructions "$dep" "$pkg_manager" "$pkg_name" "$description"
        return 1
    fi
}

# Check multiple dependencies
check_dependencies() {
    local deps=("$@")
    local missing_deps=()
    local failed_installs=()
    
    if [ ${#deps[@]} -eq 0 ]; then
        log_debug "No dependencies to check"
        return 0
    fi
    
    log_info "Checking dependencies: ${deps[*]}"
    
    # Check which dependencies are missing
    for dep in "${deps[@]}"; do
        if ! check_dependency "$dep"; then
            missing_deps+=("$dep")
            log_debug "Missing dependency: $dep"
        else
            log_debug "Found dependency: $dep"
        fi
    done
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        log_success "All dependencies are satisfied"
        return 0
    fi
    
    # Show missing dependencies
    log_warning "Missing dependencies: ${missing_deps[*]}"
    echo
    echo "The following dependencies need to be installed:"
    for dep in "${missing_deps[@]}"; do
        echo "  - $dep"
    done
    echo
    
    read -p "Install missing dependencies automatically? (Y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log_error "Cannot proceed without required dependencies"
        echo "Please install the missing dependencies manually:"
        for dep in "${missing_deps[@]}"; do
            local install_cmd=$(get_install_command "$dep")
            if [ -n "$install_cmd" ]; then
                echo "  $install_cmd"
            fi
        done
        return 1
    fi
    
    # Install missing dependencies
    for dep in "${missing_deps[@]}"; do
        if ! install_dependency "$dep" "false"; then
            failed_installs+=("$dep")
        fi
    done
    
    # Check results
    if [ ${#failed_installs[@]} -gt 0 ]; then
        log_error "Failed to install: ${failed_installs[*]}"
        return 1
    else
        log_success "All dependencies installed successfully"
        return 0
    fi
}

# Confirmation prompt with custom message
confirm_action() {
    local message="$1"
    local confirmation_text="${2:-CONFIRM}"
    local prompt="${3:-Type '$confirmation_text' to proceed: }"
    
    echo
    echo -e "${YELLOW}⚠️  $message${NC}"
    echo
    read -p "$prompt" user_input
    
    if [ "$user_input" = "$confirmation_text" ]; then
        return 0
    else
        log_info "Action cancelled by user"
        return 1
    fi
}

# Create temporary directory with cleanup
create_temp_dir() {
    local temp_dir=$(mktemp -d)
    
    # Set up cleanup trap
    cleanup_temp_dir() {
        if [ -n "$temp_dir" ] && [ -d "$temp_dir" ]; then
            rm -rf "$temp_dir"
            log_debug "Cleaned up temporary directory: $temp_dir"
        fi
    }
    
    trap cleanup_temp_dir EXIT
    echo "$temp_dir"
}

# Initialize common environment
init_common() {
    # Create necessary directories
    mkdir -p "$OPSKIT_DIR" "$OPSKIT_TOOLS_DIR"
    
    # Set debug mode if requested
    if [ "${1:-}" = "--debug" ] || [ "${OPSKIT_DEBUG:-}" = "1" ]; then
        export OPSKIT_DEBUG=1
        log_debug "Debug mode enabled"
    fi
    
    log_debug "Common library initialized"
    log_debug "OPSKIT_DIR: $OPSKIT_DIR"
    log_debug "OPSKIT_TOOLS_DIR: $OPSKIT_TOOLS_DIR"
    log_debug "GITHUB_REPO: $GITHUB_REPO"
    log_debug "System: $(detect_system)"
    log_debug "Package Manager: $(get_package_manager)"
}

# Export functions for use in other scripts
export -f log_debug log_info log_success log_warning log_error log_critical
export -f show_progress command_exists detect_system get_package_manager
export -f download_file load_dependency_config get_package_name
export -f get_dependency_description build_install_command show_manual_install_instructions
export -f check_dependency install_dependency check_dependencies
export -f confirm_action create_temp_dir init_common
#!/bin/bash

# OpsKit Installation Script
# GitHub: https://github.com/monlor/opskit
# Usage: curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash
# Usage: curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash -s -- --version=v1.0.0

set -euo pipefail

# Configuration
REPO="monlor/opskit"
GITHUB_API="https://api.github.com/repos/${REPO}"
GITHUB_RELEASES="${GITHUB_API}/releases"
INSTALL_DIR="/usr/local/bin"
BINARY_NAME="opskit"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
VERSION=""
FORCE=false
DEBUG=false

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_debug() {
    if [[ "$DEBUG" == "true" ]]; then
        echo -e "${YELLOW}[DEBUG]${NC} $1"
    fi
}

# Help function
show_help() {
    cat << EOF
OpsKit Installation Script

Usage: $0 [OPTIONS]

OPTIONS:
    --version=VERSION   Install specific version (e.g., v1.0.0, main)
    --force            Force reinstallation even if already installed
    --debug            Enable debug output
    --help             Show this help message

Examples:
    # Install latest release
    $0

    # Install specific version
    $0 --version=v1.0.0

    # Install main branch (development version)
    $0 --version=main

    # Remote installation
    curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash
    curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash -s -- --version=v1.0.0
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version=*)
                VERSION="${1#*=}"
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Detect operating system
detect_os() {
    local os
    case "$(uname -s)" in
        Linux*)
            os="linux"
            ;;
        Darwin*)
            os="darwin"
            ;;
        CYGWIN*|MINGW32*|MSYS*|MINGW*)
            os="windows"
            ;;
        *)
            print_error "Unsupported operating system: $(uname -s)"
            exit 1
            ;;
    esac
    echo "$os"
}

# Detect architecture
detect_arch() {
    local arch
    case "$(uname -m)" in
        x86_64|amd64)
            arch="amd64"
            ;;
        i386|i686)
            arch="386"
            ;;
        arm64|aarch64)
            arch="arm64"
            ;;
        armv7l)
            arch="arm"
            ;;
        *)
            print_error "Unsupported architecture: $(uname -m)"
            exit 1
            ;;
    esac
    echo "$arch"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
check_dependencies() {
    local missing_deps=()
    
    for cmd in curl tar; do
        if ! command_exists "$cmd"; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        print_info "Please install the missing dependencies and try again."
        exit 1
    fi
}

# Get latest release version
get_latest_version() {
    local latest_url="${GITHUB_RELEASES}/latest"
    print_debug "Fetching latest release from: $latest_url"
    
    curl -fsSL "$latest_url" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/' || {
        print_error "Failed to fetch latest release information"
        exit 1
    }
}

# Validate version exists
validate_version() {
    local version="$1"
    
    if [[ "$version" == "main" ]]; then
        return 0
    fi
    
    local releases_url="${GITHUB_RELEASES}"
    print_debug "Validating version $version"
    
    if ! curl -fsSL "$releases_url" | grep -q "\"tag_name\": \"$version\""; then
        print_error "Version $version not found in releases"
        print_info "Available versions:"
        curl -fsSL "$releases_url" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/' | head -10
        exit 1
    fi
}

# Download and install binary
install_binary() {
    local version="$1"
    local os="$2"
    local arch="$3"
    
    local binary_name="${BINARY_NAME}"
    if [[ "$os" == "windows" ]]; then
        binary_name="${BINARY_NAME}.exe"
    fi
    
    local download_url
    if [[ "$version" == "main" ]]; then
        # For main branch, we would need to build from source or use a CI artifact
        print_error "Main branch installation not yet supported"
        print_info "Main branch requires building from source. Please use a release version."
        exit 1
    else
        # Download from releases
        local archive_name="${BINARY_NAME}_${version#v}_${os}_${arch}.tar.gz"
        download_url="https://github.com/${REPO}/releases/download/${version}/${archive_name}"
    fi
    
    print_info "Downloading OpsKit $version for $os/$arch..."
    print_debug "Download URL: $download_url"
    
    local temp_dir
    temp_dir=$(mktemp -d)
    local archive_path="${temp_dir}/${archive_name}"
    
    # Download the archive
    if ! curl -fsSL "$download_url" -o "$archive_path"; then
        print_error "Failed to download OpsKit binary"
        print_info "Download URL: $download_url"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Extract the archive
    print_info "Extracting archive..."
    if ! tar -xzf "$archive_path" -C "$temp_dir"; then
        print_error "Failed to extract archive"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Find the binary
    local binary_path="${temp_dir}/${binary_name}"
    if [[ ! -f "$binary_path" ]]; then
        print_error "Binary not found in archive"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Install the binary
    print_info "Installing OpsKit to $INSTALL_DIR..."
    
    # Check if we need sudo
    if [[ ! -w "$INSTALL_DIR" ]]; then
        if command_exists sudo; then
            sudo cp "$binary_path" "$INSTALL_DIR/$BINARY_NAME"
            sudo chmod +x "$INSTALL_DIR/$BINARY_NAME"
        else
            print_error "Cannot write to $INSTALL_DIR and sudo is not available"
            print_info "Please run as root or choose a different installation directory"
            rm -rf "$temp_dir"
            exit 1
        fi
    else
        cp "$binary_path" "$INSTALL_DIR/$BINARY_NAME"
        chmod +x "$INSTALL_DIR/$BINARY_NAME"
    fi
    
    # Clean up
    rm -rf "$temp_dir"
    
    print_success "OpsKit $version installed successfully!"
}

# Check if already installed
check_existing_installation() {
    if command_exists "$BINARY_NAME"; then
        local current_version
        current_version=$("$BINARY_NAME" --version 2>/dev/null | grep -o 'v[0-9.]*' || echo "unknown")
        
        if [[ "$FORCE" == "false" ]]; then
            print_warning "OpsKit is already installed (version: $current_version)"
            print_info "Use --force to reinstall or --version to install a different version"
            exit 0
        else
            print_info "Force reinstallation requested (current version: $current_version)"
        fi
    fi
}

# Main installation function
main() {
    parse_args "$@"
    
    print_info "Starting OpsKit installation..."
    
    # Check dependencies
    check_dependencies
    
    # Detect system
    local os arch
    os=$(detect_os)
    arch=$(detect_arch)
    print_info "Detected system: $os/$arch"
    
    # Check existing installation
    check_existing_installation
    
    # Determine version to install
    if [[ -z "$VERSION" ]]; then
        print_info "No version specified, fetching latest release..."
        VERSION=$(get_latest_version)
        print_info "Latest version: $VERSION"
    fi
    
    # Validate version
    if [[ "$VERSION" != "main" ]]; then
        validate_version "$VERSION"
    fi
    
    # Install binary
    install_binary "$VERSION" "$os" "$arch"
    
    # Verify installation
    if command_exists "$BINARY_NAME"; then
        local installed_version
        installed_version=$("$BINARY_NAME" --version 2>/dev/null || echo "unknown")
        print_success "Installation verified: $installed_version"
        print_info "Run '$BINARY_NAME --help' to get started"
    else
        print_error "Installation verification failed"
        exit 1
    fi
}

# Run main function
main "$@"
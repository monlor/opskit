#!/bin/bash

# OpsKit Build Script
# This script builds the OpsKit Go application for multiple platforms

set -euo pipefail

VERSION="${VERSION:-2.0.0}"
BUILD_DIR="build"
BINARY_NAME="opskit"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Clean build directory
clean_build() {
    log_info "Cleaning build directory..."
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
}

# Build for single platform
build_platform() {
    local os=$1
    local arch=$2
    local ext=$3
    
    log_info "Building for $os/$arch..."
    
    local output_name="${BINARY_NAME}"
    if [ "$os" = "windows" ]; then
        output_name="${BINARY_NAME}.exe"
    fi
    
    local output_path="$BUILD_DIR/${BINARY_NAME}-${os}-${arch}${ext}"
    
    GOOS=$os GOARCH=$arch go build -ldflags="-X main.version=$VERSION" -o "$output_path" main.go
    
    if [ $? -eq 0 ]; then
        log_success "Built $output_path"
        
        # Create platform-specific directory
        local platform_dir="$BUILD_DIR/$os-$arch"
        mkdir -p "$platform_dir"
        cp "$output_path" "$platform_dir/$output_name"
        
        # Copy documentation
        cp README-GO.md "$platform_dir/README.md"
        cp tools/tools.json "$platform_dir/" 2>/dev/null || true
        cp tools/dependencies.json "$platform_dir/" 2>/dev/null || true
        
        # Create archive
        cd "$BUILD_DIR"
        if command -v tar >/dev/null 2>&1; then
            tar -czf "${BINARY_NAME}-${os}-${arch}.tar.gz" "$os-$arch"
            log_success "Created archive: ${BINARY_NAME}-${os}-${arch}.tar.gz"
        fi
        cd ..
    else
        log_error "Failed to build for $os/$arch"
        return 1
    fi
}

# Build for all platforms
build_all() {
    log_info "Building OpsKit v$VERSION for all platforms..."
    
    # Common platforms
    build_platform "linux" "amd64" ""
    build_platform "linux" "arm64" ""
    build_platform "darwin" "amd64" ""
    build_platform "darwin" "arm64" ""
    build_platform "windows" "amd64" ".exe"
    
    log_success "All builds completed successfully!"
}

# Build for current platform only
build_current() {
    local os=$(go env GOOS)
    local arch=$(go env GOARCH)
    
    log_info "Building for current platform ($os/$arch)..."
    
    local output_name="$BINARY_NAME"
    if [ "$os" = "windows" ]; then
        output_name="${BINARY_NAME}.exe"
    fi
    
    go build -ldflags="-X main.version=$VERSION" -o "$output_name" main.go
    
    if [ $? -eq 0 ]; then
        log_success "Built $output_name"
        log_info "You can now run: ./$output_name"
    else
        log_error "Build failed"
        return 1
    fi
}

# Test the build
test_build() {
    log_info "Running tests..."
    go test ./... -v
    
    if [ $? -eq 0 ]; then
        log_success "All tests passed"
    else
        log_error "Some tests failed"
        return 1
    fi
}

# Install dependencies
install_deps() {
    log_info "Installing Go dependencies..."
    go mod tidy
    go mod download
    log_success "Dependencies installed"
}

# Show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  all      Build for all platforms (default)"
    echo "  current  Build for current platform only"
    echo "  test     Run tests"
    echo "  deps     Install dependencies"
    echo "  clean    Clean build directory"
    echo "  help     Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  VERSION  Set build version (default: 2.0.0)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Build for all platforms"
    echo "  $0 current            # Build for current platform"
    echo "  VERSION=2.1.0 $0      # Build with custom version"
}

# Main script
main() {
    local command=${1:-all}
    
    case $command in
        all)
            install_deps
            test_build
            clean_build
            build_all
            ;;
        current)
            install_deps
            test_build
            build_current
            ;;
        test)
            test_build
            ;;
        deps)
            install_deps
            ;;
        clean)
            clean_build
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Check if Go is installed
if ! command -v go >/dev/null 2>&1; then
    log_error "Go is not installed. Please install Go first."
    exit 1
fi

# Run main function
main "$@"
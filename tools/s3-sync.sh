#!/bin/bash

# S3 Storage Synchronization Tool
# Part of OpsKit - Remote Operations Toolkit

set -euo pipefail

# Load common library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_FILE="$SCRIPT_DIR/common.sh"

if [ -f "$COMMON_FILE" ]; then
    source "$COMMON_FILE"
    log_debug "S3 Sync Tool loaded with common library"
else
    # Fallback logging functions
    log_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
    log_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
    log_warning() { echo -e "\033[1;33m[WARNING]\033[0m $1"; }
    log_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }
    command_exists() { command -v "$1" >/dev/null 2>&1; }
    confirm_action() {
        local message="$1"
        echo -e "\033[1;33m⚠️  $message\033[0m"
        read -p "Proceed? (y/N): " -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]]
    }
fi

# Validate path format
validate_path() {
    local path="$1"
    local path_type="$2"
    
    if [[ "$path" =~ ^s3:// ]]; then
        if [[ ! "$path" =~ ^s3://[a-zA-Z0-9.\-_]+(/.*)?$ ]]; then
            log_error "Invalid S3 path format: $path"
            echo "S3 path should be in format: s3://bucket-name/path/to/folder/"
            return 1
        fi
    else
        if [ ! -e "$path" ]; then
            if [ "$path_type" = "source" ]; then
                log_error "Source path does not exist: $path"
                return 1
            else
                log_warning "Destination path does not exist: $path"
                read -p "Create destination directory? (Y/n): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                    mkdir -p "$path" 2>/dev/null || {
                        log_error "Cannot create destination directory: $path"
                        return 1
                    }
                    log_success "Created destination directory: $path"
                fi
            fi
        fi
    fi
    return 0
}

# Check AWS credentials
check_aws_credentials() {
    log_info "Checking AWS credentials..."
    
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_warning "AWS credentials not configured or invalid"
        echo
        echo "Please configure AWS credentials using one of these methods:"
        echo "1. Run 'aws configure' to set up credentials interactively"
        echo "2. Set environment variables:"
        echo "   export AWS_ACCESS_KEY_ID=your_access_key"
        echo "   export AWS_SECRET_ACCESS_KEY=your_secret_key"
        echo "   export AWS_DEFAULT_REGION=your_region"
        echo "3. Use IAM roles (if running on EC2)"
        echo
        
        read -p "Configure AWS credentials now? (Y/n): " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            aws configure
            # Test again after configuration
            if ! aws sts get-caller-identity >/dev/null 2>&1; then
                log_error "AWS credentials still not working"
                return 1
            fi
        else
            return 1
        fi
    fi
    
    # Show current AWS identity
    local aws_identity=$(aws sts get-caller-identity --output text --query 'Account' 2>/dev/null || echo "Unknown")
    local aws_region=$(aws configure get region 2>/dev/null || echo "Not set")
    
    log_success "AWS credentials verified"
    echo "  Account: $aws_identity"
    echo "  Region: $aws_region"
    echo
    
    return 0
}

# Get sync statistics
get_sync_stats() {
    local src_path="$1"
    local dst_path="$2"
    
    echo "=== Sync Preview ==="
    echo "Analyzing paths..."
    
    # Dry run to get statistics
    aws s3 sync "$src_path" "$dst_path" --dryrun 2>/dev/null | head -20
    
    local changes=$(aws s3 sync "$src_path" "$dst_path" --dryrun 2>/dev/null | wc -l)
    
    if [ "$changes" -gt 0 ]; then
        echo
        echo "Expected changes: $changes file operations"
        if [ "$changes" -gt 20 ]; then
            echo "(Showing first 20 operations above)"
        fi
    else
        echo "No changes detected - source and destination are in sync"
    fi
    echo
}

# S3 sync main function
s3_sync() {
    log_info "Starting S3 Sync Tool..."
    
    # Check dependencies using common library if available
    if command_exists check_dependencies; then
        log_info "Checking AWS CLI dependencies..."
        if ! check_dependencies "awscli"; then
            log_error "Required dependencies not available"
            return 1
        fi
    else
        # Fallback dependency check
        if ! command_exists aws; then
            log_error "AWS CLI is not installed. Please install it first."
            echo "Installation commands:"
            echo "  macOS: brew install awscli"
            echo "  Ubuntu/Debian: sudo apt-get install awscli"
            echo "  CentOS/RHEL: sudo yum install awscli"
            echo "  Or use pip: pip install awscli"
            return 1
        fi
    fi
    
    # Check AWS credentials
    if ! check_aws_credentials; then
        log_error "Cannot proceed without valid AWS credentials"
        return 1
    fi
    
    echo "=== S3 Synchronization ==="
    echo
    
    # Source and destination input
    echo "Enter synchronization paths:"
    echo "Supported formats:"
    echo "  - Local: /path/to/local/folder"
    echo "  - S3: s3://bucket-name/path/to/folder/"
    echo
    
    read -p "Source path: " src_path
    read -p "Destination path: " dst_path
    
    # Validate paths
    if ! validate_path "$src_path" "source"; then
        return 1
    fi
    
    if ! validate_path "$dst_path" "destination"; then
        return 1
    fi
    
    # Ensure paths end with / for directories
    if [[ "$src_path" != */ ]] && [[ "$src_path" =~ ^s3:// ]]; then
        src_path="$src_path/"
    fi
    if [[ "$dst_path" != */ ]] && [[ "$dst_path" =~ ^s3:// ]]; then
        dst_path="$dst_path/"
    fi
    
    echo
    echo "Synchronization Details:"
    echo "  Source: $src_path"
    echo "  Destination: $dst_path"
    echo
    
    # Sync options
    local aws_options=""
    
    # Delete option
    echo "Sync Options:"
    read -p "Delete files in destination that don't exist in source? (y/N): " -n 1 -r delete_option
    echo
    
    if [[ $delete_option =~ ^[Yy]$ ]]; then
        aws_options="$aws_options --delete"
        echo -e "${RED}⚠️  WARNING: Files in destination will be deleted if they don't exist in source!${NC}"
    fi
    
    # Additional options
    read -p "Include file metadata (timestamps, permissions)? (Y/n): " -n 1 -r metadata_option
    echo
    
    if [[ ! $metadata_option =~ ^[Nn]$ ]]; then
        aws_options="$aws_options --exact-timestamps"
    fi
    
    read -p "Exclude hidden files (starting with .)? (y/N): " -n 1 -r hidden_option
    echo
    
    if [[ $hidden_option =~ ^[Yy]$ ]]; then
        aws_options="$aws_options --exclude '.*'"
    fi
    
    # Size filter
    read -p "Exclude files larger than X MB (enter number, or press Enter to skip): " size_limit
    if [[ "$size_limit" =~ ^[0-9]+$ ]]; then
        aws_options="$aws_options --exclude '*' --include '*' --exclude-size-gt ${size_limit}MB"
    fi
    
    echo
    
    # Show preview
    log_info "Analyzing synchronization..."
    get_sync_stats "$src_path" "$dst_path"
    
    # Dry run option
    read -p "Perform dry run first (preview changes without applying)? (Y/n): " -n 1 -r dry_run
    echo
    
    if [[ ! $dry_run =~ ^[Nn]$ ]]; then
        log_info "Performing dry run..."
        echo
        aws s3 sync "$src_path" "$dst_path" $aws_options --dryrun
        echo
        read -p "Proceed with actual synchronization? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Synchronization cancelled by user"
            return 0
        fi
    else
        # Final confirmation for immediate sync
        echo -e "${YELLOW}Ready to start synchronization with the following settings:${NC}"
        echo "  Source: $src_path"
        echo "  Destination: $dst_path"
        echo "  Options: $aws_options"
        echo
        read -p "Proceed with synchronization? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Synchronization cancelled by user"
            return 0
        fi
    fi
    
    # Perform synchronization
    log_info "Starting S3 synchronization..."
    echo "Progress will be shown below:"
    echo
    
    local start_time=$(date +%s)
    
    if aws s3 sync "$src_path" "$dst_path" $aws_options --cli-read-timeout 0 --cli-connect-timeout 60; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        echo
        log_success "S3 synchronization completed successfully"
        echo "  Duration: ${duration} seconds"
        
        # Show final statistics
        echo
        log_info "Synchronization summary:"
        get_sync_stats "$src_path" "$dst_path"
        
    else
        local exit_code=$?
        echo
        log_error "S3 synchronization failed (exit code: $exit_code)"
        echo
        echo "Common issues and solutions:"
        echo "  - Check network connectivity"
        echo "  - Verify AWS credentials and permissions"
        echo "  - Ensure bucket exists and is accessible"
        echo "  - Check for sufficient disk space (for downloads)"
        echo "  - Verify file permissions (for uploads)"
        return 1
    fi
}

# Run the S3 sync tool
s3_sync
#!/bin/bash

# MySQL Database Synchronization Tool
# Part of OpsKit - Remote Operations Toolkit

set -euo pipefail

# Load common library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_FILE="$SCRIPT_DIR/common.sh"

if [ -f "$COMMON_FILE" ]; then
    source "$COMMON_FILE"
    log_debug "MySQL Sync Tool loaded with common library"
else
    # Fallback logging functions
    log_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
    log_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
    log_warning() { echo -e "\033[1;33m[WARNING]\033[0m $1"; }
    log_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }
    command_exists() { command -v "$1" >/dev/null 2>&1; }
    confirm_action() {
        local message="$1"
        local confirmation_text="${2:-CONFIRM}"
        echo -e "\033[1;33m⚠️  $message\033[0m"
        read -p "Type '$confirmation_text' to proceed: " user_input
        [ "$user_input" = "$confirmation_text" ]
    }
    create_temp_dir() { mktemp -d; }
fi

# MySQL sync main function
mysql_sync() {
    log_info "Starting MySQL Sync Tool..."
    
    # Check dependencies using common library if available
    if command_exists check_dependencies; then
        log_info "Checking MySQL dependencies..."
        if ! check_dependencies "mysql" "mysqldump"; then
            log_error "Required dependencies not available"
            return 1
        fi
    else
        # Fallback dependency check
        if ! command_exists mysql; then
            log_error "MySQL client is not installed. Please install it first."
            echo "Installation commands:"
            echo "  macOS: brew install mysql-client"
            echo "  Ubuntu/Debian: sudo apt-get install mysql-client"
            echo "  CentOS/RHEL: sudo yum install mysql"
            return 1
        fi
        
        if ! command_exists mysqldump; then
            log_error "mysqldump is not installed. Please install MySQL client tools."
            return 1
        fi
    fi
    
    echo
    echo "=== MySQL Database Synchronization ==="
    echo
    
    # Source database configuration
    echo "Source Database Configuration:"
    read -p "Host: " src_host
    read -p "Port [3306]: " src_port
    src_port=${src_port:-3306}
    read -p "Username: " src_user
    read -p "Password: " -s src_pass
    echo
    read -p "Database: " src_db
    echo
    
    # Target database configuration
    echo "Target Database Configuration:"
    read -p "Host: " dst_host
    read -p "Port [3306]: " dst_port
    dst_port=${dst_port:-3306}
    read -p "Username: " dst_user
    read -p "Password: " -s dst_pass
    echo
    read -p "Database: " dst_db
    echo
    
    # Test connections
    log_info "Testing database connections..."
    
    if ! mysql -h"$src_host" -P"$src_port" -u"$src_user" -p"$src_pass" -e "USE $src_db;" 2>/dev/null; then
        log_error "Cannot connect to source database"
        echo "Please check:"
        echo "  - Host and port are correct"
        echo "  - Username and password are valid"
        echo "  - Database exists and is accessible"
        echo "  - Network connectivity"
        return 1
    fi
    
    if ! mysql -h"$dst_host" -P"$dst_port" -u"$dst_user" -p"$dst_pass" -e "USE $dst_db;" 2>/dev/null; then
        log_error "Cannot connect to target database"
        echo "Please check:"
        echo "  - Host and port are correct"
        echo "  - Username and password are valid"
        echo "  - Database exists and is accessible"
        echo "  - User has write permissions"
        return 1
    fi
    
    log_success "Database connections verified"
    echo
    
    # Get database information
    local src_tables=$(mysql -h"$src_host" -P"$src_port" -u"$src_user" -p"$src_pass" -D"$src_db" -e "SHOW TABLES;" -s 2>/dev/null | wc -l)
    local dst_tables=$(mysql -h"$dst_host" -P"$dst_port" -u"$dst_user" -p"$dst_pass" -D"$dst_db" -e "SHOW TABLES;" -s 2>/dev/null | wc -l)
    
    # Show database information
    echo "=== Database Information ==="
    echo
    echo "Source Database:"
    echo "  Host: $src_host:$src_port"
    echo "  Database: $src_db"
    echo "  Tables: $src_tables"
    echo
    echo "Target Database:"
    echo "  Host: $dst_host:$dst_port"
    echo "  Database: $dst_db"
    echo "  Tables: $dst_tables"
    echo
    
    # Additional checks
    if [ "$src_tables" -eq 0 ]; then
        log_warning "Source database has no tables"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Synchronization cancelled"
            return 0
        fi
    fi
    
    # Warning and confirmation using common library if available
    local warning_msg="This operation will OVERWRITE all data in the target database!\nTarget database '$dst_db' on $dst_host will be completely replaced.\nCurrent data in target database will be LOST FOREVER.\nThis action cannot be undone. Please make sure you have backups if needed."
    
    if command_exists confirm_action; then
        if ! confirm_action "$warning_msg" "CONFIRM" "Type 'CONFIRM' to proceed with synchronization: "; then
            return 0
        fi
    else
        # Fallback confirmation
        echo -e "\033[0;31m⚠️  WARNING: $warning_msg\033[0m"
        echo
        read -p "Type 'CONFIRM' to proceed with synchronization: " confirm
        if [ "$confirm" != "CONFIRM" ]; then
            log_info "Synchronization cancelled by user"
            return 0
        fi
    fi
    
    # Create temporary directory for dump
    local temp_dir
    if command_exists create_temp_dir; then
        temp_dir=$(create_temp_dir)
    else
        temp_dir=$(mktemp -d)
        trap "rm -rf $temp_dir" EXIT
    fi
    
    # Perform synchronization
    log_info "Starting database synchronization..."
    
    # Create dump file
    local dump_file="$temp_dir/mysql_dump_$(date +%Y%m%d_%H%M%S).sql"
    
    log_info "Creating database dump from source..."
    if mysqldump -h"$src_host" -P"$src_port" -u"$src_user" -p"$src_pass" \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --add-drop-table \
        --create-options \
        --quick \
        --extended-insert \
        "$src_db" > "$dump_file"; then
        
        local dump_size=$(du -h "$dump_file" | cut -f1)
        log_success "Database dump created successfully (Size: $dump_size)"
    else
        log_error "Failed to create database dump"
        return 1
    fi
    
    log_info "Restoring to target database..."
    log_warning "This will drop and recreate all tables in the target database"
    
    if mysql -h"$dst_host" -P"$dst_port" -u"$dst_user" -p"$dst_pass" "$dst_db" < "$dump_file"; then
        log_success "Database synchronization completed successfully"
        
        # Verify synchronization
        local new_dst_tables=$(mysql -h"$dst_host" -P"$dst_port" -u"$dst_user" -p"$dst_pass" -D"$dst_db" -e "SHOW TABLES;" -s 2>/dev/null | wc -l)
        echo
        echo "=== Synchronization Summary ==="
        echo "  Source tables: $src_tables"
        echo "  Target tables after sync: $new_dst_tables"
        
        if [ "$src_tables" -eq "$new_dst_tables" ]; then
            log_success "Table count matches - synchronization appears successful"
        else
            log_warning "Table count mismatch - please verify the synchronization"
        fi
        
    else
        log_error "Failed to restore database"
        echo "The target database may be in an inconsistent state."
        echo "Please check the database manually and restore from backup if needed."
        return 1
    fi
}

# Run the MySQL sync tool
mysql_sync
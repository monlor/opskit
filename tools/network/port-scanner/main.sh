#!/bin/bash

# Port Scanner Tool
# Simple network port scanner with visual output

# Source shell libraries
source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
source "${OPSKIT_BASE_PATH}/common/shell/interactive.sh"
source "${OPSKIT_BASE_PATH}/common/shell/utils.sh"

# Initialize tool (TOOL_NAME and TOOL_VERSION are injected by framework)
tool_start "${TOOL_NAME:-port-scanner}"

# Default configuration
DEFAULT_HOST="localhost"
DEFAULT_PORTS="1-1000"
DEFAULT_PROTOCOL="tcp"
DEFAULT_TIMEOUT="1"
DEFAULT_THREADS="100"

# Environment variables are loaded from .env via core/env automatically

# Configuration with environment variable support
HOST="${HOST:-$DEFAULT_HOST}"
PORTS="${PORTS:-$DEFAULT_PORTS}"
PROTOCOL="${PROTOCOL:-$DEFAULT_PROTOCOL}"
TIMEOUT="${TIMEOUT:-$DEFAULT_TIMEOUT}"
THREADS="${THREADS:-$DEFAULT_THREADS}"

# Arrays for results
declare -a open_ports=()
declare -a closed_ports=()

# Helper functions
usage() {
    section "Port Scanner Usage"
    info "Usage: $0 [options]"
    info ""
    info "Options:"
    info "  -h, --host HOST      Target host (default: $DEFAULT_HOST)"
    info "  -p, --ports RANGE    Port range (default: $DEFAULT_PORTS)"
    info "  -t, --timeout SEC    Connection timeout (default: $DEFAULT_TIMEOUT)"
    info "  --help              Show this help"
    info ""
    info "Examples:"
    info "  $0 -h 192.168.1.1 -p 80,443,22"
    info "  $0 -h localhost -p 1-65535"
    info "  $0 --host example.com --ports 80,443,8080,3000"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--ports)
            PORTS="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Service mapping for common ports
get_service_name() {
    local port=$1
    case $port in
        21) echo "ftp" ;;
        22) echo "ssh" ;;
        23) echo "telnet" ;;
        25) echo "smtp" ;;
        53) echo "dns" ;;
        80) echo "http" ;;
        110) echo "pop3" ;;
        143) echo "imap" ;;
        443) echo "https" ;;
        993) echo "imaps" ;;
        995) echo "pop3s" ;;
        3306) echo "mysql" ;;
        5432) echo "postgresql" ;;
        6379) echo "redis" ;;
        27017) echo "mongodb" ;;
        *) echo "unknown" ;;
    esac
}

# Validate host
validate_host() {
    local host="$1"
    if [[ -z "$host" ]]; then
        error "Host cannot be empty"
        return 1
    fi
    
    # Try to resolve hostname
    if ! getent hosts "$host" >/dev/null 2>&1; then
        warning "Cannot resolve hostname '$host', proceeding anyway"
    fi
    
    return 0
}

# Parse port range
parse_ports() {
    local port_spec="$1"
    local -a ports=()
    
    # Split by comma
    IFS=',' read -ra PORT_RANGES <<< "$port_spec"
    
    for range in "${PORT_RANGES[@]}"; do
        if [[ "$range" =~ ^[0-9]+$ ]]; then
            # Single port
            if [[ $range -ge 1 && $range -le 65535 ]]; then
                ports+=("$range")
            else
                error "Invalid port: $range (must be 1-65535)"
                return 1
            fi
        elif [[ "$range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            # Port range
            local start="${BASH_REMATCH[1]}"
            local end="${BASH_REMATCH[2]}"
            
            if [[ $start -ge 1 && $start -le 65535 && $end -ge 1 && $end -le 65535 && $start -le $end ]]; then
                for ((port=start; port<=end; port++)); do
                    ports+=("$port")
                done
            else
                error "Invalid port range: $range"
                return 1
            fi
        else
            error "Invalid port specification: $range"
            return 1
        fi
    done
    
    # Remove duplicates and sort
    printf '%s\n' "${ports[@]}" | sort -n | uniq
}

# Test single port
test_port() {
    local host="$1"
    local port="$2"
    local timeout="$3"
    
    if timeout "$timeout" bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
        return 0  # Port is open
    else
        return 1  # Port is closed
    fi
}

# Scan ports with progress indication
scan_ports() {
    local host="$1"
    local port_list="$2"
    local -a ports_to_scan=()
    
    # Read ports from string parameter
    while IFS= read -r port; do
        [[ -n "$port" ]] && ports_to_scan+=("$port")
    done <<< "$port_list"
    
    local total=${#ports_to_scan[@]}
    local scanned=0
    local progress_step=$((total / 20))  # Show progress every 5%
    
    if [[ $progress_step -eq 0 ]]; then
        progress_step=1
    fi
    
    operation_start "Port scanning" "Scanning $host ports ${PORTS} ($PROTOCOL)"
    
    for port in "${ports_to_scan[@]}"; do
        ((scanned++))
        
        if test_port "$host" "$port" "$TIMEOUT"; then
            local service=$(get_service_name "$port")
            open_ports+=("$port:$service")
        else
            closed_ports+=("$port")
        fi
        
        # Show progress
        if [[ $((scanned % progress_step)) -eq 0 ]] || [[ $scanned -eq $total ]]; then
            local percentage=$((scanned * 100 / total))
            progress "Progress: $percentage% ($scanned/$total ports scanned)"
        fi
    done
    
    success "Scan complete: ${#open_ports[@]} open, ${#closed_ports[@]} closed"
}

# Display results in visual format
display_results() {
    local host="$1"
    
    section "Port Scan Results for $host"
    
    if [[ ${#open_ports[@]} -gt 0 ]]; then
        subsection "🟢 Open Ports Found"
        info "┌─────────┬─────────────┬─────────────────────────────────┐"
        info "│  PORT   │    STATE    │            SERVICE              │"
        info "├─────────┼─────────────┼─────────────────────────────────┤"
        
        for port_info in "${open_ports[@]}"; do
            local port="${port_info%:*}"
            local service="${port_info#*:}"
            info "$(printf "│  %-5s  │    OPEN     │  %-29s  │" "$port" "$service")"
        done
        
        info "└─────────┴─────────────┴─────────────────────────────────┘"
    else
        warning "🟡 No open ports found in the specified range"
    fi
    
    # Summary
    local total_scanned=$((${#open_ports[@]} + ${#closed_ports[@]}))
    display_info "📊 Summary" \
        "Host" "$host" \
        "Port Range" "$PORTS" \
        "Protocol" "$PROTOCOL" \
        "Total Scanned" "$total_scanned" \
        "Open Ports" "${#open_ports[@]}" \
        "Closed Ports" "${#closed_ports[@]}"
}

# Main execution
main() {
    # Validation phase
    step_start "Checking system requirements"
    if ! command -v timeout >/dev/null 2>&1; then
        error "timeout command not found. Please install coreutils."
        exit 1
    fi
    step_complete "Checking system requirements"
    
    step_start "Validating input parameters"
    if ! validate_host "$HOST"; then
        exit 1
    fi
    step_complete "Validating input parameters"
    
    # Parse and validate ports
    local port_list
    if ! port_list=$(parse_ports "$PORTS"); then
        exit 1
    fi
    
    # Scan phase
    step_start "Port scanning"
    scan_ports "$HOST" "$port_list"
    step_complete "Port scanning"
    
    # Display results
    display_results "$HOST"
}

# Run main function
main "$@"

tool_complete "${TOOL_NAME:-port-scanner}"
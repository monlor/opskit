#!/bin/bash
# OpsKit Shell Storage System
# Provides key-value storage using Python backend

# Ensure OPSKIT_BASE_PATH is set
if [[ -z "${OPSKIT_BASE_PATH:-}" ]]; then
    # Get the OpsKit root directory (common/shell -> ../..)
    OPSKIT_BASE_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    export OPSKIT_BASE_PATH
fi

# ==================== Storage Functions ====================

# Internal function to call Python storage
_python_storage() {
    local operation="$1"
    local namespace="$2"
    local key="${3:-}"
    local value="${4:-}"
    local default="${5:-}"
    
    python3 -c "
import sys
sys.path.insert(0, '${OPSKIT_BASE_PATH}/common/python')
from storage import get_storage

storage = get_storage('$namespace')

if '$operation' == 'set':
    storage.set('$key', '$value')
    print('OK')
elif '$operation' == 'get':
    result = storage.get('$key', '$default')
    print(result if result is not None else '$default')
elif '$operation' == 'exists':
    exists = storage.exists('$key')
    print('true' if exists else 'false')
elif '$operation' == 'delete':
    success = storage.delete('$key')
    print('true' if success else 'false')
elif '$operation' == 'keys':
    keys = list(storage.keys())
    for key in keys:
        print(key)
elif '$operation' == 'clear':
    count = storage.clear()
    print(count)
elif '$operation' == 'size':
    size = len(storage)
    print(size)
"
}


# Get storage handle (returns namespace for consistency)
get_storage() {
    local namespace="$1"
    echo "$namespace"
}

# Set a key-value pair
storage_set() {
    local namespace="$1"
    local key="$2"
    local value="$3"
    
    _python_storage "set" "$namespace" "$key" "$value"
}

# Get a value by key
storage_get() {
    local namespace="$1"
    local key="$2"
    local default="${3:-}"
    
    _python_storage "get" "$namespace" "$key" "" "$default"
}

# Check if a key exists
storage_exists() {
    local namespace="$1"
    local key="$2"
    
    local result
    result=$(_python_storage "exists" "$namespace" "$key")
    [[ "$result" == "true" ]]
}

# Delete a key
storage_delete() {
    local namespace="$1"
    local key="$2"
    
    local result
    result=$(_python_storage "delete" "$namespace" "$key")
    [[ "$result" == "true" ]]
}

# List all keys in a namespace
storage_keys() {
    local namespace="$1"
    
    _python_storage "keys" "$namespace"
}

# Clear all keys in a namespace
storage_clear() {
    local namespace="$1"
    
    _python_storage "clear" "$namespace"
}

# Get number of keys in a namespace
storage_size() {
    local namespace="$1"
    
    _python_storage "size" "$namespace"
}

# ==================== Convenience Functions ====================

# Store tool configuration
store_tool_config() {
    local tool_name="$1"
    local config_key="$2"
    local config_value="$3"
    
    storage_set "tool_${tool_name}" "$config_key" "$config_value"
}

# Get tool configuration
get_tool_config() {
    local tool_name="$1"
    local config_key="$2"
    local default="${3:-}"
    
    storage_get "tool_${tool_name}" "$config_key" "$default"
}

# Store execution result
store_execution_result() {
    local tool_name="$1"
    local execution_id="$2"
    local result="$3"
    
    storage_set "execution_${tool_name}" "$execution_id" "$result"
}

# Get execution result
get_execution_result() {
    local tool_name="$1"
    local execution_id="$2"
    local default="${3:-}"
    
    storage_get "execution_${tool_name}" "$execution_id" "$default"
}

# Export functions
export -f get_storage storage_set storage_get storage_exists storage_delete
export -f storage_keys storage_clear storage_size
export -f store_tool_config get_tool_config
export -f store_execution_result get_execution_result

# ==================== Help Function ====================

show_storage_help() {
    cat << EOF
${BOLD}OpsKit Shell Storage System${NC}

${BOLD}Main Functions:${NC}
  get_storage <namespace>                    - Get storage handle
  storage_set <namespace> <key> <value>     - Store key-value pair
  storage_get <namespace> <key> [default]   - Retrieve value by key
  storage_exists <namespace> <key>          - Check if key exists
  storage_delete <namespace> <key>          - Delete key
  storage_keys <namespace>                  - List keys
  storage_clear <namespace>                 - Clear all entries
  storage_size <namespace>                  - Get number of keys

${BOLD}Tool Helper Functions:${NC}
  store_tool_config <tool> <key> <value>    - Store tool configuration
  get_tool_config <tool> <key> [default]    - Get tool configuration
  store_execution_result <tool> <id> <result> - Store execution result
  get_execution_result <tool> <id> [default]  - Get execution result

${BOLD}Examples:${NC}
  # Basic usage
  storage_set "my_tool" "server_host" "localhost"
  host=\$(storage_get "my_tool" "server_host" "127.0.0.1")
  
  # Tool configuration
  store_tool_config "mysql-sync" "default_db" "production"
  db=\$(get_tool_config "mysql-sync" "default_db")

${BOLD}Notes:${NC}
  - Uses Python SQLite backend for reliability
  - All data stored in ~/.opskit/data/
EOF
}

# If running this file directly, show available functions
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    show_storage_help
fi
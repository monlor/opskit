#!/bin/bash

# OpsKit Test Script
# Automatically sets OPSKIT_BASE_PATH to current directory and runs opskit

# Get current directory as absolute path
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Export OPSKIT_BASE_PATH
export OPSKIT_BASE_PATH="$CURRENT_DIR"

echo "Setting OPSKIT_BASE_PATH to: $OPSKIT_BASE_PATH"

# Check if bin/opskit exists
if [ ! -f "$OPSKIT_BASE_PATH/bin/opskit" ]; then
    echo "Error: bin/opskit not found in $OPSKIT_BASE_PATH"
    exit 1
fi

# Make opskit executable if not already
chmod +x "$OPSKIT_BASE_PATH/bin/opskit"

echo "Running opskit..."
echo "----------------------------------------"

# Execute opskit with all passed arguments
"$OPSKIT_BASE_PATH/bin/opskit" "$@"
# Disk Usage Tool

## Description
A comprehensive disk usage analysis tool that displays disk usage information with configurable thresholds, multiple output formats, and environment-based configuration.

## Technical Architecture
- **Implementation Language**: Bash Shell Script
- **Configuration**: Environment variables only
- **System Requirements**: Standard Unix/Linux utilities (df, awk, timeout)
- **Output Formats**: Table, JSON, CSV

## Key Features
- **Environment-Based Configuration**: All settings controlled via environment variables
- **Threshold Alerts**: Configurable warning and critical thresholds with color coding
- **Multiple Output Formats**: Table (default), JSON, and CSV formats
- **Filesystem Filtering**: Option to exclude tmpfs, proc, and other system filesystems
- **Flexible Display**: Configurable human-readable sizes, filesystem types, and sorting
- **Timeout Protection**: Configurable timeout for df command execution

## Environment Variables
```bash
# Display settings
SHOW_PERCENTAGE=true
SHOW_HUMAN_READABLE=true
SHOW_FILESYSTEM_TYPE=false
SORT_BY_USAGE=true

# Threshold settings
WARNING_THRESHOLD=80
CRITICAL_THRESHOLD=95
ALERT_ON_THRESHOLD=true

# Output settings
OUTPUT_FORMAT=table
USE_COLORS=true
SHOW_HEADER=true
MAX_ENTRIES=20

# System settings
TIMEOUT=10
CHECK_INTERVAL=5
EXCLUDE_TMPFS=true
EXCLUDE_PROC=true
```

## Global Override Examples
```bash
# Use DISK_USAGE_ prefix for global overrides in data/.env
DISK_USAGE_WARNING_THRESHOLD=90
DISK_USAGE_CRITICAL_THRESHOLD=98
DISK_USAGE_OUTPUT_FORMAT=json
DISK_USAGE_USE_COLORS=false
```

## Usage Examples

### Basic Usage
```bash
# Run with default settings
opskit disk-usage

# Show help
opskit disk-usage --help
```

### Environment Variable Examples
```bash
# Run with custom thresholds
WARNING_THRESHOLD=85 CRITICAL_THRESHOLD=98 opskit disk-usage

# Output in JSON format
OUTPUT_FORMAT=json opskit disk-usage

# Disable colors and show filesystem types
USE_COLORS=false SHOW_FILESYSTEM_TYPE=true opskit disk-usage
```

## Output Examples

### Table Format (Default)
```
=== Disk Usage Analyzer v1.0.0 ===
Environment-based disk usage monitoring tool

Filesystem Usage Report
Filesystem      Size  Used Avail Use% Mounted on
/dev/disk1s1   466Gi  350Gi  113Gi  76% /
/dev/disk1s4   466Gi  3.0Gi  113Gi   3% /private/var/vm
```

### JSON Format
```json
[
  {"filesystem":"/dev/disk1s1","mount":"/","usage":76},
  {"filesystem":"/dev/disk1s4","mount":"/private/var/vm","usage":3}
]
```

### CSV Format
```csv
Filesystem,Mount,Usage%
/dev/disk1s1,/,76
/dev/disk1s4,/private/var/vm,3
```

## Color Coding
- **Green**: Usage below warning threshold
- **Yellow**: Usage above warning threshold
- **Red**: Usage above critical threshold

## Error Handling
- Timeout protection for df command execution
- Graceful handling of permission errors
- Validation of numeric thresholds
- Fallback to defaults for invalid configuration

## Development Notes
- Pure shell script implementation for maximum compatibility
- No external dependencies beyond standard Unix utilities
- Environment variable validation with sensible defaults
- Comprehensive help system with usage examples
- Follows OpsKit environment variable naming conventions
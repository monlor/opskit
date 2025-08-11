# MySQL Sync Tool

## Description
A MySQL database batch synchronization tool that provides safe, interactive database-to-database sync operations with enhanced connection caching, batch migration support, connection management, and detailed confirmation dialogs.

## Technical Architecture
- **Implementation Language**: Python 3.7+
- **Core Dependencies**: pymysql, click, colorama
- **System Requirements**: mysqldump and mysql commands in PATH
- **Database Support**: MySQL 5.7+, MariaDB 10.0+
- **Storage Backend**: SQLite via OpsKit storage system

## Key Features
- **Enhanced Connection Management**: Named connections with secure password caching and selection interface
- **Smart Connection Selection**: Cached connections displayed by most recent usage
- **Interactive Connection Management**: View, test, and delete cached connections
- **Batch Database Selection**: Single, multiple, range, or all database selection
- **Safety Features**: Same-database checks, system database filtering, explicit confirmations
- **Connection Caching**: Base64 encoded password storage with timestamp tracking in SQLite
- **Comprehensive Logging**: Console and file logging with detailed operation tracking
- **Command Support**: history, connections, help commands

## Configuration Schema
```yaml
# Connection settings
connections:
  default_timeout: 30
  max_retries: 3
  cache_passwords: true

# Batch operation settings
batch:
  confirm_destructive: true
  max_concurrent: 1
  show_progress: true

# Logging settings
logging:
  level: INFO
  file_rotation: true
  max_log_files: 10
```

## Code Structure

### Main Components
- **MySQLSyncTool Class**: Core synchronization logic and connection management
- **Connection Management**: Secure credential caching and validation
- **Batch Operations**: Multi-database selection and execution
- **Safety Checks**: System database filtering and validation
- **Logging System**: Comprehensive operation tracking

### Key Methods
- `get_connection_info()`: Enhanced interactive connection input with caching support
- `list_cached_connections()`: List all cached connections with usage details
- `select_cached_connection()`: Interactive selection from cached connections
- `manage_cached_connections()`: Complete connection management interface
- `test_connection()`: Connection testing and automatic caching
- `list_databases()`: Database discovery with system filtering
- `select_databases()`: Interactive batch database selection
- `sync_database()`: Core mysqldump -> mysql pipe execution
- `batch_sync()`: Orchestrate multi-database synchronization
- `show_help()`: Display comprehensive tool help

## Error Handling Strategy
- **Connection Errors**: Retry with exponential backoff
- **Database Errors**: Individual database failure handling
- **System Errors**: Graceful degradation with user guidance
- **Interrupt Handling**: Clean cancellation with Ctrl+C support

## Security Considerations
- **Password Storage**: Base64 encoding (not secure encryption) - suitable for development/internal use
- **Connection Validation**: Pre-operation connection testing before caching
- **System Database Protection**: Automatic filtering of system databases (mysql, information_schema, etc.)
- **Confirmation Required**: Explicit user confirmation for destructive operations
- **Cache Management**: Users can view, test, and delete cached connections
- **Connection Testing**: Test cached connections before use to detect credential changes
- **Temporary Use**: Option to use connections without caching for sensitive environments
- **Auto-Retry Logic**: Automatic retry with configurable attempts and delay for failed sync operations
- **Consistent Cache Sorting**: Cached connections sorted consistently by last used timestamp

## Testing Approach
- **Unit Tests**: Core functionality and edge cases
- **Integration Tests**: End-to-end database synchronization
- **Connection Tests**: Various MySQL/MariaDB versions
- **Error Scenarios**: Network failures, permission errors, invalid databases

## Usage Examples

### Basic Synchronization
```bash
# Interactive mode with enhanced connection caching
# 1. Shows cached connections if available
# 2. Allows selection from cache or creation of new connection
# 3. Tests connection before caching
```

### Connection Management
```bash
# View and manage cached connections
connections
> 1. prod-db (admin@db1.example.com:3306)
>    Last used: 2024-01-15 10:30:45
> 2. staging-db (user@db2.example.com:3306) 
>    Last used: 2024-01-14 15:22:10
> Options: del <number>, test <number>, clear, quit
```

### Command Line Options
```bash
# Show sync history
history

# Manage connections
connections

# Show help
help
```

### Database Selection
```bash
# Multiple database selection
Select databases: 1,3,5
# Range selection  
Select databases: 1-5
# All databases
Select databases: all
```

### Connection Workflow
```bash
1. Tool shows cached connections (sorted by most recent usage)
2. User selects cached connection or chooses "new" 
3. For new connections, user enters details
4. Connection is tested before proceeding
5. Successful connections are automatically cached (if enabled)
6. Failed connections prompt for retry or exit
```

## Development Notes
- Uses OpsKit common libraries for logging and storage
- Integrates with OpsKit configuration management
- Follows OpsKit tool development standards
- English-only code and comments as per project requirements
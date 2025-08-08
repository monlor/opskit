# MySQL Sync Tool

## Description
A MySQL database batch synchronization tool that provides safe, interactive database-to-database sync operations with connection caching, batch migration support, and detailed confirmation dialogs.

## Technical Architecture
- **Implementation Language**: Python 3.7+
- **Core Dependencies**: pymysql, click, colorama
- **System Requirements**: mysqldump and mysql commands in PATH
- **Database Support**: MySQL 5.7+, MariaDB 10.0+

## Key Features
- **Interactive Connection Management**: Named connections with secure password caching
- **Batch Database Selection**: Single, multiple, range, or all database selection
- **Safety Features**: Same-database checks, system database filtering, explicit confirmations
- **Connection Caching**: Base64 encoded password storage with timestamp tracking
- **Comprehensive Logging**: Console and file logging with detailed operation tracking

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
- `get_connection_info()`: Interactive connection input with validation
- `test_connection()`: Connection testing and caching
- `list_databases()`: Database discovery with system filtering
- `select_databases()`: Interactive batch database selection
- `sync_database()`: Core mysqldump -> mysql pipe execution
- `batch_sync()`: Orchestrate multi-database synchronization

## Error Handling Strategy
- **Connection Errors**: Retry with exponential backoff
- **Database Errors**: Individual database failure handling
- **System Errors**: Graceful degradation with user guidance
- **Interrupt Handling**: Clean cancellation with Ctrl+C support

## Security Considerations
- **Password Storage**: Base64 encoding (not secure encryption)
- **Connection Validation**: Pre-operation connection testing
- **System Database Protection**: Automatic filtering of system databases
- **Confirmation Required**: Explicit user confirmation for destructive operations

## Testing Approach
- **Unit Tests**: Core functionality and edge cases
- **Integration Tests**: End-to-end database synchronization
- **Connection Tests**: Various MySQL/MariaDB versions
- **Error Scenarios**: Network failures, permission errors, invalid databases

## Usage Examples

### Basic Synchronization
```bash
opskit mysql-sync
# Interactive mode with connection setup and database selection
```

### Batch Operations
```bash
# Multiple database selection
Select databases: 1,3,5
# Range selection  
Select databases: 1-5
# All databases
Select databases: all
```

## Development Notes
- Uses OpsKit common libraries for logging and storage
- Integrates with OpsKit configuration management
- Follows OpsKit tool development standards
- English-only code and comments as per project requirements
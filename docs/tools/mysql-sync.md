# MySQL Database Sync

MySQL database synchronization tool that supports complete database synchronization between MySQL databases, provides connection testing, and safety confirmation mechanisms.

## Feature Overview

- Supports complete synchronization between MySQL databases
- Automatic detection and installation of mysql client
- Connection testing to ensure database availability
- Detailed display of source and target database information
- Safety mechanism: displays detailed information and requires confirmation before synchronization
- Data protection: explicitly warns that the target database will be overwritten

## Usage

### Basic Syntax

```bash
opskit mysql-sync <command> [args] [flags]
```

### Available Commands

#### sync - Synchronize databases

Synchronizes the source database to the target database.

```bash
opskit mysql-sync sync <source> <target> [flags]
```

**Parameters:**
- `source` - Source database connection string (required)
- `target` - Target database connection string (required)

**Connection string format:**
```
user:password@host:port/database
```

**Flags:**
- `--dry-run, -n` - Show what will be executed without actually running
- `--force, -f` - Force synchronization without confirmation

**Examples:**
```bash
# Basic synchronization
opskit mysql-sync sync user:pass@source-host:3306/source_db user:pass@target-host:3306/target_db

# Dry run mode
opskit mysql-sync sync user:pass@source-host:3306/source_db user:pass@target-host:3306/target_db --dry-run

# Force sync (skip confirmation)
opskit mysql-sync sync user:pass@source-host:3306/source_db user:pass@target-host:3306/target_db --force
```

#### check - Test database connection

Tests whether a database connection is available.

```bash
opskit mysql-sync check <connection>
```

**Parameters:**
- `connection` - Database connection string to test (required)

**Examples:**
```bash
# Test database connection
opskit mysql-sync check user:pass@host:3306/database
```

## Features

### Synchronization Mechanism
- Uses mysqldump for data export
- Supports stored procedures and triggers
- Transaction consistency guarantee
- Automatic cleanup of temporary files

### Security Features
1. **Connection validation**: Validates source and target database connections before synchronization
2. **Information display**: Detailed display of source and target database information
3. **Confirmation mechanism**: Requires input of "CONFIRM" before dangerous operations
4. **Data protection**: Explicitly warns that target database data will be lost

### Error Handling
- Provides detailed error information when connection fails
- Errors during synchronization will rollback operations
- Automatic cleanup of temporary files, leaving no garbage files

## Dependencies

### Required Dependencies
- `mysql-client` - MySQL command line client
- `mysqldump` - Data export tool (usually installed with mysql-client)

### Automatic Installation
The tool will automatically detect dependencies and provide installation options:

**macOS (Homebrew):**
```bash
brew install mysql-client
```

**Ubuntu/Debian:**
```bash
sudo apt-get install mysql-client
```

**CentOS/RHEL:**
```bash
sudo yum install mysql
```

## Usage Examples

### Complete Synchronization Workflow

```bash
# 1. Test source database connection
opskit mysql-sync check admin:password@source-db.example.com:3306/production

# 2. Test target database connection
opskit mysql-sync check admin:password@target-db.example.com:3306/staging

# 3. Perform dry run to see what will be executed
opskit mysql-sync sync admin:password@source-db.example.com:3306/production admin:password@target-db.example.com:3306/staging --dry-run

# 4. Execute actual synchronization
opskit mysql-sync sync admin:password@source-db.example.com:3306/production admin:password@target-db.example.com:3306/staging
```

### Interactive Confirmation Process

When executing synchronization, the tool will display the following information and require confirmation:

```
=== MySQL Database Sync ===

Source Database:
  Host: source-db.example.com
  Port: 3306
  User: admin
  Database: production
  Tables: 45
  Size: 2.3GB

Target Database:
  Host: target-db.example.com
  Port: 3306
  User: admin
  Database: staging
  Tables: 45
  Size: 1.8GB

⚠️  WARNING: This operation will COMPLETELY REPLACE the target database!
⚠️  All existing data in 'staging' will be LOST!

Type 'CONFIRM' to proceed: 
```

## Troubleshooting

### Common Issues

1. **Connection failed**
   ```
   Error: Can't connect to MySQL server on 'host'
   ```
   - Check if hostname and port are correct
   - Verify network connectivity
   - Confirm firewall settings

2. **Authentication failed**
   ```
   Error: Access denied for user 'username'@'host'
   ```
   - Check username and password
   - Confirm user has appropriate permissions
   - Check MySQL user host restrictions

3. **Insufficient permissions**
   ```
   Error: Access denied; you need SELECT privileges
   ```
   - Source database user needs SELECT permissions
   - Target database user needs DROP, CREATE, INSERT permissions

4. **Insufficient disk space**
   ```
   Error: No space left on device
   ```
   - Check temporary directory disk space
   - Clean up unnecessary files
   - Use larger temporary directory

### Debug Mode

Enable debug mode to view detailed logs:

```bash
export OPSKIT_DEBUG=1
opskit mysql-sync sync source target --dry-run
```

## Best Practices

1. **Backup principle**
   - Backup target database before synchronization
   - Test synchronization process in testing environment first

2. **Permission management**
   - Use minimum privilege principle
   - Create dedicated users for synchronization operations

3. **Network optimization**
   - Execute synchronization in good network environment
   - Consider batch synchronization for large databases

4. **Monitoring and alerts**
   - Set up monitoring for synchronization operations
   - Establish alert mechanism for synchronization failures

## Security Considerations

1. **Data protection**
   - ⚠️ Synchronization operations will completely overwrite the target database
   - Ensure operations are performed on the correct target database
   - Important data must be backed up in advance

2. **Credential security**
   - Avoid passing passwords in plaintext on command line
   - Use configuration files or environment variables to store sensitive information
   - Regularly change database passwords

3. **Network security**
   - Use SSL connections to protect data transmission
   - Limit database access network range
   - Monitor abnormal database connections

## Configuration File

You can use configuration files to avoid passing sensitive information in command line:

```bash
# ~/.opskit/mysql-sync.conf
[source]
host=source-db.example.com
port=3306
user=admin
password=secret_password
database=production

[target]
host=target-db.example.com
port=3306
user=admin
password=secret_password
database=staging
```

Then use:
```bash
opskit mysql-sync sync --config ~/.opskit/mysql-sync.conf
```
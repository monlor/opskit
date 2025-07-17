# S3 Storage Sync

S3 storage synchronization tool that supports bidirectional sync between S3 buckets and local directories, provides dry-run preview and AWS credential management.

## Feature Overview

- Supports bidirectional sync between S3 buckets and local directories
- Automatic detection and installation of AWS CLI
- AWS credential configuration wizard
- Supports deletion of files that don't exist in the target
- Provides dry-run preview functionality
- Supports file exclusion patterns

## Usage

### Basic Syntax

```bash
opskit s3-sync <command> [args] [flags]
```

### Available Commands

#### upload - Upload files to S3

Upload local files or directories to S3 buckets.

```bash
opskit s3-sync upload <source> <target> [flags]
```

**Parameters:**
- `source` - Source directory or file (required)
- `target` - S3 bucket and path (s3://bucket/path) (required)

**Flags:**
- `--dry-run, -n` - Show what will be executed without actually running
- `--exclude, -e` - Exclude pattern (supports wildcards)

**Examples:**
```bash
# Upload entire directory
opskit s3-sync upload /local/backup s3://my-bucket/backup/

# Upload single file
opskit s3-sync upload /local/file.txt s3://my-bucket/files/

# Dry run mode
opskit s3-sync upload /local/backup s3://my-bucket/backup/ --dry-run

# Exclude specific files
opskit s3-sync upload /local/backup s3://my-bucket/backup/ --exclude "*.tmp"
opskit s3-sync upload /local/backup s3://my-bucket/backup/ --exclude "logs/*"
```

#### download - Download files from S3

Download files from S3 bucket to local directory.

```bash
opskit s3-sync download <source> <target> [flags]
```

**Parameters:**
- `source` - S3 bucket and path (s3://bucket/path) (required)
- `target` - Target directory (required)

**Flags:**
- `--dry-run, -n` - Show what will be executed without actually running

**Examples:**
```bash
# Download entire S3 path
opskit s3-sync download s3://my-bucket/backup/ /local/restore/

# Download single file
opskit s3-sync download s3://my-bucket/files/file.txt /local/

# Dry run mode
opskit s3-sync download s3://my-bucket/backup/ /local/restore/ --dry-run
```

## Features

### Synchronization Mechanism
- Uses AWS CLI for data transmission
- Supports incremental sync, only transfers changed files
- Automatically handles large file multipart upload
- Supports parallel transmission for improved efficiency

### Security Features
1. **Credential management**: Supports multiple AWS credential configuration methods
2. **Permission verification**: Verifies S3 bucket access permissions before upload
3. **Dry-run preview**: Preview operations before execution
4. **Confirmation mechanism**: Requires user confirmation for dangerous operations

### Advanced Features
- Supports file exclusion patterns
- Automatically creates target directories
- Displays transfer progress
- Error retry mechanism

## Dependencies

### Required Dependencies
- `aws-cli` - AWS command line tool

### Automatic Installation
The tool will automatically detect dependencies and provide installation options:

**macOS (Homebrew):**
```bash
brew install awscli
```

**Ubuntu/Debian:**
```bash
sudo apt-get install awscli
```

**CentOS/RHEL:**
```bash
sudo yum install awscli
```

## AWS Credential Configuration

### Configuration Methods

1. **AWS CLI configuration**
   ```bash
   aws configure
   ```

2. **Environment variables**
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

3. **IAM roles** (EC2 instances)
   - Attach IAM role to EC2 instance
   - Automatically obtain temporary credentials

4. **AWS credential files**
   ```bash
   # ~/.aws/credentials
   [default]
   aws_access_key_id = your_access_key
   aws_secret_access_key = your_secret_key
   
   # ~/.aws/config
   [default]
   region = us-east-1
   output = json
   ```

### Permission Requirements

**S3 bucket permissions:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket/*",
                "arn:aws:s3:::your-bucket"
            ]
        }
    ]
}
```

## Usage Examples

### Complete Upload Workflow

```bash
# 1. Verify AWS credentials
aws sts get-caller-identity

# 2. Dry run preview
opskit s3-sync upload /local/backup s3://my-bucket/backup/ --dry-run

# 3. Execute upload
opskit s3-sync upload /local/backup s3://my-bucket/backup/

# 4. Exclude specific file types
opskit s3-sync upload /local/backup s3://my-bucket/backup/ --exclude "*.log" --exclude "tmp/*"
```

### Batch File Management

```bash
# Upload multiple directories
opskit s3-sync upload /var/log s3://my-bucket/logs/
opskit s3-sync upload /var/www s3://my-bucket/web/
opskit s3-sync upload /etc s3://my-bucket/config/

# Restore from S3
opskit s3-sync download s3://my-bucket/backup/ /restore/
```

### Using Exclude Patterns

```bash
# Exclude temporary files and logs
opskit s3-sync upload /project s3://my-bucket/project/ \
  --exclude "*.tmp" \
  --exclude "*.log" \
  --exclude "node_modules/*" \
  --exclude ".git/*"

# Exclude large files
opskit s3-sync upload /media s3://my-bucket/media/ \
  --exclude "*.mov" \
  --exclude "*.avi"
```

## Troubleshooting

### Common Issues

1. **AWS credentials not configured**
   ```
   Error: Unable to locate credentials
   ```
   - Run `aws configure` to configure credentials
   - Check environment variable settings
   - Verify IAM role configuration

2. **Insufficient permissions**
   ```
   Error: Access Denied
   ```
   - Check S3 bucket permissions
   - Verify IAM policies
   - Confirm bucket exists

3. **Network connection issues**
   ```
   Error: Unable to connect to S3
   ```
   - Check network connection
   - Verify firewall settings
   - Check proxy configuration

4. **Insufficient disk space**
   ```
   Error: No space left on device
   ```
   - Clean up local disk space
   - Use incremental sync
   - Process large files in batches

### Debug Mode

Enable debug mode to view detailed logs:

```bash
export OPSKIT_DEBUG=1
opskit s3-sync upload /local/path s3://bucket/path --dry-run
```

Enable AWS CLI debugging:
```bash
export AWS_CLI_DEBUG=1
opskit s3-sync upload /local/path s3://bucket/path
```

## Best Practices

1. **Backup strategy**
   - Regularly backup important data to S3
   - Use versioning to protect data
   - Set lifecycle rules to manage storage costs

2. **Performance optimization**
   - Use parallel transmission to improve speed
   - Set appropriate chunk size
   - Execute sync in good network environment

3. **Security management**
   - Use IAM roles instead of long-term credentials
   - Regularly rotate access keys
   - Enable S3 bucket logging

4. **Cost control**
   - Use appropriate storage classes
   - Set lifecycle rules
   - Monitor data transfer costs

## Advanced Configuration

### Custom AWS CLI Configuration

```bash
# Use specific profile
export AWS_PROFILE=production
opskit s3-sync upload /data s3://prod-bucket/data/

# Use specific region
export AWS_DEFAULT_REGION=eu-west-1
opskit s3-sync upload /data s3://eu-bucket/data/
```

### Large File Handling

```bash
# Configure multipart upload threshold
aws configure set default.s3.multipart_threshold 64MB
aws configure set default.s3.multipart_chunksize 16MB

# Configure maximum concurrent requests
aws configure set default.s3.max_concurrent_requests 20
```

### Sync Script Example

```bash
#!/bin/bash
# Automated backup script

# Set variables
SOURCE_DIR="/important/data"
S3_BUCKET="s3://backup-bucket"
DATE=$(date +%Y%m%d)
BACKUP_PATH="${S3_BUCKET}/daily-backup/${DATE}"

# Execute backup
echo "Starting backup to ${BACKUP_PATH}"
opskit s3-sync upload "$SOURCE_DIR" "$BACKUP_PATH" \
  --exclude "*.tmp" \
  --exclude "logs/*"

# Verify backup
if [ $? -eq 0 ]; then
    echo "Backup completed successfully"
else
    echo "Backup failed"
    exit 1
fi
```

## Security Considerations

1. **Data encryption**
   - Enable S3 bucket encryption
   - Use SSL/TLS transmission
   - Consider client-side encryption

2. **Access control**
   - Use minimum privilege principle
   - Regularly audit IAM policies
   - Monitor access logs

3. **Compliance**
   - Understand data storage region requirements
   - Comply with data protection regulations
   - Implement data retention policies
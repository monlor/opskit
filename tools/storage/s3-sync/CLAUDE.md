# S3 Sync Tool

## Description
A comprehensive Amazon S3 synchronization tool that provides intelligent, bidirectional file synchronization between local directories and S3 buckets. Features AWS credential management, multi-profile support, intelligent conflict resolution, and batch operations with detailed progress tracking.

## Technical Architecture
- **Implementation Language**: Python 3.7+
- **Core Dependencies**: boto3, botocore, colorama, click
- **System Requirements**: AWS CLI (optional but recommended for credential management)
- **AWS Support**: All AWS regions, S3 compatible services (MinIO, DigitalOcean Spaces)
- **Authentication**: AWS credentials chain (environment, profile, IAM roles, EC2 instance profiles)

## Key Features
- **Bidirectional Sync**: Upload (local→S3), download (S3→local), and two-way synchronization
- **AWS Profile Management**: Interactive AWS profile selection and credential validation
- **Connection Information Caching**: Store and manage S3 connections like mysql-sync tool
- **Connection Management Interface**: Interactive UI for connection CRUD operations
- **S3-Compatible Services**: Support for MinIO, DigitalOcean Spaces via endpoint_url
- **Intelligent Conflict Resolution**: Size, timestamp, and ETag-based comparison
- **Batch Operations**: Process multiple files with progress tracking and parallel uploads
- **Resume Capability**: Resume interrupted transfers using multipart uploads
- **Exclusion Patterns**: Support .gitignore-style patterns for selective sync
- **Dry Run Mode**: Preview operations without making changes
- **Encryption Support**: Server-side encryption with KMS and customer keys
- **Storage Class Selection**: Intelligent storage class assignment (Standard, IA, Glacier)
- **Connection Caching**: Reuse AWS sessions and connections for performance
- **Comprehensive Logging**: Detailed operation logs with configurable verbosity

## Configuration Schema
```yaml
# AWS settings
aws:
  default_profile: default
  default_region: us-east-1
  session_cache: true
  max_retries: 3
  timeout: 300
  
# Sync settings
sync:
  default_direction: upload
  delete_removed: false
  preserve_timestamps: true
  verify_checksums: true
  parallel_uploads: 4
  multipart_threshold: 64MB
  multipart_chunksize: 8MB
  
# Storage settings
storage:
  default_storage_class: STANDARD
  lifecycle_management: true
  encryption_enabled: true
  default_encryption: AES256
  
# Performance settings
performance:
  connection_pool_size: 10
  max_bandwidth: 0  # 0 = unlimited
  retry_backoff_factor: 2
  progress_update_interval: 1.0
  
# Exclusion patterns
exclusions:
  default_patterns:
    - "*.tmp"
    - "*.log"
    - ".DS_Store"
    - "Thumbs.db"
    - ".git/"
    - "__pycache__/"
    - "node_modules/"
```

## Code Structure

### Main Components
- **S3SyncTool Class**: Core synchronization engine with OpsKit integration
- **AWSProfileManager**: AWS credential and profile management
- **SyncEngine**: Bidirectional synchronization logic and conflict resolution
- **FileComparator**: Intelligent file comparison using size, timestamp, and ETag
- **TransferManager**: Optimized file transfer with multipart uploads and resume
- **ExclusionManager**: Pattern-based file exclusion using .gitignore syntax
- **ProgressTracker**: Real-time progress tracking for batch operations
- **ConflictResolver**: Interactive conflict resolution for file differences

### Key Methods
- `check_aws_credentials()`: Validate AWS credentials and profile availability
- `select_aws_profile()`: Interactive AWS profile selection with validation
- `list_s3_objects()`: Paginated S3 object listing with metadata
- `compare_files()`: Intelligent local/S3 file comparison
- `sync_directory()`: Full directory synchronization with exclusion patterns
- `upload_file()`: Optimized file upload with multipart support
- `download_file()`: Resumable file download with integrity verification
- `resolve_conflicts()`: Interactive conflict resolution interface
- `cleanup_temp_files()`: Clean up temporary files using OPSKIT_TOOL_TEMP_DIR

## Error Handling Strategy
- **AWS Credential Errors**: Guide users through credential setup and profile configuration
- **Network Errors**: Automatic retry with exponential backoff for transient failures
- **Permission Errors**: Clear error messages with suggested IAM policy requirements
- **Storage Errors**: Handle insufficient storage space and disk access issues
- **Interrupt Handling**: Clean cancellation with progress preservation and cleanup
- **Validation Errors**: Comprehensive input validation with helpful error messages

## Security Considerations
- **Credential Management**: Use AWS credential chain, never store credentials in tool
- **Encryption Support**: Server-side encryption with KMS and customer-provided keys
- **Temporary Files**: All temporary files stored in OPSKIT_TOOL_TEMP_DIR
- **Access Control**: Validate bucket access before operations
- **Audit Trail**: Comprehensive logging of all operations for security auditing
- **Secure Transfer**: Use HTTPS for all AWS API communications

## AWS Integration

### Credential Sources (in order of precedence)
1. **Environment Variables**: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
2. **AWS Credentials File**: ~/.aws/credentials with named profiles
3. **AWS Config File**: ~/.aws/config for region and other settings
4. **IAM Instance Profile**: For EC2 instances with attached IAM roles
5. **ECS Task Roles**: For containerized applications
6. **AWS SSO**: Single sign-on integration

### IAM Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:GetObjectVersion",
        "s3:PutObjectAcl",
        "s3:GetObjectAcl"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket",
        "arn:aws:s3:::your-bucket/*"
      ]
    }
  ]
}
```

## Sync Operations

### Upload (Local → S3)
- Compare local files with S3 objects
- Upload new and modified files
- Optional deletion of S3 objects not present locally
- Preserve file metadata and timestamps
- Support for custom storage classes

### Download (S3 → Local)
- Compare S3 objects with local files
- Download new and modified objects
- Optional deletion of local files not present in S3
- Restore file timestamps from S3 metadata
- Verify file integrity using ETags

### Two-way Sync
- Bidirectional comparison and synchronization
- Intelligent conflict resolution for files modified in both locations
- User interaction for conflict resolution decisions
- Maintain sync state for incremental updates

## Testing Approach
- **Unit Tests**: Core functionality, file comparison, and AWS integration
- **Integration Tests**: End-to-end sync operations with test S3 buckets
- **Mock Tests**: AWS API interactions using moto library
- **Performance Tests**: Large file and batch operation performance
- **Error Scenarios**: Network failures, permission errors, interrupted transfers

## Usage Examples

### Interactive Mode
```bash
opskit s3-sync
# Interactive workflow:
# 1. Select AWS profile
# 2. Choose sync direction (upload/download/bidirectional)
# 3. Enter local directory path
# 4. Enter S3 bucket and prefix
# 5. Configure sync options
# 6. Review and execute
```

### Upload Directory to S3
```bash
# Upload local directory to S3 bucket
Source: /home/user/documents
Target: s3://my-bucket/documents/
Direction: Upload (local → S3)
Exclusions: *.tmp, .git/, __pycache__/
Storage Class: STANDARD_IA
Encryption: AES256

Files to upload: 152
Total size: 1.2 GB
Estimated time: 3m 45s
Proceed? (y/N): y
```

### Download S3 to Local
```bash
# Download S3 objects to local directory
Source: s3://backup-bucket/project/
Target: /home/user/restored-project/
Direction: Download (S3 → local)
Delete local files not in S3: No
Verify checksums: Yes

Objects to download: 89
Total size: 847 MB
Proceed? (y/N): y
```

### Bidirectional Sync with Conflict Resolution
```bash
# Two-way sync with conflict handling
Source: /home/user/shared
Target: s3://team-bucket/shared/
Direction: Bidirectional

Conflicts detected:
1. file1.txt - Modified in both locations
   Local:  2024-01-15 10:30:45 (1.2 KB)
   S3:     2024-01-15 11:15:20 (1.4 KB)
   Resolution: (l)ocal, (s)3, (r)ename, (s)kip? s

2. file2.txt - Modified in both locations
   Local:  2024-01-14 15:22:10 (2.1 KB)  
   S3:     2024-01-14 14:30:55 (2.0 KB)
   Resolution: (l)ocal, (s)3, (r)ename, (s)kip? l

Apply resolutions? (y/N): y
```

### Profile Management
```bash
# AWS profile selection
Available AWS profiles:
1. default (us-east-1)
2. development (us-west-2)
3. production (us-east-1)
4. personal (eu-west-1)

Select profile [1]: 2
Using profile: development (us-west-2)
Testing credentials... ✅ Valid
```

### Dry Run Mode
```bash
# Preview changes without executing
Dry run mode enabled

Would upload:
  + documents/report.pdf (2.1 MB)
  + images/logo.png (45 KB)
  + data/export.csv (892 KB)

Would download:
  - backup/old-config.json (1.2 KB)

Would delete (local):
  × temp/cache.tmp (5.3 KB)

Total: 3 uploads, 1 download, 1 deletion
Execute these changes? (y/N): n
```

## Dependency Management

### Required Dependencies
- **boto3**: AWS SDK for Python (S3 operations)
- **botocore**: Low-level AWS service access
- **colorama**: Cross-platform colored terminal output
- **click**: Command-line interface creation

### Optional Dependencies
- **awscli**: AWS CLI for advanced credential management
- **tqdm**: Enhanced progress bars (falls back to basic progress)
- **watchdog**: File system event monitoring for real-time sync

### System Requirements
- **Python**: 3.7 or higher
- **AWS CLI**: Optional but recommended for credential management
- **Network**: Internet connectivity for S3 API access
- **Disk Space**: Sufficient local storage for downloaded files

## Development Notes
- Uses OpsKit common libraries for logging and storage
- Integrates with OpsKit configuration management system
- Follows OpsKit tool development standards and patterns
- English-only code and comments as per project requirements
- All temporary files managed through OPSKIT_TOOL_TEMP_DIR
- Comprehensive error handling with user-friendly messages
- Support for both interactive and batch operation modes
- Optimized for performance with connection pooling and parallel transfers
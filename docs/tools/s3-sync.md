# S3 Storage Sync

S3存储同步工具，支持S3桶与本地目录双向同步，提供干运行预览和AWS凭证管理。

## 功能概述

- 支持S3桶与本地目录双向同步
- 自动检测和安装AWS CLI
- AWS凭证配置向导
- 支持删除目标中不存在的文件
- 提供干运行预览功能
- 支持文件排除模式

## 使用方法

### 基本语法

```bash
opskit s3-sync <command> [args] [flags]
```

### 可用命令

#### upload - 上传文件到S3

将本地文件或目录上传到S3桶。

```bash
opskit s3-sync upload <source> <target> [flags]
```

**参数:**
- `source` - 源目录或文件 (必需)
- `target` - S3桶和路径 (s3://bucket/path) (必需)

**标志:**
- `--dry-run, -n` - 显示将要执行的操作，但不实际执行
- `--exclude, -e` - 排除模式（支持通配符）

**示例:**
```bash
# 上传整个目录
opskit s3-sync upload /local/backup s3://my-bucket/backup/

# 上传单个文件
opskit s3-sync upload /local/file.txt s3://my-bucket/files/

# 干运行模式
opskit s3-sync upload /local/backup s3://my-bucket/backup/ --dry-run

# 排除特定文件
opskit s3-sync upload /local/backup s3://my-bucket/backup/ --exclude "*.tmp"
opskit s3-sync upload /local/backup s3://my-bucket/backup/ --exclude "logs/*"
```

#### download - 从S3下载文件

从S3桶下载文件到本地目录。

```bash
opskit s3-sync download <source> <target> [flags]
```

**参数:**
- `source` - S3桶和路径 (s3://bucket/path) (必需)
- `target` - 目标目录 (必需)

**标志:**
- `--dry-run, -n` - 显示将要执行的操作，但不实际执行

**示例:**
```bash
# 下载整个S3路径
opskit s3-sync download s3://my-bucket/backup/ /local/restore/

# 下载单个文件
opskit s3-sync download s3://my-bucket/files/file.txt /local/

# 干运行模式
opskit s3-sync download s3://my-bucket/backup/ /local/restore/ --dry-run
```

## 功能特点

### 同步机制
- 使用AWS CLI进行数据传输
- 支持增量同步，只传输变更的文件
- 自动处理大文件分片上传
- 支持并行传输提高效率

### 安全特性
1. **凭证管理**: 支持多种AWS凭证配置方式
2. **权限验证**: 上传前验证S3桶访问权限
3. **干运行预览**: 执行前预览将要进行的操作
4. **确认机制**: 危险操作前要求用户确认

### 高级功能
- 支持文件排除模式
- 自动创建目标目录
- 传输进度显示
- 错误重试机制

## 依赖要求

### 必需依赖
- `aws-cli` - AWS命令行工具

### 自动安装
工具会自动检测依赖并提供安装选项：

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

## AWS凭证配置

### 配置方式

1. **AWS CLI配置**
   ```bash
   aws configure
   ```

2. **环境变量**
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

3. **IAM角色** (EC2实例)
   - 为EC2实例附加IAM角色
   - 自动获取临时凭证

4. **AWS凭证文件**
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

### 权限要求

**S3桶权限:**
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

## 使用示例

### 完整上传流程

```bash
# 1. 验证AWS凭证
aws sts get-caller-identity

# 2. 干运行预览
opskit s3-sync upload /local/backup s3://my-bucket/backup/ --dry-run

# 3. 执行上传
opskit s3-sync upload /local/backup s3://my-bucket/backup/

# 4. 排除特定文件类型
opskit s3-sync upload /local/backup s3://my-bucket/backup/ --exclude "*.log" --exclude "tmp/*"
```

### 批量文件管理

```bash
# 上传多个目录
opskit s3-sync upload /var/log s3://my-bucket/logs/
opskit s3-sync upload /var/www s3://my-bucket/web/
opskit s3-sync upload /etc s3://my-bucket/config/

# 从S3恢复
opskit s3-sync download s3://my-bucket/backup/ /restore/
```

### 使用排除模式

```bash
# 排除临时文件和日志
opskit s3-sync upload /project s3://my-bucket/project/ \
  --exclude "*.tmp" \
  --exclude "*.log" \
  --exclude "node_modules/*" \
  --exclude ".git/*"

# 排除大文件
opskit s3-sync upload /media s3://my-bucket/media/ \
  --exclude "*.mov" \
  --exclude "*.avi"
```

## 故障排除

### 常见问题

1. **AWS凭证未配置**
   ```
   Error: Unable to locate credentials
   ```
   - 运行 `aws configure` 配置凭证
   - 检查环境变量设置
   - 验证IAM角色配置

2. **权限不足**
   ```
   Error: Access Denied
   ```
   - 检查S3桶权限
   - 验证IAM策略
   - 确认桶是否存在

3. **网络连接问题**
   ```
   Error: Unable to connect to S3
   ```
   - 检查网络连接
   - 验证防火墙设置
   - 检查代理配置

4. **磁盘空间不足**
   ```
   Error: No space left on device
   ```
   - 清理本地磁盘空间
   - 使用增量同步
   - 分批处理大文件

### 调试模式

启用调试模式查看详细日志：

```bash
export OPSKIT_DEBUG=1
opskit s3-sync upload /local/path s3://bucket/path --dry-run
```

启用AWS CLI调试：
```bash
export AWS_CLI_DEBUG=1
opskit s3-sync upload /local/path s3://bucket/path
```

## 最佳实践

1. **备份策略**
   - 定期备份重要数据到S3
   - 使用版本控制保护数据
   - 设置生命周期规则管理存储成本

2. **性能优化**
   - 使用并行传输提高速度
   - 合理设置分片大小
   - 在网络良好的环境执行同步

3. **安全管理**
   - 使用IAM角色而非长期凭证
   - 定期轮换访问密钥
   - 启用S3桶日志记录

4. **成本控制**
   - 使用适当的存储类别
   - 设置生命周期规则
   - 监控数据传输费用

## 高级配置

### 自定义AWS CLI配置

```bash
# 使用特定配置文件
export AWS_PROFILE=production
opskit s3-sync upload /data s3://prod-bucket/data/

# 使用特定区域
export AWS_DEFAULT_REGION=eu-west-1
opskit s3-sync upload /data s3://eu-bucket/data/
```

### 大文件处理

```bash
# 配置分片上传阈值
aws configure set default.s3.multipart_threshold 64MB
aws configure set default.s3.multipart_chunksize 16MB

# 配置最大并发数
aws configure set default.s3.max_concurrent_requests 20
```

### 同步脚本示例

```bash
#!/bin/bash
# 自动化备份脚本

# 设置变量
SOURCE_DIR="/important/data"
S3_BUCKET="s3://backup-bucket"
DATE=$(date +%Y%m%d)
BACKUP_PATH="${S3_BUCKET}/daily-backup/${DATE}"

# 执行备份
echo "Starting backup to ${BACKUP_PATH}"
opskit s3-sync upload "$SOURCE_DIR" "$BACKUP_PATH" \
  --exclude "*.tmp" \
  --exclude "logs/*"

# 验证备份
if [ $? -eq 0 ]; then
    echo "Backup completed successfully"
else
    echo "Backup failed"
    exit 1
fi
```

## 安全注意事项

1. **数据加密**
   - 启用S3桶加密
   - 使用SSL/TLS传输
   - 考虑客户端加密

2. **访问控制**
   - 使用最小权限原则
   - 定期审核IAM策略
   - 监控访问日志

3. **合规性**
   - 了解数据存储地区要求
   - 遵守数据保护法规
   - 实施数据保留政策
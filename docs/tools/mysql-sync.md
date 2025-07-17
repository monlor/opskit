# MySQL Database Sync

MySQL数据库同步工具，支持数据库间完整同步，提供连接测试和安全确认机制。

## 功能概述

- 支持MySQL数据库之间的完整同步
- 自动检测和安装mysql客户端
- 连接测试确保数据库可用性
- 详细的源库和目标库信息展示
- 安全机制：同步前显示详细信息并要求确认
- 数据保护：明确警告会覆盖目标数据库

## 使用方法

### 基本语法

```bash
opskit mysql-sync <command> [args] [flags]
```

### 可用命令

#### sync - 同步数据库

同步源数据库到目标数据库。

```bash
opskit mysql-sync sync <source> <target> [flags]
```

**参数:**
- `source` - 源数据库连接字符串 (必需)
- `target` - 目标数据库连接字符串 (必需)

**连接字符串格式:**
```
user:password@host:port/database
```

**标志:**
- `--dry-run, -n` - 显示将要执行的操作，但不实际执行
- `--force, -f` - 强制同步，无需确认

**示例:**
```bash
# 基本同步
opskit mysql-sync sync user:pass@source-host:3306/source_db user:pass@target-host:3306/target_db

# 干运行模式
opskit mysql-sync sync user:pass@source-host:3306/source_db user:pass@target-host:3306/target_db --dry-run

# 强制同步（跳过确认）
opskit mysql-sync sync user:pass@source-host:3306/source_db user:pass@target-host:3306/target_db --force
```

#### check - 测试数据库连接

测试数据库连接是否可用。

```bash
opskit mysql-sync check <connection>
```

**参数:**
- `connection` - 要测试的数据库连接字符串 (必需)

**示例:**
```bash
# 测试数据库连接
opskit mysql-sync check user:pass@host:3306/database
```

## 功能特点

### 同步机制
- 使用mysqldump进行数据导出
- 支持存储过程和触发器
- 事务一致性保证
- 临时文件自动清理

### 安全特性
1. **连接验证**: 同步前验证源库和目标库连接
2. **信息展示**: 详细显示源库和目标库信息
3. **确认机制**: 危险操作前要求输入"CONFIRM"确认
4. **数据保护**: 明确警告会覆盖目标数据库数据

### 错误处理
- 连接失败时提供详细错误信息
- 同步过程中的错误会回滚操作
- 临时文件自动清理，不留垃圾文件

## 依赖要求

### 必需依赖
- `mysql-client` - MySQL命令行客户端
- `mysqldump` - 数据导出工具（通常随mysql-client安装）

### 自动安装
工具会自动检测依赖并提供安装选项：

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

## 使用示例

### 完整同步流程

```bash
# 1. 测试源数据库连接
opskit mysql-sync check admin:password@source-db.example.com:3306/production

# 2. 测试目标数据库连接
opskit mysql-sync check admin:password@target-db.example.com:3306/staging

# 3. 执行干运行，查看将要执行的操作
opskit mysql-sync sync admin:password@source-db.example.com:3306/production admin:password@target-db.example.com:3306/staging --dry-run

# 4. 执行实际同步
opskit mysql-sync sync admin:password@source-db.example.com:3306/production admin:password@target-db.example.com:3306/staging
```

### 交互式确认流程

当执行同步时，工具会显示以下信息并要求确认：

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

## 故障排除

### 常见问题

1. **连接失败**
   ```
   Error: Can't connect to MySQL server on 'host'
   ```
   - 检查主机名和端口是否正确
   - 验证网络连接
   - 确认防火墙设置

2. **认证失败**
   ```
   Error: Access denied for user 'username'@'host'
   ```
   - 检查用户名和密码
   - 确认用户有相应权限
   - 检查MySQL用户主机限制

3. **权限不足**
   ```
   Error: Access denied; you need SELECT privileges
   ```
   - 源库用户需要SELECT权限
   - 目标库用户需要DROP、CREATE、INSERT权限

4. **磁盘空间不足**
   ```
   Error: No space left on device
   ```
   - 检查临时目录磁盘空间
   - 清理不必要的文件
   - 使用较大的临时目录

### 调试模式

启用调试模式查看详细日志：

```bash
export OPSKIT_DEBUG=1
opskit mysql-sync sync source target --dry-run
```

## 最佳实践

1. **备份原则**
   - 同步前备份目标数据库
   - 在测试环境先验证同步流程

2. **权限管理**
   - 使用最小权限原则
   - 为同步操作创建专用用户

3. **网络优化**
   - 在网络良好的环境执行同步
   - 大数据库考虑分批同步

4. **监控告警**
   - 设置同步操作监控
   - 建立同步失败告警机制

## 安全注意事项

1. **数据保护**
   - ⚠️ 同步操作会完全覆盖目标数据库
   - 确保在正确的目标数据库上执行操作
   - 重要数据务必提前备份

2. **凭证安全**
   - 避免在命令行中明文传递密码
   - 使用配置文件或环境变量存储敏感信息
   - 定期更换数据库密码

3. **网络安全**
   - 使用SSL连接保护数据传输
   - 限制数据库访问的网络范围
   - 监控异常的数据库连接

## 配置文件

可以使用配置文件避免在命令行中传递敏感信息：

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

然后使用：
```bash
opskit mysql-sync sync --config ~/.opskit/mysql-sync.conf
```
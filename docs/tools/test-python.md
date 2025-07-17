# Test Python Tool

Python工具示例，展示如何在OpsKit中集成Python脚本，支持命令行参数处理和环境变量传递。

## 功能概述

- 展示Python脚本集成到OpsKit的方法
- 支持命令行参数处理
- 环境变量传递示例
- 基本的日志输出和错误处理
- 多种操作模式展示

## 使用方法

### 基本语法

```bash
opskit test-python <command> [args] [flags]
```

### 可用命令

#### test - 运行简单测试

执行基本的测试功能，展示Python脚本的基本能力。

```bash
opskit test-python test [flags]
```

**标志:**
- `--verbose, -V` - 启用详细输出

**示例:**
```bash
# 基本测试
opskit test-python test

# 详细输出模式
opskit test-python test --verbose
```

#### process - 处理数据

处理输入数据，展示参数处理和数据操作。

```bash
opskit test-python process <input> [flags]
```

**参数:**
- `input` - 要处理的输入数据 (必需)

**标志:**
- `--dry-run, -n` - 显示将要执行的操作，但不实际执行

**示例:**
```bash
# 处理文本数据
opskit test-python process "Hello, World!"

# 处理JSON数据
opskit test-python process '{"name": "test", "value": 123}'

# 干运行模式
opskit test-python process "test data" --dry-run
```

## 功能特点

### Python集成
- 使用python3执行脚本
- 支持命令行参数解析
- 环境变量自动传递
- 标准输出和错误处理

### 示例功能
1. **基本测试**: 展示Python脚本的基本功能
2. **数据处理**: 展示参数处理和数据操作
3. **日志输出**: 展示不同级别的日志输出
4. **错误处理**: 展示错误处理机制

### 开发参考
- 命令行参数解析模式
- 环境变量读取方法
- 日志输出格式化
- 退出码处理

## 依赖要求

### 必需依赖
- `python3` - Python 3.x 解释器

### 自动安装
工具会自动检测依赖并提供安装选项：

**macOS (Homebrew):**
```bash
brew install python3
```

**Ubuntu/Debian:**
```bash
sudo apt-get install python3
```

**CentOS/RHEL:**
```bash
sudo yum install python3
```

## 代码示例

### 脚本结构
```python
#!/usr/bin/env python3
import sys
import os
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description='Test Python Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # test command
    test_parser = subparsers.add_parser('test', help='Run a simple test')
    test_parser.add_argument('--verbose', '-V', action='store_true', help='Enable verbose output')
    
    # process command
    process_parser = subparsers.add_parser('process', help='Process some data')
    process_parser.add_argument('input', help='Input data to process')
    process_parser.add_argument('--dry-run', '-n', action='store_true', help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    if args.command == 'test':
        run_test(args)
    elif args.command == 'process':
        process_data(args)
    else:
        parser.print_help()
        sys.exit(1)

def run_test(args):
    print("🐍 Python Test Tool")
    print("===================")
    
    if args.verbose:
        print("📊 Verbose mode enabled")
        print(f"📍 Working directory: {os.getcwd()}")
        print(f"🔧 Python version: {sys.version}")
        print(f"📦 Arguments: {args}")
    
    # Environment variables
    env_vars = {
        'OPSKIT_DEBUG': os.getenv('OPSKIT_DEBUG', 'false'),
        'OPSKIT_DIR': os.getenv('OPSKIT_DIR', '~/.opskit'),
        'USER': os.getenv('USER', 'unknown')
    }
    
    if args.verbose:
        print("🌍 Environment variables:")
        for key, value in env_vars.items():
            print(f"  {key}: {value}")
    
    print("✅ Test completed successfully")

def process_data(args):
    print(f"🔄 Processing input: {args.input}")
    
    if args.dry_run:
        print("🔍 Dry run mode - showing what would be done:")
        print(f"  - Input: {args.input}")
        print(f"  - Length: {len(args.input)}")
        print(f"  - Type: {type(args.input).__name__}")
        return
    
    # Try to parse as JSON
    try:
        data = json.loads(args.input)
        print(f"📋 Parsed JSON data: {data}")
        print(f"📊 Data type: {type(data).__name__}")
        if isinstance(data, dict):
            print(f"🗝️  Keys: {list(data.keys())}")
    except json.JSONDecodeError:
        print(f"📝 Processing as text: {args.input}")
        print(f"📏 Length: {len(args.input)}")
        print(f"🔤 Words: {len(args.input.split())}")
    
    print("✅ Processing completed")

if __name__ == '__main__':
    main()
```

## 使用示例

### 基本功能测试

```bash
# 简单测试
opskit test-python test

# 详细输出测试
opskit test-python test --verbose
```

**输出示例:**
```
🐍 Python Test Tool
===================
📊 Verbose mode enabled
📍 Working directory: /home/user
🔧 Python version: 3.9.7 (default, Sep 16 2021, 16:59:28)
📦 Arguments: Namespace(command='test', verbose=True)
🌍 Environment variables:
  OPSKIT_DEBUG: false
  OPSKIT_DIR: ~/.opskit
  USER: john
✅ Test completed successfully
```

### 数据处理示例

```bash
# 处理文本数据
opskit test-python process "Hello, OpsKit!"

# 处理JSON数据
opskit test-python process '{"name": "OpsKit", "version": "1.0.0", "language": "Go"}'

# 干运行模式
opskit test-python process "test data" --dry-run
```

**JSON处理输出:**
```
🔄 Processing input: {"name": "OpsKit", "version": "1.0.0", "language": "Go"}
📋 Parsed JSON data: {'name': 'OpsKit', 'version': '1.0.0', 'language': 'Go'}
📊 Data type: dict
🗝️  Keys: ['name', 'version', 'language']
✅ Processing completed
```

**文本处理输出:**
```
🔄 Processing input: Hello, OpsKit!
📝 Processing as text: Hello, OpsKit!
📏 Length: 14
🔤 Words: 2
✅ Processing completed
```

## 开发指南

### 创建Python工具

1. **创建Python脚本**
   ```python
   #!/usr/bin/env python3
   import sys
   import os
   import argparse
   
   def main():
       parser = argparse.ArgumentParser(description='Your Tool Description')
       # Add your arguments and subcommands here
       
       args = parser.parse_args()
       # Handle commands here
   
   if __name__ == '__main__':
       main()
   ```

2. **更新tools.json配置**
   ```json
   {
     "id": "your-python-tool",
     "name": "Your Python Tool",
     "description": "Tool description",
     "file": "your-tool.py",
     "type": "python",
     "dependencies": ["python3"],
     "category": "category",
     "version": "1.0.0",
     "commands": [
       {
         "name": "command1",
         "description": "Command description"
       }
     ]
   }
   ```

### 最佳实践

1. **错误处理**
   ```python
   try:
       # Your code here
       pass
   except Exception as e:
       print(f"❌ Error: {e}", file=sys.stderr)
       sys.exit(1)
   ```

2. **环境变量使用**
   ```python
   debug = os.getenv('OPSKIT_DEBUG', 'false').lower() == 'true'
   work_dir = os.getenv('OPSKIT_DIR', os.path.expanduser('~/.opskit'))
   ```

3. **日志输出**
   ```python
   def log_info(message):
       print(f"ℹ️  {message}")
   
   def log_error(message):
       print(f"❌ {message}", file=sys.stderr)
   
   def log_success(message):
       print(f"✅ {message}")
   ```

4. **参数验证**
   ```python
   def validate_args(args):
       if not args.input:
           log_error("Input is required")
           sys.exit(1)
       
       if not os.path.exists(args.file):
           log_error(f"File not found: {args.file}")
           sys.exit(1)
   ```

## 故障排除

### 常见问题

1. **Python未安装**
   ```
   Error: python3: command not found
   ```
   - 安装Python 3
   - 检查PATH环境变量

2. **权限问题**
   ```
   Error: Permission denied
   ```
   - 检查脚本执行权限
   - 使用chmod +x设置权限

3. **模块导入错误**
   ```
   Error: ModuleNotFoundError: No module named 'xxx'
   ```
   - 安装所需的Python模块
   - 使用pip install安装依赖

### 调试模式

启用调试模式查看详细信息：

```bash
export OPSKIT_DEBUG=1
opskit test-python test --verbose
```

## 扩展功能

### 添加外部依赖

```python
# requirements.txt
requests>=2.25.0
pyyaml>=5.4.0
click>=8.0.0

# 在脚本中使用
import requests
import yaml
import click
```

### 配置文件支持

```python
import configparser

def load_config():
    config = configparser.ConfigParser()
    config_file = os.path.expanduser('~/.opskit/python-tool.conf')
    
    if os.path.exists(config_file):
        config.read(config_file)
        return config
    
    return None
```

### 异步操作

```python
import asyncio
import aiohttp

async def async_operation():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.example.com') as response:
            return await response.json()

def main():
    # Run async operation
    result = asyncio.run(async_operation())
    print(f"Result: {result}")
```

## 性能优化

1. **使用适当的数据结构**
2. **避免不必要的循环**
3. **使用生成器处理大数据**
4. **合理使用缓存**
5. **异步处理I/O操作**

这个工具主要用于展示如何在OpsKit中集成Python脚本，为开发其他Python工具提供参考。
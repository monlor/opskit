# Test Python Tool

Python tool example that demonstrates how to integrate Python scripts into OpsKit, supporting command line parameter processing and environment variable passing.

## Feature Overview

- Demonstrates Python script integration into OpsKit
- Supports command line parameter processing
- Environment variable passing examples
- Basic log output and error handling
- Multiple operation modes demonstration

## Usage

### Basic Syntax

```bash
opskit test-python <command> [args] [flags]
```

### Available Commands

#### test - Run simple test

Executes basic test functionality to demonstrate Python script capabilities.

```bash
opskit test-python test [flags]
```

**Flags:**
- `--verbose, -V` - Enable verbose output

**Examples:**
```bash
# Basic test
opskit test-python test

# Verbose output mode
opskit test-python test --verbose
```

#### process - Process data

Process input data to demonstrate parameter handling and data operations.

```bash
opskit test-python process <input> [flags]
```

**Parameters:**
- `input` - Input data to process (required)

**Flags:**
- `--dry-run, -n` - Show what will be executed without actually executing

**Examples:**
```bash
# Process text data
opskit test-python process "Hello, World!"

# Process JSON data
opskit test-python process '{"name": "test", "value": 123}'

# Dry run mode
opskit test-python process "test data" --dry-run
```

## Features

### Python Integration
- Uses python3 to execute scripts
- Supports command line parameter parsing
- Automatic environment variable passing
- Standard output and error handling

### Example Functions
1. **Basic test**: Demonstrates basic Python script functionality
2. **Data processing**: Demonstrates parameter handling and data operations
3. **Log output**: Demonstrates different levels of log output
4. **Error handling**: Demonstrates error handling mechanisms

### Development Reference
- Command line parameter parsing patterns
- Environment variable reading methods
- Log output formatting
- Exit code handling

## Dependencies

### Required Dependencies
- `python3` - Python 3.x interpreter

### Automatic Installation
The tool will automatically detect dependencies and provide installation options:

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

## Code Example

### Script Structure
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

## Usage Examples

### Basic Functionality Test

```bash
# Simple test
opskit test-python test

# Verbose output test
opskit test-python test --verbose
```

**Output example:**
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

### Data Processing Examples

```bash
# Process text data
opskit test-python process "Hello, OpsKit!"

# Process JSON data
opskit test-python process '{"name": "OpsKit", "version": "1.0.0", "language": "Go"}'

# Dry run mode
opskit test-python process "test data" --dry-run
```

**JSON processing output:**
```
🔄 Processing input: {"name": "OpsKit", "version": "1.0.0", "language": "Go"}
📋 Parsed JSON data: {'name': 'OpsKit', 'version': '1.0.0', 'language': 'Go'}
📊 Data type: dict
🗝️  Keys: ['name', 'version', 'language']
✅ Processing completed
```

**Text processing output:**
```
🔄 Processing input: Hello, OpsKit!
📝 Processing as text: Hello, OpsKit!
📏 Length: 14
🔤 Words: 2
✅ Processing completed
```

## Development Guide

### Creating Python Tools

1. **Create Python script**
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

2. **Update tools.json configuration**
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

### Best Practices

1. **Error handling**
   ```python
   try:
       # Your code here
       pass
   except Exception as e:
       print(f"❌ Error: {e}", file=sys.stderr)
       sys.exit(1)
   ```

2. **Environment variable usage**
   ```python
   debug = os.getenv('OPSKIT_DEBUG', 'false').lower() == 'true'
   work_dir = os.getenv('OPSKIT_DIR', os.path.expanduser('~/.opskit'))
   ```

3. **Log output**
   ```python
   def log_info(message):
       print(f"ℹ️  {message}")
   
   def log_error(message):
       print(f"❌ {message}", file=sys.stderr)
   
   def log_success(message):
       print(f"✅ {message}")
   ```

4. **Parameter validation**
   ```python
   def validate_args(args):
       if not args.input:
           log_error("Input is required")
           sys.exit(1)
       
       if not os.path.exists(args.file):
           log_error(f"File not found: {args.file}")
           sys.exit(1)
   ```

## Troubleshooting

### Common Issues

1. **Python not installed**
   ```
   Error: python3: command not found
   ```
   - Install Python 3
   - Check PATH environment variable

2. **Permission issues**
   ```
   Error: Permission denied
   ```
   - Check script execution permissions
   - Use chmod +x to set permissions

3. **Module import errors**
   ```
   Error: ModuleNotFoundError: No module named 'xxx'
   ```
   - Install required Python modules
   - Use pip install to install dependencies

### Debug Mode

Enable debug mode to view detailed information:

```bash
export OPSKIT_DEBUG=1
opskit test-python test --verbose
```

## Extended Features

### Adding External Dependencies

```python
# requirements.txt
requests>=2.25.0
pyyaml>=5.4.0
click>=8.0.0

# Use in script
import requests
import yaml
import click
```

### Configuration File Support

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

### Asynchronous Operations

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

## Performance Optimization

1. **Use appropriate data structures**
2. **Avoid unnecessary loops**
3. **Use generators for large data**
4. **Use caching reasonably**
5. **Handle I/O operations asynchronously**

This tool is mainly used to demonstrate how to integrate Python scripts into OpsKit, providing reference for developing other Python tools.
# Python 工具开发指南

本文档提供了在 OpsKit 框架中开发 Python 工具的环境变量规范。

## 目录

1. [工具结构标准](#工具结构标准)
2. [环境变量规范](#环境变量规范)
3. [工具模板](#工具模板)

## 工具结构标准

每个 Python 工具必须遵循以下目录结构：

```
tools/category/tool-name/
├── CLAUDE.md           # 工具开发指南 (必需)
├── main.py             # 主程序文件 (必需)
├── requirements.txt    # Python 依赖 (必需)
└── .env               # 环境变量配置 (可选)
```

### 文件说明

- **CLAUDE.md**: 工具的开发指南，包含功能描述、架构说明、配置项等
- **main.py**: 主程序文件，包含工具的核心逻辑
- **requirements.txt**: 列出工具的 Python 依赖包
- **.env**: 环境变量配置文件（如果工具需要默认配置）

## 环境变量规范

### OpsKit 自动注入的环境变量

OpsKit 框架会自动为 Python 工具注入以下环境变量：

**核心环境变量（只读）**：
- `OPSKIT_BASE_PATH`: OpsKit 安装根目录
- `OPSKIT_TOOL_TEMP_DIR`: 工具专属临时目录
- `OPSKIT_WORKING_DIR`: 用户当前工作目录
- `TOOL_NAME`: 工具显示名称
- `TOOL_VERSION`: 工具版本号

**使用示例**：
```python
import os

# 获取 OpsKit 注入的环境变量
base_path = os.environ.get('OPSKIT_BASE_PATH')
temp_dir = os.environ.get('OPSKIT_TOOL_TEMP_DIR')
working_dir = os.environ.get('OPSKIT_WORKING_DIR')
tool_name = os.environ.get('TOOL_NAME')
tool_version = os.environ.get('TOOL_VERSION')
```

## 推荐的工具函数使用

### 使用 OpsKit 通用工具函数

**推荐方式** - 直接使用 `common/python/utils.py` 中的工具函数：

```python
import sys
import os

# 导入 OpsKit 通用工具函数
sys.path.insert(0, os.path.join(os.environ['OPSKIT_BASE_PATH'], 'common/python'))
from utils import run_command, get_env_var
```

**重要**: 不要使用 try/except ImportError fallback 实现，直接依赖 OpsKit utils。

### 避免复杂依赖

**不推荐** - 避免依赖已移除的复杂库：
```python
# ❌ 这些库已被移除，不要使用
from logger import get_logger  
from interactive import get_interactive
from storage import get_storage
```

**推荐** - 直接使用 print 输出：
```python
# ✅ 直接使用 print 输出，参考 mysql-sync 工具
print("🔍 正在检查依赖...")
print("✅ 操作成功完成")
print("❌ 操作失败")
print("⚠️  警告信息")
```
tool_name = os.environ.get('TOOL_NAME')
tool_version = os.environ.get('TOOL_VERSION')

# 获取工具特定配置（从 .env 文件或环境变量）
timeout = int(os.environ.get('TIMEOUT', '30'))
debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'
max_retries = int(os.environ.get('MAX_RETRIES', '3'))
```

### .env 文件格式

工具可以包含一个可选的 `.env` 文件来定义默认配置：

```bash
# .env 文件示例
TIMEOUT=30
DEBUG=false
MAX_RETRIES=3
HOST=localhost
USE_CACHE=true
```

### 环境变量读取最佳实践

```python
import os

class MyTool:
    def __init__(self):
        # 读取 OpsKit 注入的变量
        self.tool_name = os.environ.get('TOOL_NAME', 'Unknown Tool')
        self.version = os.environ.get('TOOL_VERSION', '1.0.0')
        self.temp_dir = os.environ.get('OPSKIT_TOOL_TEMP_DIR')
        self.working_dir = os.environ.get('OPSKIT_WORKING_DIR', os.getcwd())
        
        # 读取工具特定配置（支持类型转换和默认值）
        self.timeout = int(os.environ.get('TIMEOUT', '30'))
        self.max_retries = int(os.environ.get('MAX_RETRIES', '3'))
        self.debug = os.environ.get('DEBUG', 'false').lower() == 'true'
        self.use_cache = os.environ.get('USE_CACHE', 'true').lower() == 'true'
```

### 临时文件管理

使用工具专属临时目录：

```python
import os
from pathlib import Path

# 使用工具专属临时目录
temp_dir = os.environ.get('OPSKIT_TOOL_TEMP_DIR')
if temp_dir:
    temp_file_path = Path(temp_dir) / 'my_temp_file.txt'
    with open(temp_file_path, 'w') as f:
        f.write('Temporary data')
```


## 工具模板

```python
#!/usr/bin/env python3
"""
My Tool - OpsKit Version
Description of what this tool does
"""

import os
import sys
from pathlib import Path

class MyTool:
    """My tool implementation"""
    
    def __init__(self):
        # Tool metadata from OpsKit environment
        self.tool_name = os.environ.get('TOOL_NAME', 'My Tool')
        self.version = os.environ.get('TOOL_VERSION', '1.0.0')
        
        # OpsKit directories
        self.temp_dir = os.environ.get('OPSKIT_TOOL_TEMP_DIR')
        self.working_dir = os.environ.get('OPSKIT_WORKING_DIR', os.getcwd())
        
        # Tool-specific configuration from environment variables
        self.timeout = int(os.environ.get('TIMEOUT', '30'))
        self.max_retries = int(os.environ.get('MAX_RETRIES', '3'))
        self.debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    def run(self):
        """Main tool execution - implement your logic here"""
        print(f"Starting {self.tool_name} v{self.version}")
        
        # Example: Use temporary directory
        if self.temp_dir:
            print(f"Using temp directory: {self.temp_dir}")
        
        # Example: Access user's working directory
        print(f"User working directory: {self.working_dir}")
        
        # Your tool logic goes here
        print("Tool execution completed")


def main():
    """Entry point"""
    tool = MyTool()
    tool.run()


if __name__ == '__main__':
    main()
```

## 总结

### Python 工具开发要点

**OpsKit 提供的环境变量**：
- `OPSKIT_BASE_PATH`: OpsKit 框架根目录
- `OPSKIT_TOOL_TEMP_DIR`: 工具专属临时目录
- `OPSKIT_WORKING_DIR`: 用户当前工作目录
- `TOOL_NAME`: 工具显示名称
- `TOOL_VERSION`: 工具版本号

**工具开发自由度**：
- 工具可以自行决定实现哪些功能（日志、用户交互、错误处理等）
- 工具可以自行选择依赖和实现方式
- 工具可以自定义配置项和命令行参数
- OpsKit 仅提供基础的环境变量注入，不强制任何实现模式

**文件结构**：
- `CLAUDE.md`（必需）- 工具开发指南
- `main.py`（必需）- 主程序文件
- `requirements.txt`（必需）- Python 依赖列表
- `.env`（可选）- 默认配置文件
# Python 工具开发指南

本文档提供了在 OpsKit 框架中开发 Python 工具的关键规则和特定要求。

## 目录

1. [工具结构标准](#工具结构标准)
2. [OpsKit 特定规则](#opskit-特定规则)
3. [公共库集成](#公共库集成)
4. [配置管理](#配置管理)
5. [工具模板](#工具模板)

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

## OpsKit 特定规则

### ✅ 必须遵循的规则

**1. 公共库导入模式**
```python
import sys
import os
sys.path.insert(0, os.path.join(os.environ['OPSKIT_BASE_PATH'], 'common/python'))

from logger import get_logger
from storage import get_storage
from utils import run_command, timestamp, get_env_var
from interactive import get_input, confirm, select_from_list, delete_confirm
```

**2. 使用 OpsKit 组件初始化**
```python
# 初始化 OpsKit 组件
logger = get_logger(__name__)
storage = get_storage('tool-name')
```

**3. 配置管理**
```python
# 使用 get_env_var() 获取配置，不要使用 os.environ.get()
self.timeout = get_env_var('TIMEOUT', 30, int)
self.max_retries = get_env_var('MAX_RETRIES', 3, int)
```

**4. 工具类结构**
```python
class MyTool:
    def __init__(self):
        self.tool_name = "My Tool"
        self.description = "Tool description"
        # 不要定义 self.version
        
    def run(self):
        """主执行方法"""
        pass
```

### ❌ 禁止的做法

**1. 不要自动加载 .env 文件**
```python
# ❌ 错误 - 不要在工具中自动加载 .env
env_vars = load_env_file('.env')

# ✅ 正确 - 直接使用环境变量
self.timeout = get_env_var('TIMEOUT', 30, int)
```

**2. 不要定义版本号**
```python
# ❌ 错误
self.version = "2.0.0"

# ✅ 正确 - 版本由框架管理，工具不需要版本号
```

**3. 不要使用 os.environ.get()**
```python
# ❌ 错误
self.timeout = int(os.environ.get('TIMEOUT', '30'))

# ✅ 正确
self.timeout = get_env_var('TIMEOUT', 30, int)
```

**4. 不要使用相对导入**
```python
# ❌ 错误
from ..common.python.logger import get_logger

# ✅ 正确
sys.path.insert(0, os.path.join(os.environ['OPSKIT_BASE_PATH'], 'common/python'))
from logger import get_logger
```

**5. 不要使用 print() 或 console.print()**
```python
# ❌ 错误 - 不要使用 print 或第三方库的打印函数
print("Hello world")
console.print("Hello world")

# ✅ 正确 - 使用 OpsKit 的日志系统
logger.info("Hello world")
```


## 公共库集成

### 日志系统
```python
from logger import get_logger

logger = get_logger(__name__)
logger.info(f"🚀 Starting {self.tool_name}")
logger.error(f"❌ Operation failed: {error}")
```

### 数据存储
```python
from storage import get_storage

storage = get_storage('tool-name')
storage.set('connections', cached_connections)
history = storage.get('history', [])
```

### 工具函数
```python
from utils import run_command, get_env_var

# 执行系统命令
success, stdout, stderr = run_command(['mysql', '--version'])

# 获取环境变量（重要：必须使用这个函数）
timeout = get_env_var('TIMEOUT', 30, int)
max_retries = get_env_var('MAX_RETRIES', 3, int)
```

### 交互式组件
```python
from interactive import get_input, confirm, select_from_list, delete_confirm

# 获取用户输入（带验证）
name = get_input("Enter connection name", validator=lambda x: len(x.strip()) > 0)

# 获取确认
if confirm("Continue with operation?"):
    # 执行操作
    pass

# 从列表中选择
choice = select_from_list("Select option:", ["option1", "option2", "option3"])

# 删除确认
if delete_confirm("connection", "test-db"):
    # 执行删除
    pass
```

## 配置管理

### .env 文件格式
```bash
# .env 文件示例
TIMEOUT=30
MAX_RETRIES=3
SINGLE_TRANSACTION=true
CACHE_CONNECTIONS=true
```

### 环境变量读取
```python
class MyTool:
    def __init__(self):
        # 必须使用 get_env_var() 函数
        self.timeout = get_env_var('TIMEOUT', 30, int)
        self.max_retries = get_env_var('MAX_RETRIES', 3, int)
        self.cache_connections = get_env_var('CACHE_CONNECTIONS', True, bool)
        
        # 不要定义版本号
        # self.version = "2.0.0"  # ❌ 错误
```

### 临时文件目录环境变量

#### OPSKIT_TOOL_TEMP_DIR

OpsKit 为每个工具提供一个独立的临时目录，通过 `OPSKIT_TOOL_TEMP_DIR` 环境变量指定。

```python
from utils import get_env_var

# 获取工具专属临时目录
temp_dir = get_env_var('OPSKIT_TOOL_TEMP_DIR')

# 在临时目录创建文件（安全使用）
if temp_dir:
    temp_file_path = os.path.join(temp_dir, 'my_temp_file.txt')
    with open(temp_file_path, 'w') as f:
        f.write('Temporary data')
```

**重要特点**：
- 每个工具运行时都有独立的临时目录
- 目录由 OpsKit 框架自动创建和管理
- 使用 `get_env_var('OPSKIT_TOOL_TEMP_DIR')` 获取
- 不保证目录在工具运行后自动清理
- 不要存储敏感或需要长期保存的数据


## 工具模板
```python
#!/usr/bin/env python3
"""
My Tool - OpsKit Version
Description of what this tool does
"""

import os
import sys
from typing import Dict, List, Optional
from pathlib import Path

# Import OpsKit common libraries
sys.path.insert(0, os.path.join(os.environ['OPSKIT_BASE_PATH'], 'common/python'))

from logger import get_logger
from storage import get_storage
from utils import run_command, timestamp, get_env_var
from interactive import get_input, confirm, select_from_list, delete_confirm

# Third-party imports
try:
    import required_package
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please ensure all dependencies are installed.")
    sys.exit(1)

# Initialize OpsKit components
logger = get_logger(__name__)
storage = get_storage('my-tool')


class MyTool:
    """My tool with OpsKit integration"""
    
    def __init__(self):
        # Tool metadata
        self.tool_name = "My Tool"
        self.description = "Tool description"
        
        # Load configuration from environment variables
        self.timeout = get_env_var('TIMEOUT', 30, int)
        self.max_retries = get_env_var('MAX_RETRIES', 3, int)
        self.verbose = get_env_var('VERBOSE', False, bool)
        
        logger.info(f"🚀 Starting {self.tool_name}")
        logger.debug(f"Configuration - timeout: {self.timeout}s, max_retries: {self.max_retries}")
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        # 检查系统依赖
        required_commands = ['required_command']
        missing_commands = []
        
        for cmd in required_commands:
            success, _, _ = run_command([cmd, '--version'])
            if not success:
                missing_commands.append(cmd)
        
        if missing_commands:
            logger.error(f"Missing required commands: {', '.join(missing_commands)}")
            return False
        
        return True
    
    def main_operation(self):
        """Main tool operation"""
        try:
            # 主要逻辑实现
            logger.info("Performing main operation")
            # ...
            logger.info("✅ Operation completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Operation failed: {e}")
            raise
    
    def run(self):
        """Main tool execution"""
        try:
            # Check dependencies
            if not self.check_dependencies():
                sys.exit(1)
            
            # Execute main operation
            self.main_operation()
            
        except KeyboardInterrupt:
            logger.info("❌ Operation cancelled by user")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            sys.exit(1)


def main():
    """Entry point"""
    tool = MyTool()
    tool.run()


if __name__ == '__main__':
    main()
```

## 交互式组件参考

详细的交互式组件使用方法请参考：[交互式组件使用指南](interactive-components-guide.md)

该指南包含：
- Python 和 Shell 版本的完整 API 文档
- 使用示例和最佳实践
- 配置选项说明
- 组件对比表

## 工具注册

### 添加到 config/tools.yaml

开发完成后，必须将工具信息添加到 `config/tools.yaml` 文件中，包括：

**1. 工具定义**
```yaml
tools:
  category:
    tool-name:
      version: "1.0.0"
      description: "工具描述"
      keywords: [关键词, 列表]
      dependencies: [依赖列表]  # 可选，引用 dependencies.yaml
```

**2. 类别定义（如果是新类别）**
```yaml
categories:
  category:
    name: "类别名称"
    description: "类别描述"
    icon: 🛠️
```

**示例**：
```yaml
tools:
  development:
    icon-converter:
      version: "1.0.0"
      description: Convert single icon files to multiple sizes and formats for Web, iOS, Android, and Chrome extension development
      keywords: [icon, convert, resize, web, ios, android, chrome, favicon, app-icon, development]

categories:
  development:
    name: Development Tools
    description: Software development utilities, converters, and workflow automation tools
    icon: 🛠️
```

## 总结

### OpsKit Python 工具开发核心要点

**必须遵循**：
- 使用标准的公共库导入模式
- 使用 `get_env_var()` 获取配置，不要使用 `os.environ.get()`
- 使用交互式组件进行用户交互，不要自行实现输入/确认逻辑
- 不要定义工具版本号（由框架管理）
- 不要在工具中自动加载 .env 文件
- 使用 OpsKit 的日志和存储系统
- 开发完成后添加工具信息到 `config/tools.yaml`

**文件结构**：
- `CLAUDE.md`（必需）
- `main.py`（必需）
- `requirements.txt`（必需）
- `.env`（可选配置）

**注册流程**：
1. 完成工具开发和测试
2. 在 `config/tools.yaml` 中添加工具定义
3. 如果是新类别，添加类别定义
4. 测试工具在 OpsKit 框架中的集成
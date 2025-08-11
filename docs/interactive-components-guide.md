# Interactive Components Guide

OpsKit 提供了统一的交互式组件库，用于创建一致的用户界面体验。这些组件支持 Python 和 Shell 两种实现。

## 功能特性

### 核心交互功能
- 用户输入与验证
- 确认对话框
- 列表选择
- 密码输入
- 进度条显示
- 表格数据展示
- 菜单导航

### 高级功能 (Python Only)
- prompt_toolkit 增强选择
- 彩色输出支持
- 自动完成功能
- 复杂验证器

## Python 实现

### 基本使用

```python
# 导入组件
from interactive import get_input, confirm, select_from_list, delete_confirm, show_progress

# 用户输入
name = get_input("Enter your name", default="User")

# 带验证的输入
age = get_input(
    "Enter your age", 
    validator=lambda x: x.isdigit() and 0 <= int(x) <= 120,
    error_message="Age must be between 0 and 120"
)

# 密码输入
password = get_input("Enter password", password=True)

# 确认对话
if confirm("Continue operation?", default=True):
    print("Continuing...")

# 列表选择
items = ["Option A", "Option B", "Option C"]
selection = select_from_list(items, "Choose an option")
if selection is not None:
    print(f"Selected: {items[selection]}")

# 多选
selections = select_from_list(items, "Choose multiple", allow_multiple=True)
if selections:
    chosen = [items[i] for i in selections]
    print(f"Selected: {', '.join(chosen)}")

# 删除确认
if delete_confirm("important_file.txt", "file"):
    print("File would be deleted")

# 强制输入确认
if delete_confirm("database", "database", force_typing=True):
    print("Database would be destroyed")
```

### 高级用法

```python
from interactive import InteractiveComponents

interactive = InteractiveComponents()

# 高级选择 (使用 prompt_toolkit)
options = [
    {'name': 'Production Database', 'value': 'prod'},
    {'name': 'Staging Database', 'value': 'staging'},
    {'name': 'Development Database', 'value': 'dev'}
]

selected = interactive.advanced_select(options, "Select Database")
print(f"Selected: {selected}")

# 进度条
for i in range(101):
    interactive.show_progress_bar(i, 100)
    time.sleep(0.02)

# 表格显示
data = [
    {'Name': 'Alice', 'Age': 30, 'City': 'New York'},
    {'Name': 'Bob', 'Age': 25, 'City': 'San Francisco'}
]
interactive.display_table(data, title="User Data")
```

### 输入验证器

```python
# 预定义验证器
def validate_email(email):
    return "@" in email and "." in email.split("@")[1]

def validate_port(port):
    try:
        p = int(port)
        return 1 <= p <= 65535
    except ValueError:
        return False

# 使用验证器
email = get_input("Email address", validator=validate_email)
port = get_input("Port number", validator=validate_port)
```

## Shell 实现

### 基本使用

```bash
# 引入组件库
source "${OPSKIT_BASE_PATH}/common/shell/interactive.sh"

# 用户输入
name=$(get_user_input "Enter your name" "DefaultUser")

# 带验证的输入
validate_age() {
    local age="$1"
    [[ "$age" =~ ^[0-9]+$ ]] && [[ $age -ge 0 && $age -le 120 ]]
}

age=$(get_user_input "Enter your age" "" "true" "validate_age")

# 密码输入
password=$(get_password_input "Enter password")

# 确认对话
if confirm "Continue operation?" "true"; then
    echo "Continuing..."
fi

# 列表选择
options=("Option A" "Option B" "Option C")
selection=$(select_from_list "Choose an option" "${options[@]}")
if [[ $? -eq 0 ]]; then
    echo "Selected: ${options[$selection]}"
fi

# 删除确认
if delete_confirmation "important_file.txt" "file" "false"; then
    echo "File would be deleted"
fi

# 强制输入确认
if delete_confirmation "database" "database" "true"; then
    echo "Database would be destroyed"
fi
```

### 进度和显示

```bash
# 进度条
for i in {0..100}; do
    show_progress_bar $i 100 "Processing" "Complete"
    sleep 0.02
done

# 表格显示
display_table "User Data" \
    "Name|Age|City" \
    "Alice|30|New York" \
    "Bob|25|San Francisco"

# 菜单
menu_options=("View Files" "Edit Config" "Run Backup")
selection=$(show_menu "Main Menu" "${menu_options[@]}")
if [[ $? -eq 0 ]]; then
    echo "Selected: ${menu_options[$selection]}"
fi
```

### 预定义验证器

```bash
# 使用内置验证器
email=$(get_user_input "Email" "" "true" "validate_email")
ip=$(get_user_input "IP Address" "192.168.1.1" "true" "validate_ip")
port=$(get_user_input "Port" "8080" "true" "validate_port")

# 自定义验证器
validate_hostname() {
    local hostname="$1"
    [[ "$hostname" =~ ^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$ ]]
}

hostname=$(get_user_input "Hostname" "" "true" "validate_hostname")
```

## 配置选项

### 颜色支持

```python
# Python - 禁用颜色
interactive = InteractiveComponents(use_colors=False)
```

```bash
# Shell - 禁用颜色
export INTERACTIVE_USE_COLORS=false
```

### 环境变量

- `INTERACTIVE_USE_COLORS`: 启用/禁用颜色输出
- `OPSKIT_BASE_PATH`: OpsKit 根目录路径

## 最佳实践

### 用户体验
1. **提供合理的默认值** - 减少用户输入负担
2. **清晰的提示信息** - 告诉用户期望的输入格式
3. **有意义的错误消息** - 帮助用户理解问题
4. **适当的确认** - 对破坏性操作要求确认

### 输入验证
1. **客户端验证** - 在用户输入时立即验证
2. **友好的错误提示** - 解释为什么输入无效
3. **允许重试** - 给用户修正错误的机会

### 安全考虑
1. **密码隐藏** - 使用 password=True 隐藏密码输入
2. **敏感操作确认** - 删除等操作需要明确确认
3. **输入清理** - 验证和清理用户输入

## 组件对比

| 功能 | Python | Shell | 说明 |
|------|--------|-------|------|
| 基本输入 | ✅ | ✅ | 支持默认值和验证 |
| 密码输入 | ✅ | ✅ | 隐藏输入显示 |
| 确认对话 | ✅ | ✅ | 是/否确认 |
| 列表选择 | ✅ | ✅ | 单选和多选 |
| 删除确认 | ✅ | ✅ | 安全删除确认 |
| 进度条 | ✅ | ✅ | 进度可视化 |
| 表格显示 | ✅ | ✅ | 数据表格化显示 |
| prompt_toolkit | ✅ | ❌ | 增强交互体验 |
| 自动完成 | ✅ | ❌ | 输入自动完成 |
| 菜单导航 | ✅ | ✅ | 菜单式选择 |

## 示例工具

### mysql-sync 工具集成

mysql-sync 工具已经集成了这些交互式组件：

```python
# 连接信息输入
name = get_input("Connection name", validator=lambda x: len(x.strip()) > 0)
host = get_input("MySQL Host", default="localhost")  
port = get_input("Port", default="3306", validator=validate_port)
password = get_input("Password", password=True)

# 确认操作
if confirm("Save connection?", default=True):
    # 保存连接信息

# 删除确认
if delete_confirm(conn_name, "connection"):
    # 删除连接
```

## 开发指南

### 新工具集成

1. **导入组件**
```python
from interactive import get_input, confirm, select_from_list
```

2. **替换原生输入**
```python
# 替换 input() 
user_input = get_input("Enter value", default="default")

# 替换 getpass.getpass()
password = get_input("Password", password=True)
```

3. **添加验证**
```python
port = get_input("Port", validator=lambda x: x.isdigit() and 1 <= int(x) <= 65535)
```

### 自定义验证器

```python
def validate_database_name(name):
    """验证数据库名称格式"""
    import re
    return re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name) is not None

db_name = get_input("Database name", validator=validate_database_name)
```

通过使用这些统一的交互式组件，OpsKit 工具能够提供一致、用户友好的交互体验。
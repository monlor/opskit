# API 文档

本文档描述了OpsKit的内部API接口和配置格式。

## 配置文件格式

### tools.json

工具配置文件，定义了所有可用的工具和命令。

```json
{
  "version": "1.0.0",
  "tools": [
    {
      "id": "tool-id",
      "name": "Tool Display Name",
      "description": "Tool description",
      "file": "tool-script.sh",
      "type": "shell|python|go|binary",
      "dependencies": ["dep1", "dep2"],
      "category": "category-name",
      "version": "1.0.0",
      "commands": [
        {
          "name": "command-name",
          "description": "Command description",
          "args": [
            {
              "name": "arg-name",
              "description": "Argument description",
              "required": true
            }
          ],
          "flags": [
            {
              "name": "flag-name",
              "short": "f",
              "description": "Flag description",
              "type": "bool|string|int"
            }
          ]
        }
      ]
    }
  ]
}
```

### dependencies.json

依赖配置文件，定义了工具所需的依赖包。

```json
{
  "dependency-name": {
    "description": "Dependency description",
    "check": "command-to-check",
    "package": "package-name",
    "packages": {
      "brew": "homebrew-package",
      "apt": "apt-package",
      "yum": "yum-package",
      "dnf": "dnf-package"
    }
  }
}
```

## 内部API

### Config包

#### 类型定义

```go
type Config struct {
    Version string `json:"version"`
    Tools   []Tool `json:"tools"`
}

type Tool struct {
    ID           string    `json:"id"`
    Name         string    `json:"name"`
    Description  string    `json:"description"`
    File         string    `json:"file"`
    Type         string    `json:"type"`
    Dependencies []string  `json:"dependencies"`
    Category     string    `json:"category"`
    Version      string    `json:"version"`
    Commands     []Command `json:"commands"`
}

type Command struct {
    Name        string     `json:"name"`
    Description string     `json:"description"`
    Args        []Argument `json:"args"`
    Flags       []Flag     `json:"flags"`
}

type Argument struct {
    Name        string `json:"name"`
    Description string `json:"description"`
    Required    bool   `json:"required"`
}

type Flag struct {
    Name        string `json:"name"`
    Short       string `json:"short"`
    Description string `json:"description"`
    Type        string `json:"type"`
}
```

#### 方法

```go
// LoadConfig 从文件加载配置
func LoadConfig(path string) (*Config, error)

// GetTool 根据ID获取工具
func (c *Config) GetTool(id string) (*Tool, error)

// GetCommand 根据名称获取命令
func (t *Tool) GetCommand(name string) (*Command, error)
```

### Executor包

#### 接口定义

```go
type Executor interface {
    Execute(tool Tool, command string, args []string) error
}
```

#### 实现

```go
type ScriptExecutor struct {
    workDir string
    debug   bool
}

func NewScriptExecutor(workDir string, debug bool) *ScriptExecutor

func (e *ScriptExecutor) Execute(tool Tool, command string, args []string) error
```

### Dynamic包

#### 方法

```go
// GenerateCommand 生成动态命令
func GenerateCommand(tool Tool) *cobra.Command

// GenerateSubCommand 生成子命令
func GenerateSubCommand(tool Tool, command Command) *cobra.Command
```

### Dependencies包

#### 类型定义

```go
type DependencyManager struct {
    config map[string]Dependency
}

type Dependency struct {
    Description string            `json:"description"`
    Check       string            `json:"check"`
    Package     string            `json:"package"`
    Packages    map[string]string `json:"packages"`
}
```

#### 方法

```go
// NewDependencyManager 创建依赖管理器
func NewDependencyManager() *DependencyManager

// LoadDependencies 加载依赖配置
func (dm *DependencyManager) LoadDependencies(path string) error

// CheckDependencies 检查依赖
func (dm *DependencyManager) CheckDependencies(deps []string) error

// InstallDependency 安装依赖
func (dm *DependencyManager) InstallDependency(name string) error
```

## 环境变量

### 系统环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `OPSKIT_DIR` | 工作目录 | `$HOME/.opskit` |
| `OPSKIT_DEBUG` | 调试模式 | `false` |
| `OPSKIT_RELEASE` | 版本跟踪 | `main` |
| `OPSKIT_NO_AUTO_UPDATE` | 禁用自动更新 | `false` |
| `OPSKIT_UPDATE_INTERVAL` | 更新间隔(小时) | `1` |
| `GITHUB_REPO` | GitHub仓库 | `monlor/opskit` |

### 工具环境变量

工具执行时会自动传递以下环境变量：

| 变量名 | 描述 |
|--------|------|
| `OPSKIT_TOOL_ID` | 工具ID |
| `OPSKIT_TOOL_NAME` | 工具名称 |
| `OPSKIT_TOOL_VERSION` | 工具版本 |
| `OPSKIT_COMMAND` | 执行的命令 |
| `OPSKIT_WORK_DIR` | 工作目录 |
| `OPSKIT_DEBUG` | 调试模式 |

## 扩展接口

### 工具类型扩展

要添加新的工具类型，需要在executor中添加处理逻辑：

```go
func (e *ScriptExecutor) Execute(tool Tool, command string, args []string) error {
    switch tool.Type {
    case "shell":
        return e.executeShell(tool, command, args)
    case "python":
        return e.executePython(tool, command, args)
    case "go":
        return e.executeGo(tool, command, args)
    case "binary":
        return e.executeBinary(tool, command, args)
    case "your-new-type":
        return e.executeYourNewType(tool, command, args)
    default:
        return fmt.Errorf("unsupported tool type: %s", tool.Type)
    }
}
```

### 依赖管理扩展

要添加新的包管理器支持，需要在dependencies中添加处理逻辑：

```go
func (dm *DependencyManager) getPackageManager() string {
    if dm.commandExists("brew") {
        return "brew"
    }
    if dm.commandExists("apt-get") {
        return "apt"
    }
    if dm.commandExists("yum") {
        return "yum"
    }
    if dm.commandExists("dnf") {
        return "dnf"
    }
    if dm.commandExists("your-new-pm") {
        return "your-new-pm"
    }
    return ""
}
```

## 钩子系统

### 工具执行钩子

```go
type ToolHook interface {
    BeforeExecute(tool Tool, command string, args []string) error
    AfterExecute(tool Tool, command string, args []string, err error) error
}

type HookManager struct {
    hooks []ToolHook
}

func (hm *HookManager) RegisterHook(hook ToolHook)
func (hm *HookManager) ExecuteBeforeHooks(tool Tool, command string, args []string) error
func (hm *HookManager) ExecuteAfterHooks(tool Tool, command string, args []string, err error) error
```

### 使用示例

```go
type LoggingHook struct{}

func (h *LoggingHook) BeforeExecute(tool Tool, command string, args []string) error {
    log.Printf("Executing tool: %s, command: %s", tool.ID, command)
    return nil
}

func (h *LoggingHook) AfterExecute(tool Tool, command string, args []string, err error) error {
    if err != nil {
        log.Printf("Tool %s failed: %v", tool.ID, err)
    } else {
        log.Printf("Tool %s completed successfully", tool.ID)
    }
    return nil
}

// 注册钩子
hookManager.RegisterHook(&LoggingHook{})
```

## 错误处理

### 错误类型

```go
type OpsKitError struct {
    Code    int
    Message string
    Cause   error
}

func (e *OpsKitError) Error() string {
    if e.Cause != nil {
        return fmt.Sprintf("[%d] %s: %v", e.Code, e.Message, e.Cause)
    }
    return fmt.Sprintf("[%d] %s", e.Code, e.Message)
}

// 错误代码
const (
    ErrCodeConfigNotFound = 1001
    ErrCodeToolNotFound   = 1002
    ErrCodeCommandNotFound = 1003
    ErrCodeDependencyMissing = 1004
    ErrCodeExecutionFailed = 1005
)
```

### 错误处理示例

```go
func executeCommand(tool Tool, command string) error {
    if tool.ID == "" {
        return &OpsKitError{
            Code:    ErrCodeToolNotFound,
            Message: "Tool not found",
        }
    }
    
    if err := checkDependencies(tool.Dependencies); err != nil {
        return &OpsKitError{
            Code:    ErrCodeDependencyMissing,
            Message: "Missing dependencies",
            Cause:   err,
        }
    }
    
    return nil
}
```

## 插件系统

### 插件接口

```go
type Plugin interface {
    Name() string
    Version() string
    Initialize() error
    Execute(command string, args []string) error
    Cleanup() error
}

type PluginManager struct {
    plugins map[string]Plugin
}

func (pm *PluginManager) RegisterPlugin(plugin Plugin) error
func (pm *PluginManager) GetPlugin(name string) (Plugin, error)
func (pm *PluginManager) ExecutePlugin(name string, command string, args []string) error
```

### 插件示例

```go
type MyPlugin struct{}

func (p *MyPlugin) Name() string {
    return "my-plugin"
}

func (p *MyPlugin) Version() string {
    return "1.0.0"
}

func (p *MyPlugin) Initialize() error {
    // 初始化逻辑
    return nil
}

func (p *MyPlugin) Execute(command string, args []string) error {
    // 执行逻辑
    return nil
}

func (p *MyPlugin) Cleanup() error {
    // 清理逻辑
    return nil
}
```

## 事件系统

### 事件类型

```go
type Event struct {
    Type      string
    Timestamp time.Time
    Data      interface{}
}

type EventHandler interface {
    HandleEvent(event Event) error
}

type EventManager struct {
    handlers map[string][]EventHandler
}

func (em *EventManager) RegisterHandler(eventType string, handler EventHandler)
func (em *EventManager) EmitEvent(event Event) error
```

### 事件使用

```go
// 注册事件处理器
eventManager.RegisterHandler("tool.started", &ToolStartedHandler{})
eventManager.RegisterHandler("tool.completed", &ToolCompletedHandler{})

// 发送事件
eventManager.EmitEvent(Event{
    Type:      "tool.started",
    Timestamp: time.Now(),
    Data:      tool,
})
```

## 配置验证

### 验证规则

```go
type ConfigValidator struct {
    rules []ValidationRule
}

type ValidationRule interface {
    Validate(config *Config) error
}

type ToolIDUniqueRule struct{}

func (r *ToolIDUniqueRule) Validate(config *Config) error {
    seen := make(map[string]bool)
    for _, tool := range config.Tools {
        if seen[tool.ID] {
            return fmt.Errorf("duplicate tool ID: %s", tool.ID)
        }
        seen[tool.ID] = true
    }
    return nil
}
```

### 验证使用

```go
validator := &ConfigValidator{
    rules: []ValidationRule{
        &ToolIDUniqueRule{},
        &RequiredFieldsRule{},
        &DependencyExistsRule{},
    },
}

if err := validator.Validate(config); err != nil {
    return fmt.Errorf("config validation failed: %v", err)
}
```

## 性能监控

### 指标收集

```go
type Metrics struct {
    ToolExecutions map[string]int
    ExecutionTime  map[string]time.Duration
    Errors         map[string]int
}

type MetricsCollector struct {
    metrics *Metrics
    mutex   sync.RWMutex
}

func (mc *MetricsCollector) RecordExecution(toolID string, duration time.Duration, err error)
func (mc *MetricsCollector) GetMetrics() *Metrics
```

### 监控使用

```go
collector := &MetricsCollector{
    metrics: &Metrics{
        ToolExecutions: make(map[string]int),
        ExecutionTime:  make(map[string]time.Duration),
        Errors:         make(map[string]int),
    },
}

// 记录执行
start := time.Now()
err := executor.Execute(tool, command, args)
collector.RecordExecution(tool.ID, time.Since(start), err)
```

这些API接口为OpsKit提供了强大的扩展能力，允许开发者根据需要添加新功能和集成第三方系统。
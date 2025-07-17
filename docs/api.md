# API Documentation

This document describes the internal API interfaces and configuration formats of OpsKit.

## Configuration File Formats

### tools.json

Tool configuration file that defines all available tools and commands.

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

Dependency configuration file that defines required packages for tools.

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

## Internal APIs

### Config Package

#### Type Definitions

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

#### Methods

```go
// LoadConfig loads configuration from file
func LoadConfig(path string) (*Config, error)

// GetTool gets tool by ID
func (c *Config) GetTool(id string) (*Tool, error)

// GetCommand gets command by name
func (t *Tool) GetCommand(name string) (*Command, error)
```

### Executor Package

#### Interface Definition

```go
type Executor interface {
    Execute(tool Tool, command string, args []string) error
}
```

#### Implementation

```go
type ScriptExecutor struct {
    workDir string
    debug   bool
}

func NewScriptExecutor(workDir string, debug bool) *ScriptExecutor

func (e *ScriptExecutor) Execute(tool Tool, command string, args []string) error
```

### Dynamic Package

#### Methods

```go
// GenerateCommand generates dynamic command
func GenerateCommand(tool Tool) *cobra.Command

// GenerateSubCommand generates subcommand
func GenerateSubCommand(tool Tool, command Command) *cobra.Command
```

### Dependencies Package

#### Type Definitions

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

#### Methods

```go
// NewDependencyManager creates dependency manager
func NewDependencyManager() *DependencyManager

// LoadDependencies loads dependency configuration
func (dm *DependencyManager) LoadDependencies(path string) error

// CheckDependencies checks dependencies
func (dm *DependencyManager) CheckDependencies(deps []string) error

// InstallDependency installs dependency
func (dm *DependencyManager) InstallDependency(name string) error
```

## Environment Variables

### System Environment Variables

| Variable Name | Description | Default Value |
|---------------|-------------|---------------|
| `OPSKIT_DIR` | Working directory | `$HOME/.opskit` |
| `OPSKIT_DEBUG` | Debug mode | `false` |
| `OPSKIT_RELEASE` | Version tracking | `main` |
| `OPSKIT_NO_AUTO_UPDATE` | Disable auto-update | `false` |
| `OPSKIT_UPDATE_INTERVAL` | Update interval (hours) | `1` |
| `GITHUB_REPO` | GitHub repository | `monlor/opskit` |

### Tool Environment Variables

The following environment variables are automatically passed to tool execution:

| Variable Name | Description |
|---------------|-------------|
| `OPSKIT_TOOL_ID` | Tool ID |
| `OPSKIT_TOOL_NAME` | Tool name |
| `OPSKIT_TOOL_VERSION` | Tool version |
| `OPSKIT_COMMAND` | Executed command |
| `OPSKIT_WORK_DIR` | Working directory |
| `OPSKIT_DEBUG` | Debug mode |

## Extension Interfaces

### Tool Type Extension

To add new tool types, add processing logic in the executor:

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

### Dependency Management Extension

To add new package manager support, add processing logic in dependencies:

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

## Hook System

### Tool Execution Hooks

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

### Usage Example

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

// Register hook
hookManager.RegisterHook(&LoggingHook{})
```

## Event System

### Event Types

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

### Event Usage

```go
// Register event handlers
eventManager.RegisterHandler("tool.started", &ToolStartedHandler{})
eventManager.RegisterHandler("tool.completed", &ToolCompletedHandler{})

// Send events
eventManager.EmitEvent(Event{
    Type:      "tool.started",
    Timestamp: time.Now(),
    Data:      tool,
})
```

## Configuration Validation

### Validation Rules

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

### Validation Usage

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

## Performance Monitoring

### Metrics Collection

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

### Monitoring Usage

```go
collector := &MetricsCollector{
    metrics: &Metrics{
        ToolExecutions: make(map[string]int),
        ExecutionTime:  make(map[string]time.Duration),
        Errors:         make(map[string]int),
    },
}

// Record execution
start := time.Now()
err := executor.Execute(tool, command, args)
collector.RecordExecution(tool.ID, time.Since(start), err)
```

These API interfaces provide powerful extensibility for OpsKit, allowing developers to add new features and integrate third-party systems as needed.
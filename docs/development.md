# Development Guide

This guide provides detailed instructions for developing new tools for OpsKit and contributing code.

## Development Environment Setup

### System Requirements
- **Go**: 1.21 or higher
- **Git**: Version control
- **Make**: Build tool (optional)

### Environment Preparation

#### 1. Clone Repository
```bash
git clone https://github.com/monlor/opskit.git
cd opskit
```

#### 2. Install Dependencies
```bash
go mod download
```

#### 3. Build Project
```bash
./build.sh
```

#### 4. Run Tests
```bash
go test ./... -v
```

## Project Structure

```
opskit/
├── cmd/                    # CLI command definitions
│   ├── list.go            # List tools command
│   ├── root.go            # Root command and dynamic command loading
│   └── run.go             # Run tool command
├── internal/               # Internal packages
│   ├── config/            # Configuration management
│   │   ├── config.go      # Configuration loading and parsing
│   │   └── config_test.go # Configuration tests
│   ├── dependencies/      # Dependency management
│   │   └── manager.go     # Dependency checking and installation
│   ├── downloader/        # File downloader
│   │   └── downloader.go  # Remote file download
│   ├── dynamic/           # Dynamic command generation
│   │   ├── command.go     # Dynamic command generation
│   │   └── command_test.go# Dynamic command tests
│   ├── executor/          # Tool executor
│   │   ├── executor.go    # Tool execution logic
│   │   └── executor_test.go# Executor tests
│   └── logger/            # Logging system
│       └── logger.go      # Log output
├── tools/                 # Tool scripts and configurations
│   ├── tools.json         # Tool configuration
│   ├── dependencies.json  # Dependency configuration
│   ├── mysql-sync.sh      # MySQL sync tool
│   ├── s3-sync.sh         # S3 sync tool
│   └── test-python.py     # Python test tool
├── docs/                  # Documentation
│   ├── installation.md    # Installation guide
│   ├── development.md     # Development guide
│   └── tools/             # Tool documentation
├── build.sh               # Build script
├── install.sh             # Installation script
├── main.go                # Main entry
└── README.md              # Project description
```

## Core Components

### 1. Configuration Management (internal/config)

Responsible for loading and parsing tool configuration files:

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
```

### 2. Tool Executor (internal/executor)

Responsible for executing different types of tool scripts:

```go
type Executor interface {
    Execute(tool Tool, command string, args []string) error
}

type ScriptExecutor struct {
    workDir string
    debug   bool
}

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
    default:
        return fmt.Errorf("unsupported tool type: %s", tool.Type)
    }
}
```

### 3. Dynamic Command Generation (internal/dynamic)

Generates Cobra commands based on configuration files:

```go
func GenerateCommand(tool Tool) *cobra.Command {
    cmd := &cobra.Command{
        Use:   tool.ID,
        Short: tool.Description,
        Long:  tool.Description,
    }
    
    for _, command := range tool.Commands {
        subCmd := generateSubCommand(tool, command)
        cmd.AddCommand(subCmd)
    }
    
    return cmd
}
```

### 4. Dependency Management (internal/dependencies)

Automatically checks and installs tool dependencies:

```go
type DependencyManager struct {
    config map[string]Dependency
}

type Dependency struct {
    Package     string            `json:"package"`
    Packages    map[string]string `json:"packages"`
    Description string            `json:"description"`
    Check       string            `json:"check"`
}

func (dm *DependencyManager) CheckDependencies(deps []string) error {
    for _, dep := range deps {
        if !dm.isInstalled(dep) {
            return dm.installDependency(dep)
        }
    }
    return nil
}
```

## Adding New Tools

### Step 1: Create Tool Script

Create tool scripts in the `tools/` directory:

```bash
# Create Shell tool
cat > tools/my-tool.sh << 'EOF'
#!/bin/bash
set -euo pipefail

# Tool script handles parameters itself
command=$1
shift

case "$command" in
    "deploy")
        echo "Deploying with args: $@"
        # Implement deployment logic
        ;;
    "status")
        echo "Checking status with args: $@"
        # Implement status checking logic
        ;;
    *)
        echo "Unknown command: $command"
        exit 1
        ;;
esac
EOF

chmod +x tools/my-tool.sh
```

```python
# Create Python tool
cat > tools/my-python-tool.py << 'EOF'
#!/usr/bin/env python3
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='My Python Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze data')
    analyze_parser.add_argument('file', help='File to analyze')
    
    # report command
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.add_argument('--format', choices=['json', 'yaml'], default='json')
    
    args = parser.parse_args()
    
    if args.command == 'analyze':
        print(f"Analyzing file: {args.file}")
    elif args.command == 'report':
        print(f"Generating report in {args.format} format")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
EOF

chmod +x tools/my-python-tool.py
```

### Step 2: Update Tool Configuration

Edit `tools/tools.json` to add new tools:

```json
{
  "version": "1.0.0",
  "tools": [
    {
      "id": "my-tool",
      "name": "My Deployment Tool",
      "description": "A tool for deployment and status checking",
      "file": "my-tool.sh",
      "type": "shell",
      "dependencies": ["docker", "kubectl"],
      "category": "deployment",
      "version": "1.0.0",
      "commands": [
        {
          "name": "deploy",
          "description": "Deploy application",
          "args": [
            {
              "name": "app",
              "description": "Application name",
              "required": true
            },
            {
              "name": "environment",
              "description": "Target environment",
              "required": true
            }
          ],
          "flags": [
            {
              "name": "dry-run",
              "short": "n",
              "description": "Show what would be done without executing",
              "type": "bool"
            }
          ]
        },
        {
          "name": "status",
          "description": "Check deployment status",
          "args": [
            {
              "name": "app",
              "description": "Application name",
              "required": true
            }
          ]
        }
      ]
    }
  ]
}
```

### Step 3: Add Dependency Configuration

Edit `tools/dependencies.json` to add new dependencies:

```json
{
  "docker": {
    "description": "Docker container runtime",
    "check": "docker --version",
    "packages": {
      "brew": "docker",
      "apt": "docker.io",
      "yum": "docker"
    }
  },
  "kubectl": {
    "description": "Kubernetes command-line tool",
    "check": "kubectl version --client",
    "packages": {
      "brew": "kubectl",
      "apt": "kubectl",
      "yum": "kubernetes-client"
    }
  }
}
```

### Step 4: Create Tool Documentation

Create tool documentation in the `docs/tools/` directory:

```markdown
# My Deployment Tool

Deployment tool that supports application deployment and status checking.

## Usage

### Deploy Application
```bash
opskit my-tool deploy myapp production
opskit my-tool deploy myapp staging --dry-run
```

### Check Status
```bash
opskit my-tool status myapp
```

## Features
- Support for multi-environment deployment
- Dry-run mode available
- Automatic status checking

## Dependencies
- Docker
- Kubectl
```

### Step 5: Test Tool

```bash
# Build project
./build.sh

# Test tool list
./opskit list

# Test new tool
./opskit my-tool --help
./opskit my-tool deploy --help
```

## Tool Type Support

### Shell Script (type: "shell")

```bash
#!/bin/bash
set -euo pipefail

command=$1
shift

case "$command" in
    "action1")
        echo "Execute action 1: $@"
        ;;
    "action2")
        echo "Execute action 2: $@"
        ;;
    *)
        echo "Unknown command: $command"
        exit 1
        ;;
esac
```

### Python Script (type: "python")

```python
#!/usr/bin/env python3
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Python Tool')
    subparsers = parser.add_subparsers(dest='command')
    
    # Define subcommands
    action1_parser = subparsers.add_parser('action1')
    action1_parser.add_argument('param1', help='Parameter 1')
    
    action2_parser = subparsers.add_parser('action2')
    action2_parser.add_argument('--flag', action='store_true')
    
    args = parser.parse_args()
    
    if args.command == 'action1':
        print(f"Execute action 1: {args.param1}")
    elif args.command == 'action2':
        print(f"Execute action 2: flag={args.flag}")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### Go Program (type: "go")

```go
package main

import (
    "fmt"
    "os"
)

func main() {
    if len(os.Args) < 2 {
        fmt.Println("Usage: program <command> [args...]")
        os.Exit(1)
    }
    
    command := os.Args[1]
    args := os.Args[2:]
    
    switch command {
    case "action1":
        fmt.Printf("Execute action 1: %v\n", args)
    case "action2":
        fmt.Printf("Execute action 2: %v\n", args)
    default:
        fmt.Printf("Unknown command: %s\n", command)
        os.Exit(1)
    }
}
```

### Binary File (type: "binary")

Direct execution of precompiled binary files without script wrapping.

## Testing

### Unit Tests

```bash
# Run all tests
go test ./... -v

# Run specific package tests
go test ./internal/config -v
go test ./internal/executor -v
go test ./internal/dynamic -v

# Run coverage tests
go test ./... -cover
```

### Integration Tests

```bash
# Build project
./build.sh

# Test basic functionality
./opskit --help
./opskit list
./opskit --version-info

# Test tool execution
./opskit test-python test --verbose
```

### Writing Test Cases

```go
func TestToolExecution(t *testing.T) {
    tool := Tool{
        ID:   "test-tool",
        Type: "shell",
        File: "test-tool.sh",
    }
    
    executor := NewScriptExecutor("/tmp", false)
    err := executor.Execute(tool, "test", []string{"arg1", "arg2"})
    
    if err != nil {
        t.Errorf("Expected no error, got %v", err)
    }
}
```

## Build and Release

### Local Build

```bash
# Build current platform
./build.sh

# Build all platforms
./build.sh --all

# Build specific platform
GOOS=linux GOARCH=amd64 go build -o opskit-linux-amd64
GOOS=darwin GOARCH=amd64 go build -o opskit-darwin-amd64
GOOS=windows GOARCH=amd64 go build -o opskit-windows-amd64.exe
```

### Version Release

```bash
# Create version tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# GitHub Actions will automatically build and release
```

## Debugging

### Enable Debug Mode

```bash
# Environment variable
export OPSKIT_DEBUG=1

# Command line flag
./opskit --debug list
```

### Add Debug Logs

```go
import "github.com/monlor/opskit/internal/logger"

func myFunction() {
    logger.Debug("Debug message")
    logger.Info("Info message")
    logger.Warning("Warning message")
    logger.Error("Error message")
}
```

## Contribution Guidelines

### Code Style

1. **Go Code Style**
   - Use `go fmt` to format code
   - Use `go vet` to check code
   - Follow Go official coding standards

2. **Shell Script Style**
   - Use `#!/bin/bash` as shebang
   - Set `set -euo pipefail`
   - Use double quotes for variables

3. **Python Script Style**
   - Use `#!/usr/bin/env python3`
   - Follow PEP 8 standards
   - Use type hints

### Commit Standards

```bash
# Commit format
git commit -m "type(scope): description"

# Type descriptions
feat:     New feature
fix:      Bug fix
docs:     Documentation update
style:    Code formatting
refactor: Code refactoring
test:     Testing related
chore:    Build process or auxiliary tool changes

# Examples
git commit -m "feat(tools): add deployment tool"
git commit -m "fix(executor): handle python script errors"
git commit -m "docs(readme): update installation instructions"
```

### Pull Request Process

1. **Fork repository**
2. **Create feature branch**
   ```bash
   git checkout -b feature/new-tool
   ```
3. **Develop and test**
4. **Commit code**
5. **Create Pull Request**
6. **Code review**
7. **Merge code**

## Best Practices

### Tool Development

1. **Error Handling**
   - Use appropriate exit codes
   - Provide useful error messages
   - Gracefully handle interrupt signals

2. **User Experience**
   - Provide clear help information
   - Support dry-run mode
   - Show operation progress

3. **Security**
   - Validate input parameters
   - Use secure temporary files
   - Avoid code injection

### Performance Optimization

1. **Resource Management**
   - Release resources promptly
   - Use connection pools
   - Avoid memory leaks

2. **Concurrent Processing**
   - Use goroutines for concurrency
   - Use channels appropriately
   - Avoid race conditions

## Release Cycle

### Version Strategy

- **Major version** (v1.0.0): Major feature updates or breaking changes
- **Minor version** (v1.1.0): New feature additions
- **Patch version** (v1.1.1): Bug fixes

### Release Process

1. **Feature development and testing**
2. **Update documentation**
3. **Create release candidate**
4. **Test and validate**
5. **Create official release**
6. **Publish to GitHub Releases**

## Community

### Getting Help

- 📖 [Documentation](https://github.com/monlor/opskit/wiki)
- 💬 [Discussions](https://github.com/monlor/opskit/discussions)
- 🐛 [Issue Reports](https://github.com/monlor/opskit/issues)

### Contribution Methods

- Report bugs
- Propose feature suggestions
- Contribute code
- Improve documentation
- Share usage experience

Welcome to the OpsKit community, let's build better operational tools together!
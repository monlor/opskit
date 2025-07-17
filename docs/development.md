# 开发指南

本指南详细介绍了如何为OpsKit开发新工具和贡献代码。

## 开发环境设置

### 系统要求
- **Go**: 1.21 或更高版本
- **Git**: 版本控制
- **Make**: 构建工具（可选）

### 环境准备

#### 1. 克隆仓库
```bash
git clone https://github.com/monlor/opskit.git
cd opskit
```

#### 2. 安装依赖
```bash
go mod download
```

#### 3. 构建项目
```bash
./build.sh
```

#### 4. 运行测试
```bash
go test ./... -v
```

## 项目结构

```
opskit/
├── cmd/                    # CLI命令定义
│   ├── list.go            # 列出工具命令
│   ├── root.go            # 根命令和动态命令加载
│   └── run.go             # 运行工具命令
├── internal/               # 内部包
│   ├── config/            # 配置管理
│   │   ├── config.go      # 配置加载和解析
│   │   └── config_test.go # 配置测试
│   ├── dependencies/      # 依赖管理
│   │   └── manager.go     # 依赖检查和安装
│   ├── downloader/        # 文件下载器
│   │   └── downloader.go  # 远程文件下载
│   ├── dynamic/           # 动态命令生成
│   │   ├── command.go     # 动态命令生成
│   │   └── command_test.go# 动态命令测试
│   ├── executor/          # 工具执行器
│   │   ├── executor.go    # 工具执行逻辑
│   │   └── executor_test.go# 执行器测试
│   └── logger/            # 日志系统
│       └── logger.go      # 日志输出
├── tools/                 # 工具脚本和配置
│   ├── tools.json         # 工具配置
│   ├── dependencies.json  # 依赖配置
│   ├── mysql-sync.sh      # MySQL同步工具
│   ├── s3-sync.sh         # S3同步工具
│   └── test-python.py     # Python测试工具
├── docs/                  # 文档
│   ├── installation.md    # 安装指南
│   ├── development.md     # 开发指南
│   └── tools/             # 工具文档
├── build.sh               # 构建脚本
├── install.sh             # 安装脚本
├── main.go                # 主入口
└── README.md              # 项目说明
```

## 核心组件

### 1. 配置管理 (internal/config)

负责加载和解析工具配置文件：

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

### 2. 工具执行器 (internal/executor)

负责执行不同类型的工具脚本：

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

### 3. 动态命令生成 (internal/dynamic)

基于配置文件动态生成Cobra命令：

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

### 4. 依赖管理 (internal/dependencies)

自动检查和安装工具依赖：

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

## 添加新工具

### 步骤1: 创建工具脚本

在`tools/`目录下创建工具脚本：

```bash
# 创建Shell工具
cat > tools/my-tool.sh << 'EOF'
#!/bin/bash
set -euo pipefail

# 工具脚本自己处理参数
command=$1
shift

case "$command" in
    "deploy")
        echo "Deploying with args: $@"
        # 实现部署逻辑
        ;;
    "status")
        echo "Checking status with args: $@"
        # 实现状态检查逻辑
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
# 创建Python工具
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

### 步骤2: 更新工具配置

编辑`tools/tools.json`，添加新工具：

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

### 步骤3: 添加依赖配置

编辑`tools/dependencies.json`，添加新依赖：

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

### 步骤4: 创建工具文档

在`docs/tools/`目录创建工具文档：

```markdown
# My Deployment Tool

部署工具，支持应用部署和状态检查。

## 使用方法

### 部署应用
```bash
opskit my-tool deploy myapp production
opskit my-tool deploy myapp staging --dry-run
```

### 检查状态
```bash
opskit my-tool status myapp
```

## 功能特点
- 支持多环境部署
- 提供干运行模式
- 自动状态检查

## 依赖要求
- Docker
- Kubectl
```

### 步骤5: 测试工具

```bash
# 构建项目
./build.sh

# 测试工具列表
./opskit list

# 测试新工具
./opskit my-tool --help
./opskit my-tool deploy --help
```

## 工具类型支持

### Shell脚本 (type: "shell")

```bash
#!/bin/bash
set -euo pipefail

command=$1
shift

case "$command" in
    "action1")
        echo "执行动作1: $@"
        ;;
    "action2")
        echo "执行动作2: $@"
        ;;
    *)
        echo "未知命令: $command"
        exit 1
        ;;
esac
```

### Python脚本 (type: "python")

```python
#!/usr/bin/env python3
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Python Tool')
    subparsers = parser.add_subparsers(dest='command')
    
    # 定义子命令
    action1_parser = subparsers.add_parser('action1')
    action1_parser.add_argument('param1', help='Parameter 1')
    
    action2_parser = subparsers.add_parser('action2')
    action2_parser.add_argument('--flag', action='store_true')
    
    args = parser.parse_args()
    
    if args.command == 'action1':
        print(f"执行动作1: {args.param1}")
    elif args.command == 'action2':
        print(f"执行动作2: flag={args.flag}")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### Go程序 (type: "go")

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
        fmt.Printf("执行动作1: %v\n", args)
    case "action2":
        fmt.Printf("执行动作2: %v\n", args)
    default:
        fmt.Printf("未知命令: %s\n", command)
        os.Exit(1)
    }
}
```

### 二进制文件 (type: "binary")

直接执行预编译的二进制文件，不需要脚本包装。

## 测试

### 单元测试

```bash
# 运行所有测试
go test ./... -v

# 运行特定包的测试
go test ./internal/config -v
go test ./internal/executor -v
go test ./internal/dynamic -v

# 运行覆盖率测试
go test ./... -cover
```

### 集成测试

```bash
# 构建项目
./build.sh

# 测试基本功能
./opskit --help
./opskit list
./opskit --version-info

# 测试工具执行
./opskit test-python test --verbose
```

### 编写测试用例

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

## 构建和发布

### 本地构建

```bash
# 构建当前平台
./build.sh

# 构建所有平台
./build.sh --all

# 构建特定平台
GOOS=linux GOARCH=amd64 go build -o opskit-linux-amd64
GOOS=darwin GOARCH=amd64 go build -o opskit-darwin-amd64
GOOS=windows GOARCH=amd64 go build -o opskit-windows-amd64.exe
```

### 版本发布

```bash
# 创建版本标签
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# GitHub Actions会自动构建和发布
```

## 调试

### 启用调试模式

```bash
# 环境变量
export OPSKIT_DEBUG=1

# 命令行标志
./opskit --debug list
```

### 添加调试日志

```go
import "github.com/monlor/opskit/internal/logger"

func myFunction() {
    logger.Debug("Debug message")
    logger.Info("Info message")
    logger.Warning("Warning message")
    logger.Error("Error message")
}
```

## 贡献指南

### 代码风格

1. **Go代码风格**
   - 使用`go fmt`格式化代码
   - 使用`go vet`检查代码
   - 遵循Go官方编码规范

2. **Shell脚本风格**
   - 使用`#!/bin/bash`作为shebang
   - 设置`set -euo pipefail`
   - 使用双引号包围变量

3. **Python脚本风格**
   - 使用`#!/usr/bin/env python3`
   - 遵循PEP 8规范
   - 使用type hints

### 提交规范

```bash
# 提交格式
git commit -m "type(scope): description"

# 类型说明
feat:     新功能
fix:      bug修复
docs:     文档更新
style:    代码格式化
refactor: 代码重构
test:     测试相关
chore:    构建过程或辅助工具的变动

# 示例
git commit -m "feat(tools): add deployment tool"
git commit -m "fix(executor): handle python script errors"
git commit -m "docs(readme): update installation instructions"
```

### Pull Request流程

1. **Fork仓库**
2. **创建功能分支**
   ```bash
   git checkout -b feature/new-tool
   ```
3. **开发和测试**
4. **提交代码**
5. **创建Pull Request**
6. **代码审查**
7. **合并代码**

## 最佳实践

### 工具开发

1. **错误处理**
   - 使用适当的退出码
   - 提供有用的错误信息
   - 优雅地处理中断信号

2. **用户体验**
   - 提供清晰的帮助信息
   - 支持干运行模式
   - 显示操作进度

3. **安全性**
   - 验证输入参数
   - 使用安全的临时文件
   - 避免代码注入

### 性能优化

1. **资源管理**
   - 及时释放资源
   - 使用连接池
   - 避免内存泄漏

2. **并发处理**
   - 使用goroutine处理并发
   - 合理使用channel
   - 避免竞态条件

## 发布周期

### 版本策略

- **主版本** (v1.0.0): 重大功能更新或不兼容变更
- **次版本** (v1.1.0): 新功能添加
- **补丁版本** (v1.1.1): Bug修复

### 发布流程

1. **功能开发和测试**
2. **更新文档**
3. **创建发布候选版本**
4. **测试和验证**
5. **创建正式版本**
6. **发布到GitHub Releases**

## 社区

### 获取帮助

- 📖 [文档](https://github.com/monlor/opskit/wiki)
- 💬 [讨论](https://github.com/monlor/opskit/discussions)
- 🐛 [问题反馈](https://github.com/monlor/opskit/issues)

### 贡献方式

- 报告bug
- 提出功能建议
- 贡献代码
- 改进文档
- 分享使用经验

欢迎加入OpsKit社区，一起构建更好的运维工具！
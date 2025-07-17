# OpsKit - Go Version

A lightweight remote operations toolkit rewritten in Go with support for both interactive and command-line parameter execution.

## Features

- **Dual Interface**: Both interactive menu and command-line parameter support
- **Intelligent Dependency Management**: Automatic dependency checking and installation
- **Dynamic Tool Loading**: Modular design with independent tool maintenance
- **Version Management**: Automatic updates for main branch, stable releases
- **Security**: Multiple confirmation mechanisms for dangerous operations
- **Cross-Platform**: Works on Linux, macOS, and Windows

## Installation

### From Source

```bash
go build -o opskit main.go
```

### Using Go Install

```bash
go install github.com/monlor/opskit@latest
```

## Usage

### Interactive Mode

Run without arguments to start the interactive menu:

```bash
./opskit
```

### Command Line Mode

#### List Available Tools

```bash
./opskit list                    # List all tools
./opskit list -c storage         # List tools in storage category
./opskit list --verbose          # List with detailed information
```

#### Run Specific Tools

```bash
./opskit run mysql-sync          # Run MySQL sync tool
./opskit run s3-sync            # Run S3 sync tool
./opskit mysql                  # Direct MySQL tool access
./opskit s3                     # Direct S3 tool access
```

#### Version Information

```bash
./opskit --version              # Show version
./opskit --version-info         # Show detailed version info
```

## Available Tools

### MySQL Database Sync

Synchronize MySQL databases with safety checks:

```bash
./opskit mysql
# or
./opskit run mysql-sync
```

Features:
- Connection testing before sync
- Complete database synchronization
- Safety confirmations (type "CONFIRM")
- Detailed progress information

### S3 Storage Sync

Synchronize files with Amazon S3:

```bash
./opskit s3
# or
./opskit run s3-sync
```

Features:
- AWS credential verification
- Bidirectional sync (upload/download)
- Dry run preview
- Safety confirmations
- Progress tracking

## Configuration

### Environment Variables

- `OPSKIT_DIR` - Working directory (default: `$HOME/.opskit`)
- `OPSKIT_DEBUG` - Enable debug mode (set to `1`)
- `OPSKIT_RELEASE` - Version tracking (default: `main`)
- `OPSKIT_NO_AUTO_UPDATE` - Disable main version auto-update (set to `1`)
- `OPSKIT_UPDATE_INTERVAL` - Update interval in hours (default: `1`)
- `GITHUB_REPO` - Custom repository URL for development

### Configuration Files

The tool automatically downloads and caches configuration files:

- `tools/tools.json` - Tool definitions and metadata
- `tools/dependencies.json` - Dependency configurations

## Architecture

### Core Components

1. **Main Entry Point** (`main.go`)
   - Application initialization
   - Configuration loading
   - Command execution

2. **CLI Framework** (`cmd/`)
   - Cobra-based command structure
   - Interactive and parameter modes
   - Command routing

3. **Configuration Management** (`internal/config/`)
   - Environment variable handling
   - Configuration file parsing
   - Version management

4. **Dependency Management** (`internal/dependencies/`)
   - Automatic dependency checking
   - Package manager detection
   - Interactive installation

5. **Tool Management** (`internal/tools/`)
   - Tool implementations
   - Execution management
   - Safety mechanisms

6. **Interactive Menu** (`internal/menu/`)
   - User interface
   - Tool selection
   - Progress feedback

7. **File Management** (`internal/downloader/`)
   - Configuration downloading
   - Caching mechanisms
   - Local file priority

### Tool Development

To add a new tool:

1. **Create Tool Implementation** (`internal/tools/your-tool.go`):
   ```go
   package tools
   
   import "opskit/internal/logger"
   
   type YourTool struct {
       // Tool configuration
   }
   
   func NewYourTool() *YourTool {
       return &YourTool{}
   }
   
   func (t *YourTool) Run() error {
       logger.Info("Running your tool...")
       // Tool implementation
       return nil
   }
   ```

2. **Add Command** (`cmd/your-tool.go`):
   ```go
   package cmd
   
   import (
       "github.com/spf13/cobra"
       "opskit/internal/tools"
   )
   
   var yourToolCmd = &cobra.Command{
       Use:   "your-tool",
       Short: "Your tool description",
       RunE: func(cmd *cobra.Command, args []string) error {
           tool := tools.NewYourTool()
           return tool.Run()
       },
   }
   
   func init() {
       rootCmd.AddCommand(yourToolCmd)
   }
   ```

3. **Update Configuration** (`tools/tools.json`):
   ```json
   {
     "id": "your-tool",
     "name": "Your Tool Name",
     "description": "Tool description",
     "file": "your-tool.sh",
     "dependencies": ["dependency1"],
     "category": "category",
     "version": "1.0.0"
   }
   ```

## Development

### Building

```bash
go build -o opskit main.go
```

### Running Tests

```bash
go test ./...
```

### Development Mode

Set environment variables for development:

```bash
export OPSKIT_DEBUG=1
export GITHUB_REPO="file://$(pwd)"
./opskit
```

### Cross-Platform Building

```bash
# Linux
GOOS=linux GOARCH=amd64 go build -o opskit-linux main.go

# macOS
GOOS=darwin GOARCH=amd64 go build -o opskit-darwin main.go

# Windows
GOOS=windows GOARCH=amd64 go build -o opskit-windows.exe main.go
```

## Dependencies

### Go Dependencies

- `github.com/spf13/cobra` - CLI framework
- `github.com/spf13/viper` - Configuration management
- `github.com/manifoldco/promptui` - Interactive prompts
- `github.com/fatih/color` - Colored output
- `github.com/schollz/progressbar/v3` - Progress bars

### System Dependencies

- `curl` - File downloading (fallback)
- `mysql` - MySQL client (for mysql-sync)
- `mysqldump` - MySQL dump utility (for mysql-sync)
- `aws` - AWS CLI (for s3-sync)

## Migration from Shell Version

The Go version maintains compatibility with the original shell-based architecture:

1. **Same Tool Interface**: Tools still use the same JSON configuration format
2. **Environment Variables**: All original environment variables are supported
3. **File Structure**: Same directory structure and caching mechanisms
4. **Tool Compatibility**: Can still execute shell-based tools via `run` command

### Migration Steps

1. Build the Go version: `go build -o opskit main.go`
2. Replace the shell version with the Go binary
3. All existing configurations and cache will work seamlessly
4. New features (direct tool commands) become available

## Security

- **Dependency Verification**: All dependencies are checked before installation
- **User Confirmation**: Dangerous operations require explicit confirmation
- **Safe Downloads**: File integrity checks and safe download mechanisms
- **Isolated Execution**: Tools run in isolated environments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the original project for details.

## Changelog

### v2.0.0 (Go Rewrite)

- Complete rewrite in Go
- Added command-line parameter support
- Improved dependency management
- Enhanced error handling
- Better cross-platform support
- Maintained backward compatibility
- Added direct tool commands
- Improved interactive menu
- Better progress feedback

### v1.0.0 (Original Shell Version)

- Initial shell-based implementation
- Dynamic tool loading
- Interactive menu system
- Dependency management
- Version control system
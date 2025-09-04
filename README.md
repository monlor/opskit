# OpsKit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/monlor/opskit)

> 🛠️ Unified Operations Tool Management Platform

OpsKit is a modern CLI tool that unifies operational utilities into a single, easy-to-use interface. It solves the common problems of scattered tools, complex dependencies, and inconsistent configurations in operations workflows.

## ✨ Features

- **🎯 Unified Interface**: Access all tools through a single `opskit` command
- **📦 Smart Dependencies**: Shared virtual environment with on-demand tool isolation
- **🚀 Zero Config**: Works out of the box with intelligent defaults
- **🔄 Git Native**: Version control and updates through Git
- **🖥️ Cross Platform**: Supports macOS and major Linux distributions
- **🎨 Rich UI**: Beautiful terminal interface with interactive menus
- **🧩 Extensible**: Easy plugin system for adding new tools
- **🤖 AI Friendly**: Every tool includes development guides for AI assistance

## 🚀 Quick Start

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/monlor/opskit.git ~/.opskit
   cd ~/.opskit
   ```

2. **Run setup**:
   ```bash
   python3 setup.py
   ```

3. **Add to your shell** (add to `~/.bashrc` or `~/.zshrc`):
   ```bash
   export OPSKIT_BASE_PATH="$HOME/.opskit"
   export PATH="$OPSKIT_BASE_PATH/bin:$PATH"
   ```

4. **Reload your shell** and start using:
  ```bash
  source ~/.bashrc  # or ~/.zshrc
  opskit
  ```

### Optional: Shell Completion

Enable auto-completion for `opskit` commands:

- Bash:
  ```bash
  # Append once, then reload
  opskit completion bash >> ~/.bashrc
  source ~/.bashrc
  ```

- Zsh:
  ```bash
  # Enable for current session
  source <(opskit completion zsh)

  # Enable automatically in new shells
  echo 'source <(opskit completion zsh)' >> ~/.zshrc
  ```

- Fish:
  ```bash
  mkdir -p ~/.config/fish/completions
  opskit completion fish > ~/.config/fish/completions/opskit.fish
  ```

If you relocate OpsKit, re-run the command to refresh the completion script.

### First Run

Launch the interactive interface:
```bash
opskit
```

Or list all available tools:
```bash
opskit list
```

Run a specific tool:
```bash
opskit run system-info
```

## 🛠️ Available Tools

### Database Tools
- **mysql-sync**: MySQL database synchronization and backup utility
  ```bash
  opskit run mysql-sync
  ```

### Network Tools
- **port-scanner**: Network port scanning and service detection
  ```bash
  opskit run port-scanner
  ```

### System Tools
- **disk-usage**: Disk space analysis and cleanup recommendations
  ```bash
  opskit run disk-usage
  ```
- **system-info**: Comprehensive system information gathering
  ```bash
  opskit run system-info
  ```

### Cloud Native Tools
- **k8s-resource-copy**: Kubernetes resource copying between clusters/namespaces
  ```bash
  opskit run k8s-resource-copy
  ```

## 📖 Usage

### Interactive Mode
Launch the main interface to browse and select tools:
```bash
opskit
```

### Direct Tool Execution
Run tools directly with arguments:
```bash
opskit run <tool-name> [tool-arguments...]
```

### Tool Discovery
Search for tools by name or description:
```bash
opskit search database
opskit search "port scan"
```

### Configuration Management
Access tool configuration:
```bash
opskit config                    # Global configuration
opskit config mysql-sync         # Tool-specific configuration
```

### System Management
Check system status and health:
```bash
opskit status                    # System status
opskit version                   # Version information
opskit update                    # Update OpsKit via git pull
opskit clean-cache --all         # Clean all caches (from env.cache_dir)
opskit clean-cache <service>     # Clean cache for a specific tool
```

## 🏗️ Architecture

OpsKit uses a hybrid dependency management approach:

- **Shared Environment** (`.venv/`): Core dependencies shared across all tools
- **Tool Isolation** (`cache/venvs/`): Individual environments for tools with conflicts
- **Smart Caching** (`cache/`): Dependency and resource caching for performance
- **Environment Variables**: Modern configuration via `data/.env`

### Project Structure
```
~/.opskit/
├── bin/opskit              # Main executable
├── core/                   # Core modules
│   ├── cli.py             # Interactive interface
│   ├── dependency_manager.py  # Smart dependency management
│   ├── env.py             # Environment configuration
│   └── platform_utils.py  # Cross-platform utilities
├── tools/                 # Tool plugins organized by category
│   ├── database/          # Database tools
│   ├── network/           # Network tools
│   ├── system/            # System tools
│   └── cloudnative/       # Cloud native tools
├── common/                # Shared libraries
├── cache/                 # Dependency and tool caches
└── data/                  # User configuration and storage
```

## 🔧 Configuration

OpsKit uses environment variables for configuration. Create `data/.env` to customize:

```bash
# Logging configuration
OPSKIT_LOGGING_CONSOLE_LEVEL=INFO
OPSKIT_LOGGING_FILE_ENABLED=false

# Path configuration  
OPSKIT_PATHS_CACHE_DIR=cache
OPSKIT_PATHS_LOGS_DIR=logs

# Tool-specific configuration
MYSQL_SYNC_DEFAULT_HOST=localhost
MYSQL_SYNC_DEFAULT_PORT=3306
```

## 🧩 Adding New Tools

### 1. Create Tool Structure
```bash
mkdir -p tools/category/tool-name
cd tools/category/tool-name
```

### 2. Add Required Files
- `CLAUDE.md` - Tool documentation and development guide
- `main.py` or `main.sh` - Main executable
- `requirements.txt` - Python dependencies (if needed)

### 3. Register Tool
Update `config/tools.yaml` with tool metadata.

### 4. Test Tool
```bash
opskit run tool-name
```

For detailed development guides, see:
- [Python Tool Development](docs/python-tool-development.md)
- [Shell Tool Development](docs/shell-tool-development.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-tool`
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Code Standards
- Follow existing code patterns
- Include documentation for new tools
- Add tests for new functionality
- Ensure cross-platform compatibility

## 📋 Requirements

### System Requirements
- Python 3.7 or higher
- Git (for updates and version control)
- Internet connection (for dependency installation)

### Supported Platforms
- **macOS**: 10.14+ (Intel and Apple Silicon)
- **Linux**: Ubuntu 18.04+, CentOS 7+, Arch Linux, openSUSE

### Dependencies
Core dependencies are automatically managed:
- Rich - Beautiful terminal interfaces
- Click - Command line interface framework
- PyYAML - Configuration file handling
- python-dotenv - Environment variable management
- psutil - System information
- And more (see `requirements.txt`)

## 🐛 Troubleshooting

### Common Issues

**Tool not found**:
```bash
opskit list  # Check available tools
opskit search <partial-name>  # Search for tools
```

**Dependency issues**:
```bash
opskit status  # Check system status
rm -rf cache/venvs/<tool-name>  # Reset tool environment
```

**Permission errors**:
```bash
chmod +x bin/opskit  # Ensure executable permissions
```

**Environment issues**:
```bash
echo $OPSKIT_BASE_PATH  # Verify environment variables
echo $PATH | grep opskit  # Check PATH configuration
```

### Getting Help
- Check tool-specific help: `opskit run <tool> --help`
- View system status: `opskit status`
- Enable debug mode: `opskit --debug <command>`

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal interfaces
- Powered by [Click](https://github.com/pallets/click) for command line interfaces
- Inspired by modern DevOps tooling practices

## 📬 Contact

- **Issues**: [GitHub Issues](https://github.com/monlor/opskit/issues)
- **Discussions**: [GitHub Discussions](https://github.com/monlor/opskit/discussions)
- **Security**: Please report security issues privately via email

---

<div align="center">

**[⬆ Back to Top](#opskit)**

Made with ❤️ by the OpsKit team

</div>

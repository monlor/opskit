# OpsKit - Remote Operations Toolkit

<div align="center">

![OpsKit Logo](https://via.placeholder.com/120x120/0066CC/FFFFFF?text=OpsKit)

**Lightweight Remote Operations Toolkit**

[![Go Version](https://img.shields.io/badge/Go-1.21+-blue.svg)](https://golang.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/monlor/opskit)](https://github.com/monlor/opskit/releases)
[![Build Status](https://img.shields.io/github/actions/workflow/status/monlor/opskit/build.yml)](https://github.com/monlor/opskit/actions)

</div>

## 🚀 Quick Start

### One-Click Installation

```bash
# Install latest version
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash

# Install specific version
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash -s -- --version=v1.0.0
```

### Quick Usage

```bash
# Show help
opskit --help

# List all tools
opskit list

# Use MySQL sync tool
opskit mysql-sync sync source_db target_db

# Use S3 sync tool
opskit s3-sync upload /local/path s3://bucket/path
```

## 📖 Overview

OpsKit is a lightweight remote operations toolkit developed in Go, focusing on providing:

- **🔧 Dynamic Tool Loading** - Lightweight main program with on-demand tool loading
- **🏗️ Modular Design** - Independent tool maintenance and updates
- **🔍 Intelligent Dependency Management** - Automatic detection and installation of required dependencies
- **🛡️ Safe Operations** - Multiple confirmation mechanisms to prevent misoperations
- **🌐 Multi-language Support** - Shell, Python, Go, Binary script types

## ✨ Core Features

### 🎯 Dynamic Tool System
- JSON configuration-driven dynamic command generation
- Support for multiple script types (Shell, Python, Go, Binary)
- Version management and auto-update mechanism
- Local file priority with remote download fallback

### 📦 Intelligent Dependency Management
- Automatic system dependency detection
- Cross-platform package manager support (brew, apt, yum, dnf)
- User-confirmed installation, safe and controllable

### 🔒 Security Design
- Multiple confirmation mechanisms for dangerous operations
- Detailed operation preview and information display
- Parameter filtering and validation
- Debug mode support

## 🛠️ Built-in Tools

| Tool | Description | Documentation |
|------|-------------|---------------|
| [mysql-sync](docs/tools/mysql-sync.md) | MySQL Database Sync Tool | Support for complete database synchronization and connection testing |
| [s3-sync](docs/tools/s3-sync.md) | S3 Storage Sync Tool | Support for bidirectional sync between S3 and local with dry-run preview |
| [test-python](docs/tools/test-python.md) | Python Tool Example | Demonstration of Python script integration |

## 📋 Supported Systems

- **Operating Systems**: Linux, macOS, Windows
- **Architectures**: amd64, arm64, 386, arm
- **Go Version**: 1.21+

## 📚 Documentation

- [Installation Guide](docs/installation.md) - Detailed installation and configuration instructions
- [Development Guide](docs/development.md) - Development environment setup and contribution guide
- [Tool Documentation](docs/tools/) - Detailed usage instructions for each tool
- [API Documentation](docs/api.md) - Program interfaces and configuration specifications

## 🏗️ Architecture Overview

```
OpsKit/
├── cmd/                    # CLI command definitions
├── internal/               # Internal packages
│   ├── config/            # Configuration management
│   ├── executor/          # Tool executor
│   ├── dynamic/           # Dynamic command generation
│   └── dependencies/      # Dependency management
├── tools/                 # Tool scripts and configuration
│   ├── tools.json         # Tool configuration
│   ├── dependencies.json  # Dependency configuration
│   └── *.sh|*.py|*.go     # Tool scripts
└── docs/                  # Documentation
```

## 🔧 Development

### Local Build

```bash
# Clone repository
git clone https://github.com/monlor/opskit.git
cd opskit

# Build project
./build.sh

# Run tests
go test ./... -v
```

### Adding New Tools

1. Create tool script in `tools/` directory
2. Update `tools/tools.json` configuration
3. Update `tools/dependencies.json` dependency configuration
4. Add documentation in `docs/tools/`

For detailed steps, see [Development Guide](docs/development.md)

## 📄 License

This project is open-sourced under the MIT License - see the [LICENSE](LICENSE) file for details

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for how to participate in project development.

## 📞 Support

- 🐛 [Report Issues](https://github.com/monlor/opskit/issues)
- 💬 [Discussions](https://github.com/monlor/opskit/discussions)
- 📖 [Documentation](https://github.com/monlor/opskit/wiki)

---

<div align="center">
Made with ❤️ by OpsKit Team
</div>
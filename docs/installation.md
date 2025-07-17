# Installation Guide

This guide provides detailed instructions for installing and configuring OpsKit on different operating systems.

## System Requirements

### Supported Operating Systems
- **Linux**: Ubuntu 18.04+, CentOS 7+, Debian 9+, Fedora 28+
- **macOS**: 10.14+ (Mojave and later)
- **Windows**: Windows 10+ (via WSL)

### Supported Architectures
- **x86_64 (amd64)**: 64-bit Intel/AMD processors
- **arm64 (aarch64)**: 64-bit ARM processors (Apple Silicon, ARM servers)
- **i386 (386)**: 32-bit Intel/AMD processors
- **armv7l (arm)**: 32-bit ARM processors

### System Dependencies
- **curl**: For downloading files
- **tar**: For extracting archives
- **bash**: For running installation scripts

## Installation Methods

### Method 1: One-Click Installation (Recommended)

#### Install Latest Version
```bash
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash
```

#### Install Specific Version
```bash
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash -s -- --version=v1.0.0
```

#### Force Reinstallation
```bash
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash -s -- --force
```

### Method 2: Manual Installation

#### 1. Download Installation Script
```bash
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh -o install.sh
chmod +x install.sh
```

#### 2. Run Installation Script
```bash
# Show help
./install.sh --help

# Install latest version
./install.sh

# Install specific version
./install.sh --version=v1.0.0

# Enable debug mode
./install.sh --debug --version=v1.0.0
```

### Method 3: Manual Binary Download

#### 1. Download from GitHub Releases
Visit the [GitHub Releases](https://github.com/monlor/opskit/releases) page and download the binary for your system.

#### 2. Extract and Install
```bash
# Extract file
tar -xzf opskit_v1.0.0_linux_amd64.tar.gz

# Copy to system path
sudo cp opskit /usr/local/bin/

# Set execute permissions
sudo chmod +x /usr/local/bin/opskit
```

## Installation Options

### Command Line Options

The installation script supports the following options:

```bash
./install.sh [OPTIONS]
```

#### Option Descriptions
- `--version=VERSION`: Install specific version (e.g., v1.0.0, main)
- `--force`: Force reinstallation even if already installed
- `--debug`: Enable debug output
- `--help`: Show help information

#### Usage Examples
```bash
# Install latest stable version
./install.sh

# Install specific version
./install.sh --version=v1.0.0

# Install development version (not recommended for production)
./install.sh --version=main

# Force reinstallation with debug
./install.sh --force --debug
```

## Platform-Specific Installation

### Ubuntu/Debian

```bash
# Update package manager
sudo apt-get update

# Install dependencies
sudo apt-get install -y curl tar

# Install OpsKit
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash
```

### CentOS/RHEL

```bash
# Install dependencies
sudo yum install -y curl tar

# Install OpsKit
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash
```

### macOS

```bash
# Install dependencies using Homebrew (if needed)
brew install curl

# Install OpsKit
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash
```

### Windows (WSL)

```bash
# Install in WSL
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash
```

## Verify Installation

### Check Installation Status
```bash
# Check version
opskit --version

# Show help
opskit --help

# List tools
opskit list
```

### Expected Output
```bash
$ opskit --version
OpsKit v1.0.0 (build: abc123, date: 2024-01-01)

$ opskit list
Available tools:
  mysql-sync    - MySQL Database Sync
  s3-sync       - S3 Storage Sync
  test-python   - Test Python Tool
```

## Configuration

### Environment Variables

OpsKit supports the following environment variables for configuration:

```bash
# Set working directory (default: $HOME/.opskit)
export OPSKIT_DIR="$HOME/.opskit"

# Enable debug mode
export OPSKIT_DEBUG=1

# Set version tracking (default: main)
export OPSKIT_RELEASE=v1.0.0

# Disable main version auto-update
export OPSKIT_NO_AUTO_UPDATE=1

# Set update check interval (default: 1 hour)
export OPSKIT_UPDATE_INTERVAL=6

# Custom GitHub repository (for development/testing)
export GITHUB_REPO=https://github.com/your-username/opskit
```

### Configuration File

Create a configuration file for persistent settings:

```bash
# Create configuration directory
mkdir -p ~/.opskit

# Create configuration file
cat > ~/.opskit/config.yaml << EOF
# OpsKit configuration file
debug: false
auto_update: true
update_interval: 1h
work_dir: ~/.opskit
release: main
EOF
```

## Uninstallation

### Complete Uninstallation
```bash
# Remove binary file
sudo rm -f /usr/local/bin/opskit

# Remove configuration and cache
rm -rf ~/.opskit

# Remove environment variables (from ~/.bashrc or ~/.zshrc)
# unset OPSKIT_DIR OPSKIT_DEBUG OPSKIT_RELEASE
```

### Uninstall but Keep Configuration
```bash
# Remove binary file only
sudo rm -f /usr/local/bin/opskit

# Keep ~/.opskit directory for reinstallation
```

## Troubleshooting

### Common Issues

#### 1. Permission Denied
```
Error: Permission denied
```
**Solution:**
```bash
# Check script permissions
chmod +x install.sh

# Use sudo if needed
sudo ./install.sh
```

#### 2. Command Not Found
```
Error: opskit: command not found
```
**Solution:**
```bash
# Check PATH environment variable
echo $PATH

# Add /usr/local/bin to PATH
export PATH="/usr/local/bin:$PATH"

# Add permanently to shell configuration
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### 3. Download Failed
```
Error: Failed to download OpsKit binary
```
**Solution:**
```bash
# Check network connection
curl -I https://github.com/monlor/opskit/releases

# Use proxy
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# Manual download
wget https://github.com/monlor/opskit/releases/download/v1.0.0/opskit_v1.0.0_linux_amd64.tar.gz
```

#### 4. Version Mismatch
```
Error: Version v1.0.0 not found in releases
```
**Solution:**
```bash
# Check available versions
curl -s https://api.github.com/repos/monlor/opskit/releases | grep tag_name

# Use correct version number
./install.sh --version=v1.0.0
```

#### 5. Missing Dependencies
```
Error: Missing required dependencies: curl
```
**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install curl tar

# CentOS/RHEL
sudo yum install curl tar

# macOS
brew install curl
```

### Debug Mode

Enable debug mode for detailed information:

```bash
# Enable debug during installation
./install.sh --debug

# Enable debug during runtime
export OPSKIT_DEBUG=1
opskit --version-info
```

### Log Viewing

```bash
# View installation logs
tail -f /tmp/opskit-install.log

# View runtime logs
export OPSKIT_DEBUG=1
opskit list 2>&1 | tee opskit-debug.log
```

## Advanced Installation

### Enterprise Environment Installation

#### 1. Offline Installation
```bash
# 1. Download on a networked machine
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh -o install.sh
curl -L https://github.com/monlor/opskit/releases/download/v1.0.0/opskit_v1.0.0_linux_amd64.tar.gz -o opskit.tar.gz

# 2. Transfer to target machine
scp install.sh opskit.tar.gz user@target:/tmp/

# 3. Install on target machine
tar -xzf /tmp/opskit.tar.gz
sudo cp opskit /usr/local/bin/
sudo chmod +x /usr/local/bin/opskit
```

#### 2. Batch Installation
```bash
#!/bin/bash
# Batch installation script

HOSTS=(
    "server1.example.com"
    "server2.example.com"
    "server3.example.com"
)

for host in "${HOSTS[@]}"; do
    echo "Installing on $host"
    ssh "$host" 'curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash'
done
```

#### 3. Docker Container Installation
```dockerfile
FROM ubuntu:20.04

RUN apt-get update && apt-get install -y curl tar
RUN curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash

ENTRYPOINT ["opskit"]
```

### Custom Installation Directory

```bash
# Install to custom directory
mkdir -p ~/bin
curl -L https://github.com/monlor/opskit/releases/download/v1.0.0/opskit_v1.0.0_linux_amd64.tar.gz | tar -xzf - -C ~/bin

# Add to PATH
export PATH="$HOME/bin:$PATH"
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
```

## Upgrade and Updates

### Auto Update
```bash
# Check for updates
opskit --version-info

# Main version auto-updates, release versions require manual update
export OPSKIT_RELEASE=main
```

### Manual Update
```bash
# Re-run installation script
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash

# Or force update
curl -fsSL https://raw.githubusercontent.com/monlor/opskit/main/install.sh | bash -s -- --force
```

### Version Rollback
```bash
# Install specific version
./install.sh --version=v1.0.0 --force

# Disable auto-update
export OPSKIT_NO_AUTO_UPDATE=1
```

## Security Considerations

### Installation Verification
```bash
# Check binary file
ls -la /usr/local/bin/opskit

# Verify version
opskit --version

# Check tool list
opskit list
```

### Security Recommendations
1. Download from official repository
2. Verify downloaded file integrity
3. Test in development environment first
4. Keep updated to latest version
5. Monitor system logs

With these instructions, you can successfully install and configure OpsKit in various environments.
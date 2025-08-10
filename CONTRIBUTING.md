# Contributing to OpsKit

Thank you for your interest in contributing to OpsKit! This guide will help you get started with contributing to our unified operations tool management platform.

## 🎯 Ways to Contribute

- **🐛 Bug Reports**: Help us identify and fix issues
- **✨ Feature Requests**: Suggest new tools or improvements
- **🛠️ New Tools**: Add operational tools to the platform
- **📚 Documentation**: Improve guides and documentation
- **🧪 Testing**: Help test across different platforms
- **💡 Ideas**: Share ideas for platform improvements

## 🚀 Getting Started

### Prerequisites

- **Python 3.7+**: Required for core functionality
- **Git**: For version control and contributions
- **Basic Shell Knowledge**: For testing and tool development
- **Platform Access**: macOS or Linux for testing

### Development Setup

1. **Fork the Repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/opskit.git ~/.opskit-dev
   cd ~/.opskit-dev
   ```

2. **Set Up Development Environment**
   ```bash
   # Create development environment
   python3 setup.py
   
   # Set development environment variables
   export OPSKIT_BASE_PATH="$HOME/.opskit-dev"
   export PATH="$OPSKIT_BASE_PATH/bin:$PATH"
   export OPSKIT_LOGGING_CONSOLE_LEVEL=DEBUG
   ```

3. **Verify Installation**
   ```bash
   opskit version
   opskit status
   opskit list
   ```

4. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b tool/new-tool-name
   # or  
   git checkout -b fix/issue-description
   ```

## 🛠️ Development Guidelines

### Code Standards

#### Python Code
- **Style**: Follow PEP 8 with 88-character line limit
- **Type Hints**: Use type hints for function parameters and returns
- **Documentation**: Include docstrings for all public functions/classes
- **Error Handling**: Use proper exception handling with specific error types
- **Logging**: Use the unified logging system from `common/python/logger.py`

```python
def example_function(tool_name: str, config: dict) -> bool:
    """
    Example function with proper style.
    
    Args:
        tool_name: Name of the tool to process
        config: Configuration dictionary
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        ToolError: When tool processing fails
    """
    try:
        # Implementation here
        return True
    except Exception as e:
        logger.error(f"Tool processing failed: {e}")
        raise ToolError(f"Failed to process {tool_name}: {e}")
```

#### Shell Code
- **Portability**: Write POSIX-compliant shell scripts
- **Error Handling**: Use `set -euo pipefail` for strict error handling
- **Functions**: Use functions for reusable code blocks
- **Logging**: Use the unified logging from `common/shell/logger.sh`

```bash
#!/bin/bash
set -euo pipefail

# Import common functions
source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
source "${OPSKIT_BASE_PATH}/common/shell/utils.sh"

main() {
    log_info "Starting tool execution"
    
    # Tool implementation
    if ! command_exists "required-command"; then
        log_error "Required command not found"
        exit 1
    fi
    
    log_info "Tool execution completed"
}

main "$@"
```

### File Structure Standards

Every contribution should maintain the established directory structure:

```
~/.opskit/
├── bin/opskit              # Main executable (do not modify without approval)
├── core/                   # Core modules (careful with changes)
├── tools/                  # Tool contributions welcome here
│   └── category/
│       └── tool-name/
│           ├── CLAUDE.md   # Required: Tool documentation
│           ├── main.py     # Required: Tool implementation  
│           └── requirements.txt  # Optional: Python dependencies
├── common/                 # Shared utilities (coordinate changes)
├── config/                 # Configuration files
└── docs/                   # Documentation contributions welcome
```

## 🧩 Adding New Tools

### Tool Development Process

1. **Choose Tool Category**
   - `database/` - Database operations and management
   - `network/` - Network diagnostics and utilities
   - `system/` - System administration and monitoring
   - `cloudnative/` - Kubernetes, Docker, cloud tools
   - `security/` - Security scanning and auditing
   - `monitoring/` - Observability and alerting tools

2. **Create Tool Structure**
   ```bash
   mkdir -p tools/category/tool-name
   cd tools/category/tool-name
   ```

3. **Required Files**

   **CLAUDE.md** (Required):
   ```markdown
   # Tool Name
   
   ## Description
   Brief description of what this tool does and why it's useful.
   
   ## Usage
   ```bash
   opskit run tool-name [options]
   ```
   
   ## Configuration
   Environment variables and configuration options.
   
   ## Dependencies
   - System dependencies required
   - Python packages (if any)
   
   ## Examples
   Common use cases and examples.
   
   ## Development
   Notes for developers and contributors.
   ```

   **main.py** (Python tools):
   ```python
   #!/usr/bin/env python3
   """
   Tool Name - Brief Description
   """
   
   import sys
   import os
   from pathlib import Path
   
   # Add common Python libraries to path
   opskit_root = Path(__file__).parent.parent.parent.parent
   sys.path.insert(0, str(opskit_root / 'common' / 'python'))
   
   from logger import get_logger
   from storage import get_storage
   
   logger = get_logger(__name__)
   
   def main():
       """Main tool entry point"""
       logger.info("Tool starting")
       # Tool implementation
       
   if __name__ == '__main__':
       main()
   ```

   **main.sh** (Shell tools):
   ```bash
   #!/bin/bash
   set -euo pipefail
   
   # Import common shell functions
   source "${OPSKIT_BASE_PATH}/common/shell/logger.sh"
   source "${OPSKIT_BASE_PATH}/common/shell/utils.sh"
   
   main() {
       log_info "Tool starting"
       # Tool implementation
   }
   
   main "$@"
   ```

4. **Register Tool**
   Add tool entry to `config/tools.yaml`:
   ```yaml
   tools:
     tool-name:
       name: "Tool Display Name"
       category: "category"
       description: "Brief description"
       language: "python"  # or "shell"
       executable: "main.py"  # or "main.sh"
       author: "Your Name"
       version: "1.0.0"
   ```

### Tool Development Best Practices

#### Dependency Management
- **Minimal Dependencies**: Only add truly necessary dependencies
- **Version Pinning**: Specify version ranges in requirements.txt
- **Conflict Awareness**: Check for conflicts with existing tools
- **Fallback Handling**: Gracefully handle missing optional dependencies

```txt
# requirements.txt example
requests>=2.25.0,<3.0.0
pyyaml>=6.0,<7.0
click>=8.0.0,<9.0.0
```

#### Configuration Management
- **Environment Variables**: Use OPSKIT_TOOLNAME_* prefix for tool configs
- **Sensible Defaults**: Always provide reasonable default values  
- **Validation**: Validate configuration on startup
- **Documentation**: Document all configuration options

```python
# Configuration example
import os

def get_config():
    return {
        'host': os.getenv('OPSKIT_MYSQL_SYNC_HOST', 'localhost'),
        'port': int(os.getenv('OPSKIT_MYSQL_SYNC_PORT', '3306')),
        'timeout': int(os.getenv('OPSKIT_MYSQL_SYNC_TIMEOUT', '30'))
    }
```

#### Error Handling
- **Graceful Failures**: Never crash without explanation
- **User-Friendly Messages**: Provide actionable error messages
- **Exit Codes**: Use appropriate exit codes (0=success, 1=error, 2=misuse)
- **Logging**: Log errors with appropriate levels

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    print(f"❌ Error: {e}")
    print("💡 Try: Check your configuration and try again")
    sys.exit(1)
```

## 🧪 Testing Guidelines

### Before Submitting

1. **Unit Testing**
   ```bash
   # Test your tool directly
   opskit run your-tool
   
   # Test with various inputs
   opskit run your-tool --help
   opskit run your-tool invalid-input
   ```

2. **Integration Testing**
   ```bash
   # Test tool discovery
   opskit list | grep your-tool
   opskit search "your tool"
   
   # Test dependency management
   rm -rf cache/venvs/your-tool  # Force dependency reinstall
   opskit run your-tool
   ```

3. **Cross-Platform Testing** (if possible)
   - Test on multiple Linux distributions
   - Test on macOS (Intel and Apple Silicon)
   - Verify shell compatibility

### Test Checklist

- [ ] Tool runs without errors
- [ ] Help documentation is accurate
- [ ] Dependencies install correctly
- [ ] Error messages are user-friendly
- [ ] Exit codes are appropriate
- [ ] Logging output is reasonable
- [ ] Configuration works as documented
- [ ] Tool appears in `opskit list`
- [ ] Tool is discoverable via `opskit search`

## 📋 Pull Request Process

### Before Creating PR

1. **Code Quality**
   ```bash
   # Format Python code (if available)
   black tools/category/your-tool/
   
   # Check shell scripts (if available)
   shellcheck tools/category/your-tool/main.sh
   ```

2. **Documentation**
   - Ensure CLAUDE.md is complete
   - Update README.md if needed
   - Add configuration documentation

3. **Testing**
   - Run comprehensive tests
   - Verify on clean environment
   - Test edge cases and error conditions

### PR Submission

1. **Commit Messages**
   Use conventional commit format:
   ```
   feat(tools): add mysql-backup tool for database backups
   fix(core): resolve dependency conflict in tool isolation
   docs(readme): update installation instructions for macOS
   ```

2. **PR Description Template**
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New tool
   - [ ] Core improvement
   - [ ] Documentation update
   
   ## Testing
   - [ ] Unit tests pass
   - [ ] Integration tests pass
   - [ ] Cross-platform tested
   
   ## Tool Information (if applicable)
   - **Category**: database
   - **Language**: Python
   - **Dependencies**: mysql-client
   - **Platforms**: Linux, macOS
   
   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] CLAUDE.md documentation complete
   - [ ] Tool registered in config/tools.yaml
   - [ ] No breaking changes to existing tools
   ```

### Review Process

1. **Automated Checks**
   - Code quality validation
   - Basic functionality testing
   - Documentation completeness

2. **Manual Review**
   - Code review by maintainers
   - Architecture compliance check
   - Security review (if applicable)

3. **Testing**
   - Cross-platform testing
   - Integration testing
   - Performance impact assessment

## 🐛 Bug Reports

### Bug Report Template

```markdown
**Bug Description**
Clear description of the bug

**To Reproduce**
Steps to reproduce the behavior:
1. Run `opskit ...`
2. Select option '...'
3. See error

**Expected Behavior**
What you expected to happen

**Environment**
- OS: [e.g., Ubuntu 22.04, macOS 13.0]
- Python Version: [e.g., 3.9.7]
- OpsKit Version: [run `opskit version`]

**Logs**
```bash
# Enable debug logging and paste relevant output
OPSKIT_LOGGING_CONSOLE_LEVEL=DEBUG opskit run tool-name
```

**Additional Context**
Any other context about the problem
```

### Security Issues

For security-related issues:
- **DO NOT** create public issues
- Email security concerns privately
- Include reproduction steps if safe
- Allow reasonable time for response

## ✨ Feature Requests

### Feature Request Template

```markdown
**Feature Description**
Clear description of the proposed feature

**Problem Statement**
What problem does this solve?

**Proposed Solution**
How would you like it to work?

**Alternatives Considered**
Other solutions you've considered

**Implementation Ideas**
Technical approach (if you have ideas)

**Additional Context**
Screenshots, examples, references
```

## 🏷️ Release Process

### Versioning
- Follow [Semantic Versioning](https://semver.org/)
- **Major**: Breaking changes to core functionality
- **Minor**: New tools, backward-compatible features
- **Patch**: Bug fixes, minor improvements

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped appropriately
- [ ] Cross-platform testing completed

## 🤝 Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different perspectives and approaches

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Request Comments**: Code-specific discussions
- **Email**: Security issues and private communications

### Recognition
Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes for significant contributions
- Tool attribution in CLAUDE.md files

## 📚 Resources

### Documentation
- [Python Tool Development Guide](docs/python-tool-development.md)
- [Shell Tool Development Guide](docs/shell-tool-development.md)
- [Architecture Overview](CLAUDE.md)

### External References
- [Python PEP 8 Style Guide](https://pep8.org/)
- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
- [Conventional Commits](https://conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

### Development Tools
- [Rich Documentation](https://rich.readthedocs.io/) - Terminal UI framework
- [Click Documentation](https://click.palletsprojects.com/) - CLI framework
- [pytest](https://docs.pytest.org/) - Testing framework

## 🆘 Getting Help

Stuck? Here's how to get help:

1. **Check Documentation**: Look through existing docs and guides
2. **Search Issues**: Your question might already be answered
3. **Ask Questions**: Create a GitHub Discussion
4. **Join Community**: Participate in ongoing discussions

### Questions?

Don't hesitate to ask! We're here to help make your contribution experience smooth and rewarding.

---

Thank you for contributing to OpsKit! 🎉

<div align="center">

**[⬆ Back to Top](#contributing-to-opskit)**

</div>
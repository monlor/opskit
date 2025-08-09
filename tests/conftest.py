"""Test configuration and fixtures for OpsKit test suite"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'core'))
sys.path.insert(0, str(PROJECT_ROOT / 'common' / 'python'))

@pytest.fixture
def project_root():
    """Fixture providing path to project root directory"""
    return PROJECT_ROOT

@pytest.fixture
def temp_opskit_dir():
    """Create a temporary OpsKit directory for testing"""
    with tempfile.TemporaryDirectory(prefix="opskit_test_") as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create essential directory structure
        (temp_path / 'core').mkdir()
        (temp_path / 'common' / 'python').mkdir(parents=True)
        (temp_path / 'common' / 'shell').mkdir()
        (temp_path / 'tools').mkdir()
        (temp_path / 'config').mkdir()
        (temp_path / 'data').mkdir()
        (temp_path / 'cache' / 'venvs').mkdir(parents=True)
        (temp_path / 'logs').mkdir()
        
        # Set environment variable
        os.environ['OPSKIT_BASE_PATH'] = str(temp_path)
        
        yield temp_path
        
        # Cleanup
        if 'OPSKIT_BASE_PATH' in os.environ:
            del os.environ['OPSKIT_BASE_PATH']

@pytest.fixture
def mock_platform_utils():
    """Mock platform utilities for testing"""
    mock = Mock()
    mock.detect_os.return_value = 'ubuntu'
    mock.detect_distro.return_value = 'Ubuntu 22.04'
    mock.get_package_managers.return_value = ['apt', 'apt-get']
    mock.command_exists.return_value = True
    mock.install_system_package.return_value = (True, "Package installed successfully")
    mock.get_system_info.return_value = {
        'os': 'Linux',
        'distro': 'Ubuntu 22.04',
        'architecture': 'x86_64',
        'python_version': '3.12.0'
    }
    return mock

@pytest.fixture
def mock_subprocess():
    """Mock subprocess for testing system commands"""
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "success"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run

@pytest.fixture
def sample_tool_structure(temp_opskit_dir):
    """Create sample tool structure for testing"""
    tool_dir = temp_opskit_dir / 'tools' / 'test' / 'sample-tool'
    tool_dir.mkdir(parents=True)
    
    # Create CLAUDE.md
    claude_md = """# Sample Tool

## 功能描述
A sample tool for testing

## 技术架构
- 实现语言: Python
- 核心依赖: requests

## 配置项
None

## 开发指南
Sample tool implementation

## 使用示例
./sample-tool
"""
    (tool_dir / 'CLAUDE.md').write_text(claude_md)
    
    # Create main.py
    main_py = """#!/usr/bin/env python3
import sys
print("Sample tool executed successfully")
"""
    (tool_dir / 'main.py').write_text(main_py)
    
    # Create requirements.txt
    (tool_dir / 'requirements.txt').write_text("requests>=2.25.0\n")
    
    return tool_dir

@pytest.fixture
def mock_sqlite_db(temp_opskit_dir):
    """Mock SQLite database for testing"""
    db_path = temp_opskit_dir / 'data' / 'storage.db'
    
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.execute('''
        CREATE TABLE IF NOT EXISTS kv_store (
            key TEXT PRIMARY KEY,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    
    return db_path

@pytest.fixture
def sample_dependencies_config(temp_opskit_dir):
    """Create sample dependencies configuration"""
    config_content = """
system_dependencies:
  mysql-client:
    commands: ['mysql']
    packages:
      ubuntu: ['mysql-client']
      centos: ['mysql']
      arch: ['mysql']
      
  curl:
    commands: ['curl']
    packages:
      ubuntu: ['curl']
      centos: ['curl']
      arch: ['curl']
"""
    config_path = temp_opskit_dir / 'config' / 'dependencies.yaml'
    config_path.write_text(config_content)
    return config_path

@pytest.fixture
def sample_tools_config(temp_opskit_dir):
    """Create sample tools configuration"""
    config_content = """
tools:
  sample-tool:
    category: test
    type: python
    description: A sample tool for testing
    version: 1.0.0
"""
    config_path = temp_opskit_dir / 'config' / 'tools.yaml'
    config_path.write_text(config_content)
    return config_path

@pytest.fixture
def mock_environment():
    """Mock environment variables for testing"""
    original_env = os.environ.copy()
    
    # Set test environment
    test_env = {
        'OPSKIT_DEBUG': 'true',
        'OPSKIT_LOG_LEVEL': 'DEBUG',
        'PYTHONPATH': str(PROJECT_ROOT)
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def capture_logs():
    """Fixture to capture log output for testing"""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    
    # Get logger and add handler
    logger = logging.getLogger('opskit')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    # Cleanup
    logger.removeHandler(handler)

# Pytest hooks for better test organization
def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "tool: Tool-specific tests")
    config.addinivalue_line("markers", "shell: Shell script tests")
    config.addinivalue_line("markers", "python: Python module tests")
    config.addinivalue_line("markers", "core: Core module tests")
    config.addinivalue_line("markers", "common: Common library tests")

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "core" in str(item.fspath):
            item.add_marker(pytest.mark.core)
        elif "common" in str(item.fspath):
            item.add_marker(pytest.mark.common)
        elif "tools" in str(item.fspath):
            item.add_marker(pytest.mark.tool)
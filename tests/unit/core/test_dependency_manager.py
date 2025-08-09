"""Tests for dependency_manager.py"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import subprocess

from core.dependency_manager import DependencyManager


class TestDependencyManager:
    """Test cases for DependencyManager"""
    
    def test_init(self, temp_opskit_dir, mock_platform_utils):
        """Test DependencyManager initialization"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(debug=True)
            
            assert dm.debug is True
            assert dm.base_path == Path.cwd()  # Uses current directory as fallback
            assert dm.venvs_dir.name == 'venvs'
            assert dm.cache_dir.name == 'cache'
    
    def test_init_with_base_path(self, temp_opskit_dir, mock_platform_utils):
        """Test DependencyManager initialization with custom base path"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir, debug=False)
            
            assert dm.debug is False
            assert dm.base_path == temp_opskit_dir
            assert dm.venvs_dir == temp_opskit_dir / 'cache' / 'venvs'
    
    def test_load_dependencies_config_success(self, temp_opskit_dir, sample_dependencies_config, mock_platform_utils):
        """Test successful loading of dependencies configuration"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir)
            config = dm._load_dependencies_config()
            
            assert 'system_dependencies' in config
            assert 'mysql-client' in config['system_dependencies']
            assert 'curl' in config['system_dependencies']
    
    def test_load_dependencies_config_missing_file(self, temp_opskit_dir, mock_platform_utils):
        """Test loading dependencies configuration with missing file"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir, debug=True)
            config = dm._load_dependencies_config()
            
            assert config == {}  # Should return empty dict for missing file
    
    def test_get_tool_python_executable_existing_venv(self, temp_opskit_dir, mock_platform_utils):
        """Test getting Python executable for existing virtual environment"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir)
            
            # Create a mock venv structure
            venv_dir = dm.venvs_dir / 'test-tool'
            venv_dir.mkdir(parents=True)
            bin_dir = venv_dir / 'bin'
            bin_dir.mkdir()
            python_exe = bin_dir / 'python'
            python_exe.write_text("#!/usr/bin/env python3")
            python_exe.chmod(0o755)
            
            result = dm.get_tool_python_executable('test-tool')
            assert result == python_exe
            assert result.exists()
    
    def test_get_tool_python_executable_non_existing_venv(self, temp_opskit_dir, mock_platform_utils):
        """Test getting Python executable for non-existing virtual environment"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir)
            
            result = dm.get_tool_python_executable('non-existing-tool')
            assert result is None
    
    @patch('venv.create')
    @patch('subprocess.run')
    def test_setup_python_environment_success(self, mock_subprocess, mock_venv_create, 
                                            temp_opskit_dir, sample_tool_structure, mock_platform_utils):
        """Test successful Python environment setup"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir, debug=True)
            
            # Mock subprocess for pip operations
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Successfully installed"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result
            
            # Mock successful dependency check
            with patch.object(dm, '_are_python_deps_satisfied', return_value=False):
                success, message = dm.setup_python_environment('sample-tool', sample_tool_structure)
            
            assert success is True
            assert "successfully" in message.lower()
            mock_venv_create.assert_called_once()
    
    @patch('subprocess.run')
    def test_are_python_deps_satisfied_all_satisfied(self, mock_subprocess, 
                                                   temp_opskit_dir, sample_tool_structure, mock_platform_utils):
        """Test checking Python dependencies when all are satisfied"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir, debug=True)
            
            # Create mock venv structure
            venv_dir = dm.venvs_dir / 'sample-tool'
            venv_dir.mkdir(parents=True)
            bin_dir = venv_dir / 'bin'
            bin_dir.mkdir()
            python_exe = bin_dir / 'python'
            python_exe.write_text("#!/usr/bin/env python3")
            python_exe.chmod(0o755)
            
            # Mock pip list output
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps([{'name': 'requests', 'version': '2.28.1'}])
            mock_subprocess.return_value = mock_result
            
            requirements_file = sample_tool_structure / 'requirements.txt'
            result = dm._are_python_deps_satisfied('sample-tool', requirements_file)
            
            assert result is True
    
    @patch('subprocess.run')
    def test_are_python_deps_satisfied_missing_deps(self, mock_subprocess, 
                                                  temp_opskit_dir, sample_tool_structure, mock_platform_utils):
        """Test checking Python dependencies when some are missing"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir, debug=True)
            
            # Create mock venv structure
            venv_dir = dm.venvs_dir / 'sample-tool'
            venv_dir.mkdir(parents=True)
            bin_dir = venv_dir / 'bin'
            bin_dir.mkdir()
            python_exe = bin_dir / 'python'
            python_exe.write_text("#!/usr/bin/env python3")
            python_exe.chmod(0o755)
            
            # Mock pip list output with missing package
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps([{'name': 'urllib3', 'version': '1.26.12'}])
            mock_subprocess.return_value = mock_result
            
            requirements_file = sample_tool_structure / 'requirements.txt'
            result = dm._are_python_deps_satisfied('sample-tool', requirements_file)
            
            assert result is False
    
    def test_is_dependency_satisfied_cached(self, temp_opskit_dir, sample_dependencies_config, mock_platform_utils):
        """Test dependency satisfaction check with caching"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir, debug=True)
            
            # First call should check and cache
            result1 = dm._is_dependency_satisfied('curl')
            
            # Second call should use cache
            result2 = dm._is_dependency_satisfied('curl')
            
            assert result1 is True
            assert result2 is True
            assert 'curl' in dm._system_deps_cache
    
    def test_clear_dependency_cache(self, temp_opskit_dir, mock_platform_utils):
        """Test clearing dependency cache"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir, debug=True)
            
            # Add something to cache
            dm._system_deps_cache['test'] = True
            dm._last_cache_time = 123456
            
            dm.clear_dependency_cache()
            
            assert dm._system_deps_cache == {}
            assert dm._last_cache_time == 0
    
    def test_get_cache_status(self, temp_opskit_dir, mock_platform_utils):
        """Test getting cache status information"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir)
            
            # Add test data to cache
            dm._system_deps_cache = {'curl': True, 'mysql-client': False}
            dm._last_cache_time = 1234567890
            
            with patch('time.time', return_value=1234567950):  # 60 seconds later
                status = dm.get_cache_status()
            
            assert 'cached_dependencies' in status
            assert 'cache_age_seconds' in status
            assert 'cache_valid' in status
            assert status['cached_dependencies'] == ['curl', 'mysql-client']
            assert status['cache_age_seconds'] == 60
            assert status['cache_valid'] is True  # Less than 300 seconds
    
    @patch('subprocess.run')
    def test_validate_venv_integrity_healthy(self, mock_subprocess, temp_opskit_dir, mock_platform_utils):
        """Test validating healthy virtual environment"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir)
            
            # Create mock venv structure
            venv_dir = dm.venvs_dir / 'test-tool'
            venv_dir.mkdir(parents=True)
            bin_dir = venv_dir / 'bin'
            bin_dir.mkdir()
            python_exe = bin_dir / 'python'
            python_exe.write_text("#!/usr/bin/env python3")
            python_exe.chmod(0o755)
            
            # Mock successful subprocess calls
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "pip 21.2.4"
            mock_subprocess.return_value = mock_result
            
            is_valid, message = dm.validate_venv_integrity('test-tool')
            
            assert is_valid is True
            assert "healthy" in message.lower()
    
    @patch('subprocess.run')
    def test_validate_venv_integrity_broken(self, mock_subprocess, temp_opskit_dir, mock_platform_utils):
        """Test validating broken virtual environment"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir)
            
            # Create mock venv structure without python executable
            venv_dir = dm.venvs_dir / 'test-tool'
            venv_dir.mkdir(parents=True)
            
            is_valid, message = dm.validate_venv_integrity('test-tool')
            
            assert is_valid is False
            assert "missing" in message.lower()
    
    def test_check_tool_dependencies_all_satisfied(self, temp_opskit_dir, sample_tool_structure, 
                                                 sample_dependencies_config, mock_platform_utils):
        """Test checking tool dependencies when all are satisfied"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir)
            
            # Create tool info
            tool_info = {
                'name': 'sample-tool',
                'path': sample_tool_structure,
                'type': 'python',
                'dependencies': ['curl']
            }
            
            # Mock that all dependencies are satisfied
            with patch.object(dm, '_are_python_deps_satisfied', return_value=True):
                status = dm.check_tool_dependencies(tool_info)
            
            assert status['python_deps_satisfied'] is True
            assert status['system_deps_satisfied'] is True
            assert not status['missing_python_deps']
            assert not status['missing_system_deps']
    
    def test_setup_tool_dependencies_python_tool(self, temp_opskit_dir, sample_tool_structure,
                                                sample_dependencies_config, mock_platform_utils):
        """Test setting up dependencies for Python tool"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir, debug=True)
            
            tool_info = {
                'name': 'sample-tool',
                'path': sample_tool_structure,
                'type': 'python',
                'dependencies': []
            }
            
            with patch.object(dm, 'setup_python_environment', return_value=(True, "Success")):
                success, message = dm.setup_tool_dependencies(tool_info)
                
                assert success is True
                assert "success" in message.lower()

@pytest.mark.integration
class TestDependencyManagerIntegration:
    """Integration tests for DependencyManager with real file system operations"""
    
    def test_full_python_environment_setup(self, temp_opskit_dir, sample_tool_structure, mock_platform_utils):
        """Test complete Python environment setup with real venv creation"""
        with patch('dependency_manager.PlatformUtils', return_value=mock_platform_utils):
            dm = DependencyManager(base_path=temp_opskit_dir, debug=True)
            
            # This test will actually create a venv but we'll mock pip operations
            with patch('subprocess.run') as mock_subprocess:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "Successfully installed requests"
                mock_subprocess.return_value = mock_result
                
                success, message = dm.setup_python_environment('sample-tool', sample_tool_structure)
                
                # Check that venv was created
                venv_path = dm.venvs_dir / 'sample-tool'
                assert venv_path.exists()
                assert success is True
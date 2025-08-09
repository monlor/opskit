"""Tests for platform_utils.py"""

import pytest
import platform
import subprocess
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from core.platform_utils import PlatformUtils


class TestPlatformUtils:
    """Test cases for PlatformUtils"""
    
    def test_get_platform_info_darwin(self):
        """Test platform info detection on macOS"""
        with patch('platform.system', return_value='Darwin'), \
             patch('platform.machine', return_value='arm64'), \
             patch('platform.mac_ver', return_value=('13.4.1', ('', '', ''), 'arm64')):
            
            result = PlatformUtils.get_platform_info()
            assert "macOS 13.4.1 (arm64)" == result
    
    def test_get_platform_info_linux_with_distro(self):
        """Test platform info detection on Linux with distro module"""
        with patch('platform.system', return_value='Linux'), \
             patch('platform.machine', return_value='x86_64'), \
             patch('platform_utils.distro') as mock_distro:
            
            mock_distro.name.return_value = 'Ubuntu'
            mock_distro.version.return_value = '22.04'
            
            result = PlatformUtils.get_platform_info()
            assert "Ubuntu 22.04 (x86_64)" == result
    
    def test_get_platform_info_linux_without_distro(self):
        """Test platform info detection on Linux without distro module"""
        with patch('platform.system', return_value='Linux'), \
             patch('platform.machine', return_value='x86_64'), \
             patch('platform_utils.distro', None):
            
            result = PlatformUtils.get_platform_info()
            assert "Linux (x86_64)" == result
    
    def test_get_os_type_darwin(self):
        """Test OS type detection for macOS"""
        with patch('platform.system', return_value='Darwin'):
            result = PlatformUtils.get_os_type()
            assert result == 'darwin'
    
    def test_get_os_type_linux(self):
        """Test OS type detection for Linux"""
        with patch('platform.system', return_value='Linux'):
            result = PlatformUtils.get_os_type()
            assert result == 'linux'
    
    def test_get_linux_distribution_with_distro(self):
        """Test Linux distribution detection with distro module"""
        with patch('platform.system', return_value='Linux'), \
             patch('platform_utils.distro') as mock_distro:
            
            mock_distro.id.return_value = 'Ubuntu'
            
            result = PlatformUtils.get_linux_distribution()
            assert result == 'ubuntu'
    
    def test_get_linux_distribution_without_distro(self):
        """Test Linux distribution detection without distro module"""
        os_release_content = '''NAME="Ubuntu"
VERSION="22.04.3 LTS"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 22.04.3 LTS"
VERSION_ID="22.04"'''
        
        with patch('platform.system', return_value='Linux'), \
             patch('platform_utils.distro', None), \
             patch('builtins.open', mock_open(read_data=os_release_content)):
            
            result = PlatformUtils.get_linux_distribution()
            assert result == 'ubuntu'
    
    def test_get_linux_distribution_non_linux(self):
        """Test Linux distribution detection on non-Linux system"""
        with patch('platform.system', return_value='Darwin'):
            result = PlatformUtils.get_linux_distribution()
            assert result is None
    
    def test_command_exists_true(self):
        """Test command existence check for existing command"""
        with patch('shutil.which', return_value='/usr/bin/ls'):
            result = PlatformUtils.command_exists('ls')
            assert result is True
    
    def test_command_exists_false(self):
        """Test command existence check for non-existing command"""
        with patch('shutil.which', return_value=None):
            result = PlatformUtils.command_exists('nonexistent-command')
            assert result is False
    
    @patch('subprocess.run')
    def test_run_command_success(self, mock_subprocess):
        """Test successful command execution"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Success output"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        success, stdout, stderr = PlatformUtils.run_command(['echo', 'test'])
        
        assert success is True
        assert stdout == "Success output"
        assert stderr == ""
    
    @patch('subprocess.run')
    def test_run_command_failure(self, mock_subprocess):
        """Test failed command execution"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error occurred"
        mock_subprocess.return_value = mock_result
        
        success, stdout, stderr = PlatformUtils.run_command(['false'])
        
        assert success is False
        assert stdout == ""
        assert stderr == "Error occurred"
    
    @patch('subprocess.run')
    def test_run_command_timeout(self, mock_subprocess):
        """Test command execution timeout"""
        mock_subprocess.side_effect = subprocess.TimeoutExpired(['sleep', '10'], 5)
        
        success, stdout, stderr = PlatformUtils.run_command(['sleep', '10'], timeout=5)
        
        assert success is False
        assert stdout == ""
        assert "timed out" in stderr
    
    @patch('subprocess.run')
    def test_run_command_not_found(self, mock_subprocess):
        """Test command execution with non-existent command"""
        mock_subprocess.side_effect = FileNotFoundError()
        
        success, stdout, stderr = PlatformUtils.run_command(['nonexistent-command'])
        
        assert success is False
        assert stdout == ""
        assert "Command not found" in stderr
    
    def test_detect_available_package_managers_darwin(self):
        """Test package manager detection on macOS"""
        with patch.object(PlatformUtils, 'get_os_type', return_value='darwin'), \
             patch.object(PlatformUtils, 'command_exists') as mock_exists, \
             patch.object(PlatformUtils, 'run_command') as mock_run:
            
            # Mock brew exists and works
            mock_exists.side_effect = lambda cmd: cmd == 'brew'
            mock_run.return_value = (True, "Homebrew 4.0.0", "")
            
            result = PlatformUtils.detect_available_package_managers()
            assert 'brew' in result
    
    def test_detect_available_package_managers_linux(self):
        """Test package manager detection on Linux"""
        with patch.object(PlatformUtils, 'get_os_type', return_value='linux'), \
             patch.object(PlatformUtils, 'command_exists') as mock_exists, \
             patch.object(PlatformUtils, 'run_command') as mock_run:
            
            # Mock apt exists and works
            mock_exists.side_effect = lambda cmd: cmd == 'apt'
            mock_run.return_value = (True, "apt 2.4.9", "")
            
            result = PlatformUtils.detect_available_package_managers()
            assert 'apt' in result
    
    def test_get_preferred_package_manager_user_preference(self):
        """Test getting preferred package manager with user preference"""
        with patch.object(PlatformUtils, 'detect_available_package_managers', 
                         return_value=['apt', 'dnf']):
            
            result = PlatformUtils.get_preferred_package_manager(preference='dnf')
            assert result == 'dnf'
    
    def test_get_preferred_package_manager_auto_darwin(self):
        """Test auto-selection of package manager on macOS"""
        with patch.object(PlatformUtils, 'detect_available_package_managers', 
                         return_value=['brew', 'port']), \
             patch.object(PlatformUtils, 'get_os_type', return_value='darwin'):
            
            result = PlatformUtils.get_preferred_package_manager()
            assert result == 'brew'
    
    def test_get_preferred_package_manager_auto_ubuntu(self):
        """Test auto-selection of package manager on Ubuntu"""
        with patch.object(PlatformUtils, 'detect_available_package_managers', 
                         return_value=['apt', 'dnf']), \
             patch.object(PlatformUtils, 'get_os_type', return_value='linux'), \
             patch.object(PlatformUtils, 'get_linux_distribution', return_value='ubuntu'):
            
            result = PlatformUtils.get_preferred_package_manager()
            assert result == 'apt'
    
    @patch('builtins.print')
    def test_install_system_package_success(self, mock_print):
        """Test successful system package installation"""
        with patch.object(PlatformUtils, 'get_preferred_package_manager', return_value='apt'), \
             patch.object(PlatformUtils, 'get_os_type', return_value='linux'), \
             patch.object(PlatformUtils, 'run_command', 
                         return_value=(True, "Package installed", "")):
            
            success, message = PlatformUtils.install_system_package('curl')
            
            assert success is True
            assert "Successfully installed curl" == message
    
    def test_install_system_package_no_manager(self):
        """Test system package installation with no package manager"""
        with patch.object(PlatformUtils, 'get_preferred_package_manager', return_value=None):
            
            success, message = PlatformUtils.install_system_package('curl')
            
            assert success is False
            assert "No package manager available" == message
    
    def test_get_system_info_basic(self):
        """Test getting basic system information"""
        with patch.object(PlatformUtils, 'get_platform_info', return_value='Linux Ubuntu 22.04'), \
             patch.object(PlatformUtils, 'get_os_type', return_value='linux'), \
             patch.object(PlatformUtils, 'get_linux_distribution', return_value='ubuntu'), \
             patch.object(PlatformUtils, 'detect_available_package_managers', return_value=['apt']), \
             patch.object(PlatformUtils, 'get_preferred_package_manager', return_value='apt'), \
             patch('sys.version_info', Mock(major=3, minor=12, micro=0)), \
             patch('sys.executable', '/usr/bin/python3'):
            
            info = PlatformUtils.get_system_info()
            
            assert info['platform'] == 'Linux Ubuntu 22.04'
            assert info['os_type'] == 'linux'
            assert info['python_version'] == '3.12.0'
            assert info['distribution'] == 'ubuntu'
            assert info['package_managers'] == ['apt']
            assert info['preferred_package_manager'] == 'apt'
    
    def test_get_system_info_with_psutil(self):
        """Test getting system information with psutil available"""
        mock_psutil = Mock()
        mock_psutil.cpu_count.return_value = 8
        mock_memory = Mock()
        mock_memory.total = 16 * 1024**3  # 16 GB
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_disk = Mock()
        mock_disk.free = 500 * 1024**3  # 500 GB
        mock_psutil.disk_usage.return_value = mock_disk
        
        with patch.object(PlatformUtils, 'get_platform_info', return_value='Linux'), \
             patch.object(PlatformUtils, 'get_os_type', return_value='linux'), \
             patch.object(PlatformUtils, 'detect_available_package_managers', return_value=[]), \
             patch.object(PlatformUtils, 'get_preferred_package_manager', return_value=None), \
             patch('platform_utils.psutil', mock_psutil):
            
            info = PlatformUtils.get_system_info()
            
            assert info['cpu_count'] == '8'
            assert info['memory_gb'] == '16.0'
            assert info['disk_free_gb'] == '500.0'
    
    def test_create_script_wrapper_success(self, tmp_path):
        """Test successful script wrapper creation"""
        script_path = tmp_path / 'test_script.py'
        script_path.write_text('print("Hello World")')
        target_dir = tmp_path / 'wrappers'
        
        result = PlatformUtils.create_script_wrapper(str(script_path), str(target_dir))
        
        assert result is True
        wrapper_path = target_dir / 'test_script'
        assert wrapper_path.exists()
        assert wrapper_path.stat().st_mode & 0o111  # Check executable bit
    
    def test_get_shell_rc_files(self, tmp_path):
        """Test getting shell RC files"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            # Create some RC files
            (tmp_path / '.bashrc').write_text('# bashrc')
            (tmp_path / '.zshrc').write_text('# zshrc')
            
            rc_files = PlatformUtils.get_shell_rc_files()
            
            assert len(rc_files) >= 2
            assert any('.bashrc' in f for f in rc_files)
            assert any('.zshrc' in f for f in rc_files)
    
    def test_add_to_path_already_exists(self):
        """Test adding directory to PATH when it already exists"""
        test_dir = '/test/directory'
        
        with patch.dict('os.environ', {'PATH': f'/usr/bin:{test_dir}:/bin'}):
            result = PlatformUtils.add_to_path(test_dir)
            assert result is True
    
    def test_add_to_path_new_directory(self, tmp_path):
        """Test adding new directory to PATH"""
        test_dir = str(tmp_path / 'test_dir')
        rc_file = tmp_path / '.bashrc'
        rc_file.write_text('# existing bashrc content')
        
        with patch.dict('os.environ', {'PATH': '/usr/bin:/bin'}, clear=False), \
             patch.object(PlatformUtils, 'get_shell_rc_files', return_value=[str(rc_file)]):
            
            result = PlatformUtils.add_to_path(test_dir)
            
            assert result is True
            assert test_dir in os.environ['PATH']
            
            # Check if RC file was updated
            content = rc_file.read_text()
            assert f'export PATH="{test_dir}:$PATH"' in content
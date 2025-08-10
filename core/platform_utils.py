"""
Platform Utilities Module

Provides cross-platform compatibility utilities including:
- OS detection and system information
- Package manager detection and adaptation  
- System command execution
- Path and environment handling
"""

import os
import sys
import platform
import subprocess
import shutil
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    import distro
except ImportError:
    distro = None

try:
    import psutil
except ImportError:
    psutil = None


class PlatformUtils:
    """Platform-specific utility functions"""
    
    # Package managers mapping by OS type
    PACKAGE_MANAGERS = {
        'darwin': {
            'brew': {
                'check': ['brew', '--version'],
                'install': 'brew install {}',
                'search': 'brew search {}',
                'info': 'brew info {}',
                'list': 'brew list',
                'is_installed': 'brew list --formula --versions {}',
                'query': 'brew list | grep -E "^{}$"',
                'parser': {
                    'exclude_prefixes': ['='],
                    'field_index': 0
                }
            },
            'port': {
                'check': ['port', 'version'],
                'install': 'sudo port install {}',
                'search': 'port search {}',
                'info': 'port info {}',
                'list': 'port installed',
                'is_installed': 'port installed {}',
                'query': 'port installed {} | grep -v "No ports"',
                'parser': {
                    'field_index': 0,
                    'suffix_removal': [' @']
                }
            }
        },
        'linux': {
            'apt': {
                'check': ['apt', '--version'],
                'install': 'sudo apt-get install -y {}',
                'search': 'apt search {}',
                'info': 'apt show {}',
                'list': 'dpkg -l',
                'is_installed': 'dpkg -l {} 2>/dev/null | grep -q "^ii"',
                'query': 'dpkg -l {} 2>/dev/null | grep "^ii"',
                'parser': {
                    'line_prefix': 'ii ',
                    'field_index': 1,
                    'suffix_removal': [':']
                }
            },
            'yum': {
                'check': ['yum', '--version'],
                'install': 'sudo yum install -y {}',
                'search': 'yum search {}',
                'info': 'yum info {}',
                'list': 'yum list installed',
                'is_installed': 'yum list installed {} &>/dev/null',
                'query': 'rpm -q {}',
                'parser': {
                    'exclude_prefixes': ['Installed', 'Last'],
                    'field_index': 0,
                    'suffix_removal': ['.']
                }
            },
            'dnf': {
                'check': ['dnf', '--version'],
                'install': 'sudo dnf install -y {}',
                'search': 'dnf search {}',
                'info': 'dnf info {}',
                'list': 'dnf list installed',
                'is_installed': 'dnf list installed {} &>/dev/null',
                'query': 'rpm -q {}',
                'parser': {
                    'exclude_prefixes': ['Installed', 'Last'],
                    'field_index': 0,
                    'suffix_removal': ['.']
                }
            },
            'pacman': {
                'check': ['pacman', '--version'],
                'install': 'sudo pacman -S --noconfirm {}',
                'search': 'pacman -Ss {}',
                'info': 'pacman -Si {}',
                'list': 'pacman -Q',
                'is_installed': 'pacman -Q {} &>/dev/null',
                'query': 'pacman -Q {}',
                'parser': {
                    'field_index': 0
                }
            },
            'zypper': {
                'check': ['zypper', '--version'],
                'install': 'sudo zypper install -y {}',
                'search': 'zypper search {}',
                'info': 'zypper info {}',
                'list': 'zypper pa --installed-only',
                'is_installed': 'zypper se --installed-only {} | grep -q "^i"',
                'query': 'rpm -q {}',
                'parser': {
                    'line_prefix': 'i ',
                    'separator': '|',
                    'field_index': 1
                }
            },
            'snap': {
                'check': ['snap', '--version'],
                'install': 'sudo snap install {}',
                'search': 'snap find {}',
                'info': 'snap info {}',
                'list': 'snap list',
                'is_installed': 'snap list {} &>/dev/null',
                'query': 'snap list {}',
                'parser': {
                    'skip_lines': 1,
                    'field_index': 0
                }
            },
            'flatpak': {
                'check': ['flatpak', '--version'],
                'install': 'flatpak install -y {}',
                'search': 'flatpak search {}',
                'info': 'flatpak info {}',
                'list': 'flatpak list',
                'is_installed': 'flatpak list | grep -q {}',
                'query': 'flatpak list | grep {}',
                'parser': {
                    'skip_lines': 1,
                    'field_index': 0
                }
            },
            'apk': {
                'check': ['apk', '--version'],
                'install': 'sudo apk add {}',
                'search': 'apk search {}',
                'info': 'apk info {}',
                'list': 'apk list --installed',
                'is_installed': 'apk list --installed {} | grep -q {}',
                'query': 'apk list --installed {}',
                'parser': {
                    'field_index': 0,
                    'suffix_removal': ['-']
                }
            }
        },
        'freebsd': {
            'pkg': {
                'check': ['pkg', '--version'],
                'install': 'sudo pkg install -y {}',
                'search': 'pkg search {}',
                'info': 'pkg info {}',
                'list': 'pkg info',
                'is_installed': 'pkg info {} &>/dev/null',
                'query': 'pkg info {}',
                'parser': {
                    'field_index': 0,
                    'suffix_removal': ['-']
                }
            }
        }
    }
    
    @classmethod
    def get_platform_info(cls) -> str:
        """Get detailed platform information"""
        try:
            system = platform.system()
            machine = platform.machine()
            
            if system == 'Darwin':
                version = platform.mac_ver()[0]
                return f"macOS {version} ({machine})"
            elif system == 'Linux':
                if distro:
                    dist_name = distro.name()
                    dist_version = distro.version()
                    return f"{dist_name} {dist_version} ({machine})"
                else:
                    return f"Linux ({machine})"
            else:
                return f"{system} ({machine})"
        except Exception:
            return "Unknown platform"
    
    @classmethod
    def get_os_type(cls) -> str:
        """Get normalized OS type"""
        system = platform.system().lower()
        if system == 'darwin':
            return 'darwin'
        elif system == 'linux':
            return 'linux'
        elif system == 'freebsd':
            return 'freebsd'
        else:
            return system
    
    @classmethod
    def get_linux_distribution(cls) -> Optional[str]:
        """Get Linux distribution name"""
        if platform.system() != 'Linux':
            return None
        
        if distro:
            return distro.id().lower()
        
        # Fallback method
        try:
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('ID='):
                        return line.split('=')[1].strip().strip('"').lower()
        except Exception:
            pass
        
        return None
    
    @classmethod
    def command_exists(cls, command: str) -> bool:
        """Check if a command exists in system PATH"""
        return shutil.which(command) is not None
    
    @classmethod
    def run_command(cls, command: List[str], timeout: int = 30, 
                   capture_output: bool = True) -> Tuple[bool, str, str]:
        """
        Run a system command
        
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False
            )
            return (
                result.returncode == 0,
                result.stdout if capture_output else "",
                result.stderr if capture_output else ""
            )
        except subprocess.TimeoutExpired:
            return (False, "", f"Command timed out after {timeout} seconds")
        except FileNotFoundError:
            return (False, "", f"Command not found: {command[0]}")
        except Exception as e:
            return (False, "", str(e))
    
    @classmethod
    def detect_available_package_managers(cls) -> List[str]:
        """Detect available package managers on the system"""
        os_type = cls.get_os_type()
        available = []
        
        managers = cls.PACKAGE_MANAGERS.get(os_type, {})
        
        for manager_name, manager_config in managers.items():
            check_command = manager_config.get('check')
            if check_command and cls.command_exists(check_command[0]):
                # Verify the manager actually works
                success, _, _ = cls.run_command(check_command, timeout=5)
                if success:
                    available.append(manager_name)
        
        return available
    
    @classmethod
    def get_preferred_package_manager(cls, preference: Optional[str] = None) -> Optional[str]:
        """
        Get the preferred package manager
        
        Args:
            preference: User's preferred manager, or None for auto-detection
        """
        available = cls.detect_available_package_managers()
        
        if not available:
            return None
        
        # If user specified a preference and it's available, use it
        if preference and preference in available:
            return preference
        
        # Auto-selection based on OS and distribution
        os_type = cls.get_os_type()
        
        if os_type == 'darwin':
            # Prefer Homebrew on macOS
            return 'brew' if 'brew' in available else available[0]
        
        elif os_type == 'linux':
            distro_name = cls.get_linux_distribution()
            
            # Distribution-specific preferences
            if distro_name in ['ubuntu', 'debian'] and 'apt' in available:
                return 'apt'
            elif distro_name in ['centos', 'rhel', 'fedora']:
                if 'dnf' in available:
                    return 'dnf'
                elif 'yum' in available:
                    return 'yum'
            elif distro_name == 'arch' and 'pacman' in available:
                return 'pacman'
            elif distro_name in ['opensuse', 'sle'] and 'zypper' in available:
                return 'zypper'
            
            # Fallback to first available
            return available[0]
        
        return available[0] if available else None
    
    @classmethod
    def is_package_installed(cls, package_name: str, 
                           package_manager: Optional[str] = None) -> bool:
        """
        Check if a system package is installed using the appropriate package manager
        
        Args:
            package_name: Name of the package to check
            package_manager: Specific package manager to use (auto-detect if None)
        
        Returns:
            True if package is installed, False otherwise
        """
        if not package_manager:
            package_manager = cls.get_preferred_package_manager()
        
        if not package_manager:
            return False
        
        os_type = cls.get_os_type()
        managers = cls.PACKAGE_MANAGERS.get(os_type, {})
        manager_config = managers.get(package_manager)
        
        if not manager_config or 'is_installed' not in manager_config:
            return False
        
        check_command = manager_config['is_installed'].format(package_name)
        
        # Handle shell commands with pipes and redirects
        if '|' in check_command or '&>' in check_command or '2>' in check_command:
            # Execute as shell command
            success, _, _ = cls.run_command(['sh', '-c', check_command], timeout=10)
        else:
            # Execute as regular command
            command_parts = check_command.split()
            success, _, _ = cls.run_command(command_parts, timeout=10)
        
        return success

    @classmethod
    def get_installed_packages(cls, package_manager: Optional[str] = None) -> List[str]:
        """
        Get list of all installed packages
        
        Args:
            package_manager: Specific package manager to use (auto-detect if None)
        
        Returns:
            List of installed package names
        """
        if not package_manager:
            package_manager = cls.get_preferred_package_manager()
        
        if not package_manager:
            return []
        
        os_type = cls.get_os_type()
        managers = cls.PACKAGE_MANAGERS.get(os_type, {})
        manager_config = managers.get(package_manager)
        
        if not manager_config or 'list' not in manager_config:
            return []
        
        list_command = manager_config['list']
        command_parts = list_command.split()
        
        success, stdout, _ = cls.run_command(command_parts, timeout=30)
        
        if not success or not stdout:
            return []
        
        # Parse package names using manager configuration
        os_type = cls.get_os_type()
        managers = cls.PACKAGE_MANAGERS.get(os_type, {})
        manager_config = managers.get(package_manager, {})
        
        packages = []
        lines = stdout.strip().split('\n')
        
        # Use configured parser rules
        packages = cls._parse_package_list(lines, manager_config)
        
        return packages

    @classmethod
    def _parse_package_list(cls, lines: List[str], manager_config: Dict) -> List[str]:
        """Parse package list using manager configuration"""
        if not manager_config:
            return []
        
        packages = []
        parser = manager_config.get('parser', {})
        
        skip_lines = parser.get('skip_lines', 0)
        line_prefix = parser.get('line_prefix', '')
        exclude_prefixes = parser.get('exclude_prefixes', [])
        field_index = parser.get('field_index', 0)
        separator = parser.get('separator', None)
        suffix_removal = parser.get('suffix_removal', [])
        
        for i, line in enumerate(lines):
            if i < skip_lines or not line.strip():
                continue
                
            if line_prefix and not line.startswith(line_prefix):
                continue
                
            if any(line.startswith(prefix) for prefix in exclude_prefixes):
                continue
            
            # Extract package name
            parts = line.split(separator) if separator else line.split()
            
            if len(parts) > field_index:
                package_name = parts[field_index].strip()
                
                # Remove suffixes (architecture, version, etc.)
                for suffix in suffix_removal:
                    if suffix in package_name:
                        package_name = package_name.split(suffix)[0]
                
                if package_name:
                    packages.append(package_name)
        
        return packages

    @classmethod
    def install_system_package(cls, package_name: str, 
                             package_manager: Optional[str] = None, 
                             force_install: bool = False) -> Tuple[bool, str]:
        """
        Install a system package using the appropriate package manager
        
        Args:
            package_name: Name of the package to install
            package_manager: Specific package manager to use (auto-detect if None)
            force_install: Skip package existence check and force installation
        
        Returns:
            Tuple of (success, message)
        """
        if not package_manager:
            package_manager = cls.get_preferred_package_manager()
        
        if not package_manager:
            return (False, "No package manager available")
        
        # Check if package is already installed (unless forced)
        if not force_install and cls.is_package_installed(package_name, package_manager):
            return (True, f"Package {package_name} is already installed")
        
        os_type = cls.get_os_type()
        managers = cls.PACKAGE_MANAGERS.get(os_type, {})
        manager_config = managers.get(package_manager)
        
        if not manager_config:
            return (False, f"Unsupported package manager: {package_manager}")
        
        install_command = manager_config['install'].format(package_name)
        command_parts = install_command.split()
        
        print(f"Installing {package_name} using {package_manager}...")
        success, stdout, stderr = cls.run_command(command_parts, timeout=300)
        
        if success:
            return (True, f"Successfully installed {package_name}")
        else:
            error_msg = stderr or stdout or "Installation failed"
            return (False, f"Failed to install {package_name}: {error_msg}")
    
    @classmethod
    def get_system_info(cls) -> Dict[str, str]:
        """Get comprehensive system information"""
        info = {
            'platform': cls.get_platform_info(),
            'os_type': cls.get_os_type(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'python_executable': sys.executable,
        }
        
        # Add Linux distribution info
        if cls.get_os_type() == 'linux':
            info['distribution'] = cls.get_linux_distribution() or 'unknown'
        
        # Add package managers info
        info['package_managers'] = cls.detect_available_package_managers()
        info['preferred_package_manager'] = cls.get_preferred_package_manager()
        
        # Add system resources if psutil is available
        if psutil:
            try:
                info['cpu_count'] = str(psutil.cpu_count())
                info['memory_gb'] = f"{psutil.virtual_memory().total / (1024**3):.1f}"
                info['disk_free_gb'] = f"{psutil.disk_usage('/').free / (1024**3):.1f}"
            except Exception:
                pass
        
        return info
    
    @classmethod
    def create_script_wrapper(cls, script_path: str, target_dir: str) -> bool:
        """
        Create a wrapper script for easier execution
        
        Args:
            script_path: Path to the original script
            target_dir: Directory to create the wrapper in
        
        Returns:
            True if wrapper was created successfully
        """
        try:
            script_path = Path(script_path).resolve()
            target_dir = Path(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            wrapper_path = target_dir / script_path.stem
            
            # Create shell wrapper
            wrapper_content = f'''#!/bin/bash
# OpsKit tool wrapper for {script_path.name}
# Generated automatically - do not edit

TOOL_DIR="$(dirname "$(readlink -f "$0")")"
OPSKIT_ROOT="$(dirname "$TOOL_DIR")"

# Set environment
export OPSKIT_HOME="$OPSKIT_ROOT"
export PYTHONPATH="$OPSKIT_ROOT:$PYTHONPATH"

# Run the tool
exec "{sys.executable}" "{script_path}" "$@"
'''
            
            with open(wrapper_path, 'w') as f:
                f.write(wrapper_content)
            
            # Make executable
            os.chmod(wrapper_path, 0o755)
            
            return True
            
        except Exception:
            return False
    
    @classmethod
    def get_shell_rc_files(cls) -> List[str]:
        """Get list of shell RC files that might need PATH updates"""
        home = Path.home()
        rc_files = []
        
        # Common shell RC files
        candidates = [
            '.bashrc',
            '.bash_profile', 
            '.zshrc',
            '.profile',
            '.zprofile'
        ]
        
        for candidate in candidates:
            rc_file = home / candidate
            if rc_file.exists():
                rc_files.append(str(rc_file))
        
        return rc_files
    
    @classmethod
    def add_to_path(cls, directory: str) -> bool:
        """
        Add directory to system PATH (persistent)
        
        Returns:
            True if PATH was updated successfully
        """
        try:
            directory = str(Path(directory).resolve())
            
            # Check if already in PATH
            current_path = os.environ.get('PATH', '')
            if directory in current_path.split(':'):
                return True
            
            # Update current session
            os.environ['PATH'] = f"{directory}:{current_path}"
            
            # Add to shell RC files for persistence
            export_line = f'export PATH="{directory}:$PATH"'
            rc_files = cls.get_shell_rc_files()
            
            for rc_file in rc_files[:1]:  # Only update the first one found
                try:
                    with open(rc_file, 'r') as f:
                        content = f.read()
                    
                    if export_line not in content:
                        with open(rc_file, 'a') as f:
                            f.write(f'\n# Added by OpsKit\n{export_line}\n')
                    
                    return True
                except Exception:
                    continue
            
            return False
            
        except Exception:
            return False
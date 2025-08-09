"""
Dependency Manager

Handles automatic dependency installation for tools:
- Python virtual environments and pip packages
- System dependency detection and installation guidance
- Caching and version management
"""

import os
import sys
import subprocess
import venv
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import yaml

from .platform_utils import PlatformUtils


class DependencyManager:
    """Manages tool dependencies automatically"""
    
    def __init__(self, opskit_root: Path, debug: bool = False):
        """Initialize dependency manager"""
        self.opskit_root = opskit_root
        self.debug = debug
        self.cache_dir = opskit_root / 'cache'
        self.venvs_dir = self.cache_dir / 'venvs'
        self.pip_cache_dir = self.cache_dir / 'pip_cache'
        
        # Create directories
        self.venvs_dir.mkdir(parents=True, exist_ok=True)
        self.pip_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Platform utilities
        self.platform_utils = PlatformUtils()
        
        # Load dependency configuration
        self.dependencies_config = self._load_dependencies_config()
        
        # Cache for system dependency checks (avoid repeated checks)
        self._system_deps_cache = {}
        self._last_cache_time = 0
    
    def _load_dependencies_config(self) -> Dict:
        """Load system dependencies configuration from YAML"""
        config_file = self.opskit_root / 'config' / 'dependencies.yaml'
        
        if not config_file.exists():
            if self.debug:
                print(f"Dependencies config not found: {config_file}")
            return {}
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config or {}
        except Exception as e:
            if self.debug:
                print(f"Failed to load dependencies config: {e}")
            return {}
    
    def ensure_tool_dependencies(self, tool_info: Dict) -> Tuple[bool, str]:
        """
        Ensure all dependencies for a tool are available
        
        Returns:
            (success, error_message)
        """
        tool_name = tool_info['name']
        tool_path = Path(tool_info['path'])
        
        try:
            # Check Python dependencies
            if tool_info.get('has_python_deps', False):
                success, message = self._ensure_python_dependencies(tool_name, tool_path)
                if not success:
                    return False, f"Python dependencies failed: {message}"
            
            # Check and install system dependencies
            missing_deps = self._check_system_dependencies(tool_info)
            if missing_deps:
                # Try to install missing dependencies
                installed, failed = self._install_system_dependencies(missing_deps)
                if failed:
                    return False, f"Missing system dependencies: {', '.join(failed)}"
            
            return True, "All dependencies satisfied"
        
        except Exception as e:
            return False, f"Dependency check failed: {e}"
    
    def _ensure_python_dependencies(self, tool_name: str, tool_path: Path) -> Tuple[bool, str]:
        """Ensure Python dependencies are installed in virtual environment"""
        requirements_file = tool_path / 'requirements.txt'
        
        if not requirements_file.exists():
            return True, "No requirements.txt found"
        
        venv_path = self.venvs_dir / tool_name
        
        try:
            # Create virtual environment if it doesn't exist
            if not venv_path.exists():
                if self.debug:
                    print(f"Creating virtual environment for {tool_name}...")
                
                venv.create(venv_path, with_pip=True, clear=True)
            else:
                # Check if dependencies are already satisfied
                if self._are_python_deps_satisfied(tool_name, requirements_file):
                    if self.debug:
                        print(f"Python dependencies already satisfied for {tool_name}")
                    return True, "Dependencies already installed"
            
            # Get pip executable path
            if os.name == 'nt':  # Windows
                pip_exe = venv_path / 'Scripts' / 'pip.exe'
                python_exe = venv_path / 'Scripts' / 'python.exe'
            else:  # Unix-like
                pip_exe = venv_path / 'bin' / 'pip'
                python_exe = venv_path / 'bin' / 'python'
            
            if not pip_exe.exists():
                return False, f"pip not found in virtual environment: {pip_exe}"
            
            # Install core requirements first (needed for common libraries)
            core_requirements = self.opskit_root / 'requirements.txt'
            if core_requirements.exists():
                if self.debug:
                    print(f"Installing core requirements for {tool_name}...")
                
                cmd = [
                    str(pip_exe), 'install',
                    '--cache-dir', str(self.pip_cache_dir),
                    '--requirement', str(core_requirements),
                    '--quiet'
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode != 0:
                    return False, f"Core requirements install failed: {result.stderr}"
            
            # Install tool-specific requirements
            if self.debug:
                print(f"Installing tool requirements for {tool_name}...")
            
            cmd = [
                str(pip_exe), 'install',
                '--cache-dir', str(self.pip_cache_dir),
                '--requirement', str(requirements_file),
                '--quiet'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                return False, f"Tool requirements install failed: {result.stderr}"
            
            if self.debug:
                print(f"Dependencies installed successfully for {tool_name}")
            
            return True, "Dependencies installed successfully"
        
        except subprocess.TimeoutExpired:
            return False, "pip install timed out"
        except Exception as e:
            return False, f"Failed to setup Python environment: {e}"
    
    def _are_python_deps_satisfied(self, tool_name: str, requirements_file: Path) -> bool:
        """Check if Python dependencies are already satisfied in virtual environment"""
        try:
            python_exe = self.get_tool_python_executable(tool_name)
            if not python_exe or not python_exe.exists():
                return False
            
            # Use pip list to get all installed packages (more reliable than import checks)
            cmd = [str(python_exe), '-m', 'pip', 'list', '--format=json']
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    return False
                
                installed_packages = json.loads(result.stdout)
                installed_dict = {pkg['name'].lower().replace('-', '_'): pkg['version'] 
                                for pkg in installed_packages}
            except Exception as e:
                if self.debug:
                    print(f"Failed to get installed packages list: {e}")
                return False
            
            # Parse requirements.txt to get required packages
            with open(requirements_file, 'r', encoding='utf-8') as f:
                requirements = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-') and not line.startswith('http'):
                        # Extract package name (before version specifiers)
                        import re
                        # Split on version specifiers but keep only the package name
                        pkg_match = re.match(r'^([a-zA-Z0-9_\-\.]+)', line)
                        if pkg_match:
                            pkg_name = pkg_match.group(1).lower().replace('-', '_')
                            requirements.append(pkg_name)
            
            if not requirements:
                return True  # No requirements to check
            
            # Check each required package
            missing_packages = []
            for pkg_name in requirements:
                if pkg_name not in installed_dict:
                    missing_packages.append(pkg_name)
            
            if missing_packages:
                if self.debug:
                    print(f"Missing packages in venv for {tool_name}: {missing_packages}")
                return False
            
            if self.debug:
                print(f"All Python dependencies satisfied for {tool_name}")
            return True
        
        except Exception as e:
            if self.debug:
                print(f"Error checking Python dependencies: {e}")
            return False
    
    def _check_system_dependencies(self, tool_info: Dict) -> List[str]:
        """Check for missing system dependencies specific to this tool"""
        missing_deps = []
        tool_path = Path(tool_info['path'])
        
        # First check for tool-specific dependency file
        deps_file = tool_path / 'system_deps.txt'
        if deps_file.exists():
            try:
                with open(deps_file, 'r', encoding='utf-8') as f:
                    required_deps = [line.strip() for line in f.readlines() 
                                   if line.strip() and not line.startswith('#')]
                return [dep for dep in required_deps 
                       if not self._is_dependency_satisfied(dep)]
            except Exception:
                pass
        
        # Fallback: analyze tool content for specific dependencies
        if not self.dependencies_config:
            return missing_deps
            
        main_file = tool_path / tool_info['main_file']
        if not main_file.exists():
            return missing_deps
        
        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            system_deps = self.dependencies_config.get('system_dependencies', {})
            
            # Only check dependencies whose commands appear in the tool's content
            for dep_name, dep_config in system_deps.items():
                commands = dep_config.get('commands', [])
                if commands:
                    # Check if any command from this dependency appears in the tool content
                    if any(cmd in content for cmd in commands):
                        # Check if the dependency is actually missing
                        if not self._is_dependency_satisfied(dep_name):
                            missing_deps.append(dep_name)
        
        except Exception:
            pass
        
        return missing_deps
    
    def _is_dependency_satisfied(self, dep_name: str) -> bool:
        """Check if a dependency is satisfied (with caching)"""
        if not self.dependencies_config:
            return True
        
        import time
        current_time = time.time()
        cache_duration = 300  # 5 minutes cache
        
        # Check cache first
        if (dep_name in self._system_deps_cache and 
            current_time - self._last_cache_time < cache_duration):
            if self.debug:
                print(f"Using cached result for dependency {dep_name}")
            return self._system_deps_cache[dep_name]
            
        system_deps = self.dependencies_config.get('system_dependencies', {})
        dep_config = system_deps.get(dep_name, {})
        commands = dep_config.get('commands', [])
        
        if not commands:
            result = True
        else:
            # Dependency is satisfied if ALL required commands exist
            result = all(self.platform_utils.command_exists(cmd) for cmd in commands)
        
        # Cache the result
        self._system_deps_cache[dep_name] = result
        self._last_cache_time = current_time
        
        if self.debug:
            print(f"Dependency {dep_name}: {'satisfied' if result else 'missing'}")
        
        return result
    
    def _install_system_dependencies(self, missing_deps: List[str]) -> Tuple[List[str], List[str]]:
        """Install missing system dependencies"""
        if not missing_deps or not self.dependencies_config:
            return [], missing_deps
        
        settings = self.dependencies_config.get('settings', {})
        auto_install = settings.get('auto_install', False)
        
        if not auto_install:
            self._show_install_guidance(missing_deps)
            return [], missing_deps
        
        installed, failed = [], []
        for dep_name in missing_deps:
            if self._install_dependency(dep_name):
                installed.append(dep_name)
            else:
                failed.append(dep_name)
        
        return installed, failed
    
    def _install_dependency(self, dep_name: str) -> bool:
        """Install a single dependency"""
        system_deps = self.dependencies_config.get('system_dependencies', {})
        dep_config = system_deps.get(dep_name, {})
        
        if not dep_config:
            return False
        
        # Get package name for current platform
        packages = dep_config.get('packages', {})
        os_type = self.platform_utils.get_os_type()
        
        if os_type == 'linux':
            distro = self.platform_utils.get_linux_distribution()
            package_name = packages.get(distro)
        elif os_type == 'darwin':
            package_name = packages.get('macos')
        else:
            package_name = packages.get(os_type)
        
        if not package_name:
            return False
        
        success, _ = self.platform_utils.install_system_package(package_name)
        
        # Clear cache for this dependency if installation was successful
        if success and dep_name in self._system_deps_cache:
            del self._system_deps_cache[dep_name]
            if self.debug:
                print(f"Cleared cache for {dep_name} after installation")
        
        return success
    
    def _show_install_guidance(self, missing_deps: List[str]):
        """Show installation guidance"""
        if not missing_deps:
            return
        
        print(f"\nError: Missing system dependencies: {', '.join(missing_deps)}")
        print("\nTo install the required dependencies:")
        
        system_deps = self.dependencies_config.get('system_dependencies', {})
        os_type = self.platform_utils.get_os_type()
        pm = self.platform_utils.get_preferred_package_manager()
        
        for dep_name in missing_deps:
            dep_config = system_deps.get(dep_name, {})
            packages = dep_config.get('packages', {})
            
            if os_type == 'linux':
                distro = self.platform_utils.get_linux_distribution()
                package = packages.get(distro)
            elif os_type == 'darwin':
                package = packages.get('macos')
            else:
                package = packages.get(os_type)
            
            if package and pm:
                managers = self.platform_utils.PACKAGE_MANAGERS.get(os_type, {})
                pm_config = managers.get(pm, {})
                install_cmd = pm_config.get('install', '').format(package)
                if install_cmd:
                    print(f"  {install_cmd}")
    
    def get_tool_python_executable(self, tool_name: str) -> Optional[Path]:
        """Get Python executable for a tool's virtual environment"""
        venv_path = self.venvs_dir / tool_name
        
        if os.name == 'nt':  # Windows
            python_exe = venv_path / 'Scripts' / 'python.exe'
        else:  # Unix-like
            python_exe = venv_path / 'bin' / 'python'
        
        return python_exe if python_exe.exists() else None
    
    def run_tool_with_dependencies(self, tool_info: Dict, args: List[str] = None) -> int:
        """
        Run a tool with proper dependency management
        
        Returns:
            Exit code from tool execution
        """
        tool_name = tool_info['name']
        tool_path = Path(tool_info['path'])
        main_file = tool_path / tool_info['main_file']
        
        if args is None:
            args = []
        
        try:
            # Ensure dependencies are available
            success, message = self.ensure_tool_dependencies(tool_info)
            if not success:
                print(f"Error: {message}")
                return 1
            
            # Prepare execution command
            if tool_info['type'] == 'python':
                # Use virtual environment Python if available
                python_exe = self.get_tool_python_executable(tool_name)
                if python_exe:
                    cmd = [str(python_exe), str(main_file)] + args
                else:
                    cmd = [sys.executable, str(main_file)] + args
            else:
                # Shell script
                cmd = [str(main_file)] + args
            
            # Change to tool directory
            original_cwd = os.getcwd()
            os.chdir(tool_path)
            
            try:
                if self.debug:
                    print(f"Executing: {' '.join(cmd)}")
                
                # Execute tool directly (inherits stdin/stdout/stderr)
                result = subprocess.run(cmd)
                return result.returncode
            
            finally:
                os.chdir(original_cwd)
        
        except Exception as e:
            print(f"Error running tool {tool_name}: {e}")
            return 1
    
    def clean_tool_cache(self, tool_name: str) -> bool:
        """Clean cache for a specific tool"""
        try:
            venv_path = self.venvs_dir / tool_name
            if venv_path.exists():
                shutil.rmtree(venv_path)
                return True
            return False
        except Exception:
            return False
    
    def clean_all_cache(self) -> bool:
        """Clean all dependency caches"""
        try:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self.venvs_dir.mkdir(parents=True, exist_ok=True)
                self.pip_cache_dir.mkdir(parents=True, exist_ok=True)
                return True
            return False
        except Exception:
            return False
    
    def get_dependency_status(self, tool_info: Dict) -> Dict:
        """Get dependency status for a tool"""
        tool_name = tool_info['name']
        tool_path = Path(tool_info['path'])
        
        status = {
            'tool_name': tool_name,
            'has_venv': False,
            'python_deps_satisfied': False,
            'system_deps_satisfied': True,
            'missing_system_deps': [],
            'venv_size': 0
        }
        
        # Check virtual environment
        venv_path = self.venvs_dir / tool_name
        if venv_path.exists():
            status['has_venv'] = True
            try:
                # Calculate venv size
                total_size = sum(f.stat().st_size for f in venv_path.rglob('*') if f.is_file())
                status['venv_size'] = total_size
            except Exception:
                pass
        
        # Check Python dependencies
        if tool_info.get('has_python_deps', False):
            python_exe = self.get_tool_python_executable(tool_name)
            if python_exe and python_exe.exists():
                status['python_deps_satisfied'] = True
        else:
            status['python_deps_satisfied'] = True  # No Python deps needed
        
        # Check system dependencies
        missing_deps = self._check_system_dependencies(tool_info)
        if missing_deps:
            status['system_deps_satisfied'] = False
            status['missing_system_deps'] = missing_deps
        
        return status
    
    def clear_dependency_cache(self):
        """Clear the system dependency cache"""
        self._system_deps_cache.clear()
        self._last_cache_time = 0
        if self.debug:
            print("System dependency cache cleared")
    
    def get_cache_status(self) -> Dict:
        """Get information about the current dependency cache"""
        import time
        current_time = time.time()
        cache_age = current_time - self._last_cache_time if self._last_cache_time > 0 else 0
        
        return {
            'cached_dependencies': list(self._system_deps_cache.keys()),
            'cache_age_seconds': cache_age,
            'cache_valid': cache_age < 300  # 5 minutes
        }
    
    def validate_venv_integrity(self, tool_name: str) -> Tuple[bool, str]:
        """Validate virtual environment integrity and suggest refresh if needed"""
        venv_path = self.venvs_dir / tool_name
        
        if not venv_path.exists():
            return False, "Virtual environment does not exist"
        
        try:
            python_exe = self.get_tool_python_executable(tool_name)
            if not python_exe or not python_exe.exists():
                return False, "Python executable missing in virtual environment"
            
            # Check if pip is working
            cmd = [str(python_exe), '-m', 'pip', '--version']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, "pip is not working in virtual environment"
            
            # Check if basic packages are importable
            cmd = [str(python_exe), '-c', 'import sys, os, json']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, "Basic Python modules not importable"
            
            return True, "Virtual environment is healthy"
        
        except Exception as e:
            return False, f"Validation failed: {e}"
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
import logging

from .platform_utils import PlatformUtils

# Note: Interactive functionality removed - tools should implement their own UI


class DependencyManager:
    """Manages tool dependencies automatically"""
    
    def __init__(self, opskit_root: Path):
        """Initialize dependency manager"""
        self.opskit_root = opskit_root
        self.cache_dir = opskit_root / 'cache'
        self.shared_venv = opskit_root / '.venv'
        self.pip_cache_dir = self.cache_dir / 'pip_cache'
        self.requirements_cache_dir = self.cache_dir / 'requirements'
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Create directories
        self.pip_cache_dir.mkdir(parents=True, exist_ok=True)
        self.requirements_cache_dir.mkdir(parents=True, exist_ok=True)
        
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
            self.logger.debug(f"Dependencies config not found: {config_file}")
            return {}
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config or {}
        except Exception as e:
            self.logger.debug(f"Failed to load dependencies config: {e}")
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
            # Start check message; append status at the end of the same line
            print(f"Checking dependencies for {tool_name}...", end="", flush=True)
            
            # Check Python dependencies
            if tool_info.get('has_python_deps', False):
                self.logger.info(f"🔍 Checking Python dependencies for {tool_name}")
                success, message = self._ensure_python_dependencies(tool_name, tool_path)
                if not success:
                    print(" ❌")
                    print()  # empty line after completion
                    print("❌ Python dependencies failed")
                    return False, f"Python dependencies failed: {message}"
            else:
                self.logger.info(f"✅ Python dependencies satisfied for {tool_name}")
            
            # Check and install system dependencies
            self.logger.info(f"🔍 Checking system dependencies for {tool_name}")
            missing_deps = self._check_system_dependencies(tool_info)
            if missing_deps:
                self.logger.warning(f"⚠️  Missing system dependencies: {', '.join(missing_deps)}")
                # Try to install missing dependencies
                installed, failed = self._install_system_dependencies(missing_deps)
                if failed:
                    print(" ❌")
                    print()  # empty line after completion
                    print("❌ System dependencies failed")
                    return False, f"Missing system dependencies: {', '.join(failed)}"
                else:
                    self.logger.info(f"✅ System dependencies installed: {', '.join(installed)}")
            else:
                self.logger.info(f"✅ All system dependencies satisfied for {tool_name}")
            
            print(" ✅")
            print()  # empty line after completion
            return True, "All dependencies satisfied"

        except Exception as e:
            # Ensure we end the status line with failure mark
            try:
                print(" ❌")
                print()  # empty line after completion
            except Exception:
                pass
            self.logger.error(f"❌ Dependency check failed for {tool_name}: {e}")
            return False, f"Dependency check failed: {e}"
    
    def _ensure_python_dependencies(self, tool_name: str, tool_path: Path) -> Tuple[bool, str]:
        """Ensure Python dependencies are installed in shared virtual environment"""
        requirements_file = tool_path / 'requirements.txt'
        
        if not requirements_file.exists():
            return True, "No requirements.txt found"
        
        try:
            # Create shared virtual environment if it doesn't exist
            if not self.shared_venv.exists():
                print("Creating shared virtual environment...")
                self.logger.info("📦 Creating shared virtual environment...")
                
                try:
                    venv.create(self.shared_venv, with_pip=True, clear=True)
                    print("✅ Shared virtual environment created")
                    self.logger.info("✅ Shared virtual environment created successfully")
                    
                    # Upgrade pip in new environment
                    pip_exe = self._get_pip_executable()
                    if pip_exe:
                        self.logger.info("📦 Upgrading pip in virtual environment...")
                        result = subprocess.run(
                            [str(pip_exe), 'install', '--upgrade', 'pip'],
                            capture_output=True,
                            timeout=60
                        )
                        if result.returncode == 0:
                            self.logger.info("✅ Pip upgraded successfully")
                        else:
                            self.logger.warning(f"⚠️  Pip upgrade failed: {result.stderr}")
                except Exception as e:
                    print("❌ Failed to create virtual environment")
                    self.logger.error(f"❌ Failed to create virtual environment: {e}")
                    raise
            
            # Check if dependencies are already satisfied
            if self._are_python_deps_satisfied(tool_name, requirements_file):
                self.logger.debug(f"Python dependencies already satisfied for {tool_name}")
                return True, "Dependencies already installed"
            
            # Get pip executable path
            pip_exe = self._get_pip_executable()
            if not pip_exe or not pip_exe.exists():
                return False, f"pip not found in shared virtual environment: {pip_exe}"
            
            # Install tool-specific requirements into shared venv
            self.logger.info(f"📦 Installing Python requirements for {tool_name}...")
            
            # Parse requirements file to show what we're installing
            try:
                with open(requirements_file, 'r', encoding='utf-8') as f:
                    requirements_content = f.read().strip()
                    requirements_lines = [line.strip() for line in requirements_content.split('\n') 
                                        if line.strip() and not line.startswith('#')]
                    if requirements_lines:
                        self.logger.info(f"📋 Requirements to install: {', '.join(requirements_lines[:5])}")
                        if len(requirements_lines) > 5:
                            self.logger.info(f"    ... and {len(requirements_lines) - 5} more packages")
            except Exception as e:
                self.logger.debug(f"Could not parse requirements file: {e}")
            
            cmd = [
                str(pip_exe), 'install',
                '--cache-dir', str(self.pip_cache_dir),
                '--requirement', str(requirements_file),
                '--upgrade',  # Handle version conflicts by upgrading
                '--quiet'
            ]
            
            self.logger.debug(f"📋 Running pip command: {' '.join(cmd[:-1])} [requirements_file]")
            self.logger.info(f"⏳ Installing packages (timeout: 5 minutes)...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"❌ Pip install failed: {result.stderr}")
                return False, f"Tool requirements install failed: {result.stderr}"
            
            # Cache requirements for tracking
            self._cache_tool_requirements(tool_name, requirements_file)
            
            self.logger.info(f"✅ Python dependencies installed successfully for {tool_name}")
            
            return True, "Dependencies installed successfully"
        
        except subprocess.TimeoutExpired:
            return False, "pip install timed out"
        except Exception as e:
            return False, f"Failed to setup Python environment: {e}"
    
    def _cache_tool_requirements(self, tool_name: str, requirements_file: Path):
        """Cache tool requirements for tracking which tools installed which packages"""
        try:
            cache_file = self.requirements_cache_dir / f"{tool_name}.txt"
            shutil.copy(requirements_file, cache_file)
            self.logger.debug(f"Cached requirements for {tool_name}")
        except Exception as e:
            self.logger.debug(f"Failed to cache requirements for {tool_name}: {e}")
    
    def _are_python_deps_satisfied(self, tool_name: str, requirements_file: Path) -> bool:
        """Check if Python dependencies are already satisfied in shared virtual environment"""
        self.logger.debug(f"🔍 Checking if Python dependencies are satisfied for {tool_name}")
        
        try:
            python_exe = self._get_python_executable()
            if not python_exe or not python_exe.exists():
                self.logger.debug(f"❌ Python executable not found: {python_exe}")
                return False
            
            # Use pip list to get all installed packages (more reliable than import checks)
            cmd = [str(python_exe), '-m', 'pip', 'list', '--format=json']
            self.logger.debug(f"📋 Getting installed packages list...")
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    self.logger.debug(f"❌ Failed to get pip list: {result.stderr}")
                    return False
                
                installed_packages = json.loads(result.stdout)
                installed_dict = {pkg['name'].lower().replace('-', '_'): pkg['version'] 
                                for pkg in installed_packages}
                self.logger.debug(f"📦 Found {len(installed_packages)} installed packages")
            except Exception as e:
                self.logger.debug(f"❌ Failed to get installed packages list: {e}")
                return False
            
            # Parse requirements.txt to get required packages
            self.logger.debug(f"📋 Parsing requirements file: {requirements_file}")
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
                self.logger.debug(f"📋 No requirements found in {requirements_file}")
                return True  # No requirements to check
            
            self.logger.debug(f"📋 Found {len(requirements)} requirements to check: {requirements}")
            
            # Check each required package
            missing_packages = []
            for pkg_name in requirements:
                if pkg_name not in installed_dict:
                    missing_packages.append(pkg_name)
                else:
                    self.logger.debug(f"✅ Package {pkg_name} found (version: {installed_dict[pkg_name]})")
            
            if missing_packages:
                self.logger.debug(f"❌ Missing packages in venv for {tool_name}: {missing_packages}")
                return False
            
            self.logger.debug(f"✅ All Python dependencies satisfied for {tool_name}")
            return True
        
        except Exception as e:
            self.logger.debug(f"Error checking Python dependencies: {e}")
            return False
    
    def _check_system_dependencies(self, tool_info: Dict) -> List[str]:
        """Check for missing system dependencies specific to this tool"""
        missing_deps = []
        tool_path = Path(tool_info['path'])
        
        # Method 1: Check explicit dependencies from tools.yaml (highest priority)
        declared_deps = tool_info.get('dependencies', [])
        if declared_deps:
            self.logger.info(f"🔍 Checking {len(declared_deps)} declared dependencies for {tool_info['name']}: {declared_deps}")
            for dep_name in declared_deps:
                self.logger.debug(f"  Checking dependency: {dep_name}")
                if not self._is_dependency_satisfied(dep_name):
                    self.logger.warning(f"  ❌ Missing dependency: {dep_name}")
                    missing_deps.append(dep_name)
                else:
                    self.logger.debug(f"  ✅ Dependency satisfied: {dep_name}")
            return missing_deps
        
        # Method 2: Check for tool-specific dependency file
        deps_file = tool_path / 'system_deps.txt'
        if deps_file.exists():
            self.logger.info(f"🔍 Found system_deps.txt for {tool_info['name']}")
            try:
                with open(deps_file, 'r', encoding='utf-8') as f:
                    required_deps = [line.strip() for line in f.readlines() 
                                   if line.strip() and not line.startswith('#')]
                self.logger.info(f"  Checking {len(required_deps)} dependencies from file")
                for dep in required_deps:
                    if not self._is_dependency_satisfied(dep):
                        self.logger.warning(f"  ❌ Missing dependency: {dep}")
                        missing_deps.append(dep)
                    else:
                        self.logger.debug(f"  ✅ Dependency satisfied: {dep}")
                return missing_deps
            except Exception as e:
                self.logger.error(f"❌ Failed to read system_deps.txt: {e}")
        
        # No dependencies declared - skip dependency checking
        self.logger.debug(f"ℹ️  No dependencies declared for {tool_info['name']}, skipping dependency checks")
        
        return missing_deps
    
    def _is_dependency_satisfied(self, dep_name: str) -> bool:
        """Check if a dependency is satisfied (with caching and package manager support)"""
        if not self.dependencies_config:
            return True
        
        import time
        current_time = time.time()
        cache_duration = 300  # 5 minutes cache
        
        # Check cache first
        if (dep_name in self._system_deps_cache and 
            current_time - self._last_cache_time < cache_duration):
            cached_result = self._system_deps_cache[dep_name]
            self.logger.debug(f"📋 Using cached result for {dep_name}: {'satisfied' if cached_result else 'missing'}")
            return cached_result
            
        system_deps = self.dependencies_config.get('system_dependencies', {})
        settings = self.dependencies_config.get('settings', {})
        check_commands = settings.get('check_commands', True)
        
        dep_config = system_deps.get(dep_name, {})
        commands = dep_config.get('commands', [])
        packages = dep_config.get('packages', {})
        
        result = False
        
        # Method 1: Check if package is installed via package manager
        if packages:
            os_type = self.platform_utils.get_os_type()
            
            if os_type == 'linux':
                distro = self.platform_utils.get_linux_distribution()
                package_name = packages.get(distro)
            elif os_type == 'darwin':
                package_name = packages.get('macos')
            else:
                package_name = packages.get(os_type)
            
            if package_name:
                self.logger.debug(f"🔍 Checking package manager for {dep_name} -> {package_name}")
                result = self.platform_utils.is_package_installed(package_name)
                if result:
                    self.logger.debug(f"✅ Package {package_name} found via package manager")
        
        # Method 2: Fallback to command existence check (if enabled)
        if not result and commands and check_commands:
            result = all(self.platform_utils.command_exists(cmd) for cmd in commands)
            if result:
                self.logger.debug(f"Commands {commands} found in PATH")
        elif not result and commands and not check_commands:
            self.logger.debug(f"Command checking disabled for {dep_name}, skipping command verification")
        
        # Method 3: No specific check method - assume satisfied
        if not commands and not packages:
            result = True
        
        # Cache the result
        self._system_deps_cache[dep_name] = result
        self._last_cache_time = current_time
        
        self.logger.debug(f"Dependency {dep_name}: {'satisfied' if result else 'missing'} (check_commands={check_commands})")
        
        return result
    
    def _install_system_dependencies(self, missing_deps: List[str]) -> Tuple[List[str], List[str]]:
        """Install missing system dependencies"""
        if not missing_deps or not self.dependencies_config:
            return [], missing_deps
        
        settings = self.dependencies_config.get('settings', {})
        auto_install = settings.get('auto_install', False)
        
        if not auto_install:
            self.logger.info(f"📋 Auto-install disabled, showing installation guidance for {len(missing_deps)} dependencies")
            self._show_install_guidance(missing_deps)
            return [], missing_deps
        
        self.logger.info(f"🔧 Auto-installing {len(missing_deps)} system dependencies: {missing_deps}")
        
        installed, failed = [], []
        
        print(f"Installing {len(missing_deps)} system dependencies...")
        for i, dep_name in enumerate(missing_deps):
            print(f"Installing {dep_name}...")
            self.logger.info(f"📦 Installing dependency {i+1}/{len(missing_deps)}: {dep_name}")
            
            if self._install_dependency(dep_name):
                installed.append(dep_name)
                self.logger.info(f"✅ Successfully installed {dep_name}")
            else:
                failed.append(dep_name)
                self.logger.warning(f"❌ Failed to install {dep_name}")
        
        if installed:
            self.logger.info(f"✅ Successfully installed {len(installed)} dependencies: {', '.join(installed)}")
        if failed:
            self.logger.warning(f"❌ Failed to install {len(failed)} dependencies: {', '.join(failed)}")
        
        return installed, failed
    
    def _install_dependency(self, dep_name: str) -> bool:
        """Install a single dependency using enhanced package manager support"""
        self.logger.debug(f"🔧 Attempting to install dependency: {dep_name}")
        
        system_deps = self.dependencies_config.get('system_dependencies', {})
        dep_config = system_deps.get(dep_name, {})
        
        if not dep_config:
            self.logger.warning(f"❌ No configuration found for dependency: {dep_name}")
            return False
        
        # Get package name for current platform
        packages = dep_config.get('packages', {})
        os_type = self.platform_utils.get_os_type()
        
        if os_type == 'linux':
            distro = self.platform_utils.get_linux_distribution()
            package_name = packages.get(distro)
            platform_info = f"{os_type} ({distro})"
        elif os_type == 'darwin':
            package_name = packages.get('macos')
            platform_info = "macOS"
        else:
            package_name = packages.get(os_type)
            platform_info = os_type
        
        if not package_name:
            self.logger.warning(f"❌ No package mapping found for {dep_name} on {platform_info}")
            return False
        
        self.logger.info(f"📦 Installing package '{package_name}' for dependency '{dep_name}' on {platform_info}")
        
        # Use enhanced install method with config-based package manager preference
        preferred_manager = self._get_preferred_package_manager()
        self.logger.debug(f"🔧 Using package manager: {preferred_manager}")
        
        success, message = self.platform_utils.install_system_package(package_name, preferred_manager)
        
        if success:
            self.logger.info(f"✅ Successfully installed {package_name}: {message}")
        else:
            self.logger.error(f"❌ Failed to install {package_name}: {message}")
        
        # Clear cache for this dependency regardless of outcome to force recheck
        if dep_name in self._system_deps_cache:
            del self._system_deps_cache[dep_name]
            self._last_cache_time = 0  # Force cache refresh
            self.logger.debug(f"🧹 Cleared cache for {dep_name} after installation attempt")
        
        return success
    
    def _show_install_guidance(self, missing_deps: List[str]):
        """Show installation guidance with descriptions and install notes"""
        if not missing_deps:
            return
        
        settings = self.dependencies_config.get('settings', {})
        suggest_install = settings.get('suggest_install', True)
        
        if not suggest_install:
            self.logger.debug("Installation suggestions disabled by configuration")
            return
        
        print(f"\nError: Missing system dependencies: {', '.join(missing_deps)}")
        print("\nTo install the required dependencies:")
        
        system_deps = self.dependencies_config.get('system_dependencies', {})
        os_type = self.platform_utils.get_os_type()
        pm = self._get_preferred_package_manager()
        
        for dep_name in missing_deps:
            dep_config = system_deps.get(dep_name, {})
            packages = dep_config.get('packages', {})
            description = dep_config.get('description', '')
            install_notes = dep_config.get('install_notes', {})
            
            # Show dependency description
            if description:
                print(f"\n• {dep_name}: {description}")
            else:
                print(f"\n• {dep_name}")
            
            # Get platform-specific package name
            if os_type == 'linux':
                distro = self.platform_utils.get_linux_distribution()
                package = packages.get(distro)
            elif os_type == 'darwin':
                package = packages.get('macos')
            else:
                package = packages.get(os_type)
            
            # Show standard installation command
            if package and pm:
                managers = self.platform_utils.PACKAGE_MANAGERS.get(os_type, {})
                pm_config = managers.get(pm, {})
                install_cmd = pm_config.get('install', '').format(package)
                if install_cmd:
                    print(f"  {install_cmd}")
            
            # Show special installation notes if available
            if install_notes:
                platform_key = None
                if os_type == 'linux':
                    platform_key = self.platform_utils.get_linux_distribution()
                elif os_type == 'darwin':
                    platform_key = 'macos'
                else:
                    platform_key = os_type
                
                # Check for platform-specific install notes
                note = install_notes.get(platform_key) or install_notes.get('all')
                if note:
                    print(f"  Note: {note}")
            
            # Special handling for packages with null package names
            if not package and install_notes:
                note = install_notes.get('all')
                if note:
                    print(f"  Manual installation required: {note}")
    
    def _get_preferred_package_manager(self) -> Optional[str]:
        """Get preferred package manager based on config or auto-detection"""
        package_managers_config = self.dependencies_config.get('package_managers', {})
        os_type = self.platform_utils.get_os_type()
        
        if os_type == 'linux':
            distro = self.platform_utils.get_linux_distribution()
            preferred_order = package_managers_config.get(distro, [])
        elif os_type == 'darwin':
            preferred_order = package_managers_config.get('macos', [])
        else:
            preferred_order = package_managers_config.get(os_type, [])
        
        # If config specifies an order, try them in that order
        if preferred_order:
            available = self.platform_utils.detect_available_package_managers()
            for manager in preferred_order:
                if manager in available:
                    self.logger.debug(f"Using package manager {manager} from config preference")
                    return manager
        
        # Fallback to platform utils default behavior
        return self.platform_utils.get_preferred_package_manager()
    
    def _get_python_executable(self) -> Optional[Path]:
        """Get Python executable for shared virtual environment"""
        python_exe = self.shared_venv / 'bin' / 'python'
        return python_exe if python_exe.exists() else None
    
    def _get_pip_executable(self) -> Optional[Path]:
        """Get pip executable for shared virtual environment"""
        pip_exe = self.shared_venv / 'bin' / 'pip'
        return pip_exe if pip_exe.exists() else None
    
    def get_tool_python_executable(self, tool_name: str) -> Optional[Path]:
        """Get Python executable for tool execution (uses shared venv)"""
        return self._get_python_executable()
    
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
        
        self.logger.info(f"🚀 Running tool: {tool_name}")
        if args:
            self.logger.debug(f"📋 Tool arguments: {args}")
        
        try:
            # Ensure dependencies are available
            self.logger.info(f"🔍 Ensuring dependencies for {tool_name}")
            success, message = self.ensure_tool_dependencies(tool_info)
            if not success:
                self.logger.error(f"❌ Dependency check failed: {message}")
                print(f"Error: {message}")
                return 1
            
            # Prepare execution command
            if tool_info['type'] == 'python':
                # Use virtual environment Python if available
                python_exe = self.get_tool_python_executable(tool_name)
                if python_exe:
                    cmd = [str(python_exe), str(main_file)] + args
                    self.logger.debug(f"🐍 Using virtual environment Python: {python_exe}")
                else:
                    cmd = [sys.executable, str(main_file)] + args
                    self.logger.debug(f"🐍 Using system Python: {sys.executable}")
            else:
                # Shell script
                cmd = [str(main_file)] + args
                self.logger.debug(f"🐚 Running shell script: {main_file}")
            
            # Change to tool directory
            original_cwd = os.getcwd()
            self.logger.debug(f"📂 Changing directory to: {tool_path}")
            os.chdir(tool_path)
            
            try:
                self.logger.debug(f"📋 Executing command: {' '.join(cmd)}")
                self.logger.info(f"▶️  Starting {tool_name} execution")
                
                # Execute tool directly (inherits stdin/stdout/stderr)
                # Use subprocess.run with proper stdio inheritance for interactive tools
                result = subprocess.run(cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
                
                if result.returncode == 0:
                    self.logger.info(f"✅ Tool {tool_name} completed successfully")
                else:
                    self.logger.warning(f"⚠️  Tool {tool_name} exited with code {result.returncode}")
                
                return result.returncode
            
            finally:
                os.chdir(original_cwd)
                self.logger.debug(f"📂 Restored directory to: {original_cwd}")
        
        except Exception as e:
            self.logger.error(f"❌ Error running tool {tool_name}: {e}")
            print(f"Error running tool {tool_name}: {e}")
            return 1
    
    def clean_tool_cache(self, tool_name: str) -> bool:
        """Clean cache for a specific tool (removes requirement cache)"""
        try:
            cache_file = self.requirements_cache_dir / f"{tool_name}.txt"
            if cache_file.exists():
                cache_file.unlink()
                return True
            return False
        except Exception:
            return False
    
    def clean_all_cache(self) -> bool:
        """Clean all dependency caches and shared venv"""
        try:
            # Remove shared virtual environment
            if self.shared_venv.exists():
                shutil.rmtree(self.shared_venv)
            
            # Remove cache directory
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                
            # Recreate cache directories
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.pip_cache_dir.mkdir(parents=True, exist_ok=True)
            self.requirements_cache_dir.mkdir(parents=True, exist_ok=True)
            return True
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
        
        # Check shared virtual environment
        if self.shared_venv.exists():
            status['has_venv'] = True
            try:
                # Calculate shared venv size (only reported once)
                if tool_name == 'shared_venv_info':
                    total_size = sum(f.stat().st_size for f in self.shared_venv.rglob('*') if f.is_file())
                    status['venv_size'] = total_size
                else:
                    status['venv_size'] = 0  # Don't report size for individual tools
            except Exception:
                pass
        
        # Check Python dependencies
        if tool_info.get('has_python_deps', False):
            python_exe = self._get_python_executable()
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
        self.logger.debug("System dependency cache cleared")
    
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
    
    def get_package_manager_info(self) -> Dict:
        """Get information about available package managers"""
        return {
            'available_managers': self.platform_utils.detect_available_package_managers(),
            'preferred_manager': self.platform_utils.get_preferred_package_manager(),
            'os_type': self.platform_utils.get_os_type(),
            'platform_info': self.platform_utils.get_platform_info()
        }
    
    def check_package_installed(self, package_name: str, package_manager: str = None) -> bool:
        """Check if a specific package is installed using package manager"""
        return self.platform_utils.is_package_installed(package_name, package_manager)
    
    def get_installed_packages(self, package_manager: str = None) -> List[str]:
        """Get list of all installed packages"""
        return self.platform_utils.get_installed_packages(package_manager)
    
    def install_package(self, package_name: str, package_manager: str = None, force: bool = False) -> Tuple[bool, str]:
        """Install a package directly using package manager"""
        return self.platform_utils.install_system_package(package_name, package_manager, force)
    
    def bulk_check_dependencies(self, dep_names: List[str]) -> Dict[str, bool]:
        """Check multiple dependencies at once"""
        results = {}
        for dep_name in dep_names:
            results[dep_name] = self._is_dependency_satisfied(dep_name)
        return results
    
    def validate_venv_integrity(self, tool_name: str = None) -> Tuple[bool, str]:
        """Validate shared virtual environment integrity and suggest refresh if needed"""
        if not self.shared_venv.exists():
            return False, "Shared virtual environment does not exist"
        
        try:
            python_exe = self._get_python_executable()
            if not python_exe or not python_exe.exists():
                return False, "Python executable missing in shared virtual environment"
            
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

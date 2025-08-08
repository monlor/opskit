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
            
            # Check system dependencies (basic detection)
            missing_deps = self._check_system_dependencies(tool_info)
            if missing_deps:
                return False, f"Missing system dependencies: {', '.join(missing_deps)}"
            
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
            
            # Get pip executable path
            if os.name == 'nt':  # Windows
                pip_exe = venv_path / 'Scripts' / 'pip.exe'
                python_exe = venv_path / 'Scripts' / 'python.exe'
            else:  # Unix-like
                pip_exe = venv_path / 'bin' / 'pip'
                python_exe = venv_path / 'bin' / 'python'
            
            if not pip_exe.exists():
                return False, f"pip not found in virtual environment: {pip_exe}"
            
            # Install requirements
            if self.debug:
                print(f"Installing requirements for {tool_name}...")
            
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
                return False, f"pip install failed: {result.stderr}"
            
            if self.debug:
                print(f"Dependencies installed successfully for {tool_name}")
            
            return True, "Dependencies installed successfully"
        
        except subprocess.TimeoutExpired:
            return False, "pip install timed out"
        except Exception as e:
            return False, f"Failed to setup Python environment: {e}"
    
    def _check_system_dependencies(self, tool_info: Dict) -> List[str]:
        """Check for missing system dependencies"""
        missing = []
        tool_path = Path(tool_info['path'])
        
        # Basic dependency detection from main file
        main_file = tool_path / tool_info['main_file']
        if not main_file.exists():
            return []
        
        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Common system commands to check
            common_commands = [
                'mysql', 'mysqldump', 'psql', 'pg_dump',
                'git', 'curl', 'wget', 'jq', 'docker',
                'ssh', 'scp', 'rsync', 'tar', 'gzip'
            ]
            
            for cmd in common_commands:
                # Simple check if command is mentioned in the file
                if cmd in content and not self.platform_utils.command_exists(cmd):
                    missing.append(cmd)
        
        except Exception:
            pass  # Ignore errors in basic dependency detection
        
        return missing
    
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
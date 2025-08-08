"""
Environment Variable Management Module

Handles environment variable loading and injection for OpsKit tools including:
- Tool-level .env file loading from tool directories
- Global .env file loading from data directory  
- Environment variable priority and override system
- Tool name prefix conversion for global overrides
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional


class EnvManager:
    """Environment variable management system for OpsKit tools"""
    
    def __init__(self, opskit_root: Optional[str] = None):
        """Initialize environment manager"""
        if opskit_root:
            self.opskit_root = Path(opskit_root)
        else:
            # Auto-detect OpsKit root
            current_file = Path(__file__).resolve()
            self.opskit_root = current_file.parent.parent
        
        self.data_dir = self.opskit_root / 'data'
        self.tools_dir = self.opskit_root / 'tools'
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
    
    def _parse_env_file(self, env_file: Path) -> Dict[str, str]:
        """
        Parse .env file and return key-value pairs
        
        Args:
            env_file: Path to .env file
            
        Returns:
            Dictionary of environment variables
        """
        env_vars = {}
        
        if not env_file.exists():
            return env_vars
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Match KEY=VALUE pattern
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Validate key format (alphanumeric + underscore)
                        if re.match(r'^[A-Z][A-Z0-9_]*$', key):
                            env_vars[key] = value
                        else:
                            print(f"Warning: Invalid environment variable name '{key}' in {env_file}:{line_num}")
                    else:
                        print(f"Warning: Invalid line format in {env_file}:{line_num}: {line}")
        
        except Exception as e:
            print(f"Error reading {env_file}: {e}")
        
        return env_vars
    
    def _tool_name_to_prefix(self, tool_name: str) -> str:
        """
        Convert tool name to environment variable prefix
        
        Args:
            tool_name: Tool name (e.g., 'mysql-sync', 'port-scanner')
            
        Returns:
            Environment variable prefix (e.g., 'MYSQL_SYNC', 'PORT_SCANNER')
        """
        # Convert kebab-case to SCREAMING_SNAKE_CASE
        return tool_name.upper().replace('-', '_')
    
    def load_tool_env(self, tool_path: str) -> Dict[str, str]:
        """
        Load environment variables from tool's .env file
        
        Args:
            tool_path: Path to tool directory or main file
            
        Returns:
            Dictionary of tool environment variables
        """
        tool_path = Path(tool_path)
        
        # If tool_path points to a file, get its directory
        if tool_path.is_file():
            tool_dir = tool_path.parent
        else:
            tool_dir = tool_path
        
        env_file = tool_dir / '.env'
        return self._parse_env_file(env_file)
    
    def load_global_env(self) -> Dict[str, str]:
        """
        Load global environment variables from data/.env
        
        Returns:
            Dictionary of global environment variables
        """
        global_env_file = self.data_dir / '.env'
        return self._parse_env_file(global_env_file)
    
    def get_tool_name_from_path(self, tool_path: str) -> str:
        """
        Extract tool name from tool path
        
        Args:
            tool_path: Path to tool directory or main file
            
        Returns:
            Tool name (directory name)
        """
        tool_path = Path(tool_path)
        
        # If tool_path points to a file, get its directory
        if tool_path.is_file():
            return tool_path.parent.name
        else:
            return tool_path.name
    
    def inject_env_vars(self, tool_path: str) -> Dict[str, str]:
        """
        Load and merge environment variables with proper precedence
        
        Precedence (high to low):
        1. System environment variables
        2. Global .env file (data/.env) with tool prefix
        3. Tool .env file
        
        Args:
            tool_path: Path to tool directory or main file
            
        Returns:
            Final merged environment variables dictionary
        """
        tool_name = self.get_tool_name_from_path(tool_path)
        tool_prefix = self._tool_name_to_prefix(tool_name)
        
        # Start with tool-level environment variables (lowest priority)
        final_env = self.load_tool_env(tool_path)
        
        # Apply global environment variables with prefix matching
        global_env = self.load_global_env()
        for key, value in global_env.items():
            if key.startswith(tool_prefix + '_'):
                # Remove tool prefix to get the base variable name
                base_key = key[len(tool_prefix) + 1:]
                final_env[base_key] = value
            else:
                # Direct global variable (no prefix)
                final_env[key] = value
        
        # System environment variables have highest priority
        for key in final_env.keys():
            # Check for tool-prefixed system env var first
            prefixed_key = f"{tool_prefix}_{key}"
            if prefixed_key in os.environ:
                final_env[key] = os.environ[prefixed_key]
            elif key in os.environ:
                final_env[key] = os.environ[key]
        
        return final_env
    
    def set_environment_variables(self, env_vars: Dict[str, str]) -> None:
        """
        Set environment variables in current process
        
        Args:
            env_vars: Dictionary of environment variables to set
        """
        for key, value in env_vars.items():
            os.environ[key] = value
    
    def get_env_var(self, key: str, default: Any = None, var_type: type = str) -> Any:
        """
        Get environment variable with type conversion
        
        Args:
            key: Environment variable name
            default: Default value if not found
            var_type: Type to convert to (str, int, float, bool)
            
        Returns:
            Environment variable value converted to specified type
        """
        value = os.environ.get(key)
        
        if value is None:
            return default
        
        try:
            if var_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif var_type == int:
                return int(value)
            elif var_type == float:
                return float(value)
            else:
                return str(value)
        except (ValueError, TypeError):
            print(f"Warning: Cannot convert env var '{key}={value}' to {var_type.__name__}, using default")
            return default
    
    def get_config_summary(self, tool_path: str) -> Dict[str, Any]:
        """
        Get summary of environment configuration for a tool
        
        Args:
            tool_path: Path to tool directory or main file
            
        Returns:
            Configuration summary dictionary
        """
        tool_name = self.get_tool_name_from_path(tool_path)
        tool_env = self.load_tool_env(tool_path)
        global_env = self.load_global_env()
        final_env = self.inject_env_vars(tool_path)
        
        return {
            'tool_name': tool_name,
            'tool_prefix': self._tool_name_to_prefix(tool_name),
            'tool_env_count': len(tool_env),
            'global_env_count': len(global_env),
            'final_env_count': len(final_env),
            'tool_env_file': str(Path(tool_path).parent / '.env'),
            'global_env_file': str(self.data_dir / '.env'),
            'sample_vars': dict(list(final_env.items())[:5])  # Show first 5 variables
        }
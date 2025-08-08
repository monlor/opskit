"""
Configuration Management Module for OpsKit

Handles reading, parsing, and accessing configuration from opskit.yaml
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """
    Configuration management for OpsKit
    Handles reading and accessing configuration values from opskit.yaml
    """

    def __init__(self, opskit_root: Path):
        """
        Initialize ConfigManager with the OpsKit root directory
        
        Args:
            opskit_root (Path): Root directory of the OpsKit project
        """
        self.opskit_root = opskit_root
        self._config = None
        self._load_config()

    def _load_config(self):
        """
        Load configuration from opskit.yaml
        """
        config_path = self.opskit_root / 'data' / 'opskit.yaml'
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            # Create default configuration if file doesn't exist
            self._config = {
                'paths': {
                    'cache_dir': 'cache',
                    'logs_dir': 'logs'
                }
            }
        except yaml.YAMLError as e:
            # Log or handle YAML parsing errors
            print(f"Error parsing configuration: {e}")
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot-separated key path

        Args:
            key (str): Dot-separated configuration key path
            default (Any, optional): Default value if key is not found

        Returns:
            Any: Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        
        return value if value is not None else default

    def get_paths(self) -> Dict[str, str]:
        """
        Get paths configuration with default fallbacks

        Returns:
            Dict[str, str]: Paths configuration
        """
        paths = self.get('paths', {})
        
        # Ensure absolute paths
        for key, value in paths.items():
            if not os.path.isabs(value):
                paths[key] = str(self.opskit_root / value)
        
        return paths

    def get_cache_dir(self) -> str:
        """
        Get the cache directory path

        Returns:
            str: Absolute path to cache directory
        """
        return self.get_paths().get('cache_dir', str(self.opskit_root / 'cache'))

    def get_tool_temp_dir(self, tool_name: Optional[str] = None) -> str:
        """
        Get tool-specific temporary directory path

        Args:
            tool_name (Optional[str], optional): Name of the tool. Defaults to None.

        Returns:
            str: Absolute path to tool's temporary directory
        """
        cache_dir = Path(self.get_cache_dir())
        tool_temp_dir = cache_dir / 'tools'
        tool_temp_dir.mkdir(parents=True, exist_ok=True)
        
        if tool_name:
            tool_dir = tool_temp_dir / tool_name
            tool_dir.mkdir(exist_ok=True)
            return str(tool_dir)
        
        return str(tool_temp_dir)

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the configuration

        Returns:
            Dict[str, Any]: Configuration summary
        """
        return {
            'main_config_exists': bool(self._config),
            'tool_configs_count': len(self._config.get('tools', {})),
            'paths': self.get_paths()
        }
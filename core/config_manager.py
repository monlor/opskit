"""
Configuration Management Module

Handles configuration file management and persistence including:
- Configuration template system
- User configuration storage and validation
- Configuration import/export functionality
- Tool-specific configuration management
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
import shutil


@dataclass
class ConfigSchema:
    """Configuration schema definition"""
    name: str
    type: str  # 'string', 'integer', 'boolean', 'list', 'dict'
    default: Any
    description: str
    required: bool = False
    choices: Optional[List[str]] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None


class ConfigurationError(Exception):
    """Configuration-related errors"""
    pass


class ConfigManager:
    """Configuration management system"""
    
    def __init__(self, opskit_root: Optional[str] = None):
        """Initialize configuration manager"""
        if opskit_root:
            self.opskit_root = Path(opskit_root)
        else:
            # Auto-detect OpsKit root
            current_file = Path(__file__).resolve()
            self.opskit_root = current_file.parent.parent
        
        self.config_dir = self.opskit_root / 'config'
        self.data_dir = self.opskit_root / 'data'
        
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        
        self.main_config_file = self.data_dir / 'opskit.yaml'
        self.main_config_template = self.config_dir / 'opskit.yaml.template'
        
        # Load configurations
        self.main_config = self._load_main_config()
        self.tool_configs = {}
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse a YAML file"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            return {}
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML syntax in {file_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error reading config file {file_path}: {e}")
    
    def _save_yaml_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Save data to a YAML file"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, indent=2, 
                         allow_unicode=True, sort_keys=False)
        except Exception as e:
            raise ConfigurationError(f"Error saving config file {file_path}: {e}")
    
    def _load_main_config(self) -> Dict[str, Any]:
        """Load main OpsKit configuration"""
        # Load user config if it exists
        if self.main_config_file.exists():
            return self._load_yaml_file(self.main_config_file)
        
        # Create default config from template
        return self._create_default_main_config()
    
    def _create_default_main_config(self) -> Dict[str, Any]:
        """Create default main configuration"""
        default_config = {
            'general': {
                'default_editor': 'vim',
                'auto_update': True,
                'confirm_destructive': True
            },
            'display': {
                'show_colors': True,
                'page_size': 20,
                'show_descriptions': True
            },
            'logging': {
                'file_enabled': False,
                'console_level': 'INFO',
                'file_level': 'DEBUG',
                'console_simple_format': True,
                'max_files': 5,
                'max_size': '10MB'
            },
            'tools': {},
            'platforms': {
                'preferred_package_manager': 'auto'
            },
            'paths': {
                'cache_dir': str(self.opskit_root / 'cache'),
                'logs_dir': str(self.opskit_root / 'logs')
            }
        }
        
        # Save default config
        self._save_yaml_file(self.main_config_file, default_config)
        return default_config
    
    def ensure_user_config(self) -> None:
        """Ensure user configuration exists and is valid"""
        if not self.main_config_file.exists():
            self._create_default_main_config()
        
        # Validate and update config if needed
        self._validate_and_update_config()
    
    def _validate_and_update_config(self) -> None:
        """Validate and update configuration with missing keys"""
        default_config = self._create_default_main_config()
        updated = False
        
        def merge_configs(current: Dict[str, Any], default: Dict[str, Any]) -> bool:
            """Merge default config into current config"""
            nonlocal updated
            for key, value in default.items():
                if key not in current:
                    current[key] = value
                    updated = True
                elif isinstance(value, dict) and isinstance(current[key], dict):
                    merge_configs(current[key], value)
            return updated
        
        merge_configs(self.main_config, default_config)
        
        if updated:
            self._save_yaml_file(self.main_config_file, self.main_config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'general.log_level')
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        try:
            keys = key.split('.')
            value = self.main_config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
        except Exception:
            return default
    
    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        Set configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'general.log_level')
            value: Value to set
            save: Whether to save to file immediately
        """
        keys = key.split('.')
        current = self.main_config
        
        # Navigate to parent dictionary
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the value
        current[keys[-1]] = value
        
        if save:
            self._save_yaml_file(self.main_config_file, self.main_config)
    
    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Get configuration for a specific tool"""
        if tool_name in self.tool_configs:
            return self.tool_configs[tool_name]
        
        # Try to load from file
        config_file = self.data_dir / f'{tool_name}.yaml'
        if config_file.exists():
            config = self._load_yaml_file(config_file)
            self.tool_configs[tool_name] = config
            return config
        
        # Return empty config
        self.tool_configs[tool_name] = {}
        return {}
    
    def set_tool_config(self, tool_name: str, config: Dict[str, Any], 
                       save: bool = True) -> None:
        """Set configuration for a specific tool"""
        self.tool_configs[tool_name] = config
        
        if save:
            config_file = self.data_dir / f'{tool_name}.yaml'
            self._save_yaml_file(config_file, config)
    
    def get_tool_config_value(self, tool_name: str, key: str, default: Any = None) -> Any:
        """Get a specific configuration value for a tool"""
        config = self.get_tool_config(tool_name)
        
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_tool_config_value(self, tool_name: str, key: str, value: Any,
                            save: bool = True) -> None:
        """Set a specific configuration value for a tool"""
        config = self.get_tool_config(tool_name)
        
        keys = key.split('.')
        current = config
        
        # Navigate to parent dictionary
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the value
        current[keys[-1]] = value
        
        if save:
            self.set_tool_config(tool_name, config, save=True)
    
    def validate_config_schema(self, config: Dict[str, Any], 
                             schema: List[ConfigSchema]) -> List[str]:
        """
        Validate configuration against schema
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        for field in schema:
            value = config.get(field.name)
            
            # Check required fields
            if field.required and value is None:
                errors.append(f"Required field '{field.name}' is missing")
                continue
            
            # Skip validation if field is not provided and not required
            if value is None:
                continue
            
            # Type validation
            if field.type == 'string' and not isinstance(value, str):
                errors.append(f"Field '{field.name}' must be a string")
            elif field.type == 'integer' and not isinstance(value, int):
                errors.append(f"Field '{field.name}' must be an integer")
            elif field.type == 'boolean' and not isinstance(value, bool):
                errors.append(f"Field '{field.name}' must be a boolean")
            elif field.type == 'list' and not isinstance(value, list):
                errors.append(f"Field '{field.name}' must be a list")
            elif field.type == 'dict' and not isinstance(value, dict):
                errors.append(f"Field '{field.name}' must be a dictionary")
            
            # Choice validation
            if field.choices and value not in field.choices:
                errors.append(f"Field '{field.name}' must be one of: {field.choices}")
            
            # Range validation for integers
            if field.type == 'integer' and isinstance(value, int):
                if field.min_value is not None and value < field.min_value:
                    errors.append(f"Field '{field.name}' must be >= {field.min_value}")
                if field.max_value is not None and value > field.max_value:
                    errors.append(f"Field '{field.name}' must be <= {field.max_value}")
        
        return errors
    
    def export_config(self, export_path: str, include_tools: bool = True) -> None:
        """Export configuration to a file"""
        export_data = {
            'opskit_version': '0.1.0',
            'export_timestamp': str(Path().cwd()),  # Simple timestamp
            'main_config': self.main_config
        }
        
        if include_tools:
            export_data['tool_configs'] = {}
            for config_file in self.data_dir.glob('*.yaml'):
                if config_file.name != 'opskit.yaml':
                    tool_name = config_file.stem
                    export_data['tool_configs'][tool_name] = self._load_yaml_file(config_file)
        
        export_path = Path(export_path)
        if export_path.suffix.lower() == '.json':
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        else:
            self._save_yaml_file(export_path, export_data)
    
    def import_config(self, import_path: str, merge: bool = True) -> None:
        """Import configuration from a file"""
        import_path = Path(import_path)
        
        if not import_path.exists():
            raise ConfigurationError(f"Import file not found: {import_path}")
        
        try:
            if import_path.suffix.lower() == '.json':
                with open(import_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
            else:
                import_data = self._load_yaml_file(import_path)
        except Exception as e:
            raise ConfigurationError(f"Error reading import file: {e}")
        
        # Import main configuration
        if 'main_config' in import_data:
            if merge:
                # Merge imported config into existing
                def merge_dicts(target: Dict[str, Any], source: Dict[str, Any]) -> None:
                    for key, value in source.items():
                        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                            merge_dicts(target[key], value)
                        else:
                            target[key] = value
                
                merge_dicts(self.main_config, import_data['main_config'])
            else:
                # Replace entire config
                self.main_config = import_data['main_config']
            
            self._save_yaml_file(self.main_config_file, self.main_config)
        
        # Import tool configurations
        if 'tool_configs' in import_data:
            for tool_name, tool_config in import_data['tool_configs'].items():
                if merge:
                    existing_config = self.get_tool_config(tool_name)
                    if existing_config:
                        def merge_dicts(target: Dict[str, Any], source: Dict[str, Any]) -> None:
                            for key, value in source.items():
                                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                                    merge_dicts(target[key], value)
                                else:
                                    target[key] = value
                        merge_dicts(existing_config, tool_config)
                        self.set_tool_config(tool_name, existing_config)
                    else:
                        self.set_tool_config(tool_name, tool_config)
                else:
                    self.set_tool_config(tool_name, tool_config)
    
    def reset_config(self, tool_name: Optional[str] = None) -> None:
        """Reset configuration to defaults"""
        if tool_name:
            # Reset specific tool configuration
            config_file = self.data_dir / f'{tool_name}.yaml'
            if config_file.exists():
                config_file.unlink()
            if tool_name in self.tool_configs:
                del self.tool_configs[tool_name]
        else:
            # Reset main configuration
            if self.main_config_file.exists():
                self.main_config_file.unlink()
            self.main_config = self._create_default_main_config()
    
    def list_tool_configs(self) -> List[str]:
        """List all available tool configurations"""
        tool_names = []
        
        # From loaded configs
        tool_names.extend(self.tool_configs.keys())
        
        # From config files (exclude main opskit.yaml)
        for config_file in self.data_dir.glob('*.yaml'):
            if config_file.name != 'opskit.yaml':
                tool_name = config_file.stem
                if tool_name not in tool_names:
                    tool_names.append(tool_name)
        
        return sorted(tool_names)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            'main_config_file': str(self.main_config_file),
            'main_config_exists': self.main_config_file.exists(),
            'data_dir': str(self.data_dir),
            'tool_configs_count': len(self.list_tool_configs()),
            'log_level': self.get('logging.console_level', 'INFO'),
            'file_logging': self.get('logging.file_enabled', False),
            'auto_update': self.get('general.auto_update', True),
            'package_manager': self.get('platforms.preferred_package_manager', 'auto')
        }
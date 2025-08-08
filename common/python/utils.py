"""
Common Utility Functions

Provides utility functions for OpsKit tools including:
- Configuration file loading and saving
- File and directory operations
- String manipulation and formatting
- Data validation helpers
"""

import os
import sys
import yaml
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime


def load_config(tool_name: str, config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration for a tool
    
    Args:
        tool_name: Name of the tool
        config_file: Specific config file path (optional)
    
    Returns:
        Configuration dictionary
    """
    try:
        # Import here to avoid circular imports
        from ..core.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        
        if config_file:
            # Load specific config file
            config_path = Path(config_file)
            if config_path.exists():
                return config_manager._load_yaml_file(config_path)
            else:
                return {}
        else:
            # Load tool configuration
            return config_manager.get_tool_config(tool_name)
    
    except ImportError:
        # Fallback method without config manager
        return _load_config_fallback(tool_name, config_file)


def _load_config_fallback(tool_name: str, config_file: Optional[str] = None) -> Dict[str, Any]:
    """Fallback config loading method"""
    if config_file:
        config_path = Path(config_file)
    else:
        # Try to find config in standard locations
        current_file = Path(__file__).resolve()
        opskit_root = current_file.parent.parent.parent
        config_path = opskit_root / 'user_config' / 'tool_configs' / f'{tool_name}.yaml'
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    
    return {}


def save_config(tool_name: str, config: Dict[str, Any], 
               config_file: Optional[str] = None) -> bool:
    """
    Save configuration for a tool
    
    Args:
        tool_name: Name of the tool
        config: Configuration dictionary to save
        config_file: Specific config file path (optional)
    
    Returns:
        True if saved successfully
    """
    try:
        # Import here to avoid circular imports
        from ..core.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        
        if config_file:
            # Save to specific file
            config_path = Path(config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_manager._save_yaml_file(config_path, config)
        else:
            # Save tool configuration
            config_manager.set_tool_config(tool_name, config)
        
        return True
    
    except ImportError:
        # Fallback method
        return _save_config_fallback(tool_name, config, config_file)


def _save_config_fallback(tool_name: str, config: Dict[str, Any], 
                         config_file: Optional[str] = None) -> bool:
    """Fallback config saving method"""
    try:
        if config_file:
            config_path = Path(config_file)
        else:
            current_file = Path(__file__).resolve()
            opskit_root = current_file.parent.parent.parent
            config_dir = opskit_root / 'user_config' / 'tool_configs'
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / f'{tool_name}.yaml'
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2, 
                     allow_unicode=True, sort_keys=False)
        
        return True
    
    except Exception:
        return False


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary
    
    Args:
        path: Directory path
    
    Returns:
        Path object for the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(filename: str) -> str:
    """
    Convert a string to a safe filename
    
    Args:
        filename: Original filename
    
    Returns:
        Safe filename string
    """
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    safe_name = filename
    
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Remove multiple underscores and trim
    while '__' in safe_name:
        safe_name = safe_name.replace('__', '_')
    
    safe_name = safe_name.strip('_')
    
    # Ensure it's not empty
    if not safe_name:
        safe_name = 'unnamed'
    
    return safe_name


def format_size(size_bytes: int) -> str:
    """
    Format byte size in human-readable format
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    if i == 0:
        return f"{size_bytes} {size_names[i]}"
    else:
        return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted duration string (e.g., "2h 30m 15s")
    """
    if seconds < 0:
        return "0s"
    
    parts = []
    
    # Hours
    if seconds >= 3600:
        hours = int(seconds // 3600)
        parts.append(f"{hours}h")
        seconds %= 3600
    
    # Minutes
    if seconds >= 60:
        minutes = int(seconds // 60)
        parts.append(f"{minutes}m")
        seconds %= 60
    
    # Seconds
    if seconds >= 1 or not parts:
        parts.append(f"{int(seconds)}s")
    elif seconds > 0:
        parts.append(f"{seconds:.1f}s")
    
    return " ".join(parts)


def calculate_file_hash(file_path: Union[str, Path], algorithm: str = 'sha256') -> str:
    """
    Calculate hash of a file
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm ('md5', 'sha1', 'sha256', 'sha512')
    
    Returns:
        Hex digest of the file hash
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def run_command(command: List[str], cwd: Optional[str] = None, 
               env: Optional[Dict[str, str]] = None,
               timeout: int = 30) -> Tuple[bool, str, str]:
    """
    Run a system command and return result
    
    Args:
        command: Command and arguments as list
        cwd: Working directory
        env: Environment variables
        timeout: Timeout in seconds
    
    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        
        return (
            result.returncode == 0,
            result.stdout,
            result.stderr
        )
    
    except subprocess.TimeoutExpired:
        return (False, "", f"Command timed out after {timeout} seconds")
    except FileNotFoundError:
        return (False, "", f"Command not found: {command[0]}")
    except Exception as e:
        return (False, "", str(e))


def validate_email(email: str) -> bool:
    """
    Basic email validation
    
    Args:
        email: Email address to validate
    
    Returns:
        True if email format is valid
    """
    import re
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """
    Basic URL validation
    
    Args:
        url: URL to validate
    
    Returns:
        True if URL format is valid
    """
    import re
    
    pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    return re.match(pattern, url) is not None


def parse_key_value_pairs(text: str, separator: str = '=') -> Dict[str, str]:
    """
    Parse key-value pairs from text
    
    Args:
        text: Text containing key-value pairs
        separator: Separator between key and value
    
    Returns:
        Dictionary of key-value pairs
    """
    result = {}
    
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if separator in line:
            key, value = line.split(separator, 1)
            result[key.strip()] = value.strip()
    
    return result


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple dictionaries recursively
    
    Args:
        *dicts: Dictionaries to merge
    
    Returns:
        Merged dictionary
    """
    result = {}
    
    for d in dicts:
        for key, value in d.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value)
            else:
                result[key] = value
    
    return result


def flatten_dict(d: Dict[str, Any], parent_key: str = '', separator: str = '.') -> Dict[str, Any]:
    """
    Flatten a nested dictionary
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        separator: Key separator
    
    Returns:
        Flattened dictionary
    """
    items = []
    
    for key, value in d.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, separator).items())
        else:
            items.append((new_key, value))
    
    return dict(items)


def unflatten_dict(d: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """
    Unflatten a dictionary with dot notation keys
    
    Args:
        d: Flattened dictionary
        separator: Key separator
    
    Returns:
        Unflattened nested dictionary
    """
    result = {}
    
    for key, value in d.items():
        keys = key.split(separator)
        current = result
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    return result


def get_user_input(prompt: str, default: Optional[str] = None,
                  validator: Optional[callable] = None,
                  max_attempts: int = 3) -> str:
    """
    Get validated user input
    
    Args:
        prompt: Input prompt
        default: Default value
        validator: Validation function
        max_attempts: Maximum validation attempts
    
    Returns:
        Validated user input
    """
    for attempt in range(max_attempts):
        try:
            full_prompt = prompt
            if default:
                full_prompt += f" [{default}]"
            full_prompt += ": "
            
            user_input = input(full_prompt).strip()
            
            if not user_input and default:
                user_input = default
            
            if validator:
                if validator(user_input):
                    return user_input
                else:
                    print("Invalid input. Please try again.")
            else:
                return user_input
        
        except KeyboardInterrupt:
            print("\nCancelled by user")
            sys.exit(0)
        except EOFError:
            if default:
                return default
            else:
                raise
    
    raise ValueError(f"Failed to get valid input after {max_attempts} attempts")


def timestamp() -> str:
    """
    Get current timestamp in ISO format
    
    Returns:
        ISO format timestamp string
    """
    return datetime.now().isoformat()


def is_interactive() -> bool:
    """
    Check if running in interactive mode
    
    Returns:
        True if stdin is a terminal
    """
    return sys.stdin.isatty()


def get_terminal_size() -> Tuple[int, int]:
    """
    Get terminal size
    
    Returns:
        Tuple of (width, height)
    """
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 24  # Default size
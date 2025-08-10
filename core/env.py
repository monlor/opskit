"""
Environment Management Module for OpsKit

Uses python-dotenv for environment variable management.

Usage:
    from core.env import env, get_tool_temp_dir, load_tool_env
    
    print(env.cache_dir)
    print(env.logs_dir)
    print(env.log_level)
"""

import os
from pathlib import Path
from dotenv import load_dotenv, dotenv_values


# Find OpsKit root and load main .env file
current_file = Path(__file__).resolve()
opskit_root = current_file.parent.parent
env_file = opskit_root / 'data' / '.env'

# Load environment variables
if env_file.exists():
    load_dotenv(env_file)


class EnvConfig:
    """Environment configuration object"""
    
    @property
    def cache_dir(self) -> str:
        cache_dir = os.getenv('OPSKIT_PATHS_CACHE_DIR', 'cache')
        if not os.path.isabs(cache_dir):
            cache_dir = str(opskit_root / cache_dir)
        return cache_dir
    
    @property
    def logs_dir(self) -> str:
        logs_dir = os.getenv('OPSKIT_PATHS_LOGS_DIR', 'logs')
        if not os.path.isabs(logs_dir):
            logs_dir = str(opskit_root / logs_dir)
        return logs_dir
    
    @property
    def log_level(self) -> str:
        return os.getenv('OPSKIT_LOGGING_CONSOLE_LEVEL', 'INFO')
    
    @property
    def log_file_enabled(self) -> bool:
        return os.getenv('OPSKIT_LOGGING_FILE_ENABLED', 'false').lower() == 'true'
    
    @property
    def log_file_level(self) -> str:
        return os.getenv('OPSKIT_LOGGING_FILE_LEVEL', 'DEBUG')
    
    @property
    def log_simple_format(self) -> bool:
        return os.getenv('OPSKIT_LOGGING_CONSOLE_SIMPLE_FORMAT', 'true').lower() == 'true'
    
    @property
    def log_max_files(self) -> int:
        return int(os.getenv('OPSKIT_LOGGING_MAX_FILES', '5'))
    
    @property
    def log_max_size(self) -> str:
        return os.getenv('OPSKIT_LOGGING_MAX_SIZE', '10MB')
    
    @property
    def version(self) -> str:
        return os.getenv('OPSKIT_VERSION', '0.1.0')
    
    @property
    def author(self) -> str:
        return os.getenv('OPSKIT_AUTHOR', 'OpsKit Development Team')


# Global env object
env = EnvConfig()


def get_tool_temp_dir(tool_name: str) -> str:
    """Get tool-specific temporary directory"""
    cache_dir = Path(env.cache_dir)
    tool_dir = cache_dir / 'tools' / tool_name
    tool_dir.mkdir(parents=True, exist_ok=True)
    return str(tool_dir)


def load_tool_env(tool_path: str) -> dict:
    """Load environment variables from tool's .env file"""
    tool_env_file = Path(tool_path) / '.env'
    
    if tool_env_file.exists():
        return dict(dotenv_values(tool_env_file))
    
    return {}


def get_config_summary() -> dict:
    """Get configuration summary"""
    env_file_exists = env_file.exists()
    opskit_vars = {k: v for k, v in os.environ.items() if k.startswith('OPSKIT_')}
    
    return {
        'main_config_exists': env_file_exists,
        'tool_configs_count': len(opskit_vars),
        'paths': {
            'cache_dir': env.cache_dir,
            'logs_dir': env.logs_dir
        }
    }
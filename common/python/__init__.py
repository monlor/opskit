"""
OpsKit Python Common Libraries

Provides common functionality for Python tools including:
- Unified logging system
- Key-value storage with SQLite backend
- Configuration management utilities
- Common utility functions
"""

__version__ = "0.1.0"
__all__ = [
    'get_logger',
    'get_storage', 
    'load_config',
    'save_config',
    'setup_logging'
]

# Import commonly used functions for easy access
from .logger import get_logger, setup_logging
from .storage import get_storage
from .utils import load_config, save_config
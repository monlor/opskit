"""
Unified Logging System

Provides centralized logging functionality for all OpsKit tools with:
- Multiple output targets (console, file, rotating files)
- Configurable log levels and formats
- Tool-specific log files
- Colorized console output
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Import OpsKit environment configuration using OPSKIT_BASE_PATH
if 'OPSKIT_BASE_PATH' in os.environ:
    sys.path.insert(0, os.environ['OPSKIT_BASE_PATH'])
    from core.env import env
    env_available = True
else:
    env_available = False

try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)
    colorama_available = True
except ImportError:
    colorama_available = False


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': Fore.CYAN if colorama_available else '',
        'INFO': '',  # No color for INFO logs (black/default)
        'WARNING': Fore.YELLOW if colorama_available else '',
        'ERROR': Fore.RED if colorama_available else '',
        'CRITICAL': Fore.RED + Style.BRIGHT if colorama_available else '',
    }
    
    def format(self, record):
        # Get the original formatted message
        formatted = super().format(record)
        
        # Add color if available
        if colorama_available:
            color = self.COLORS.get(record.levelname, '')
            reset = Style.RESET_ALL
            return f"{color}{formatted}{reset}"
        
        return formatted


class OpsKitLogger:
    """Unified logger for OpsKit tools"""
    
    _loggers: Dict[str, logging.Logger] = {}
    _initialized: bool = False
    _log_dir: Optional[Path] = None
    
    @classmethod
    def _parse_size(cls, size_str: str) -> int:
        """Parse size string like '10MB' to bytes"""
        size_str = size_str.upper().strip()
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024
        }
        
        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                number_str = size_str[:-len(suffix)].strip()
                try:
                    return int(float(number_str) * multiplier)
                except ValueError:
                    pass
        
        # Default to 10MB if parsing fails
        return 10 * 1024 * 1024
    
    @classmethod
    def initialize(cls, log_dir: Optional[str] = None, 
                  console_level: Optional[str] = None,
                  file_level: Optional[str] = None,
                  console_simple_format: Optional[bool] = None,
                  file_enabled: Optional[bool] = None) -> None:
        """Initialize the logging system with environment variable support"""
        if cls._initialized:
            return
        
        # Set log directory
        cls._log_dir = Path(log_dir) if log_dir else Path(env.logs_dir)
        cls._log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set configuration from environment variables
        console_level_to_use = console_level or (env.log_level if env_available else 'INFO')
        file_level_to_use = file_level or (env.log_file_level if env_available else 'DEBUG')
        
        cls._console_level = getattr(logging, console_level_to_use.upper())
        cls._file_level = getattr(logging, file_level_to_use.upper())
        cls._console_simple_format = (console_simple_format 
            if console_simple_format is not None else (env.log_simple_format if env_available else True))
        cls._file_enabled = (file_enabled 
            if file_enabled is not None else (env.log_file_enabled if env_available else False))
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str, tool_name: Optional[str] = None) -> logging.Logger:
        """
        Get or create a logger instance
        
        Args:
            name: Logger name (usually module name)
            tool_name: Optional tool name for tool-specific log files
        
        Returns:
            Configured logger instance
        """
        if not cls._initialized:
            cls.initialize()
        
        # Create unique logger name
        logger_key = f"{tool_name}.{name}" if tool_name else name
        
        if logger_key in cls._loggers:
            return cls._loggers[logger_key]
        
        # Create new logger
        logger = logging.getLogger(logger_key)
        # Set logger to the lowest level, let handlers control actual filtering
        logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(cls._console_level)
        
        # Choose console format based on configuration
        if cls._console_simple_format:
            console_format = '%(message)s'
            console_formatter = ColoredFormatter(console_format)
        else:
            console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            console_formatter = ColoredFormatter(
                console_format,
                datefmt='%H:%M:%S'
            )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler for general logs (only if file logging is enabled)
        if cls._file_enabled:
            # Parse max file size from environment
            max_size_str = env.log_max_size if env_available else '10MB'
            max_size_bytes = cls._parse_size(max_size_str)
            max_files = env.log_max_files if env_available else 5
            
            general_log_file = cls._log_dir / 'opskit.log'
            file_handler = logging.handlers.RotatingFileHandler(
                general_log_file,
                maxBytes=max_size_bytes,
                backupCount=max_files,
                encoding='utf-8'
            )
            file_handler.setLevel(cls._file_level)
            
            file_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            file_formatter = logging.Formatter(file_format)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            # Tool-specific log file if tool_name provided
            if tool_name:
                tool_log_file = cls._log_dir / f'{tool_name}.log'
                tool_handler = logging.handlers.RotatingFileHandler(
                    tool_log_file,
                    maxBytes=max_size_bytes // 2,  # Half size for tool-specific logs
                    backupCount=3,
                    encoding='utf-8'
                )
                tool_handler.setLevel(cls._file_level)
                tool_handler.setFormatter(file_formatter)
                logger.addHandler(tool_handler)
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
        
        cls._loggers[logger_key] = logger
        return logger
    
    @classmethod
    def set_level(cls, level: str, target: str = 'both') -> None:
        """
        Change logging level for existing loggers
        
        Args:
            level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            target: Target to update ('console', 'file', 'both')
        """
        new_level = getattr(logging, level.upper())
        
        for logger in cls._loggers.values():
            for handler in logger.handlers:
                if target == 'both':
                    handler.setLevel(new_level)
                elif target == 'console' and isinstance(handler, logging.StreamHandler):
                    handler.setLevel(new_level)
                elif target == 'file' and isinstance(handler, logging.handlers.RotatingFileHandler):
                    handler.setLevel(new_level)
    
    @classmethod
    def add_handler(cls, logger_name: str, handler: logging.Handler) -> None:
        """Add a custom handler to a specific logger"""
        if logger_name in cls._loggers:
            cls._loggers[logger_name].addHandler(handler)
    
    @classmethod
    def get_log_files(cls) -> Dict[str, str]:
        """Get information about current log files"""
        if not cls._initialized:
            cls.initialize()
        
        log_files = {}
        
        if cls._log_dir and cls._log_dir.exists():
            for log_file in cls._log_dir.glob('*.log'):
                try:
                    stat = log_file.stat()
                    log_files[log_file.name] = {
                        'path': str(log_file),
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    }
                except Exception:
                    log_files[log_file.name] = {
                        'path': str(log_file),
                        'size': 'unknown',
                        'modified': 'unknown'
                    }
        
        return log_files
    
    @classmethod
    def cleanup_old_logs(cls, days: int = 7) -> int:
        """
        Clean up old log files
        
        Args:
            days: Remove log files older than this many days
        
        Returns:
            Number of files removed
        """
        if not cls._log_dir or not cls._log_dir.exists():
            return 0
        
        removed_count = 0
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for log_file in cls._log_dir.glob('*.log*'):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    removed_count += 1
            except Exception:
                pass
        
        return removed_count


# Convenience functions for easy access
def get_logger(name: str, tool_name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name (usually __name__)
        tool_name: Optional tool name for tool-specific logging
    
    Returns:
        Configured logger instance
    
    Example:
        logger = get_logger(__name__)
        logger = get_logger(__name__, 'mysql-sync')
    """
    return OpsKitLogger.get_logger(name, tool_name)


def setup_logging(log_dir: Optional[str] = None,
                 console_level: Optional[str] = None,
                 file_level: Optional[str] = None,
                 console_simple_format: Optional[bool] = None,
                 file_enabled: Optional[bool] = None) -> None:
    """
    Initialize the logging system with environment variable support
    
    Args:
        log_dir: Directory for log files (uses env.logs_dir if None)
        console_level: Console logging level (uses env.log_level if None)
        file_level: File logging level (uses env.log_file_level if None)
        console_simple_format: Use simple format for console output (uses env.log_simple_format if None)
        file_enabled: Enable file logging (uses env.log_file_enabled if None)
    
    Example:
        setup_logging()  # Use all environment defaults
        setup_logging(console_level='DEBUG')
        setup_logging(log_dir='/custom/log/path', file_enabled=True)
    """
    OpsKitLogger.initialize(log_dir, console_level, file_level, console_simple_format, file_enabled)


def set_log_level(level: str, target: str = 'both') -> None:
    """
    Change logging level
    
    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        target: Target to update ('console', 'file', 'both')
    
    Example:
        set_log_level('DEBUG')
        set_log_level('WARNING', 'console')
    """
    OpsKitLogger.set_level(level, target)


def get_log_info() -> Dict[str, Any]:
    """Get information about current logging setup"""
    return {
        'initialized': OpsKitLogger._initialized,
        'log_directory': str(OpsKitLogger._log_dir) if OpsKitLogger._log_dir else None,
        'active_loggers': list(OpsKitLogger._loggers.keys()),
        'log_files': OpsKitLogger.get_log_files()
    }



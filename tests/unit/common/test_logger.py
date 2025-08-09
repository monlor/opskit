"""Tests for common/python/logger.py"""

import pytest
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Import the logger module
import sys
import os

# Add the common/python directory to the path for testing
TEST_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(TEST_DIR / 'common' / 'python'))

from logger import OpsKitLogger, get_logger, setup_logging, set_log_level, get_log_info, ColoredFormatter


class TestColoredFormatter:
    """Test cases for ColoredFormatter"""
    
    def test_format_without_colorama(self):
        """Test formatting without colorama available"""
        with patch('logger.colorama_available', False):
            formatter = ColoredFormatter('%(levelname)s - %(message)s')
            record = logging.LogRecord(
                name='test', level=logging.INFO, pathname='', lineno=0,
                msg='Test message', args=(), exc_info=None
            )
            result = formatter.format(record)
            assert result == 'INFO - Test message'
    
    def test_format_with_colorama(self):
        """Test formatting with colorama available"""
        with patch('logger.colorama_available', True), \
             patch('logger.Fore') as mock_fore, \
             patch('logger.Style') as mock_style:
            
            mock_fore.GREEN = '\033[32m'
            mock_style.RESET_ALL = '\033[0m'
            
            formatter = ColoredFormatter('%(levelname)s - %(message)s')
            record = logging.LogRecord(
                name='test', level=logging.INFO, pathname='', lineno=0,
                msg='Test message', args=(), exc_info=None
            )
            result = formatter.format(record)
            assert '\033[32m' in result  # Contains color code
            assert '\033[0m' in result   # Contains reset code


class TestOpsKitLogger:
    """Test cases for OpsKitLogger"""
    
    def setup_method(self):
        """Reset logger state before each test"""
        OpsKitLogger._loggers.clear()
        OpsKitLogger._initialized = False
        OpsKitLogger._log_dir = None
    
    def test_parse_size_mb(self):
        """Test parsing size string in MB"""
        result = OpsKitLogger._parse_size('10MB')
        assert result == 10 * 1024 * 1024
    
    def test_parse_size_kb(self):
        """Test parsing size string in KB"""
        result = OpsKitLogger._parse_size('500KB')
        assert result == 500 * 1024
    
    def test_parse_size_gb(self):
        """Test parsing size string in GB"""
        result = OpsKitLogger._parse_size('2GB')
        assert result == 2 * 1024 * 1024 * 1024
    
    def test_parse_size_invalid(self):
        """Test parsing invalid size string returns default"""
        result = OpsKitLogger._parse_size('invalid')
        assert result == 10 * 1024 * 1024  # Default 10MB
    
    def test_initialize_basic(self, tmp_path):
        """Test basic logger initialization"""
        with patch('logger.env_available', False):
            OpsKitLogger.initialize(
                log_dir=str(tmp_path),
                console_level='INFO',
                file_level='DEBUG',
                console_simple_format=False,
                file_enabled=False
            )
            
            assert OpsKitLogger._initialized is True
            assert OpsKitLogger._log_dir == tmp_path
            assert OpsKitLogger._console_level == logging.INFO
            assert OpsKitLogger._file_level == logging.DEBUG
    
    def test_initialize_with_env(self, tmp_path):
        """Test logger initialization with environment variables"""
        mock_env = Mock()
        mock_env.logs_dir = str(tmp_path)
        mock_env.log_level = 'DEBUG'
        mock_env.log_file_level = 'INFO'
        mock_env.log_simple_format = True
        mock_env.log_file_enabled = True
        
        with patch('logger.env_available', True), \
             patch('logger.env', mock_env):
            
            OpsKitLogger.initialize()
            
            assert OpsKitLogger._initialized is True
            assert OpsKitLogger._log_dir == tmp_path
            assert OpsKitLogger._console_level == logging.DEBUG
            assert OpsKitLogger._file_level == logging.INFO
            assert OpsKitLogger._console_simple_format is True
            assert OpsKitLogger._file_enabled is True
    
    def test_get_logger_console_only(self, tmp_path):
        """Test getting logger with console output only"""
        with patch('logger.env_available', False):
            OpsKitLogger.initialize(
                log_dir=str(tmp_path),
                console_level='INFO',
                file_enabled=False
            )
            
            logger = OpsKitLogger.get_logger('test_module')
            
            assert isinstance(logger, logging.Logger)
            assert logger.name == 'test_module'
            assert len(logger.handlers) == 1
            assert isinstance(logger.handlers[0], logging.StreamHandler)
    
    def test_get_logger_with_file(self, tmp_path):
        """Test getting logger with file output"""
        mock_env = Mock()
        mock_env.logs_dir = str(tmp_path)
        mock_env.log_level = 'INFO'
        mock_env.log_file_level = 'DEBUG'
        mock_env.log_simple_format = False
        mock_env.log_file_enabled = True
        mock_env.log_max_size = '10MB'
        mock_env.log_max_files = 5
        
        with patch('logger.env_available', True), \
             patch('logger.env', mock_env):
            
            logger = OpsKitLogger.get_logger('test_module')
            
            assert len(logger.handlers) == 2  # Console + file handler
            assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
            assert any(isinstance(h, logging.handlers.RotatingFileHandler) for h in logger.handlers)
    
    def test_get_logger_with_tool_name(self, tmp_path):
        """Test getting logger with tool-specific logging"""
        mock_env = Mock()
        mock_env.logs_dir = str(tmp_path)
        mock_env.log_level = 'INFO'
        mock_env.log_file_level = 'DEBUG'
        mock_env.log_simple_format = False
        mock_env.log_file_enabled = True
        mock_env.log_max_size = '10MB'
        mock_env.log_max_files = 5
        
        with patch('logger.env_available', True), \
             patch('logger.env', mock_env):
            
            logger = OpsKitLogger.get_logger('test_module', 'mysql-sync')
            
            assert len(logger.handlers) == 3  # Console + general file + tool file
            assert logger.name == 'mysql-sync.test_module'
    
    def test_get_logger_cached(self, tmp_path):
        """Test that loggers are cached properly"""
        with patch('logger.env_available', False):
            OpsKitLogger.initialize(log_dir=str(tmp_path), file_enabled=False)
            
            logger1 = OpsKitLogger.get_logger('test_module')
            logger2 = OpsKitLogger.get_logger('test_module')
            
            assert logger1 is logger2
            assert len(OpsKitLogger._loggers) == 1
    
    def test_set_level_both(self, tmp_path):
        """Test setting log level for both console and file"""
        mock_env = Mock()
        mock_env.logs_dir = str(tmp_path)
        mock_env.log_level = 'INFO'
        mock_env.log_file_level = 'DEBUG'
        mock_env.log_simple_format = False
        mock_env.log_file_enabled = True
        mock_env.log_max_size = '10MB'
        mock_env.log_max_files = 5
        
        with patch('logger.env_available', True), \
             patch('logger.env', mock_env):
            
            logger = OpsKitLogger.get_logger('test_module')
            OpsKitLogger.set_level('WARNING', 'both')
            
            for handler in logger.handlers:
                assert handler.level == logging.WARNING
    
    def test_set_level_console_only(self, tmp_path):
        """Test setting log level for console only"""
        mock_env = Mock()
        mock_env.logs_dir = str(tmp_path)
        mock_env.log_level = 'INFO'
        mock_env.log_file_level = 'DEBUG'
        mock_env.log_simple_format = False
        mock_env.log_file_enabled = True
        mock_env.log_max_size = '10MB'
        mock_env.log_max_files = 5
        
        with patch('logger.env_available', True), \
             patch('logger.env', mock_env):
            
            logger = OpsKitLogger.get_logger('test_module')
            original_file_level = None
            
            # Find file handler level before change
            for handler in logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    original_file_level = handler.level
                    break
            
            OpsKitLogger.set_level('WARNING', 'console')
            
            # Check console handler changed, file handler unchanged
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.handlers.RotatingFileHandler):
                    assert handler.level == logging.WARNING
                elif isinstance(handler, logging.handlers.RotatingFileHandler):
                    assert handler.level == original_file_level
    
    def test_add_handler(self, tmp_path):
        """Test adding custom handler to logger"""
        with patch('logger.env_available', False):
            OpsKitLogger.initialize(log_dir=str(tmp_path), file_enabled=False)
            
            logger = OpsKitLogger.get_logger('test_module')
            original_handler_count = len(logger.handlers)
            
            custom_handler = logging.StreamHandler()
            OpsKitLogger.add_handler('test_module', custom_handler)
            
            assert len(logger.handlers) == original_handler_count + 1
            assert custom_handler in logger.handlers
    
    def test_get_log_files(self, tmp_path):
        """Test getting log file information"""
        # Create some test log files
        log_file1 = tmp_path / 'opskit.log'
        log_file2 = tmp_path / 'mysql-sync.log'
        log_file1.write_text('Test log content')
        log_file2.write_text('Another log content')
        
        OpsKitLogger._log_dir = tmp_path
        OpsKitLogger._initialized = True
        
        log_files = OpsKitLogger.get_log_files()
        
        assert 'opskit.log' in log_files
        assert 'mysql-sync.log' in log_files
        assert log_files['opskit.log']['size'] > 0
        assert 'path' in log_files['opskit.log']
        assert 'modified' in log_files['opskit.log']
    
    def test_cleanup_old_logs(self, tmp_path):
        """Test cleaning up old log files"""
        import time
        
        # Create test log files
        old_log = tmp_path / 'old.log'
        recent_log = tmp_path / 'recent.log'
        old_log.write_text('Old log')
        recent_log.write_text('Recent log')
        
        # Make old log actually old
        old_time = time.time() - (8 * 24 * 60 * 60)  # 8 days ago
        os.utime(old_log, (old_time, old_time))
        
        OpsKitLogger._log_dir = tmp_path
        
        removed_count = OpsKitLogger.cleanup_old_logs(days=7)
        
        assert removed_count == 1
        assert not old_log.exists()
        assert recent_log.exists()


class TestConvenienceFunctions:
    """Test cases for convenience functions"""
    
    def setup_method(self):
        """Reset logger state before each test"""
        OpsKitLogger._loggers.clear()
        OpsKitLogger._initialized = False
        OpsKitLogger._log_dir = None
    
    def test_get_logger_function(self, tmp_path):
        """Test get_logger convenience function"""
        with patch('logger.env_available', False):
            logger = get_logger('test_module')
            assert isinstance(logger, logging.Logger)
    
    def test_setup_logging_function(self, tmp_path):
        """Test setup_logging convenience function"""
        with patch('logger.env_available', False):
            setup_logging(
                log_dir=str(tmp_path),
                console_level='DEBUG',
                file_enabled=False
            )
            
            assert OpsKitLogger._initialized is True
            assert OpsKitLogger._log_dir == tmp_path
    
    def test_set_log_level_function(self, tmp_path):
        """Test set_log_level convenience function"""
        with patch('logger.env_available', False):
            setup_logging(log_dir=str(tmp_path), file_enabled=False)
            logger = get_logger('test_module')
            
            set_log_level('ERROR')
            
            for handler in logger.handlers:
                assert handler.level == logging.ERROR
    
    def test_get_log_info_function(self, tmp_path):
        """Test get_log_info convenience function"""
        with patch('logger.env_available', False):
            setup_logging(log_dir=str(tmp_path), file_enabled=False)
            get_logger('test_module')
            
            info = get_log_info()
            
            assert info['initialized'] is True
            assert info['log_directory'] == str(tmp_path)
            assert 'test_module' in info['active_loggers']
            assert isinstance(info['log_files'], dict)


@pytest.mark.integration 
class TestLoggerIntegration:
    """Integration tests for the logger system"""
    
    def test_full_logging_workflow(self, tmp_path):
        """Test complete logging workflow with file output"""
        mock_env = Mock()
        mock_env.logs_dir = str(tmp_path)
        mock_env.log_level = 'DEBUG'
        mock_env.log_file_level = 'INFO'
        mock_env.log_simple_format = False
        mock_env.log_file_enabled = True
        mock_env.log_max_size = '1MB'
        mock_env.log_max_files = 3
        
        with patch('logger.env_available', True), \
             patch('logger.env', mock_env):
            
            # Setup logging
            setup_logging()
            
            # Get logger and log messages
            logger = get_logger(__name__, 'test-tool')
            logger.info('Test info message')
            logger.warning('Test warning message')
            logger.error('Test error message')
            
            # Verify log files were created
            general_log = tmp_path / 'opskit.log'
            tool_log = tmp_path / 'test-tool.log'
            
            assert general_log.exists()
            assert tool_log.exists()
            
            # Check log file contents
            general_content = general_log.read_text()
            tool_content = tool_log.read_text()
            
            assert 'Test info message' in general_content
            assert 'Test warning message' in general_content
            assert 'Test info message' in tool_content
            assert 'Test warning message' in tool_content
    
    def test_log_rotation(self, tmp_path):
        """Test log file rotation functionality"""
        mock_env = Mock()
        mock_env.logs_dir = str(tmp_path)
        mock_env.log_level = 'DEBUG'
        mock_env.log_file_level = 'DEBUG'
        mock_env.log_simple_format = False
        mock_env.log_file_enabled = True
        mock_env.log_max_size = '100B'  # Very small to trigger rotation
        mock_env.log_max_files = 2
        
        with patch('logger.env_available', True), \
             patch('logger.env', mock_env):
            
            logger = get_logger('test_rotation')
            
            # Write enough to trigger rotation
            for i in range(20):
                logger.info(f'This is a long test message number {i} that should help trigger log rotation')
            
            # Check for rotated files
            log_files = list(tmp_path.glob('opskit.log*'))
            assert len(log_files) > 1  # Should have main + rotated files
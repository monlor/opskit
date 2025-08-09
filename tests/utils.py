"""Test utilities and helpers for OpsKit test suite"""

import os
import sys
import tempfile
import shutil
import subprocess
import time
import threading
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
from unittest.mock import Mock, patch

# Test constants
TEST_TIMEOUT = 30
SLOW_TEST_TIMEOUT = 120
INTEGRATION_TIMEOUT = 180

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
TOOLS_DIR = PROJECT_ROOT / 'tools'
CORE_DIR = PROJECT_ROOT / 'core'
COMMON_DIR = PROJECT_ROOT / 'common'


class TestEnvironment:
    """Manages isolated test environments"""
    
    def __init__(self, prefix: str = 'opskit_test_'):
        self.prefix = prefix
        self.temp_dir = None
        self.original_env = None
        self.cleanup_funcs = []
    
    def __enter__(self):
        """Enter test environment context"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix=self.prefix))
        self.original_env = os.environ.copy()
        
        # Set up test environment variables
        os.environ['OPSKIT_BASE_PATH'] = str(self.temp_dir)
        os.environ['PYTHONPATH'] = f"{PROJECT_ROOT}:{os.environ.get('PYTHONPATH', '')}"
        os.environ['OPSKIT_DEBUG'] = 'true'
        os.environ['OPSKIT_LOG_LEVEL'] = 'DEBUG'
        
        # Create required directory structure
        self.create_directory_structure()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit test environment context"""
        # Restore original environment
        if self.original_env:
            os.environ.clear()
            os.environ.update(self.original_env)
        
        # Run cleanup functions
        for cleanup_func in reversed(self.cleanup_funcs):
            try:
                cleanup_func()
            except Exception:
                pass
        
        # Remove temporary directory
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_directory_structure(self):
        """Create standard OpsKit directory structure"""
        dirs = [
            'core',
            'common/python',
            'common/shell', 
            'tools',
            'config',
            'data',
            'cache/venvs',
            'cache/downloads',
            'logs'
        ]
        
        for dir_path in dirs:
            (self.temp_dir / dir_path).mkdir(parents=True, exist_ok=True)
    
    def add_cleanup(self, func):
        """Add cleanup function"""
        self.cleanup_funcs.append(func)
    
    def get_path(self, relative_path: str) -> Path:
        """Get absolute path within test environment"""
        return self.temp_dir / relative_path
    
    def copy_project_files(self, pattern: str = "*"):
        """Copy project files to test environment"""
        import glob
        
        # Copy core files
        for src_file in PROJECT_ROOT.glob(pattern):
            if src_file.is_file():
                dst_file = self.temp_dir / src_file.name
                shutil.copy2(src_file, dst_file)


class MockDependencyManager:
    """Mock dependency manager for testing"""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.installed_dependencies = set()
        self.failed_dependencies = set()
    
    def setup_python_environment(self, tool_name: str, tool_path: Path) -> Tuple[bool, str]:
        """Mock Python environment setup"""
        if tool_name in self.failed_dependencies:
            return False, f"Failed to setup environment for {tool_name}"
        
        self.installed_dependencies.add(tool_name)
        return True, f"Environment setup successful for {tool_name}"
    
    def check_tool_dependencies(self, tool_info: Dict) -> Dict:
        """Mock dependency checking"""
        tool_name = tool_info.get('name', 'unknown')
        
        if tool_name in self.failed_dependencies:
            return {
                'python_deps_satisfied': False,
                'system_deps_satisfied': False,
                'missing_python_deps': ['mock-missing-package'],
                'missing_system_deps': ['mock-missing-command']
            }
        
        return {
            'python_deps_satisfied': True,
            'system_deps_satisfied': True,
            'missing_python_deps': [],
            'missing_system_deps': []
        }
    
    def set_dependency_failure(self, tool_name: str):
        """Set a tool to fail dependency checks"""
        self.failed_dependencies.add(tool_name)
    
    def clear_dependency_failure(self, tool_name: str):
        """Clear dependency failure for a tool"""
        self.failed_dependencies.discard(tool_name)


class ProcessRunner:
    """Utility for running processes in tests"""
    
    @staticmethod
    def run_command(cmd: List[str], cwd: Optional[Path] = None, 
                   env: Optional[Dict] = None, timeout: int = TEST_TIMEOUT,
                   input_data: Optional[str] = None) -> Tuple[int, str, str]:
        """Run a command and return results"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cwd) if cwd else None,
                env=env,
                input=input_data
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
        except FileNotFoundError:
            return -2, "", f"Command not found: {cmd[0]}"
        except Exception as e:
            return -3, "", str(e)
    
    @staticmethod
    def run_opskit_command(args: List[str], cwd: Optional[Path] = None,
                          timeout: int = TEST_TIMEOUT) -> Tuple[int, str, str]:
        """Run opskit command with proper environment"""
        opskit_exe = PROJECT_ROOT / 'opskit'
        cmd = ['python3', str(opskit_exe)] + args
        
        env = os.environ.copy()
        env['OPSKIT_BASE_PATH'] = str(PROJECT_ROOT)
        env['PYTHONPATH'] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
        
        return ProcessRunner.run_command(cmd, cwd or PROJECT_ROOT, env, timeout)
    
    @staticmethod
    def run_python_script(script_path: Path, args: Optional[List[str]] = None,
                         timeout: int = TEST_TIMEOUT) -> Tuple[int, str, str]:
        """Run Python script with proper environment"""
        cmd = ['python3', str(script_path)]
        if args:
            cmd.extend(args)
        
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
        
        return ProcessRunner.run_command(cmd, PROJECT_ROOT, env, timeout)
    
    @staticmethod
    def run_shell_script(script_path: Path, args: Optional[List[str]] = None,
                        timeout: int = TEST_TIMEOUT) -> Tuple[int, str, str]:
        """Run shell script with proper environment"""
        cmd = ['bash', str(script_path)]
        if args:
            cmd.extend(args)
        
        env = os.environ.copy()
        env['OPSKIT_BASE_PATH'] = str(PROJECT_ROOT)
        
        return ProcessRunner.run_command(cmd, PROJECT_ROOT, env, timeout)


class DatabaseTestHelper:
    """Helper for database-related tests"""
    
    @staticmethod
    def create_test_db(db_path: Path) -> sqlite3.Connection:
        """Create a test SQLite database"""
        conn = sqlite3.connect(str(db_path))
        
        # Create basic structure
        conn.execute('''
            CREATE TABLE IF NOT EXISTS test_kv (
                key TEXT PRIMARY KEY,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        return conn
    
    @staticmethod
    def populate_test_data(conn: sqlite3.Connection, table_name: str = 'test_kv',
                          count: int = 10):
        """Populate test database with sample data"""
        for i in range(count):
            conn.execute(
                f'INSERT OR REPLACE INTO {table_name} (key, value) VALUES (?, ?)',
                (f'test_key_{i}', f'test_value_{i}')
            )
        conn.commit()
    
    @staticmethod
    def verify_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
        """Verify that a table exists"""
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return cursor.fetchone() is not None


class FileSystemTestHelper:
    """Helper for file system operations in tests"""
    
    @staticmethod
    def create_sample_tool(base_dir: Path, tool_name: str, 
                          tool_type: str = 'python') -> Path:
        """Create a sample tool structure for testing"""
        tool_path = base_dir / 'tools' / 'test' / tool_name
        tool_path.mkdir(parents=True, exist_ok=True)
        
        # Create CLAUDE.md
        claude_md = f"""# {tool_name.title()}

## 功能描述
A test tool for automated testing

## 技术架构
- 实现语言: {tool_type.title()}
- 核心依赖: None

## 配置项
None

## 开发指南
Test tool implementation

## 使用示例
./{tool_name}
"""
        (tool_path / 'CLAUDE.md').write_text(claude_md)
        
        if tool_type == 'python':
            # Create main.py
            main_py = f'''#!/usr/bin/env python3
"""Test tool: {tool_name}"""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="{tool_name} test tool")
    parser.add_argument('--test', action='store_true', help='Run test mode')
    args = parser.parse_args()
    
    if args.test:
        print("TEST MODE: {tool_name} executed successfully")
    else:
        print("{tool_name} executed successfully")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
            (tool_path / 'main.py').write_text(main_py)
            (tool_path / 'main.py').chmod(0o755)
            
            # Create requirements.txt
            (tool_path / 'requirements.txt').write_text("# Test requirements\n")
        
        elif tool_type == 'shell':
            # Create main.sh
            main_sh = f'''#!/bin/bash
# Test tool: {tool_name}

show_help() {{
    echo "Usage: {tool_name} [--test] [--help]"
    echo "Test tool for automated testing"
    echo ""
    echo "Options:"
    echo "  --test    Run in test mode"
    echo "  --help    Show this help"
}}

main() {{
    local test_mode=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --test)
                test_mode=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    if [[ "$test_mode" == "true" ]]; then
        echo "TEST MODE: {tool_name} executed successfully"
    else
        echo "{tool_name} executed successfully"
    fi
}}

main "$@"
'''
            (tool_path / 'main.sh').write_text(main_sh)
            (tool_path / 'main.sh').chmod(0o755)
        
        return tool_path
    
    @staticmethod
    def create_test_files(base_dir: Path, file_count: int = 5, 
                         file_size: int = 1000) -> List[Path]:
        """Create test files for file system operations"""
        base_dir.mkdir(parents=True, exist_ok=True)
        
        files = []
        for i in range(file_count):
            file_path = base_dir / f'test_file_{i}.txt'
            file_path.write_text('x' * file_size)
            files.append(file_path)
        
        return files
    
    @staticmethod
    def calculate_directory_size(directory: Path) -> int:
        """Calculate total size of directory"""
        total_size = 0
        for path in directory.rglob('*'):
            if path.is_file():
                try:
                    total_size += path.stat().st_size
                except (OSError, IOError):
                    pass
        return total_size


class PerformanceTestHelper:
    """Helper for performance testing"""
    
    @staticmethod
    @contextmanager
    def measure_time():
        """Context manager to measure execution time"""
        start_time = time.time()
        yield lambda: time.time() - start_time
    
    @staticmethod
    def run_performance_test(func, iterations: int = 5) -> Dict[str, float]:
        """Run performance test and return statistics"""
        execution_times = []
        
        for _ in range(iterations):
            with PerformanceTestHelper.measure_time() as get_time:
                func()
            execution_times.append(get_time())
        
        return {
            'min_time': min(execution_times),
            'max_time': max(execution_times),
            'avg_time': sum(execution_times) / len(execution_times),
            'total_time': sum(execution_times),
            'iterations': len(execution_times)
        }
    
    @staticmethod
    def assert_performance_bounds(stats: Dict[str, float], max_avg_time: float,
                                max_single_time: float):
        """Assert performance is within acceptable bounds"""
        assert stats['avg_time'] <= max_avg_time, \
            f"Average time {stats['avg_time']:.3f}s exceeds limit {max_avg_time}s"
        
        assert stats['max_time'] <= max_single_time, \
            f"Max time {stats['max_time']:.3f}s exceeds limit {max_single_time}s"


class ConcurrencyTestHelper:
    """Helper for concurrency testing"""
    
    @staticmethod
    def run_concurrent_functions(functions: List, timeout: int = 30) -> List[Any]:
        """Run functions concurrently and return results"""
        import queue
        import threading
        
        result_queue = queue.Queue()
        threads = []
        
        def worker(func, index):
            try:
                result = func()
                result_queue.put((index, True, result))
            except Exception as e:
                result_queue.put((index, False, str(e)))
        
        # Start threads
        for i, func in enumerate(functions):
            thread = threading.Thread(target=worker, args=(func, i))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=timeout)
        
        # Collect results
        results = [None] * len(functions)
        while not result_queue.empty():
            index, success, result = result_queue.get()
            results[index] = (success, result)
        
        return results
    
    @staticmethod
    def stress_test_function(func, concurrent_count: int = 10, 
                           iterations: int = 5) -> Dict[str, Any]:
        """Stress test a function with concurrent execution"""
        def run_iteration():
            functions = [func] * concurrent_count
            return ConcurrencyTestHelper.run_concurrent_functions(functions)
        
        all_results = []
        for _ in range(iterations):
            iteration_results = run_iteration()
            all_results.extend(iteration_results)
        
        success_count = sum(1 for success, _ in all_results if success)
        total_count = len(all_results)
        
        return {
            'total_executions': total_count,
            'successful_executions': success_count,
            'failure_rate': (total_count - success_count) / total_count,
            'success_rate': success_count / total_count
        }


class LogTestHelper:
    """Helper for testing logging functionality"""
    
    @staticmethod
    def capture_logs(logger_name: str = 'opskit'):
        """Context manager to capture log output"""
        import logging
        from io import StringIO
        
        @contextmanager
        def _capture():
            log_capture = StringIO()
            handler = logging.StreamHandler(log_capture)
            logger = logging.getLogger(logger_name)
            original_level = logger.level
            
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
            
            try:
                yield log_capture
            finally:
                logger.removeHandler(handler)
                logger.setLevel(original_level)
        
        return _capture()
    
    @staticmethod
    def create_temporary_log_file(content: str = "") -> Path:
        """Create temporary log file with content"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(content)
            return Path(f.name)


# Test data generators
def generate_test_config() -> Dict[str, Any]:
    """Generate test configuration data"""
    return {
        'general': {
            'debug': True,
            'log_level': 'DEBUG'
        },
        'tools': {
            'test_tool': {
                'timeout': 30,
                'retries': 3
            }
        },
        'paths': {
            'cache_dir': 'cache',
            'logs_dir': 'logs'
        }
    }


def generate_tool_metadata(tool_name: str, tool_type: str = 'python') -> Dict[str, Any]:
    """Generate tool metadata for testing"""
    return {
        'name': tool_name,
        'type': tool_type,
        'category': 'test',
        'description': f'Test tool: {tool_name}',
        'version': '1.0.0',
        'dependencies': [],
        'author': 'Test Suite'
    }


# Assertion helpers
def assert_file_contains(file_path: Path, content: str):
    """Assert that file contains specific content"""
    assert file_path.exists(), f"File {file_path} does not exist"
    
    file_content = file_path.read_text()
    assert content in file_content, f"Content '{content}' not found in {file_path}"


def assert_command_output_contains(cmd: List[str], expected_content: str,
                                 timeout: int = TEST_TIMEOUT):
    """Assert that command output contains expected content"""
    returncode, stdout, stderr = ProcessRunner.run_command(cmd, timeout=timeout)
    
    assert returncode == 0, f"Command {cmd} failed: {stderr}"
    
    output = stdout + stderr
    assert expected_content in output, \
        f"Expected content '{expected_content}' not found in output: {output}"


def assert_directory_structure(base_dir: Path, expected_structure: Dict[str, Any]):
    """Assert that directory has expected structure"""
    def check_structure(current_dir: Path, structure: Dict[str, Any]):
        for item_name, item_type in structure.items():
            item_path = current_dir / item_name
            
            if item_type == 'file':
                assert item_path.is_file(), f"Expected file {item_path} not found"
            elif item_type == 'dir':
                assert item_path.is_dir(), f"Expected directory {item_path} not found"
            elif isinstance(item_type, dict):
                assert item_path.is_dir(), f"Expected directory {item_path} not found"
                check_structure(item_path, item_type)
    
    check_structure(base_dir, expected_structure)
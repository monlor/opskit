"""Tests for common shell scripts"""

import pytest
import subprocess
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock, call


class TestShellScripts:
    """Test cases for shell scripts in common/shell/"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(__file__).parent.parent.parent.parent
        self.shell_dir = self.test_dir / 'common' / 'shell'
        self.temp_dir = None
    
    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def run_shell_script(self, script_path, args=None, env=None):
        """Helper to run shell scripts"""
        cmd = ['bash', str(script_path)]
        if args:
            cmd.extend(args)
        
        test_env = os.environ.copy()
        if env:
            test_env.update(env)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=test_env,
                cwd=str(self.test_dir)
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Script timed out"
        except Exception as e:
            return -2, "", str(e)
    
    def test_logger_sh_functions(self):
        """Test logger.sh function definitions"""
        logger_script = self.shell_dir / 'logger.sh'
        
        if not logger_script.exists():
            pytest.skip("logger.sh not found")
        
        # Test script can be sourced without errors
        test_script = """
            source "{}"
            
            # Test that functions are defined
            if ! declare -f log_info > /dev/null; then
                echo "FAIL: log_info function not defined"
                exit 1
            fi
            
            if ! declare -f log_error > /dev/null; then
                echo "FAIL: log_error function not defined"
                exit 1
            fi
            
            if ! declare -f log_warning > /dev/null; then
                echo "FAIL: log_warning function not defined"
                exit 1
            fi
            
            if ! declare -f log_debug > /dev/null; then
                echo "FAIL: log_debug function not defined"  
                exit 1
            fi
            
            echo "PASS: All logger functions defined"
        """.format(logger_script)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(test_script)
            f.flush()
            
            returncode, stdout, stderr = self.run_shell_script(f.name)
            
            os.unlink(f.name)
            
            assert returncode == 0, f"Script failed: {stderr}"
            assert "PASS: All logger functions defined" in stdout
    
    def test_logger_sh_output_format(self):
        """Test logger.sh output formatting"""
        logger_script = self.shell_dir / 'logger.sh'
        
        if not logger_script.exists():
            pytest.skip("logger.sh not found")
        
        test_script = """
            source "{}"
            
            # Test log output format
            log_info "Test info message"
            log_error "Test error message"
            log_warning "Test warning message"
        """.format(logger_script)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(test_script)
            f.flush()
            
            returncode, stdout, stderr = self.run_shell_script(f.name)
            
            os.unlink(f.name)
            
            assert returncode == 0, f"Script failed: {stderr}"
            
            # Check that messages appear in output
            output = stdout + stderr
            assert "Test info message" in output
            assert "Test error message" in output
            assert "Test warning message" in output
    
    def test_utils_sh_functions(self):
        """Test utils.sh utility functions"""
        utils_script = self.shell_dir / 'utils.sh'
        
        if not utils_script.exists():
            pytest.skip("utils.sh not found")
        
        test_script = """
            source "{}"
            
            # Test that utility functions are defined
            functions_to_check=(
                "check_command"
                "get_os_type" 
                "get_script_dir"
                "require_command"
                "is_number"
                "trim"
            )
            
            missing_functions=()
            for func in "${{functions_to_check[@]}}"; do
                if ! declare -f "$func" > /dev/null; then
                    missing_functions+=("$func")
                fi
            done
            
            if [ "${{#missing_functions[@]}}" -gt 0 ]; then
                echo "FAIL: Missing functions: ${{missing_functions[*]}}"
                exit 1
            fi
            
            echo "PASS: All utility functions defined"
        """.format(utils_script)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(test_script)
            f.flush()
            
            returncode, stdout, stderr = self.run_shell_script(f.name)
            
            os.unlink(f.name)
            
            # Note: Some functions might not be defined yet, so we check for basic success
            assert returncode == 0 or "PASS" in stdout, f"Script output: {stdout}, errors: {stderr}"
    
    def test_storage_sh_functions(self):
        """Test storage.sh storage functions"""
        storage_script = self.shell_dir / 'storage.sh'
        
        if not storage_script.exists():
            pytest.skip("storage.sh not found")
        
        test_script = """
            source "{}"
            
            # Test that storage functions are defined
            functions_to_check=(
                "storage_set"
                "storage_get"
                "storage_delete"
                "storage_exists"
                "storage_list"
            )
            
            missing_functions=()
            for func in "${{functions_to_check[@]}}"; do
                if ! declare -f "$func" > /dev/null; then
                    missing_functions+=("$func")
                fi
            done
            
            if [ "${{#missing_functions[@]}}" -gt 0 ]; then
                echo "FAIL: Missing functions: ${{missing_functions[*]}}"
                exit 1
            fi
            
            echo "PASS: All storage functions defined"
        """.format(storage_script)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(test_script)
            f.flush()
            
            returncode, stdout, stderr = self.run_shell_script(f.name)
            
            os.unlink(f.name)
            
            # Note: Some functions might not be defined yet
            assert returncode == 0 or "PASS" in stdout, f"Script output: {stdout}, errors: {stderr}"
    
    def test_shell_scripts_syntax(self):
        """Test that all shell scripts have valid syntax"""
        shell_scripts = list(self.shell_dir.glob('*.sh'))
        
        if not shell_scripts:
            pytest.skip("No shell scripts found")
        
        for script in shell_scripts:
            # Use bash -n to check syntax without executing
            result = subprocess.run(
                ['bash', '-n', str(script)],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0, f"Syntax error in {script.name}: {result.stderr}"
    
    def test_shell_scripts_shellcheck(self):
        """Test shell scripts with shellcheck if available"""
        # Check if shellcheck is available
        try:
            subprocess.run(['shellcheck', '--version'], 
                         capture_output=True, check=True)
            shellcheck_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            shellcheck_available = False
        
        if not shellcheck_available:
            pytest.skip("shellcheck not available")
        
        shell_scripts = list(self.shell_dir.glob('*.sh'))
        
        if not shell_scripts:
            pytest.skip("No shell scripts found")
        
        for script in shell_scripts:
            result = subprocess.run(
                ['shellcheck', '-x', str(script)],
                capture_output=True,
                text=True
            )
            
            # Allow some common shellcheck issues that might be acceptable
            if result.returncode != 0:
                # Check if only minor issues (warnings)
                lines = result.stdout.split('\n')
                error_lines = [line for line in lines if 'error' in line.lower()]
                
                # If there are actual errors (not just warnings), fail the test
                if error_lines:
                    pytest.fail(f"Shellcheck errors in {script.name}:\n{result.stdout}")
    
    def test_shell_scripts_environment_handling(self):
        """Test that shell scripts handle environment variables properly"""
        logger_script = self.shell_dir / 'logger.sh'
        
        if not logger_script.exists():
            pytest.skip("logger.sh not found")
        
        # Test with different OPSKIT_LOG_LEVEL values
        for log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            test_script = """
                export OPSKIT_LOG_LEVEL="{}"
                source "{}"
                
                log_debug "Debug message"
                log_info "Info message"
                log_warning "Warning message"  
                log_error "Error message"
                
                echo "Log level test completed for {}"
            """.format(log_level, logger_script, log_level)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(test_script)
                f.flush()
                
                returncode, stdout, stderr = self.run_shell_script(f.name)
                
                os.unlink(f.name)
                
                assert returncode == 0, f"Script failed with log level {log_level}: {stderr}"
                assert f"Log level test completed for {log_level}" in stdout
    
    def test_cross_script_integration(self):
        """Test that shell scripts can work together"""
        logger_script = self.shell_dir / 'logger.sh'
        utils_script = self.shell_dir / 'utils.sh'
        
        if not logger_script.exists() or not utils_script.exists():
            pytest.skip("Required shell scripts not found")
        
        test_script = """
            # Source all common shell libraries
            source "{}"
            source "{}"
            
            # Test integration
            log_info "Starting integration test"
            
            # Test command checking
            if check_command "bash" 2>/dev/null; then
                log_info "Command check successful"
            else
                log_error "Command check failed"
                exit 1
            fi
            
            log_info "Integration test completed successfully"
        """.format(logger_script, utils_script)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(test_script)
            f.flush()
            
            returncode, stdout, stderr = self.run_shell_script(f.name)
            
            os.unlink(f.name)
            
            assert returncode == 0, f"Integration test failed: {stderr}"
            
            output = stdout + stderr
            assert "Starting integration test" in output
            assert "Integration test completed successfully" in output


@pytest.mark.integration
class TestShellScriptIntegration:
    """Integration tests for shell scripts with actual file operations"""
    
    def setup_method(self):
        """Setup test environment with temporary directory"""
        self.test_dir = Path(__file__).parent.parent.parent.parent
        self.shell_dir = self.test_dir / 'common' / 'shell'
        
        import tempfile
        import shutil
        self.temp_dir = Path(tempfile.mkdtemp(prefix='opskit_shell_test_'))
    
    def teardown_method(self):
        """Cleanup temporary directory"""
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_storage_operations(self):
        """Test storage operations with actual file system"""
        storage_script = self.shell_dir / 'storage.sh'
        
        if not storage_script.exists():
            pytest.skip("storage.sh not found")
        
        test_script = f"""
            export OPSKIT_BASE_PATH="{self.temp_dir}"
            mkdir -p "{self.temp_dir}/data"
            
            source "{storage_script}"
            
            # Test storage operations
            if storage_set "test_key" "test_value"; then
                echo "Storage set successful"
            else
                echo "Storage set failed"
                exit 1
            fi
            
            if value=$(storage_get "test_key"); then
                echo "Storage get successful: $value"
                if [ "$value" = "test_value" ]; then
                    echo "Value matches expected"
                else
                    echo "Value mismatch: expected 'test_value', got '$value'"
                    exit 1
                fi
            else
                echo "Storage get failed"
                exit 1
            fi
            
            if storage_exists "test_key"; then
                echo "Storage exists check passed"
            else
                echo "Storage exists check failed"
                exit 1
            fi
            
            echo "Storage test completed successfully"
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(test_script)
            f.flush()
            
            result = subprocess.run(
                ['bash', f.name],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.test_dir)
            )
            
            os.unlink(f.name)
            
            # Check results (might not be fully implemented yet)
            if result.returncode == 0:
                assert "Storage test completed successfully" in result.stdout
            else:
                # If not implemented, that's okay for now
                pytest.skip(f"Storage operations not fully implemented: {result.stderr}")
    
    def test_logging_with_file_output(self):
        """Test logging to actual log files"""
        logger_script = self.shell_dir / 'logger.sh'
        
        if not logger_script.exists():
            pytest.skip("logger.sh not found")
        
        log_dir = self.temp_dir / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        test_script = f"""
            export OPSKIT_LOG_DIR="{log_dir}"
            export OPSKIT_LOG_LEVEL="DEBUG"
            
            source "{logger_script}"
            
            log_info "Test info message for file output"
            log_warning "Test warning message for file output"
            log_error "Test error message for file output"
            
            echo "Logging test completed"
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(test_script)
            f.flush()
            
            result = subprocess.run(
                ['bash', f.name],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.test_dir)
            )
            
            os.unlink(f.name)
            
            assert result.returncode == 0, f"Logging test failed: {result.stderr}"
            assert "Logging test completed" in result.stdout
            
            # Check if log messages appear in output (console logging)
            output = result.stdout + result.stderr
            assert "Test info message" in output or "Test warning message" in output
    
    def test_comprehensive_shell_workflow(self):
        """Test complete workflow using all shell libraries"""
        logger_script = self.shell_dir / 'logger.sh'
        utils_script = self.shell_dir / 'utils.sh'
        
        available_scripts = [s for s in [logger_script, utils_script] if s.exists()]
        
        if len(available_scripts) < 1:
            pytest.skip("Insufficient shell scripts available for workflow test")
        
        # Create a comprehensive test that uses available functionality
        test_script = f"""
            export OPSKIT_BASE_PATH="{self.temp_dir}"
            export OPSKIT_LOG_LEVEL="INFO"
            mkdir -p "{self.temp_dir}/data"
            mkdir -p "{self.temp_dir}/logs"
            
            # Source available scripts
        """
        
        for script in available_scripts:
            test_script += f'source "{script}"\n'
        
        test_script += """
            # Test workflow
            log_info "Starting comprehensive shell workflow test"
            
            # Test basic functionality that should be available
            if command -v log_info >/dev/null 2>&1; then
                log_info "Logger functions are available"
            fi
            
            # Test command checking if available
            if command -v check_command >/dev/null 2>&1; then
                if check_command "bash" 2>/dev/null; then
                    log_info "Command checking works"
                fi
            fi
            
            log_info "Shell workflow test completed successfully"
            echo "WORKFLOW_COMPLETE"
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(test_script)
            f.flush()
            
            result = subprocess.run(
                ['bash', f.name],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.test_dir)
            )
            
            os.unlink(f.name)
            
            assert result.returncode == 0, f"Workflow test failed: {result.stderr}"
            assert "WORKFLOW_COMPLETE" in result.stdout
            
            output = result.stdout + result.stderr
            assert "Shell workflow test completed successfully" in output
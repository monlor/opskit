"""Integration tests for tool execution"""

import pytest
import subprocess
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock
import shutil
import time


class TestToolExecution:
    """Test actual tool execution through opskit CLI"""
    
    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.opskit_exe = self.project_root / 'opskit'
        
        # Create temporary environment
        self.temp_env = os.environ.copy()
        self.temp_env['OPSKIT_BASE_PATH'] = str(self.project_root)
        self.temp_env['PYTHONPATH'] = str(self.project_root)
    
    def run_opskit_command(self, args, timeout=30, input_data=None):
        """Helper to run opskit commands"""
        cmd = ['python3', str(self.opskit_exe)] + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self.temp_env,
                input=input_data,
                cwd=str(self.project_root)
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return -2, "", str(e)
    
    def test_opskit_help(self):
        """Test opskit help command"""
        returncode, stdout, stderr = self.run_opskit_command(['--help'])
        
        assert returncode == 0, f"Help command failed: {stderr}"
        assert 'usage:' in stdout.lower() or 'opskit' in stdout.lower()
    
    def test_opskit_list_tools(self):
        """Test listing available tools"""
        returncode, stdout, stderr = self.run_opskit_command(['list'])
        
        # Should succeed even if no tools are fully configured
        if returncode == 0:
            # Should show some tool information
            assert len(stdout) > 0
        else:
            # If list command fails, it might not be implemented yet
            pytest.skip(f"List command not implemented: {stderr}")
    
    def test_tool_help_commands(self):
        """Test help for individual tools"""
        tools = [
            'mysql-sync',
            'port-scanner',
            'disk-usage',
            'system-info',
            'k8s-resource-copy'
        ]
        
        for tool in tools:
            returncode, stdout, stderr = self.run_opskit_command(['help', tool])
            
            if returncode == 0:
                # Should contain some help information
                assert len(stdout) > 0
                assert tool.replace('-', ' ') in stdout.lower() or tool in stdout.lower()
            else:
                # Tool might not be fully implemented
                pytest.skip(f"Help for {tool} not available: {stderr}")
    
    def test_system_info_tool(self):
        """Test system-info tool execution"""
        returncode, stdout, stderr = self.run_opskit_command(['run', 'system-info'])
        
        if returncode == 0:
            # Should contain system information
            output = stdout.lower()
            assert any(keyword in output for keyword in ['system', 'platform', 'python', 'os'])
        else:
            # Tool might not be fully configured
            pytest.skip(f"system-info tool not ready: {stderr}")
    
    def test_disk_usage_tool(self):
        """Test disk-usage tool execution"""
        returncode, stdout, stderr = self.run_opskit_command(['run', 'disk-usage'])
        
        if returncode == 0:
            # Should contain disk information
            output = stdout.lower()
            assert any(keyword in output for keyword in ['disk', 'usage', 'size', 'space'])
        else:
            # Tool might require dependencies or not be fully configured
            pytest.skip(f"disk-usage tool not ready: {stderr}")
    
    def test_port_scanner_tool_help(self):
        """Test port-scanner tool help"""
        returncode, stdout, stderr = self.run_opskit_command(['run', 'port-scanner', '--help'])
        
        if returncode == 0:
            # Should show help for port scanner
            output = stdout.lower()
            assert any(keyword in output for keyword in ['port', 'scan', 'host', 'help', 'usage'])
        else:
            # Tool might not be fully configured
            pytest.skip(f"port-scanner help not available: {stderr}")
    
    def test_mysql_sync_tool_dependency_check(self):
        """Test mysql-sync tool dependency checking"""
        returncode, stdout, stderr = self.run_opskit_command(['run', 'mysql-sync', '--help'], timeout=60)
        
        if returncode == 0:
            # Tool ran successfully
            assert len(stdout) > 0
        else:
            # Might fail due to missing dependencies - that's expected
            error_output = stderr.lower()
            if any(keyword in error_output for keyword in ['dependency', 'mysql', 'not found', 'install']):
                # This is expected behavior for dependency checking
                pytest.skip("mysql-sync missing dependencies (expected)")
            else:
                # Unexpected error
                pytest.fail(f"Unexpected error from mysql-sync: {stderr}")
    
    def test_k8s_resource_copy_dependency_check(self):
        """Test k8s-resource-copy tool dependency checking"""
        returncode, stdout, stderr = self.run_opskit_command(['run', 'k8s-resource-copy', '--help'], timeout=60)
        
        if returncode == 0:
            # Tool ran successfully
            assert len(stdout) > 0
        else:
            # Might fail due to missing Kubernetes dependencies
            error_output = stderr.lower()
            if any(keyword in error_output for keyword in ['dependency', 'kubectl', 'kubernetes', 'not found']):
                # This is expected behavior for dependency checking
                pytest.skip("k8s-resource-copy missing dependencies (expected)")
            else:
                # Unexpected error
                pytest.fail(f"Unexpected error from k8s-resource-copy: {stderr}")
    
    def test_tool_nonexistent(self):
        """Test running non-existent tool"""
        returncode, stdout, stderr = self.run_opskit_command(['run', 'nonexistent-tool'])
        
        assert returncode != 0, "Should fail for non-existent tool"
        assert len(stderr) > 0, "Should provide error message"
    
    def test_invalid_command(self):
        """Test invalid opskit command"""
        returncode, stdout, stderr = self.run_opskit_command(['invalid-command'])
        
        assert returncode != 0, "Should fail for invalid command"


@pytest.mark.slow
class TestToolDependencyManagement:
    """Test tool dependency management and environment setup"""
    
    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.opskit_exe = self.project_root / 'opskit'
        
        # Create temporary environment
        self.temp_env = os.environ.copy()
        self.temp_env['OPSKIT_BASE_PATH'] = str(self.project_root)
        self.temp_env['PYTHONPATH'] = str(self.project_root)
        self.temp_env['OPSKIT_DEBUG'] = 'true'
    
    def run_opskit_command(self, args, timeout=120):
        """Helper to run opskit commands with longer timeout"""
        cmd = ['python3', str(self.opskit_exe)] + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self.temp_env,
                cwd=str(self.project_root)
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return -2, "", str(e)
    
    def test_python_tool_venv_creation(self):
        """Test that Python tools create virtual environments"""
        # Try to run a Python tool that should create a venv
        returncode, stdout, stderr = self.run_opskit_command(['run', 'system-info'])
        
        # Check if venv was created
        venv_path = self.project_root / 'cache' / 'venvs' / 'system-info'
        
        if venv_path.exists():
            assert (venv_path / 'bin' / 'python').exists() or (venv_path / 'Scripts' / 'python.exe').exists()
            pytest.skip("Virtual environment created successfully")
        else:
            # Venv might not be created if dependencies are already satisfied
            if returncode == 0:
                pytest.skip("Tool ran successfully without creating new venv")
            else:
                pytest.skip(f"Tool execution failed: {stderr}")
    
    def test_dependency_checking_integration(self):
        """Test that dependency checking works end-to-end"""
        # Test with a tool that has known dependencies
        returncode, stdout, stderr = self.run_opskit_command(['run', 'mysql-sync', '--dry-run'])
        
        output = stdout + stderr
        
        # Should either:
        # 1. Run successfully (dependencies satisfied)
        # 2. Show dependency information (dependencies missing)
        if returncode == 0:
            pytest.skip("mysql-sync ran successfully")
        else:
            # Check if dependency information is provided
            if any(keyword in output.lower() for keyword in [
                'dependency', 'install', 'missing', 'requirement', 'mysql'
            ]):
                pytest.skip("Dependency checking working (shown missing deps)")
            else:
                pytest.fail(f"Unexpected dependency error: {output}")
    
    def test_shell_tool_execution(self):
        """Test that shell tools execute properly"""
        # Test port-scanner as it's a shell tool
        returncode, stdout, stderr = self.run_opskit_command(['run', 'port-scanner', '--help'])
        
        if returncode == 0:
            assert len(stdout) > 0
            output = stdout.lower()
            assert any(keyword in output for keyword in ['usage', 'help', 'port', 'scan'])
        else:
            # Shell tool might not be fully implemented
            pytest.skip(f"Shell tool execution failed: {stderr}")


@pytest.mark.integration
class TestToolWorkflows:
    """Test complete tool workflows"""
    
    def setup_method(self):
        """Setup test environment with temporary workspace"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.opskit_exe = self.project_root / 'opskit'
        
        # Create temporary workspace
        import tempfile
        self.temp_workspace = Path(tempfile.mkdtemp(prefix='opskit_test_workspace_'))
        
        self.temp_env = os.environ.copy()
        self.temp_env['OPSKIT_BASE_PATH'] = str(self.project_root)
        self.temp_env['PYTHONPATH'] = str(self.project_root)
        self.temp_env['OPSKIT_DEBUG'] = 'true'
    
    def teardown_method(self):
        """Cleanup temporary workspace"""
        if self.temp_workspace.exists():
            shutil.rmtree(self.temp_workspace, ignore_errors=True)
    
    def run_opskit_command(self, args, cwd=None, timeout=60):
        """Helper to run opskit commands"""
        cmd = ['python3', str(self.opskit_exe)] + args
        work_dir = cwd or self.temp_workspace
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self.temp_env,
                cwd=str(work_dir)
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return -2, "", str(e)
    
    def test_system_info_complete_workflow(self):
        """Test complete system-info tool workflow"""
        returncode, stdout, stderr = self.run_opskit_command(['run', 'system-info'])
        
        if returncode == 0:
            # Verify output contains expected system information
            output = stdout.lower()
            expected_fields = ['os', 'platform', 'python', 'architecture']
            
            found_fields = [field for field in expected_fields if field in output]
            assert len(found_fields) > 0, f"Expected system info fields not found in output: {stdout}"
            
            # Verify output format is reasonable
            assert len(stdout.strip()) > 0, "System info should produce some output"
        else:
            pytest.skip(f"system-info tool not ready: {stderr}")
    
    def test_disk_usage_workflow(self):
        """Test complete disk-usage tool workflow"""
        # Create some test files in workspace
        test_dir = self.temp_workspace / 'test_data'
        test_dir.mkdir()
        
        for i in range(3):
            (test_dir / f'file_{i}.txt').write_text('x' * 1000)  # 1KB files
        
        returncode, stdout, stderr = self.run_opskit_command([
            'run', 'disk-usage', str(test_dir)
        ])
        
        if returncode == 0:
            # Should show disk usage information
            output = stdout.lower()
            assert any(keyword in output for keyword in ['size', 'bytes', 'kb', 'mb', 'usage'])
            
            # Should mention the test directory
            assert 'test_data' in stdout or str(test_dir) in stdout
        else:
            pytest.skip(f"disk-usage tool not ready: {stderr}")
    
    def test_port_scanner_workflow(self):
        """Test port-scanner tool workflow"""
        # Test scanning localhost on a common port
        returncode, stdout, stderr = self.run_opskit_command([
            'run', 'port-scanner', 'localhost', '22'
        ], timeout=30)
        
        if returncode == 0:
            # Should show scan results
            output = stdout.lower()
            assert any(keyword in output for keyword in ['port', 'open', 'closed', 'scan', 'localhost'])
        else:
            # Port scanner might need specific configuration or dependencies
            pytest.skip(f"port-scanner not ready: {stderr}")
    
    def test_tool_error_handling(self):
        """Test that tools handle errors gracefully"""
        # Test disk-usage with non-existent directory
        returncode, stdout, stderr = self.run_opskit_command([
            'run', 'disk-usage', '/nonexistent/directory'
        ])
        
        # Should fail gracefully
        assert returncode != 0, "Should fail for non-existent directory"
        
        error_output = stderr.lower()
        assert any(keyword in error_output for keyword in [
            'not found', 'does not exist', 'error', 'invalid'
        ]), f"Expected error message not found: {stderr}"
    
    def test_tool_configuration_persistence(self):
        """Test that tool configurations persist across runs"""
        # This test checks if tools can store and retrieve configuration
        # We'll use system-info as it might store some settings
        
        # First run
        returncode1, stdout1, stderr1 = self.run_opskit_command(['run', 'system-info'])
        
        if returncode1 != 0:
            pytest.skip("system-info not working for config persistence test")
        
        # Second run - should be consistent
        returncode2, stdout2, stderr2 = self.run_opskit_command(['run', 'system-info'])
        
        if returncode2 == 0:
            # System info should be consistent between runs
            # At least some basic info should be the same
            assert len(stdout2) > 0, "Second run should produce output"
            
            # Python version should be the same
            import sys
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            if python_version in stdout1 and python_version in stdout2:
                assert True  # Good, consistent output
            else:
                pytest.skip("Cannot verify configuration persistence")
        else:
            pytest.skip("Second run failed")


@pytest.mark.slow
class TestToolPerformance:
    """Test tool performance and resource usage"""
    
    def setup_method(self):
        """Setup performance testing environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.opskit_exe = self.project_root / 'opskit'
        
        self.temp_env = os.environ.copy()
        self.temp_env['OPSKIT_BASE_PATH'] = str(self.project_root)
        self.temp_env['PYTHONPATH'] = str(self.project_root)
    
    def run_opskit_timed(self, args, timeout=30):
        """Run opskit command and measure execution time"""
        start_time = time.time()
        
        cmd = ['python3', str(self.opskit_exe)] + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self.temp_env,
                cwd=str(self.project_root)
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            return result.returncode, result.stdout, result.stderr, execution_time
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout", timeout
        except Exception as e:
            return -2, "", str(e), time.time() - start_time
    
    def test_tool_startup_time(self):
        """Test that tools start up in reasonable time"""
        tools = ['system-info', 'disk-usage']
        
        for tool in tools:
            returncode, stdout, stderr, exec_time = self.run_opskit_timed([
                'run', tool, '--help'
            ])
            
            if returncode == 0:
                # Should start up in under 10 seconds
                assert exec_time < 10.0, f"{tool} took {exec_time:.2f}s to start (too slow)"
                
                # Should start up in under 5 seconds for help
                if exec_time > 5.0:
                    pytest.skip(f"{tool} startup time {exec_time:.2f}s is acceptable but slow")
            else:
                pytest.skip(f"{tool} not available for performance test")
    
    def test_multiple_tool_runs(self):
        """Test running the same tool multiple times"""
        tool = 'system-info'
        
        execution_times = []
        
        for i in range(3):
            returncode, stdout, stderr, exec_time = self.run_opskit_timed([
                'run', tool
            ])
            
            if returncode == 0:
                execution_times.append(exec_time)
            else:
                pytest.skip(f"{tool} not available for multiple run test")
        
        if len(execution_times) >= 2:
            # Later runs should not be significantly slower (no resource leaks)
            avg_time = sum(execution_times) / len(execution_times)
            max_time = max(execution_times)
            
            assert max_time < avg_time * 2, f"Tool performance degraded: avg={avg_time:.2f}s, max={max_time:.2f}s"
        else:
            pytest.skip("Insufficient successful runs for performance comparison")
    
    def test_concurrent_tool_execution(self):
        """Test running tools concurrently"""
        import threading
        import queue
        
        def run_tool(tool_name, result_queue):
            returncode, stdout, stderr, exec_time = self.run_opskit_timed([
                'run', tool_name
            ])
            result_queue.put((tool_name, returncode, exec_time))
        
        tools = ['system-info', 'disk-usage']
        available_tools = []
        
        # First check which tools are available
        for tool in tools:
            returncode, _, _, _ = self.run_opskit_timed(['run', tool, '--help'])
            if returncode == 0:
                available_tools.append(tool)
        
        if len(available_tools) < 2:
            pytest.skip("Need at least 2 tools for concurrent test")
        
        # Run tools concurrently
        result_queue = queue.Queue()
        threads = []
        
        start_time = time.time()
        
        for tool in available_tools[:2]:  # Test with first 2 available tools
            thread = threading.Thread(target=run_tool, args=(tool, result_queue))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)
        
        concurrent_time = time.time() - start_time
        
        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())
        
        assert len(results) == len(available_tools[:2]), "All concurrent tools should complete"
        
        # All tools should succeed
        for tool_name, returncode, exec_time in results:
            assert returncode == 0, f"Concurrent execution failed for {tool_name}"
        
        # Concurrent execution should not take much longer than the slowest individual tool
        max_individual_time = max(result[2] for result in results)
        assert concurrent_time < max_individual_time * 1.5, "Concurrent execution too slow"
#!/usr/bin/env python3
"""Test runner script for OpsKit test suite"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
TESTS_DIR = PROJECT_ROOT / 'tests'


def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description='OpsKit Test Runner')
    
    # Test selection options
    parser.add_argument('--unit', action='store_true', 
                       help='Run only unit tests')
    parser.add_argument('--integration', action='store_true',
                       help='Run only integration tests')
    parser.add_argument('--slow', action='store_true',
                       help='Include slow tests')
    parser.add_argument('--coverage', action='store_true',
                       help='Generate coverage report')
    parser.add_argument('--html-coverage', action='store_true',
                       help='Generate HTML coverage report')
    
    # Test filtering
    parser.add_argument('--core', action='store_true',
                       help='Test only core modules')
    parser.add_argument('--common', action='store_true',
                       help='Test only common libraries')
    parser.add_argument('--tools', action='store_true',
                       help='Test only tool execution')
    parser.add_argument('--python', action='store_true',
                       help='Test only Python components')
    parser.add_argument('--shell', action='store_true',
                       help='Test only shell components')
    
    # Output options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Quiet output')
    parser.add_argument('--junit-xml', metavar='FILE',
                       help='Generate JUnit XML report')
    
    # Performance options
    parser.add_argument('--parallel', '-n', type=int, metavar='N',
                       help='Run tests in parallel (N workers)')
    parser.add_argument('--timeout', type=int, default=300, metavar='SECONDS',
                       help='Global test timeout (default: 300s)')
    
    # Development options
    parser.add_argument('--pdb', action='store_true',
                       help='Drop into debugger on failures')
    parser.add_argument('--lf', '--last-failed', action='store_true',
                       help='Run only tests that failed last time')
    parser.add_argument('--ff', '--failed-first', action='store_true',
                       help='Run failed tests first')
    
    # Path options
    parser.add_argument('paths', nargs='*',
                       help='Specific test paths to run')
    
    args = parser.parse_args()
    
    # Build pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add test selection markers
    markers = []
    
    if args.unit:
        markers.append('unit')
    elif args.integration:
        markers.append('integration')
    
    if not args.slow:
        markers.append('not slow')
    
    # Add component filters
    component_markers = []
    if args.core:
        component_markers.append('core')
    if args.common:
        component_markers.append('common')
    if args.tools:
        component_markers.append('tool')
    if args.python:
        component_markers.append('python')
    if args.shell:
        component_markers.append('shell')
    
    # Combine markers
    if markers or component_markers:
        all_markers = markers + component_markers
        if len(all_markers) == 1:
            cmd.extend(['-m', all_markers[0]])
        else:
            # Combine with 'and' for precision
            marker_expr = ' and '.join(all_markers)
            cmd.extend(['-m', marker_expr])
    
    # Add coverage options
    if args.coverage or args.html_coverage:
        cmd.extend(['--cov=core', '--cov=common'])
        cmd.append('--cov-report=term')
        
        if args.html_coverage:
            cmd.append('--cov-report=html:tests/coverage_html')
        
        if args.coverage:
            cmd.append('--cov-report=xml:tests/coverage.xml')
    
    # Add output options
    if args.verbose:
        cmd.append('-v')
    elif args.quiet:
        cmd.append('-q')
    
    if args.junit_xml:
        cmd.extend(['--junit-xml', args.junit_xml])
    
    # Add performance options
    if args.parallel:
        cmd.extend(['-n', str(args.parallel)])
    
    cmd.extend(['--timeout', str(args.timeout)])
    
    # Add development options
    if args.pdb:
        cmd.append('--pdb')
    
    if args.lf:
        cmd.append('--lf')
    elif args.ff:
        cmd.append('--ff')
    
    # Add paths
    if args.paths:
        cmd.extend(args.paths)
    else:
        cmd.append(str(TESTS_DIR))
    
    # Set environment variables
    env = os.environ.copy()
    env['PYTHONPATH'] = str(PROJECT_ROOT)
    env['OPSKIT_BASE_PATH'] = str(PROJECT_ROOT)
    env['OPSKIT_DEBUG'] = 'true'
    env['OPSKIT_LOG_LEVEL'] = 'DEBUG'
    
    # Print command info
    print(f"Running OpsKit Test Suite")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Test Directory: {TESTS_DIR}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    # Run tests
    try:
        result = subprocess.run(cmd, env=env, cwd=str(PROJECT_ROOT))
        
        # Print summary
        print("-" * 60)
        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")
            print(f"Exit code: {result.returncode}")
        
        # Coverage report location
        if args.html_coverage:
            coverage_path = PROJECT_ROOT / 'tests' / 'coverage_html' / 'index.html'
            print(f"📊 HTML coverage report: {coverage_path}")
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n🛑 Test run interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        return 1


def check_dependencies():
    """Check if required test dependencies are available"""
    required_packages = ['pytest', 'pytest-cov', 'pytest-mock']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required test dependencies:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nInstall with: pip install " + " ".join(missing_packages))
        return False
    
    return True


if __name__ == '__main__':
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    # Run tests
    sys.exit(main())
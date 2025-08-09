#!/usr/bin/env python3
"""Test script to verify single venv usage"""

import sys
import subprocess
import os
from pathlib import Path

def main():
    opskit_root = Path(__file__).parent
    shared_venv_python = opskit_root / '.venv' / 'bin' / 'python'
    
    print("=== Virtual Environment Test ===")
    print(f"Current Python: {sys.executable}")
    print(f"Expected shared venv Python: {shared_venv_python}")
    print(f"Match: {sys.executable == str(shared_venv_python)}")
    
    print("\n=== Package Verification ===")
    try:
        import pymysql
        print(f"✅ PyMySQL found: {pymysql.__file__}")
    except ImportError:
        print("❌ PyMySQL not found")
    
    try:
        import yaml
        print(f"✅ PyYAML found: {yaml.__file__}")
    except ImportError:
        print("❌ PyYAML not found")
    
    print("\n=== Tool Dependency Check ===")
    # Check if this script is running in the same venv as tools would
    result = subprocess.run([
        str(shared_venv_python), '-c', 
        'import sys; print("Tool would use:", sys.executable)'
    ], capture_output=True, text=True)
    print(result.stdout.strip())

if __name__ == '__main__':
    main()
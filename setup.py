#!/usr/bin/env python3
"""
OpsKit Setup Script
Creates shared virtual environment with core dependencies only
"""

import os
import sys
import subprocess
import venv
from pathlib import Path


def create_shared_venv(opskit_root: Path):
    """Create shared virtual environment with core dependencies"""
    shared_venv = opskit_root / '.venv'
    
    print("🔧 Creating shared virtual environment...")
    
    # Remove existing venv if it exists
    if shared_venv.exists():
        import shutil
        shutil.rmtree(shared_venv)
    
    # Create new venv
    venv.create(shared_venv, with_pip=True, clear=True)
    
    # Get pip executable path (Unix-like systems only)
    pip_exe = shared_venv / 'bin' / 'pip'
    
    # Upgrade pip
    print("📦 Upgrading pip...")
    subprocess.run([str(pip_exe), 'install', '--upgrade', 'pip'], check=True)
    
    # Install core requirements only
    core_requirements = opskit_root / 'requirements.txt'
    if core_requirements.exists():
        print("📦 Installing core dependencies...")
        subprocess.run([
            str(pip_exe), 'install', 
            '-r', str(core_requirements),
            '--cache-dir', str(opskit_root / 'cache' / 'pip_cache')
        ], check=True)
    
    print("✅ Shared virtual environment created successfully!")
    print(f"   Location: {shared_venv}")
    print("   Tool dependencies will be installed on-demand when tools run")


def setup_opskit():
    """Main setup function"""
    opskit_root = Path(__file__).parent.resolve()
    
    print("🚀 Setting up OpsKit with single shared virtual environment...")
    print(f"   OpsKit root: {opskit_root}")
    
    # Create cache directories
    cache_dir = opskit_root / 'cache'
    cache_dir.mkdir(exist_ok=True)
    (cache_dir / 'pip_cache').mkdir(exist_ok=True)
    (cache_dir / 'requirements').mkdir(exist_ok=True)
    
    # Create bin directory
    bin_dir = opskit_root / 'bin'
    bin_dir.mkdir(exist_ok=True)
    
    # Create shared virtual environment
    create_shared_venv(opskit_root)
    
    # Update opskit executable to use shared venv
    opskit_exe = opskit_root / 'bin' / 'opskit'
    shared_venv = opskit_root / '.venv'  # Define shared_venv path here
    if opskit_exe.exists():
        # Update shebang to point to shared venv Python
        python_exe = shared_venv / 'bin' / 'python'
        
        # Read current content
        with open(opskit_exe, 'r') as f:
            content = f.read()
        
        # Replace shebang
        lines = content.split('\n')
        if lines[0].startswith('#!'):
            lines[0] = f"#!{python_exe}"
            # Remove the temporary comment if it exists
            if len(lines) > 1 and 'This script will be updated' in lines[1]:
                lines.pop(1)
        
        # Write updated content
        with open(opskit_exe, 'w') as f:
            f.write('\n'.join(lines))
        
        # Make executable
        os.chmod(opskit_exe, 0o755)
        print(f"✅ Updated opskit executable to use shared venv: {python_exe}")
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Add OpsKit to your environment:")
    print(f"   export OPSKIT_BASE_PATH=\"{opskit_root}\"")
    print(f"   export PATH=\"{opskit_root}/bin:$PATH\"")
    print("2. Run a tool:")
    print("   opskit run mysql-sync")
    print("\nTool dependencies will be installed automatically on first run.")


if __name__ == '__main__':
    try:
        setup_opskit()
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)
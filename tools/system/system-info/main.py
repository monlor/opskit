#!/usr/bin/env python3
"""
System Information Tool
Display comprehensive system information
"""

import platform
import socket
import psutil
import json
from datetime import datetime

def get_system_info():
    """Collect system information"""
    info = {
        'system': {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'hostname': socket.gethostname(),
            'python_version': platform.python_version(),
        },
        'cpu': {
            'physical_cores': psutil.cpu_count(logical=False),
            'total_cores': psutil.cpu_count(logical=True),
            'max_frequency': f"{psutil.cpu_freq().max:.2f}Mhz" if psutil.cpu_freq() else "N/A",
            'current_frequency': f"{psutil.cpu_freq().current:.2f}Mhz" if psutil.cpu_freq() else "N/A",
        },
        'memory': {
            'total': f"{psutil.virtual_memory().total / (1024**3):.2f}GB",
            'available': f"{psutil.virtual_memory().available / (1024**3):.2f}GB",
            'used': f"{psutil.virtual_memory().used / (1024**3):.2f}GB",
            'percentage': f"{psutil.virtual_memory().percent}%",
        },
        'disk': {
            'total': f"{psutil.disk_usage('/').total / (1024**3):.2f}GB",
            'used': f"{psutil.disk_usage('/').used / (1024**3):.2f}GB",
            'free': f"{psutil.disk_usage('/').free / (1024**3):.2f}GB",
        }
    }
    
    return info

def main():
    """Main function"""
    print("System Information Tool")
    print("=" * 40)
    
    info = get_system_info()
    
    print(f"Platform: {info['system']['platform']} {info['system']['platform_release']}")
    print(f"Architecture: {info['system']['architecture']}")
    print(f"Hostname: {info['system']['hostname']}")
    print(f"Python Version: {info['system']['python_version']}")
    print()
    print(f"CPU: {info['cpu']['total_cores']} cores ({info['cpu']['physical_cores']} physical)")
    print(f"Memory: {info['memory']['used']} / {info['memory']['total']} ({info['memory']['percentage']})")
    print(f"Disk: {info['disk']['used']} / {info['disk']['total']} used")

if __name__ == "__main__":
    main()
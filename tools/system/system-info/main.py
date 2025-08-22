#!/usr/bin/env python3
"""
System Information Tool - OpsKit Version
Display comprehensive system information
"""

import os
import platform
import socket
import psutil
from datetime import datetime

# 获取 OpsKit 环境变量
OPSKIT_TOOL_TEMP_DIR = os.environ.get('OPSKIT_TOOL_TEMP_DIR', os.path.join(os.getcwd(), '.system-info-temp'))
OPSKIT_BASE_PATH = os.environ.get('OPSKIT_BASE_PATH', os.path.expanduser('~/.opskit'))
OPSKIT_WORKING_DIR = os.environ.get('OPSKIT_WORKING_DIR', os.getcwd())
TOOL_NAME = os.environ.get('TOOL_NAME', 'system-info')
TOOL_VERSION = os.environ.get('TOOL_VERSION', '1.0.0')

def get_system_info():
    """Collect system information"""
    try:
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
    except Exception as e:
        print(f"❌ 获取系统信息失败: {e}")
        return None

def main():
    """Main function"""
    print("🖥️  系统信息工具")
    print("=" * 50)
    print(f"⚙️  工具版本: {TOOL_VERSION}")
    print(f"📂 临时目录: {OPSKIT_TOOL_TEMP_DIR}")
    print(f"📁 工作目录: {OPSKIT_WORKING_DIR}")
    print()
    
    info = get_system_info()
    if not info:
        print("❌ 无法获取系统信息")
        return
    
    print("📊 系统详细信息:")
    print("-" * 50)
    print(f"🖥️  平台: {info['system']['platform']} {info['system']['platform_release']}")
    print(f"🏗️  架构: {info['system']['architecture']}")
    print(f"🌐 主机名: {info['system']['hostname']}")
    print(f"🐍 Python版本: {info['system']['python_version']}")
    print()
    
    print("⚡ CPU信息:")
    print(f"   核心数: {info['cpu']['total_cores']} 逻辑核心 ({info['cpu']['physical_cores']} 物理核心)")
    print(f"   频率: {info['cpu']['current_frequency']} (最大: {info['cpu']['max_frequency']})")
    print()
    
    print("💾 内存信息:")
    print(f"   使用情况: {info['memory']['used']} / {info['memory']['total']} ({info['memory']['percentage']})")
    print(f"   可用: {info['memory']['available']}")
    print()
    
    print("💿 磁盘信息 (根分区):")
    print(f"   使用情况: {info['disk']['used']} / {info['disk']['total']}")
    print(f"   剩余空间: {info['disk']['free']}")
    print()
    
    print("✅ 系统信息收集完成")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序错误: {e}")
#!/usr/bin/env python3
"""
Port Scanner Tool
Network port scanner for checking open ports
"""

import socket
import threading
from concurrent.futures import ThreadPoolExecutor
import argparse

def scan_port(host, port, timeout=3):
    """Scan a single port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return port if result == 0 else None
    except:
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Network Port Scanner')
    parser.add_argument('--host', '-H', default='localhost', help='Target host')
    parser.add_argument('-p', '--ports', default='22,80,443,3306', help='Ports to scan (comma-separated)')
    parser.add_argument('-t', '--timeout', type=int, default=3, help='Connection timeout')
    
    args = parser.parse_args()
    
    ports = [int(p.strip()) for p in args.ports.split(',')]
    
    print(f"Scanning {args.host} for open ports...")
    print(f"Ports: {', '.join(map(str, ports))}")
    print("-" * 40)
    
    open_ports = []
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(scan_port, args.host, port, args.timeout): port for port in ports}
        
        for future in futures:
            result = future.result()
            if result:
                open_ports.append(result)
                print(f"Port {result}: OPEN")
    
    print("-" * 40)
    print(f"Found {len(open_ports)} open ports: {', '.join(map(str, open_ports))}")

if __name__ == "__main__":
    main()
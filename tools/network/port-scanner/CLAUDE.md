# Port Scanner Tool

## 功能描述
Network port scanner to check open ports on target hosts. Supports TCP and UDP scanning with configurable timeout and threading.

## 技术架构
- 实现语言: Python
- 核心依赖: socket, threading, concurrent.futures
- 系统要求: Python 3.7+

## 配置项
- default_timeout: Default connection timeout in seconds
- max_threads: Maximum number of concurrent threads
- default_ports: List of commonly scanned ports

## 开发指南
Multi-threaded port scanner with progress reporting and various output formats.

## 使用示例
```bash
opskit port-scanner --host localhost -p 80,443,22,3306
opskit port-scanner -H 192.168.1.1 -p 22,80,443,3306
```
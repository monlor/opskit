# System Information Tool

## 功能描述
Display comprehensive system information including OS details, hardware specs, network configuration, and installed software.

## 技术架构
- 实现语言: Python
- 核心依赖: psutil, platform, socket
- 系统要求: Python 3.7+

## 配置项
- output_format: json, table, or simple
- include_network: boolean to show network info
- include_hardware: boolean to show hardware details

## 开发指南
Simple system information gathering tool using Python standard library and psutil.

## 使用示例
```bash
opskit system-info
```
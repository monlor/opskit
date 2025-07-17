#!/usr/bin/env python3
"""
Test Python tool for OpsKit
"""

import sys
import os
import argparse


def main():
    parser = argparse.ArgumentParser(description='Test Python Tool')
    parser.add_argument('command', help='Command to run')
    parser.add_argument('args', nargs='*', help='Command arguments')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run mode')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    print(f"🐍 Python Tool Executed!")
    print(f"Command: {args.command}")
    print(f"Arguments: {args.args}")
    print(f"Dry run: {args.dry_run}")
    print(f"Verbose: {args.verbose}")
    
    # Environment variables from OpsKit
    print(f"OPSKIT_DIR: {os.getenv('OPSKIT_DIR', 'not set')}")
    print(f"OPSKIT_DEBUG: {os.getenv('OPSKIT_DEBUG', 'not set')}")
    print(f"OPSKIT_RELEASE: {os.getenv('OPSKIT_RELEASE', 'not set')}")
    
    if args.command == "test":
        print("✅ Python tool test passed!")
        return 0
    elif args.command == "process":
        if len(args.args) < 1:
            print("❌ Error: process command requires at least one argument")
            return 1
        print(f"📊 Processing: {args.args[0]}")
        if not args.dry_run:
            print("💾 Processing completed!")
        else:
            print("🔍 Dry run - no changes made")
        return 0
    else:
        print(f"❌ Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
MySQL Sync Tool - OpsKit Version
A safe, interactive database-to-database sync tool with batch operations support
"""

import os
import sys
import json
import base64
import getpass
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Import OpsKit common libraries
sys.path.insert(0, os.path.join(os.environ['OPSKIT_BASE_PATH'], 'common/python'))

from logger import get_logger
from storage import get_storage
from utils import run_command, timestamp, get_env_var
from interactive import get_input, confirm, select_from_list, delete_confirm

# Third-party imports
try:
    import pymysql
    import click
    from colorama import init, Fore, Style
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please ensure all dependencies are installed.")
    sys.exit(1)

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Initialize OpsKit components
logger = get_logger(__name__)
storage = get_storage('mysql-sync')


class MySQLSyncTool:
    """MySQL database synchronization tool with OpsKit integration"""
    
    def __init__(self):
        self.connections_cache = {}
        self.load_cached_connections()
        
        # Tool metadata
        self.tool_name = "MySQL Sync"
        self.description = "Interactive MySQL database batch synchronization tool"
        
        # Load configuration from environment variables using utils helper
        self.timeout = get_env_var('TIMEOUT', 30, int)
        self.max_retries = get_env_var('MAX_RETRIES', 3, int)
        self.connect_timeout = get_env_var('CONNECT_TIMEOUT', 30, int)
        self.batch_size = get_env_var('BATCH_SIZE', 100, int)
        self.confirm_destructive = get_env_var('CONFIRM_DESTRUCTIVE', True, bool)
        self.show_progress = get_env_var('SHOW_PROGRESS', True, bool)
        self.debug = get_env_var('DEBUG', False, bool)
        self.verbose = get_env_var('VERBOSE', False, bool)
        self.cache_connections = get_env_var('CACHE_CONNECTIONS', True, bool)
        self.max_history_records = get_env_var('MAX_HISTORY_RECORDS', 50, int)
        
        # MySQL dump settings
        self.single_transaction = get_env_var('SINGLE_TRANSACTION', True, bool)
        self.include_routines = get_env_var('INCLUDE_ROUTINES', True, bool)
        self.include_triggers = get_env_var('INCLUDE_TRIGGERS', True, bool)
        self.lock_tables = get_env_var('LOCK_TABLES', False, bool)
        
        logger.info(f"🚀 Starting {self.tool_name}")
        if self.debug:
            logger.info(f"Debug mode enabled - timeout: {self.timeout}s, batch_size: {self.batch_size}")
    
    def load_cached_connections(self):
        """Load cached connections from storage"""
        try:
            cached = storage.get('connections', {})
            if isinstance(cached, dict):
                self.connections_cache = cached
                logger.debug(f"Loaded {len(self.connections_cache)} cached connections")
        except Exception as e:
            logger.error(f"Failed to load cached connections: {e}")
            self.connections_cache = {}
    
    def save_cached_connections(self):
        """Save connections to storage"""
        try:
            storage.set('connections', self.connections_cache)
            logger.debug("Saved connection cache")
        except Exception as e:
            logger.error(f"Failed to save connections: {e}")
    
    def list_cached_connections(self) -> List[Dict[str, str]]:
        """List all cached connections with details"""
        if not self.connections_cache:
            return []
        
        connections = []
        for name, cached in self.connections_cache.items():
            connections.append({
                'name': name,
                'host': cached['host'],
                'port': cached['port'],
                'user': cached['user'],
                'last_used': cached.get('last_used', 'Unknown'),
                'display': f"{name} ({cached['user']}@{cached['host']}:{cached['port']})"
            })
        
        # Sort by last used (most recent first)
        connections.sort(key=lambda x: x['last_used'], reverse=True)
        return connections

    def select_cached_connection(self, connection_type: str) -> Optional[Dict[str, str]]:
        """Let user select from cached connections"""
        cached_connections = self.list_cached_connections()
        
        if not cached_connections:
            print(f"{Fore.YELLOW}No cached connections available{Style.RESET_ALL}")
            return None
        
        print(f"\n{Fore.CYAN}=== Cached {connection_type.upper()} Connections ==={Style.RESET_ALL}")
        for i, conn in enumerate(cached_connections, 1):
            print(f"{Fore.YELLOW}{i:2d}.{Style.RESET_ALL} {conn['display']}")
            print(f"    Last used: {conn['last_used']}")
        
        print(f"\n{Fore.CYAN}Options:{Style.RESET_ALL}")
        print("  Select connection: 1, 2, 3...")
        print("  Create new connection: new")
        print("  Cancel: press Ctrl+C")
        
        try:
            while True:
                selection = input(f"\n{Fore.CYAN}Your choice: {Style.RESET_ALL}").strip().lower()
                
                if selection == 'new':
                    return None  # Signal to create new connection
                
                try:
                    choice = int(selection)
                    if 1 <= choice <= len(cached_connections):
                        selected_conn = cached_connections[choice - 1]
                        
                        # Decode password and return
                        cached = self.connections_cache[selected_conn['name']]
                        try:
                            password = base64.b64decode(cached['password']).decode('utf-8')
                            
                            # Update last used timestamp
                            self.connections_cache[selected_conn['name']]['last_used'] = timestamp()
                            self.save_cached_connections()
                            
                            print(f"{Fore.GREEN}✅ Selected connection: {selected_conn['display']}{Style.RESET_ALL}")
                            
                            return {
                                'name': selected_conn['name'],
                                'host': selected_conn['host'],
                                'port': selected_conn['port'],
                                'user': selected_conn['user'],
                                'password': password
                            }
                        except Exception as e:
                            logger.error(f"Failed to decode cached password: {e}")
                            print(f"{Fore.RED}❌ Failed to decode password for '{selected_conn['name']}'{Style.RESET_ALL}")
                            return None
                    else:
                        print(f"{Fore.RED}Invalid selection. Please choose 1-{len(cached_connections)} or 'new'{Style.RESET_ALL}")
                except ValueError:
                    print(f"{Fore.RED}Invalid input. Please enter a number or 'new'{Style.RESET_ALL}")
        
        except KeyboardInterrupt:
            logger.info(f"Cached connection selection cancelled by user")
            return None

    def get_connection_info(self, connection_type: str) -> Dict[str, str]:
        """Interactive connection information collection with enhanced caching"""
        print(f"\n{Fore.CYAN}=== {connection_type.upper()} Connection Setup ==={Style.RESET_ALL}")
        
        # First, show cached connections if available
        if self.connections_cache and self.cache_connections:
            selected_connection = self.select_cached_connection(connection_type)
            if selected_connection:
                return selected_connection
            
            # If user chose 'new' or selection failed, continue to manual input
        
        # Manual connection setup
        print(f"\n{Fore.CYAN}=== Create New {connection_type.upper()} Connection ==={Style.RESET_ALL}")
        
        # Ask for connection name
        name = get_input(
            f"Enter a name for this {connection_type} connection",
            validator=lambda x: len(x.strip()) > 0,
            error_message="Connection name cannot be empty"
        )
        
        # Check if name already exists and offer to overwrite
        if name in self.connections_cache:
            if not confirm(f"Connection '{name}' already exists. Overwrite?", default=False):
                print(f"{Fore.YELLOW}Please choose a different name{Style.RESET_ALL}")
                return self.get_connection_info(connection_type)
        
        # Get connection details
        host = get_input("MySQL Host", default="localhost")
        port = get_input("MySQL Port", default="3306", validator=lambda x: x.isdigit() and 1 <= int(x) <= 65535, error_message="Port must be between 1 and 65535")
        user = get_input("MySQL User", default="root")
        
        # Get password securely
        password = get_input("MySQL Password", password=True)
        
        connection_info = {
            'name': name,
            'host': host,
            'port': port,
            'user': user,
            'password': password
        }
        
        # Test connection before caching
        print(f"\n{Fore.CYAN}Testing connection...{Style.RESET_ALL}")
        if self.test_connection(connection_info):
            # Ask if user wants to cache this connection
            if self.cache_connections:
                if confirm("Save this connection for future use?", default=True):
                    self.connections_cache[name] = {
                        'host': host,
                        'port': port,
                        'user': user,
                        'password': base64.b64encode(password.encode('utf-8')).decode('utf-8'),
                        'last_used': timestamp()
                    }
                    self.save_cached_connections()
                    print(f"{Fore.GREEN}✅ Connection '{name}' cached successfully{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Connection not cached (temporary use only){Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Connection test failed. Please check your credentials and try again.{Style.RESET_ALL}")
            if confirm("Retry connection setup?", default=True):
                return self.get_connection_info(connection_type)
            else:
                sys.exit(1)
        
        return connection_info
    
    def test_connection(self, conn_info: Dict[str, str]) -> bool:
        """Test database connection"""
        try:
            logger.info(f"Testing connection to {conn_info['host']}:{conn_info['port']}")
            
            connection = pymysql.connect(
                host=conn_info['host'],
                port=int(conn_info['port']),
                user=conn_info['user'],
                password=conn_info['password'],
                connect_timeout=self.connect_timeout
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ Connection successful - MySQL {version}")
            
            connection.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    def list_databases(self, conn_info: Dict[str, str]) -> List[str]:
        """List available databases (excluding system databases)"""
        try:
            connection = pymysql.connect(
                host=conn_info['host'],
                port=int(conn_info['port']),
                user=conn_info['user'],
                password=conn_info['password']
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                all_databases = [row[0] for row in cursor.fetchall()]
            
            connection.close()
            
            # Filter out system databases
            system_dbs = {'information_schema', 'mysql', 'performance_schema', 'sys'}
            user_databases = [db for db in all_databases if db not in system_dbs]
            
            logger.info(f"Found {len(user_databases)} user databases")
            return sorted(user_databases)
            
        except Exception as e:
            logger.error(f"Failed to list databases: {e}")
            return []
    
    def select_databases(self, available_dbs: List[str]) -> List[str]:
        """Interactive database selection"""
        if not available_dbs:
            logger.error("No databases available for selection")
            return []
        
        print(f"\n{Fore.CYAN}=== Available Databases ==={Style.RESET_ALL}")
        for i, db in enumerate(available_dbs, 1):
            print(f"{Fore.YELLOW}{i:2d}.{Style.RESET_ALL} {db}")
        
        print(f"\n{Fore.CYAN}Selection Options:{Style.RESET_ALL}")
        print("  Single database: 3")
        print("  Multiple databases: 1,3,5")
        print("  Range: 1-5")
        print("  All databases: all")
        print("  Cancel: press Ctrl+C")
        
        try:
            while True:
                selection = input(f"\n{Fore.CYAN}Select databases: {Style.RESET_ALL}").strip().lower()
                
                if selection == 'all':
                    return available_dbs
                
                selected_dbs = []
                
                try:
                    # Parse selection
                    for part in selection.split(','):
                        part = part.strip()
                        if '-' in part:
                            # Range selection
                            start, end = map(int, part.split('-'))
                            for i in range(start, end + 1):
                                if 1 <= i <= len(available_dbs):
                                    selected_dbs.append(available_dbs[i - 1])
                        else:
                            # Single selection
                            i = int(part)
                            if 1 <= i <= len(available_dbs):
                                selected_dbs.append(available_dbs[i - 1])
                    
                    if selected_dbs:
                        # Remove duplicates while preserving order
                        selected_dbs = list(dict.fromkeys(selected_dbs))
                        
                        print(f"\n{Fore.GREEN}Selected databases:{Style.RESET_ALL}")
                        for db in selected_dbs:
                            print(f"  • {db}")
                        
                        if confirm("Confirm selection?", default=True):
                            return selected_dbs
                    else:
                        print(f"{Fore.RED}No valid databases selected{Style.RESET_ALL}")
                
                except (ValueError, IndexError):
                    print(f"{Fore.RED}Invalid selection format{Style.RESET_ALL}")
        
        except KeyboardInterrupt:
            logger.info("Database selection cancelled by user")
            return []
    
    def sync_database(self, db_name: str, source_conn: Dict[str, str], 
                     target_conn: Dict[str, str]) -> bool:
        """Synchronize a single database using mysqldump -> mysql pipe"""
        try:
            logger.info(f"📋 Starting sync: {db_name}")
            
            # Build mysqldump command
            dump_cmd = [
                'mysqldump',
                f'--host={source_conn["host"]}',
                f'--port={source_conn["port"]}',
                f'--user={source_conn["user"]}',
                f'--password={source_conn["password"]}',
                db_name
            ]
            
            # Add dump options based on environment variables
            if self.single_transaction:
                dump_cmd.insert(-1, '--single-transaction')
            if self.include_routines:
                dump_cmd.insert(-1, '--routines')
            if self.include_triggers:
                dump_cmd.insert(-1, '--triggers')
            if not self.lock_tables:
                dump_cmd.insert(-1, '--lock-tables=false')
            
            # Build mysql import command
            import_cmd = [
                'mysql',
                f'--host={target_conn["host"]}',
                f'--port={target_conn["port"]}',
                f'--user={target_conn["user"]}',
                f'--password={target_conn["password"]}',
                db_name
            ]
            
            logger.debug(f"Dump command: mysqldump [connection] {db_name}")
            logger.debug(f"Import command: mysql [connection] {db_name}")
            
            # Execute pipe operation
            start_time = datetime.now()
            
            dump_process = subprocess.Popen(
                dump_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            import_process = subprocess.Popen(
                import_cmd,
                stdin=dump_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Close dump stdout to allow proper pipe behavior
            dump_process.stdout.close()
            
            # Wait for both processes
            _, import_error = import_process.communicate()
            dump_process.wait()
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            # Check results
            if dump_process.returncode != 0:
                _, dump_error = dump_process.communicate()
                logger.error(f"❌ Dump failed for {db_name}: {dump_error}")
                return False
            
            if import_process.returncode != 0:
                logger.error(f"❌ Import failed for {db_name}: {import_error}")
                return False
            
            logger.info(f"✅ Successfully synced {db_name} (duration: {duration.total_seconds():.1f}s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Sync failed for {db_name}: {e}")
            return False
    
    def batch_sync(self, databases: List[str], source_conn: Dict[str, str], 
                   target_conn: Dict[str, str]) -> Dict[str, bool]:
        """Execute batch database synchronization"""
        if not databases:
            logger.error("No databases to sync")
            return {}
        
        # Safety check: prevent syncing to same database
        if (source_conn['host'] == target_conn['host'] and 
            source_conn['port'] == target_conn['port']):
            logger.error("❌ Source and target are the same server - operation cancelled for safety")
            return {}
        
        # Show batch confirmation
        print(f"\n{Fore.YELLOW}=== Batch Sync Confirmation ==={Style.RESET_ALL}")
        print(f"Source: {source_conn['name']} ({source_conn['host']}:{source_conn['port']})")
        print(f"Target: {target_conn['name']} ({target_conn['host']}:{target_conn['port']})")
        print(f"Databases to sync: {len(databases)}")
        for db in databases:
            print(f"  • {db}")
        
        print(f"\n{Fore.RED}⚠️  WARNING: This will OVERWRITE data on the target server!{Style.RESET_ALL}")
        
        # Require explicit confirmation with typing
        print(f"\n{Fore.RED}Type 'YES' to proceed with destructive operation:{Style.RESET_ALL}")
        confirmation = get_input("Confirmation", validator=lambda x: x == 'YES', error_message="You must type 'YES' exactly to proceed")
        if confirmation != 'YES':
            logger.info("Batch sync cancelled by user")
            return {}
        
        # Execute synchronization
        results = {}
        successful = 0
        failed = 0
        
        logger.info(f"🚀 Starting batch sync of {len(databases)} databases")
        start_time = datetime.now()
        
        for i, db_name in enumerate(databases, 1):
            print(f"\n{Fore.CYAN}[{i}/{len(databases)}] Syncing {db_name}...{Style.RESET_ALL}")
            
            success = self.sync_database(db_name, source_conn, target_conn)
            results[db_name] = success
            
            if success:
                successful += 1
            else:
                failed += 1
                
                # Ask whether to continue on failure
                if i < len(databases):
                    if not confirm("Continue with remaining databases?", default=True):
                        logger.info("Batch sync stopped by user")
                        break
        
        end_time = datetime.now()
        total_duration = end_time - start_time
        
        # Show summary
        print(f"\n{Fore.CYAN}=== Batch Sync Summary ==={Style.RESET_ALL}")
        print(f"Total databases: {len(databases)}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"⏱️  Total duration: {total_duration.total_seconds():.1f}s")
        
        if successful > 0:
            print(f"\n{Fore.GREEN}Successfully synced databases:{Style.RESET_ALL}")
            for db, success in results.items():
                if success:
                    print(f"  ✅ {db}")
        
        if failed > 0:
            print(f"\n{Fore.RED}Failed databases:{Style.RESET_ALL}")
            for db, success in results.items():
                if not success:
                    print(f"  ❌ {db}")
        
        # Store operation in history
        operation_record = {
            'timestamp': timestamp(),
            'source': f"{source_conn['name']} ({source_conn['host']}:{source_conn['port']})",
            'target': f"{target_conn['name']} ({target_conn['host']}:{target_conn['port']})",
            'databases': databases,
            'results': results,
            'duration': total_duration.total_seconds(),
            'successful': successful,
            'failed': failed
        }
        
        # Save to history
        history = storage.get('sync_history', [])
        history.append(operation_record)
        # Keep only last N operations (from environment variable)
        if len(history) > self.max_history_records:
            history = history[-self.max_history_records:]
        storage.set('sync_history', history)
        
        logger.info(f"🎉 Batch sync completed: {successful} successful, {failed} failed")
        return results
    
    def show_sync_history(self):
        """Display recent synchronization history"""
        history = storage.get('sync_history', [])
        
        if not history:
            print(f"{Fore.YELLOW}No sync history available{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}=== Recent Sync Operations ==={Style.RESET_ALL}")
        
        for i, record in enumerate(reversed(history[-10:]), 1):  # Show last 10
            print(f"\n{Fore.YELLOW}{i}. {record['timestamp']}{Style.RESET_ALL}")
            print(f"   Source: {record['source']}")
            print(f"   Target: {record['target']}")
            print(f"   Databases: {len(record['databases'])} ({record['successful']} successful, {record['failed']} failed)")
            print(f"   Duration: {record['duration']:.1f}s")

    def manage_cached_connections(self):
        """Interactive cached connection management"""
        while True:
            cached_connections = self.list_cached_connections()
            
            print(f"\n{Fore.CYAN}=== Connection Management ==={Style.RESET_ALL}")
            
            if not cached_connections:
                print(f"{Fore.YELLOW}No cached connections available{Style.RESET_ALL}")
                return
            
            print(f"\n{Fore.CYAN}Cached Connections:{Style.RESET_ALL}")
            for i, conn in enumerate(cached_connections, 1):
                print(f"{Fore.YELLOW}{i:2d}.{Style.RESET_ALL} {conn['display']}")
                print(f"    Last used: {conn['last_used']}")
            
            print(f"\n{Fore.CYAN}Options:{Style.RESET_ALL}")
            print("  Delete connection: del <number>")
            print("  Test connection: test <number>")
            print("  Clear all connections: clear")
            print("  Return to main menu: quit")
            
            try:
                action = input(f"\n{Fore.CYAN}Your choice: {Style.RESET_ALL}").strip().lower()
                
                if action == 'quit' or action == 'q':
                    break
                elif action == 'clear':
                    if delete_confirm("ALL cached connections", "connections", force_typing=True, confirmation_text="CLEAR"):
                        self.connections_cache.clear()
                        self.save_cached_connections()
                        print(f"{Fore.GREEN}✅ All connections cleared{Style.RESET_ALL}")
                elif action.startswith('del '):
                    try:
                        conn_num = int(action.split()[1])
                        if 1 <= conn_num <= len(cached_connections):
                            conn_to_delete = cached_connections[conn_num - 1]
                            if delete_confirm(conn_to_delete['name'], "connection"):
                                del self.connections_cache[conn_to_delete['name']]
                                self.save_cached_connections()
                                print(f"{Fore.GREEN}✅ Connection '{conn_to_delete['name']}' deleted{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}Invalid connection number{Style.RESET_ALL}")
                    except (ValueError, IndexError):
                        print(f"{Fore.RED}Invalid command. Use: del <number>{Style.RESET_ALL}")
                elif action.startswith('test '):
                    try:
                        conn_num = int(action.split()[1])
                        if 1 <= conn_num <= len(cached_connections):
                            conn_to_test = cached_connections[conn_num - 1]
                            cached = self.connections_cache[conn_to_test['name']]
                            
                            # Decode password and test
                            try:
                                password = base64.b64decode(cached['password']).decode('utf-8')
                                test_info = {
                                    'name': conn_to_test['name'],
                                    'host': conn_to_test['host'],
                                    'port': conn_to_test['port'],
                                    'user': conn_to_test['user'],
                                    'password': password
                                }
                                
                                print(f"{Fore.CYAN}Testing connection '{conn_to_test['name']}'...{Style.RESET_ALL}")
                                if self.test_connection(test_info):
                                    print(f"{Fore.GREEN}✅ Connection test successful{Style.RESET_ALL}")
                                else:
                                    print(f"{Fore.RED}❌ Connection test failed{Style.RESET_ALL}")
                            except Exception as e:
                                print(f"{Fore.RED}❌ Failed to decode password: {e}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}Invalid connection number{Style.RESET_ALL}")
                    except (ValueError, IndexError):
                        print(f"{Fore.RED}Invalid command. Use: test <number>{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Invalid command. Type 'quit' to exit.{Style.RESET_ALL}")
                    
            except KeyboardInterrupt:
                logger.info("Connection management cancelled by user")
                break
    
    def check_system_commands(self) -> bool:
        """Check if required system commands are available"""
        required_commands = ['mysqldump', 'mysql']
        missing_commands = []
        
        for cmd in required_commands:
            success, _, _ = run_command([cmd, '--version'])
            if not success:
                missing_commands.append(cmd)
        
        if missing_commands:
            logger.error(f"❌ Missing required commands: {', '.join(missing_commands)}")
            print(f"{Fore.RED}Please install MySQL client tools:{Style.RESET_ALL}")
            print("  macOS: brew install mysql-client")
            print("  Ubuntu/Debian: sudo apt-get install mysql-client")
            print("  CentOS/RHEL: sudo yum install mysql")
            return False
        
        logger.info("✅ All required system commands available")
        return True
    
    def run(self):
        """Main tool execution"""
        try:
            # Check system dependencies
            if not self.check_system_commands():
                sys.exit(1)
            
            # Show tool info
            print(f"\n{Fore.BLUE}{Style.BRIGHT}=== {self.tool_name} ==={Style.RESET_ALL}")
            print(f"{Style.DIM}{self.description}{Style.RESET_ALL}\n")
            
            # Check for command arguments
            if len(sys.argv) > 1:
                command = sys.argv[1]
                
                if command == 'history':
                    self.show_sync_history()
                    return
                elif command == 'connections' or command == 'conn':
                    self.manage_cached_connections()
                    return
                elif command == 'help':
                    self.show_help()
                    return
                else:
                    print(f"{Fore.RED}Unknown command: {command}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Available commands: history, connections, help{Style.RESET_ALL}")
                    return
            
            # Main sync workflow
            # Get source and target connections
            source_conn = self.get_connection_info("source")
            target_conn = self.get_connection_info("target")
            
            # Get available databases from source
            print(f"\n{Fore.CYAN}Discovering databases on source server...{Style.RESET_ALL}")
            available_databases = self.list_databases(source_conn)
            
            if not available_databases:
                logger.error("No user databases found on source server")
                return
            
            # Select databases to sync
            selected_databases = self.select_databases(available_databases)
            
            if not selected_databases:
                logger.info("No databases selected for sync")
                return
            
            # Execute batch sync
            self.batch_sync(selected_databases, source_conn, target_conn)
            
        except KeyboardInterrupt:
            logger.info("❌ Operation cancelled by user")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            sys.exit(1)

    def show_help(self):
        """Display help information"""
        print(f"\n{Fore.CYAN}=== MySQL Sync Tool Help ==={Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Commands:{Style.RESET_ALL}")
        print(f"  history                              # Show sync history")
        print(f"  connections                          # Manage cached connections")
        print(f"  help                                 # Show this help")
        
        print(f"\n{Fore.YELLOW}Connection Caching:{Style.RESET_ALL}")
        print(f"  • Connections are automatically cached after successful test")
        print(f"  • Passwords are securely encoded (Base64) and stored in SQLite")
        print(f"  • Use 'connections' command to view, test, or delete cached connections")
        print(f"  • Most recently used connections appear first in selection")
        
        print(f"\n{Fore.YELLOW}Database Selection:{Style.RESET_ALL}")
        print(f"  • Single database: 3")
        print(f"  • Multiple databases: 1,3,5")
        print(f"  • Range selection: 1-5")
        print(f"  • All databases: all")
        
        print(f"\n{Fore.YELLOW}Safety Features:{Style.RESET_ALL}")
        print(f"  • System databases (mysql, information_schema) are filtered out")
        print(f"  • Source and target cannot be the same server")
        print(f"  • Explicit confirmation required for destructive operations")
        print(f"  • Connection testing before caching and sync operations")
        
        print(f"\n{Fore.YELLOW}Environment Variables:{Style.RESET_ALL}")
        print(f"  CACHE_CONNECTIONS=true/false         # Enable/disable connection caching")
        print(f"  TIMEOUT=30                           # Connection timeout in seconds")
        print(f"  BATCH_SIZE=100                       # Batch operation size")
        print(f"  MAX_HISTORY_RECORDS=50               # Maximum sync history records")
        print(f"  DEBUG=true/false                     # Enable debug logging")


@click.command()
@click.option('--config', help='Custom configuration file path')
@click.option('--history', is_flag=True, help='Show sync history')
@click.option('--connections', is_flag=True, help='Manage cached connections')
@click.option('--help-tool', is_flag=True, help='Show tool help')
def main(config: Optional[str], history: bool, connections: bool, help_tool: bool):
    """MySQL database batch synchronization tool with connection caching"""
    if history:
        sys.argv.append('history')
    elif connections:
        sys.argv.append('connections')
    elif help_tool:
        sys.argv.append('help')
    
    if config:
        # Load custom config if provided
        logger.info(f"Using custom configuration: {config}")
    
    tool = MySQLSyncTool()
    tool.run()


if __name__ == '__main__':
    main()
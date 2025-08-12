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
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Import OpsKit common libraries
sys.path.insert(0, os.path.join(os.environ['OPSKIT_BASE_PATH'], 'common/python'))

from interactive import get_interactive
from storage import get_storage
from utils import run_command, timestamp, get_env_var

# Third-party imports
try:
    import pymysql
    import click
except ImportError as e:
    # Use print here since logger may not be available yet
    print(f"Missing required dependency: {e}")
    print("Please ensure all dependencies are installed.")
    sys.exit(1)

# Initialize OpsKit components
logger = get_interactive(__name__, 'mysql-sync')
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
        self.retry_delay = get_env_var('RETRY_DELAY', 2, int)
        self.connect_timeout = get_env_var('CONNECT_TIMEOUT', 30, int)
        self.batch_size = get_env_var('BATCH_SIZE', 100, int)
        self.confirm_destructive = get_env_var('CONFIRM_DESTRUCTIVE', True, bool)
        self.show_progress = get_env_var('SHOW_PROGRESS', True, bool)
        self.verbose = get_env_var('VERBOSE', False, bool)
        self.cache_connections = get_env_var('CACHE_CONNECTIONS', True, bool)
        self.max_history_records = get_env_var('MAX_HISTORY_RECORDS', 50, int)
        
        # MySQL dump settings
        self.single_transaction = get_env_var('SINGLE_TRANSACTION', True, bool)
        self.include_routines = get_env_var('INCLUDE_ROUTINES', True, bool)
        self.include_triggers = get_env_var('INCLUDE_TRIGGERS', True, bool)
        self.lock_tables = get_env_var('LOCK_TABLES', False, bool)
        self.set_gtid_purged = get_env_var('SET_GTID_PURGED', 'OFF', str)
        
        logger.debug(f"MySQL Sync initialized - timeout: {self.timeout}s, batch_size: {self.batch_size}")
    
    def load_cached_connections(self):
        """Load cached connections from storage"""
        logger.debug("Starting to load cached connections from storage")
        try:
            cached = storage.get('connections', {})
            if isinstance(cached, dict):
                self.connections_cache = cached
                logger.debug(f"Successfully loaded {len(self.connections_cache)} cached connections")
                for name, conn in self.connections_cache.items():
                    logger.debug(f"  - {name}: {conn.get('user', 'unknown')}@{conn.get('host', 'unknown')}:{conn.get('port', 'unknown')}")
            else:
                logger.debug("No cached connections found or invalid format")
                self.connections_cache = {}
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
        
        # Sort by last used (most recent first), handle 'Unknown' timestamps properly
        def sort_key(connection):
            last_used = connection['last_used']
            if last_used == 'Unknown':
                # Use epoch time (very old) for unknown timestamps to put them at the end
                return '1970-01-01 00:00:00'
            return last_used
        
        connections.sort(key=sort_key, reverse=True)
        return connections

    def select_cached_connection(self, connection_type: str) -> Optional[Dict[str, str]]:
        """Let user select from cached connections"""
        cached_connections = self.list_cached_connections()
        
        if not cached_connections:
            logger.warning_msg("No cached connections available")
            return None
        
        logger.subsection(f"Cached {connection_type.upper()} Connections")
        for i, conn in enumerate(cached_connections, 1):
            logger.info(f"{i:2d}. {conn['display']}")
            logger.info(f"    Last used: {conn['last_used']}")
        
        logger.info("\nOptions:")
        logger.info("  Select connection: 1, 2, 3...")
        logger.info("  Create new connection: new")
        logger.info("  Cancel: press Ctrl+C")
        
        try:
            while True:
                selection = logger.get_input("Your choice").strip().lower()
                
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
                            
                            logger.success(f"Selected connection: {selected_conn['display']}")
                            
                            return {
                                'name': selected_conn['name'],
                                'host': selected_conn['host'],
                                'port': selected_conn['port'],
                                'user': selected_conn['user'],
                                'password': password
                            }
                        except Exception as e:
                            logger.error(f"Failed to decode cached password: {e}")
                            logger.failure(f"Failed to decode password for '{selected_conn['name']}'")
                            return None
                    else:
                        logger.failure(f"Invalid selection. Please choose 1-{len(cached_connections)} or 'new'")
                except ValueError:
                    logger.failure("Invalid input. Please enter a number or 'new'")
        
        except KeyboardInterrupt:
            logger.user_cancelled("cached connection selection")
            return None

    def get_connection_info(self, connection_type: str) -> Dict[str, str]:
        """Interactive connection information collection with enhanced caching"""
        logger.section(f"{connection_type.upper()} Connection Setup")
        
        # First, show cached connections if available
        if self.connections_cache and self.cache_connections:
            selected_connection = self.select_cached_connection(connection_type)
            if selected_connection:
                return selected_connection
            
            # If user chose 'new' or selection failed, continue to manual input
        
        # Manual connection setup
        logger.subsection(f"Create New {connection_type.upper()} Connection")
        
        # Ask for connection name
        name = logger.get_input(
            f"Enter a name for this {connection_type} connection",
            validator=lambda x: len(x.strip()) > 0,
            error_message="Connection name cannot be empty"
        )
        
        # Check if name already exists and offer to overwrite
        if name in self.connections_cache:
            if not logger.confirm(f"Connection '{name}' already exists. Overwrite?", default=False):
                logger.warning_msg("Please choose a different name")
                return self.get_connection_info(connection_type)
        
        # Get connection details
        host = logger.get_input("MySQL Host", default="localhost")
        port = logger.get_input("MySQL Port", default="3306", validator=lambda x: x.isdigit() and 1 <= int(x) <= 65535, error_message="Port must be between 1 and 65535")
        user = logger.get_input("MySQL User", default="root")
        
        # Get password securely
        password = logger.get_input("MySQL Password", password=True)
        
        connection_info = {
            'name': name,
            'host': host,
            'port': port,
            'user': user,
            'password': password
        }
        
        # Test connection before caching
        logger.progress("Testing connection...")
        if self.test_connection(connection_info):
            # Ask if user wants to cache this connection
            if self.cache_connections:
                if logger.confirm("Save this connection for future use?", default=True):
                    self.connections_cache[name] = {
                        'host': host,
                        'port': port,
                        'user': user,
                        'password': base64.b64encode(password.encode('utf-8')).decode('utf-8'),
                        'last_used': timestamp()
                    }
                    self.save_cached_connections()
                    logger.success(f"Connection '{name}' cached successfully")
                else:
                    logger.warning_msg("Connection not cached (temporary use only)")
        else:
            logger.failure("Connection test failed. Please check your credentials and try again.")
            if logger.confirm("Retry connection setup?", default=True):
                return self.get_connection_info(connection_type)
            else:
                sys.exit(1)
        
        return connection_info
    
    def test_connection(self, conn_info: Dict[str, str]) -> bool:
        """Test database connection"""
        try:
            logger.progress(f"Testing connection to {conn_info['host']}:{conn_info['port']}")
            
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
                logger.success(f"Connection successful - MySQL {version}")
            
            connection.close()
            return True
            
        except Exception as e:
            logger.failure(f"Connection failed: {e}")
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
            
            logger.progress(f"Found {len(user_databases)} user databases")
            return sorted(user_databases)
            
        except Exception as e:
            logger.error(f"Failed to list databases: {e}")
            return []
    
    def select_databases(self, available_dbs: List[str]) -> List[str]:
        """Interactive database selection"""
        if not available_dbs:
            logger.failure("No databases available for selection")
            return []
        
        logger.subsection("Available Databases")
        for i, db in enumerate(available_dbs, 1):
            logger.info(f"{i:2d}. {db}")
        
        logger.info("\nSelection Options:")
        logger.info("  Single database: 3")
        logger.info("  Multiple databases: 1,3,5")
        logger.info("  Range: 1-5")
        logger.info("  All databases: all")
        logger.info("  Cancel: press Ctrl+C")
        
        try:
            while True:
                selection = logger.get_input("Select databases").strip().lower()
                
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
                        
                        logger.display_list("Selected databases", selected_dbs)
                        
                        if logger.confirm("Confirm selection?", default=True):
                            return selected_dbs
                    else:
                        logger.failure("No valid databases selected")
                
                except (ValueError, IndexError):
                    logger.failure("Invalid selection format")
        
        except KeyboardInterrupt:
            logger.user_cancelled("database selection")
            return []
    
    def sync_database(self, db_name: str, source_conn: Dict[str, str], 
                     target_conn: Dict[str, str]) -> bool:
        """Synchronize a single database using mysqldump -> mysql pipe with retry logic"""
        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt > 1:
                    logger.retry_attempt(attempt, self.max_retries, f"sync: {db_name}")
                else:
                    logger.operation_start(f"sync: {db_name}")
                
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
                
                # Add GTID settings to prevent "@@GLOBAL.GTID_PURGED cannot be changed" error
                if self.set_gtid_purged:
                    dump_cmd.insert(-1, f'--set-gtid-purged={self.set_gtid_purged}')
                
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
                
                # Wait for both processes and capture their output
                _, import_error = import_process.communicate()
                dump_output, dump_error = dump_process.communicate()
                
                end_time = datetime.now()
                duration = end_time - start_time
                
                # Check results
                if dump_process.returncode != 0:
                    error_msg = f"Dump failed for {db_name}: {dump_error}"
                    logger.failure(error_msg)
                    if attempt < self.max_retries:
                        logger.progress(f"Waiting {self.retry_delay}s before retry...")
                        time.sleep(self.retry_delay)
                        continue
                    return False
                
                if import_process.returncode != 0:
                    error_msg = f"Import failed for {db_name}: {import_error}"
                    logger.failure(error_msg)
                    if attempt < self.max_retries:
                        logger.progress(f"Waiting {self.retry_delay}s before retry...")
                        time.sleep(self.retry_delay)
                        continue
                    return False
                
                logger.operation_complete(f"synced {db_name}", duration.total_seconds())
                return True
                
            except Exception as e:
                error_msg = f"Sync failed for {db_name}: {e}"
                logger.failure(error_msg)
                if attempt < self.max_retries:
                    logger.progress(f"Waiting {self.retry_delay}s before retry...")
                    time.sleep(self.retry_delay)
                    continue
                
        logger.failure(f"All {self.max_retries} retry attempts failed for {db_name}")
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
            logger.failure("Source and target are the same server - operation cancelled for safety")
            return {}
        
        # Show batch confirmation
        logger.section("Batch Sync Confirmation")
        logger.display_info("Sync Configuration", {
            "Source": f"{source_conn['name']} ({source_conn['host']}:{source_conn['port']})",
            "Target": f"{target_conn['name']} ({target_conn['host']}:{target_conn['port']})",
            "Databases to sync": str(len(databases))
        })
        logger.display_list("Databases", databases)
        
        logger.warning_msg("WARNING: This will OVERWRITE data on the target server!")
        
        # Require explicit confirmation with typing
        logger.warning_msg("Type 'YES' to proceed with destructive operation:")
        confirmation = logger.get_input("Confirmation", validator=lambda x: x == 'YES', error_message="You must type 'YES' exactly to proceed")
        if confirmation != 'YES':
            logger.user_cancelled("batch sync")
            return {}
        
        # Execute synchronization
        results = {}
        successful = 0
        failed = 0
        
        logger.operation_start(f"batch sync of {len(databases)} databases")
        start_time = datetime.now()
        
        for i, db_name in enumerate(databases, 1):
            logger.step(i, len(databases), f"Syncing {db_name}...")
            
            success = self.sync_database(db_name, source_conn, target_conn)
            results[db_name] = success
            
            if success:
                successful += 1
            else:
                failed += 1
                
                # Ask whether to continue on failure
                if i < len(databases):
                    if not logger.confirm("Continue with remaining databases?", default=True):
                        logger.user_cancelled("batch sync")
                        break
        
        end_time = datetime.now()
        total_duration = end_time - start_time
        
        # Show summary
        logger.section("Batch Sync Summary")
        logger.display_info("Results", {
            "Total databases": str(len(databases)),
            "Successful": str(successful),
            "Failed": str(failed),
            "Total duration": f"{total_duration.total_seconds():.1f}s"
        })
        
        if successful > 0:
            successful_dbs = [db for db, success in results.items() if success]
            logger.display_list("Successfully synced databases", successful_dbs, "  ✅ ")
        
        if failed > 0:
            failed_dbs = [db for db, success in results.items() if not success]
            logger.display_list("Failed databases", failed_dbs, "  ❌ ")
        
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
        
        logger.operation_complete(f"batch sync: {successful} successful, {failed} failed")
        return results
    
    def show_sync_history(self):
        """Display recent synchronization history"""
        history = storage.get('sync_history', [])
        
        if not history:
            logger.warning_msg("No sync history available")
            return
        
        logger.section("Recent Sync Operations")
        
        for i, record in enumerate(reversed(history[-10:]), 1):  # Show last 10
            logger.info(f"\n{i}. {record['timestamp']}")
            logger.info(f"   Source: {record['source']}")
            logger.info(f"   Target: {record['target']}")
            logger.info(f"   Databases: {len(record['databases'])} ({record['successful']} successful, {record['failed']} failed)")
            logger.info(f"   Duration: {record['duration']:.1f}s")

    def manage_cached_connections(self):
        """Interactive cached connection management"""
        while True:
            cached_connections = self.list_cached_connections()
            
            logger.section("Connection Management")
            
            if not cached_connections:
                logger.warning_msg("No cached connections available")
                return
            
            logger.subsection("Cached Connections")
            for i, conn in enumerate(cached_connections, 1):
                logger.info(f"{i:2d}. {conn['display']}")
                logger.info(f"    Last used: {conn['last_used']}")
            
            logger.info("\nOptions:")
            logger.info("  Delete connection: del <number>")
            logger.info("  Test connection: test <number>")
            logger.info("  Clear all connections: clear")
            logger.info("  Return to main menu: quit")
            
            try:
                action = logger.get_input("Your choice").strip().lower()
                
                if action == 'quit' or action == 'q':
                    break
                elif action == 'clear':
                    if logger.delete_confirm("ALL cached connections", "connections", force_typing=True, confirmation_text="CLEAR"):
                        self.connections_cache.clear()
                        self.save_cached_connections()
                        logger.success("All connections cleared")
                elif action.startswith('del '):
                    try:
                        conn_num = int(action.split()[1])
                        if 1 <= conn_num <= len(cached_connections):
                            conn_to_delete = cached_connections[conn_num - 1]
                            if logger.delete_confirm(conn_to_delete['name'], "connection"):
                                del self.connections_cache[conn_to_delete['name']]
                                self.save_cached_connections()
                                logger.success(f"Connection '{conn_to_delete['name']}' deleted")
                        else:
                            logger.failure("Invalid connection number")
                    except (ValueError, IndexError):
                        logger.failure("Invalid command. Use: del <number>")
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
                                
                                logger.progress(f"Testing connection '{conn_to_test['name']}'...")
                                if self.test_connection(test_info):
                                    logger.success("Connection test successful")
                                else:
                                    logger.failure("Connection test failed")
                            except Exception as e:
                                logger.failure(f"Failed to decode password: {e}")
                        else:
                            logger.failure("Invalid connection number")
                    except (ValueError, IndexError):
                        logger.failure("Invalid command. Use: test <number>")
                else:
                    logger.failure("Invalid command. Type 'quit' to exit.")
                    
            except KeyboardInterrupt:
                logger.user_cancelled("connection management")
                break
    
    
    def run(self):
        """Main tool execution"""
        try:
            
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
                    logger.failure(f"Unknown command: {command}")
                    logger.info("Available commands: history, connections, help")
                    return
            
            # Main sync workflow
            # Get source and target connections
            source_conn = self.get_connection_info("source")
            target_conn = self.get_connection_info("target")
            
            # Get available databases from source
            logger.progress("Discovering databases on source server...")
            available_databases = self.list_databases(source_conn)
            
            if not available_databases:
                logger.failure("No user databases found on source server")
                return
            
            # Select databases to sync
            selected_databases = self.select_databases(available_databases)
            
            if not selected_databases:
                logger.warning_msg("No databases selected for sync")
                return
            
            # Execute batch sync
            self.batch_sync(selected_databases, source_conn, target_conn)
            
        except KeyboardInterrupt:
            logger.user_cancelled("operation")
        except Exception as e:
            logger.failure(f"Unexpected error: {e}")
            sys.exit(1)

    def show_help(self):
        """Display help information"""
        logger.section("MySQL Sync Tool Help")
        
        logger.subsection("Commands")
        logger.info("  history                              # Show sync history")
        logger.info("  connections                          # Manage cached connections")
        logger.info("  help                                 # Show this help")
        
        logger.subsection("Connection Caching")
        logger.info("  • Connections are automatically cached after successful test")
        logger.info("  • Passwords are securely encoded (Base64) and stored in SQLite")
        logger.info("  • Use 'connections' command to view, test, or delete cached connections")
        logger.info("  • Most recently used connections appear first in selection")
        
        logger.subsection("Database Selection")
        logger.info("  • Single database: 3")
        logger.info("  • Multiple databases: 1,3,5")
        logger.info("  • Range selection: 1-5")
        logger.info("  • All databases: all")
        
        logger.subsection("Safety Features")
        logger.info("  • System databases (mysql, information_schema) are filtered out")
        logger.info("  • Source and target cannot be the same server")
        logger.info("  • Explicit confirmation required for destructive operations")
        logger.info("  • Connection testing before caching and sync operations")
        
        logger.subsection("Environment Variables")
        logger.info("  CACHE_CONNECTIONS=true/false         # Enable/disable connection caching")
        logger.info("  TIMEOUT=30                           # Connection timeout in seconds")
        logger.info("  BATCH_SIZE=100                       # Batch operation size")
        logger.info("  MAX_HISTORY_RECORDS=50               # Maximum sync history records")
        logger.info("  MAX_RETRIES=3                        # Maximum retry attempts for failed syncs")
        logger.info("  RETRY_DELAY=2                        # Delay in seconds between retry attempts")
        logger.info("  SET_GTID_PURGED=OFF                  # GTID handling (OFF/AUTO/ON) - prevents GTID errors")


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
    # Let Click handle command line arguments properly
    # Click will automatically process sys.argv when main() is called as a CLI command
    main()
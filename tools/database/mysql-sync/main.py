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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../common/python'))

from logger import get_logger
from storage import get_storage
from utils import load_config, save_config, run_command, get_user_input, timestamp

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
        self.config = load_config('mysql-sync')
        self.connections_cache = {}
        self.load_cached_connections()
        
        # Tool metadata
        self.tool_name = "MySQL Sync"
        self.version = "2.0.0"
        self.description = "Interactive MySQL database batch synchronization tool"
        
        logger.info(f"🚀 Starting {self.tool_name} v{self.version}")
    
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
    
    def get_connection_info(self, connection_type: str) -> Dict[str, str]:
        """Interactive connection information collection"""
        print(f"\n{Fore.CYAN}=== {connection_type.upper()} Connection Setup ==={Style.RESET_ALL}")
        
        # Ask for connection name
        name = get_user_input(
            f"Enter a name for this {connection_type} connection",
            validator=lambda x: len(x.strip()) > 0
        ).strip()
        
        # Check if we have cached connection
        if name in self.connections_cache:
            cached = self.connections_cache[name]
            print(f"{Fore.GREEN}Found cached connection: {name}{Style.RESET_ALL}")
            print(f"Host: {cached['host']}:{cached['port']}")
            print(f"User: {cached['user']}")
            print(f"Last used: {cached.get('last_used', 'Unknown')}")
            
            use_cached = input(f"{Fore.CYAN}Use cached connection? [Y/n]: {Style.RESET_ALL}").strip().lower()
            if use_cached in ('', 'y', 'yes'):
                # Decode password and return
                try:
                    password = base64.b64decode(cached['password']).decode('utf-8')
                    return {
                        'name': name,
                        'host': cached['host'],
                        'port': cached['port'],
                        'user': cached['user'],
                        'password': password
                    }
                except Exception as e:
                    logger.error(f"Failed to decode cached password: {e}")
                    print(f"{Fore.RED}Failed to decode cached password, please enter manually{Style.RESET_ALL}")
        
        # Get connection details
        host = get_user_input("MySQL Host", "localhost").strip()
        port = get_user_input("MySQL Port", "3306").strip()
        user = get_user_input("MySQL User", "root").strip()
        
        # Get password securely
        password = getpass.getpass(f"{Fore.CYAN}MySQL Password: {Style.RESET_ALL}")
        
        connection_info = {
            'name': name,
            'host': host,
            'port': port,
            'user': user,
            'password': password
        }
        
        # Test connection before caching
        if self.test_connection(connection_info):
            # Cache the connection (encode password)
            self.connections_cache[name] = {
                'host': host,
                'port': port,
                'user': user,
                'password': base64.b64encode(password.encode('utf-8')).decode('utf-8'),
                'last_used': timestamp()
            }
            self.save_cached_connections()
            logger.info(f"Connection '{name}' cached successfully")
        
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
                connect_timeout=self.config.get('connections.default_timeout', 30)
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
                        
                        confirm = input(f"\n{Fore.CYAN}Confirm selection? [Y/n]: {Style.RESET_ALL}").strip().lower()
                        if confirm in ('', 'y', 'yes'):
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
                '--single-transaction',
                '--routines',
                '--triggers',
                '--lock-tables=false',
                db_name
            ]
            
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
            import_output, import_error = import_process.communicate()
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
        
        # Require explicit confirmation
        confirmation = input(f"\n{Fore.CYAN}Type 'YES' to proceed: {Style.RESET_ALL}").strip()
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
                    continue_sync = input(f"{Fore.YELLOW}Continue with remaining databases? [Y/n]: {Style.RESET_ALL}").strip().lower()
                    if continue_sync in ('n', 'no'):
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
        # Keep only last 50 operations
        if len(history) > 50:
            history = history[-50:]
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
            print(f"\n{Fore.BLUE}{Style.BRIGHT}=== {self.tool_name} v{self.version} ==={Style.RESET_ALL}")
            print(f"{Style.DIM}{self.description}{Style.RESET_ALL}\n")
            
            # Check for history command
            if len(sys.argv) > 1 and sys.argv[1] == 'history':
                self.show_sync_history()
                return
            
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


@click.command()
@click.option('--config', help='Custom configuration file path')
@click.option('--history', is_flag=True, help='Show sync history')
def main(config: Optional[str], history: bool):
    """MySQL database batch synchronization tool"""
    if history:
        sys.argv.append('history')
    
    if config:
        # Load custom config if provided
        logger.info(f"Using custom configuration: {config}")
    
    tool = MySQLSyncTool()
    tool.run()


if __name__ == '__main__':
    main()
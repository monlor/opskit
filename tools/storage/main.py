#!/usr/bin/env python3
"""
S3 Sync Tool - OpsKit Version
Intelligent bidirectional synchronization between local directories and S3 buckets
"""

import os
import sys
import json
import time
import hashlib
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import fnmatch

# Import OpsKit common libraries
sys.path.insert(0, os.path.join(os.environ['OPSKIT_BASE_PATH'], 'common/python'))

from logger import get_logger
from storage import get_storage
from utils import run_command, timestamp, get_env_var
from interactive import get_input, confirm, select_from_list, delete_confirm

# Third-party imports
try:
    import boto3
    import botocore
    from botocore.exceptions import (
        ClientError, NoCredentialsError, PartialCredentialsError,
        ProfileNotFound, BotoCoreError
    )
    from boto3.s3.transfer import TransferConfig
    import click
    from colorama import init, Fore, Style, Back
    init(autoreset=True)
    
    # Optional dependencies
    try:
        import tqdm
        TQDM_AVAILABLE = True
    except ImportError:
        TQDM_AVAILABLE = False
    
    try:
        import yaml
        YAML_AVAILABLE = True
    except ImportError:
        YAML_AVAILABLE = False
        
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please ensure all dependencies are installed.")
    sys.exit(1)

# Initialize OpsKit components
logger = get_logger(__name__)
storage = get_storage('s3-sync')


@dataclass
class SyncStats:
    """Statistics for sync operations"""
    uploaded: int = 0
    downloaded: int = 0
    deleted: int = 0
    skipped: int = 0
    errors: int = 0
    total_size: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def duration(self) -> float:
        """Get operation duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dataclass
class FileInfo:
    """File information for comparison"""
    path: str
    size: int
    modified: datetime
    etag: Optional[str] = None
    is_local: bool = True
    storage_class: Optional[str] = None


class ExclusionManager:
    """Manages file exclusion patterns"""
    
    def __init__(self, patterns: Optional[List[str]] = None):
        self.patterns = patterns or []
        self.default_patterns = [
            "*.tmp", "*.temp", "*.log", "*.swp", "*~",
            ".DS_Store", "Thumbs.db", "desktop.ini",
            ".git/", ".svn/", ".hg/",
            "__pycache__/", "*.pyc", "*.pyo",
            "node_modules/", ".npm/",
            ".vscode/", ".idea/",
            "*.bak", "*.backup"
        ]
    
    def add_pattern(self, pattern: str):
        """Add exclusion pattern"""
        if pattern not in self.patterns:
            self.patterns.append(pattern)
    
    def should_exclude(self, file_path: str) -> bool:
        """Check if file should be excluded"""
        # Normalize path for comparison
        normalized_path = file_path.replace(os.sep, '/').strip('/')
        
        # Check against all patterns
        all_patterns = self.patterns + self.default_patterns
        
        for pattern in all_patterns:
            # Handle directory patterns
            if pattern.endswith('/'):
                pattern_dir = pattern.rstrip('/')
                if '/' in normalized_path:
                    if any(part == pattern_dir for part in normalized_path.split('/')):
                        return True
                elif normalized_path == pattern_dir:
                    return True
            # Handle file patterns
            elif fnmatch.fnmatch(normalized_path, pattern):
                return True
            elif fnmatch.fnmatch(os.path.basename(normalized_path), pattern):
                return True
        
        return False


@dataclass
class S3ConnectionInfo:
    """S3 connection information"""
    name: str
    profile: str
    region: str
    endpoint_url: Optional[str] = None
    last_used: Optional[str] = None
    
    @property
    def display(self) -> str:
        """Display string for connection"""
        endpoint = f" [{self.endpoint_url}]" if self.endpoint_url else ""
        return f"{self.name} ({self.profile}@{self.region}{endpoint})"


class S3ConnectionManager:
    """Manages S3 connection information with caching"""
    
    def __init__(self):
        self.session = None
        self.current_profile = None
        self.connections_cache = {}
        self.cache_connections = get_env_var('CACHE_CONNECTIONS', True, bool)
        self.load_cached_connections()
    
    def load_cached_connections(self):
        """Load cached connections from storage"""
        try:
            cached = storage.get('s3_connections', {})
            if isinstance(cached, dict):
                self.connections_cache = cached
                logger.debug(f"Loaded {len(self.connections_cache)} cached S3 connections")
        except Exception as e:
            logger.error(f"Failed to load cached S3 connections: {e}")
            self.connections_cache = {}
    
    def save_cached_connections(self):
        """Save connections to storage"""
        try:
            storage.set('s3_connections', self.connections_cache)
            logger.debug("Saved S3 connection cache")
        except Exception as e:
            logger.error(f"Failed to save S3 connections: {e}")
    
    def list_cached_connections(self) -> List[S3ConnectionInfo]:
        """List all cached connections with details"""
        if not self.connections_cache:
            return []
        
        connections = []
        for name, cached in self.connections_cache.items():
            connections.append(S3ConnectionInfo(
                name=name,
                profile=cached['profile'],
                region=cached['region'],
                endpoint_url=cached.get('endpoint_url'),
                last_used=cached.get('last_used', 'Unknown')
            ))
        
        # Sort by last used (most recent first)
        def sort_key(connection):
            last_used = connection.last_used
            if last_used == 'Unknown':
                return '1970-01-01 00:00:00'
            return last_used
        
        connections.sort(key=sort_key, reverse=True)
        return connections

    def select_cached_connection(self) -> Optional[S3ConnectionInfo]:
        """Let user select from cached connections"""
        cached_connections = self.list_cached_connections()
        
        if not cached_connections:
            print(f"{Fore.YELLOW}No cached S3 connections available{Style.RESET_ALL}")
            return None
        
        print(f"\n{Fore.CYAN}=== Cached S3 Connections ==={Style.RESET_ALL}")
        for i, conn in enumerate(cached_connections, 1):
            print(f"{Fore.YELLOW}{i:2d}.{Style.RESET_ALL} {conn.display}")
            print(f"    Last used: {conn.last_used}")
        
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
                        
                        # Update last used timestamp
                        self.connections_cache[selected_conn.name]['last_used'] = timestamp()
                        self.save_cached_connections()
                        
                        print(f"{Fore.GREEN}✅ Selected connection: {selected_conn.display}{Style.RESET_ALL}")
                        return selected_conn
                    else:
                        print(f"{Fore.RED}Invalid selection. Please choose 1-{len(cached_connections)} or 'new'{Style.RESET_ALL}")
                except ValueError:
                    print(f"{Fore.RED}Invalid input. Please enter a number or 'new'{Style.RESET_ALL}")
        
        except KeyboardInterrupt:
            logger.info("Connection selection cancelled by user")
            return None

    def get_connection_info(self) -> Optional[S3ConnectionInfo]:
        """Interactive S3 connection information collection"""
        print(f"\n{Fore.CYAN}=== S3 Connection Setup ==={Style.RESET_ALL}")
        
        # First, show cached connections if available
        if self.connections_cache and self.cache_connections:
            selected_connection = self.select_cached_connection()
            if selected_connection:
                return selected_connection
            
            # If user chose 'new' or selection failed, continue to manual input
        
        # Manual connection setup
        print(f"\n{Fore.CYAN}=== Create New S3 Connection ==={Style.RESET_ALL}")
        
        # Ask for connection name
        name = get_input(
            "Enter a name for this S3 connection",
            validator=lambda x: len(x.strip()) > 0,
            error_message="Connection name cannot be empty"
        )
        
        # Check if name already exists and offer to overwrite
        if name in self.connections_cache:
            if not confirm(f"Connection '{name}' already exists. Overwrite?", default=False):
                print(f"{Fore.YELLOW}Please choose a different name{Style.RESET_ALL}")
                return self.get_connection_info()
        
        # List available AWS profiles
        profiles = self.list_aws_profiles()
        if not profiles:
            logger.error("No AWS profiles found. Please configure AWS credentials first.")
            return None
        
        if len(profiles) == 1:
            profile = profiles[0]
            print(f"Using AWS profile: {profile}")
        else:
            print(f"\n{Fore.CYAN}Available AWS profiles:{Style.RESET_ALL}")
            for i, p in enumerate(profiles, 1):
                region = self.get_profile_region(p)
                print(f"{Fore.YELLOW}{i:2d}.{Style.RESET_ALL} {p} {Fore.DIM}({region}){Style.RESET_ALL}")
            
            profile_choice = get_input(
                "Select AWS profile",
                default="1",
                validator=lambda x: x.isdigit() and 1 <= int(x) <= len(profiles),
                error_message=f"Choose 1-{len(profiles)}"
            )
            profile = profiles[int(profile_choice) - 1]
        
        # Get region
        default_region = self.get_profile_region(profile)
        region = get_input("AWS Region", default=default_region)
        
        # Get optional endpoint URL for S3-compatible services
        endpoint_url = get_input("S3 Endpoint URL (leave empty for AWS S3)", default="")
        endpoint_url = endpoint_url.strip() or None
        
        connection_info = S3ConnectionInfo(
            name=name,
            profile=profile,
            region=region,
            endpoint_url=endpoint_url
        )
        
        # Test connection before caching
        print(f"\n{Fore.CYAN}Testing S3 connection...{Style.RESET_ALL}")
        if self.test_connection(connection_info):
            # Ask if user wants to cache this connection
            if self.cache_connections:
                if confirm("Save this connection for future use?", default=True):
                    self.connections_cache[name] = {
                        'profile': profile,
                        'region': region,
                        'endpoint_url': endpoint_url,
                        'last_used': timestamp()
                    }
                    self.save_cached_connections()
                    print(f"{Fore.GREEN}✅ Connection '{name}' cached successfully{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Connection not cached (temporary use only){Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Connection test failed. Please check your configuration and try again.{Style.RESET_ALL}")
            if confirm("Retry connection setup?", default=True):
                return self.get_connection_info()
            else:
                return None
        
        return connection_info

    def manage_cached_connections(self):
        """Interactive cached connection management"""
        while True:
            cached_connections = self.list_cached_connections()
            
            print(f"\n{Fore.CYAN}=== S3 Connection Management ==={Style.RESET_ALL}")
            
            if not cached_connections:
                print(f"{Fore.YELLOW}No cached S3 connections available{Style.RESET_ALL}")
                return
            
            print(f"\n{Fore.CYAN}Cached S3 Connections:{Style.RESET_ALL}")
            for i, conn in enumerate(cached_connections, 1):
                print(f"{Fore.YELLOW}{i:2d}.{Style.RESET_ALL} {conn.display}")
                print(f"    Last used: {conn.last_used}")
            
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
                    if delete_confirm("ALL cached S3 connections", "connections", force_typing=True, confirmation_text="CLEAR"):
                        self.connections_cache.clear()
                        self.save_cached_connections()
                        print(f"{Fore.GREEN}✅ All S3 connections cleared{Style.RESET_ALL}")
                elif action.startswith('del '):
                    try:
                        conn_num = int(action.split()[1])
                        if 1 <= conn_num <= len(cached_connections):
                            conn_to_delete = cached_connections[conn_num - 1]
                            if delete_confirm(conn_to_delete.name, "S3 connection"):
                                del self.connections_cache[conn_to_delete.name]
                                self.save_cached_connections()
                                print(f"{Fore.GREEN}✅ S3 connection '{conn_to_delete.name}' deleted{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}Invalid connection number{Style.RESET_ALL}")
                    except (ValueError, IndexError):
                        print(f"{Fore.RED}Invalid command. Use: del <number>{Style.RESET_ALL}")
                elif action.startswith('test '):
                    try:
                        conn_num = int(action.split()[1])
                        if 1 <= conn_num <= len(cached_connections):
                            conn_to_test = cached_connections[conn_num - 1]
                            
                            print(f"{Fore.CYAN}Testing S3 connection '{conn_to_test.name}'...{Style.RESET_ALL}")
                            if self.test_connection(conn_to_test):
                                print(f"{Fore.GREEN}✅ Connection test successful{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.RED}❌ Connection test failed{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}Invalid connection number{Style.RESET_ALL}")
                    except (ValueError, IndexError):
                        print(f"{Fore.RED}Invalid command. Use: test <number>{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Invalid command. Type 'quit' to exit.{Style.RESET_ALL}")
                    
            except KeyboardInterrupt:
                logger.info("Connection management cancelled by user")
                break
    
    def list_aws_profiles(self) -> List[str]:
        """List available AWS profiles"""
        profiles = []
        
        # Check for default credentials
        try:
            boto3.Session()
            profiles.append('default')
        except (NoCredentialsError, PartialCredentialsError):
            pass
        
        # Check credentials file
        credentials_file = Path.home() / '.aws' / 'credentials'
        if credentials_file.exists():
            try:
                import configparser
                config = configparser.ConfigParser()
                config.read(credentials_file)
                for section in config.sections():
                    if section != 'default' and section not in profiles:
                        profiles.append(section)
            except Exception as e:
                logger.warning(f"Failed to read AWS credentials file: {e}")
        
        return profiles
    
    def get_profile_region(self, profile: str) -> str:
        """Get region for AWS profile"""
        try:
            if profile == 'default':
                session = boto3.Session()
            else:
                session = boto3.Session(profile_name=profile)
            return session.region_name or 'us-east-1'
        except Exception:
            return 'us-east-1'
    
    def test_connection(self, connection_info: S3ConnectionInfo) -> bool:
        """Test S3 connection"""
        try:
            logger.info(f"Testing S3 connection: {connection_info.profile}@{connection_info.region}")
            
            if connection_info.profile == 'default':
                session = boto3.Session()
            else:
                session = boto3.Session(profile_name=connection_info.profile)
            
            # Create S3 client with specified region and endpoint
            s3_config = {'region_name': connection_info.region}
            if connection_info.endpoint_url:
                s3_config['endpoint_url'] = connection_info.endpoint_url
            
            s3_client = session.client('s3', **s3_config)
            
            # Test with simple list_buckets call
            response = s3_client.list_buckets()
            bucket_count = len(response.get('Buckets', []))
            
            logger.info(f"✅ S3 connection successful - {bucket_count} buckets accessible")
            
            # Store session for later use
            self.session = session
            self.current_profile = connection_info.profile
            return True
            
        except Exception as e:
            logger.error(f"❌ S3 connection failed: {e}")
            return False
    
    def select_profile(self) -> Optional[str]:
        """Interactive AWS profile selection"""
        profiles = self.list_profiles()
        
        if not profiles:
            logger.error("No AWS profiles found")
            print(f"{Fore.RED}No AWS credentials found. Please configure AWS credentials first:{Style.RESET_ALL}")
            print("  1. AWS CLI: aws configure")
            print("  2. Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            print("  3. IAM instance profile")
            return None
        
        if len(profiles) == 1:
            profile = profiles[0]
            if self.test_credentials(profile):
                logger.info(f"Using AWS profile: {profile}")
                return profile
            else:
                logger.error(f"AWS profile '{profile}' has invalid credentials")
                return None
        
        print(f"\n{Fore.CYAN}=== AWS Profile Selection ==={Style.RESET_ALL}")
        for i, profile in enumerate(profiles, 1):
            region = self.get_profile_region(profile)
            print(f"{Fore.YELLOW}{i:2d}.{Style.RESET_ALL} {profile} {Fore.DIM}({region}){Style.RESET_ALL}")
        
        while True:
            try:
                choice = get_input("Select AWS profile", default="1")
                index = int(choice) - 1
                
                if 0 <= index < len(profiles):
                    profile = profiles[index]
                    if self.test_credentials(profile):
                        logger.info(f"Selected AWS profile: {profile}")
                        return profile
                    else:
                        logger.error(f"Profile '{profile}' has invalid credentials")
                        if not confirm("Try another profile?", default=True):
                            return None
                else:
                    print(f"{Fore.RED}Invalid selection. Choose 1-{len(profiles)}{Style.RESET_ALL}")
            except (ValueError, KeyboardInterrupt):
                logger.info("Profile selection cancelled")
                return None
    
    def get_profile_region(self, profile: str) -> str:
        """Get region for AWS profile"""
        try:
            if profile == 'default':
                session = boto3.Session()
            else:
                session = boto3.Session(profile_name=profile)
            return session.region_name or 'us-east-1'
        except Exception:
            return 'us-east-1'
    
    def test_credentials(self, profile: str) -> bool:
        """Test AWS credentials for profile"""
        try:
            if profile == 'default':
                session = boto3.Session()
            else:
                session = boto3.Session(profile_name=profile)
            
            # Test credentials with simple STS call
            sts = session.client('sts')
            sts.get_caller_identity()
            
            self.session = session
            self.current_profile = profile
            return True
            
        except Exception as e:
            logger.error(f"AWS credentials test failed: {e}")
            return False


class S3SyncTool:
    """S3 synchronization tool with OpsKit integration"""
    
    def __init__(self):
        # Tool metadata
        self.tool_name = "S3 Sync Tool"
        self.description = "Intelligent bidirectional S3 synchronization"
        
        # Load configuration from environment variables
        self.default_region = get_env_var('AWS_DEFAULT_REGION', 'us-east-1', str)
        self.max_retries = get_env_var('MAX_RETRIES', 3, int)
        self.timeout = get_env_var('TIMEOUT', 300, int)
        self.parallel_uploads = get_env_var('PARALLEL_UPLOADS', 4, int)
        self.multipart_threshold = get_env_var('MULTIPART_THRESHOLD', 64*1024*1024, int)  # 64MB
        self.multipart_chunksize = get_env_var('MULTIPART_CHUNKSIZE', 8*1024*1024, int)   # 8MB
        self.delete_removed = get_env_var('DELETE_REMOVED', False, bool)
        self.verify_checksums = get_env_var('VERIFY_CHECKSUMS', True, bool)
        self.default_storage_class = get_env_var('DEFAULT_STORAGE_CLASS', 'STANDARD', str)
        self.encryption_enabled = get_env_var('ENCRYPTION_ENABLED', False, bool)
        self.debug = get_env_var('DEBUG', False, bool)
        self.dry_run = get_env_var('DRY_RUN', False, bool)
        
        # Initialize components
        self.connection_manager = S3ConnectionManager()
        self.exclusion_manager = ExclusionManager()
        self.stats = SyncStats()
        self.s3_client = None
        self.temp_dir = get_env_var('OPSKIT_TOOL_TEMP_DIR')
        
        logger.info(f"🚀 Starting {self.tool_name}")
        if self.debug:
            logger.info(f"Debug mode enabled - region: {self.default_region}, parallel: {self.parallel_uploads}")
    
    def setup_aws_session(self) -> bool:
        """Setup AWS session and S3 client using connection manager"""
        connection_info = self.connection_manager.get_connection_info()
        if not connection_info:
            return False
        
        try:
            # Test the connection
            if not self.connection_manager.test_connection(connection_info):
                return False
            
            # Get the session from connection manager
            session = self.connection_manager.session
            if not session:
                logger.error("No AWS session available")
                return False
            
            # Configure transfer settings
            transfer_config = TransferConfig(
                multipart_threshold=self.multipart_threshold,
                multipart_chunksize=self.multipart_chunksize,
                max_concurrency=self.parallel_uploads,
                use_threads=True
            )
            
            # Create S3 client with proper configuration
            s3_config = {'region_name': connection_info.region}
            if connection_info.endpoint_url:
                s3_config['endpoint_url'] = connection_info.endpoint_url
            
            self.s3_client = session.client('s3', **s3_config)
            self.transfer_config = transfer_config
            self.current_connection = connection_info
            
            logger.info(f"✅ AWS session configured: {connection_info.display}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup AWS session: {e}")
            return False
    
    def list_s3_objects(self, bucket: str, prefix: str = '') -> List[FileInfo]:
        """List S3 objects with metadata"""
        objects = []
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=bucket,
                Prefix=prefix
            )
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Skip directories (objects ending with /)
                        if obj['Key'].endswith('/'):
                            continue
                        
                        # Check exclusion patterns
                        relative_path = obj['Key'][len(prefix):].lstrip('/')
                        if self.exclusion_manager.should_exclude(relative_path):
                            continue
                        
                        objects.append(FileInfo(
                            path=obj['Key'],
                            size=obj['Size'],
                            modified=obj['LastModified'].replace(tzinfo=timezone.utc),
                            etag=obj['ETag'].strip('"'),
                            is_local=False,
                            storage_class=obj.get('StorageClass', 'STANDARD')
                        ))
            
            logger.info(f"Found {len(objects)} objects in s3://{bucket}/{prefix}")
            return objects
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                logger.error(f"Bucket '{bucket}' does not exist")
            elif error_code == 'AccessDenied':
                logger.error(f"Access denied to bucket '{bucket}'")
            else:
                logger.error(f"Failed to list S3 objects: {e}")
            return []
    
    def list_local_files(self, directory: str) -> List[FileInfo]:
        """List local files with metadata"""
        files = []
        base_path = Path(directory)
        
        if not base_path.exists():
            logger.error(f"Local directory does not exist: {directory}")
            return []
        
        try:
            for file_path in base_path.rglob('*'):
                if file_path.is_file():
                    # Get relative path from base directory
                    relative_path = str(file_path.relative_to(base_path))
                    
                    # Check exclusion patterns
                    if self.exclusion_manager.should_exclude(relative_path):
                        continue
                    
                    stat_info = file_path.stat()
                    
                    files.append(FileInfo(
                        path=relative_path,
                        size=stat_info.st_size,
                        modified=datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc),
                        etag=None,  # Will compute if needed
                        is_local=True
                    ))
            
            logger.info(f"Found {len(files)} files in {directory}")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list local files: {e}")
            return []
    
    def compute_etag(self, file_path: str) -> str:
        """Compute S3-compatible ETag for local file"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute ETag for {file_path}: {e}")
            return ""
    
    def compare_files(self, local_file: FileInfo, s3_file: FileInfo, local_base: str) -> str:
        """
        Compare local and S3 files
        Returns: 'upload', 'download', 'skip', or 'conflict'
        """
        # If sizes are different, newer wins
        if local_file.size != s3_file.size:
            if local_file.modified > s3_file.modified:
                return 'upload'
            else:
                return 'download'
        
        # If verify_checksums is enabled, compare ETags
        if self.verify_checksums:
            if not local_file.etag:
                local_path = Path(local_base) / local_file.path
                local_file.etag = self.compute_etag(str(local_path))
            
            if local_file.etag and s3_file.etag:
                if local_file.etag == s3_file.etag:
                    return 'skip'  # Files are identical
        
        # Compare modification times
        time_diff = abs((local_file.modified - s3_file.modified).total_seconds())
        
        # If timestamps are very close (within 2 seconds), consider identical
        if time_diff <= 2:
            return 'skip'
        
        # If one is significantly newer, prefer it
        if time_diff > 60:  # More than 1 minute difference
            if local_file.modified > s3_file.modified:
                return 'upload'
            else:
                return 'download'
        
        # Otherwise, it's a conflict
        return 'conflict'
    
    def upload_file(self, local_path: str, bucket: str, s3_key: str, 
                   show_progress: bool = True) -> bool:
        """Upload file to S3 with progress tracking"""
        try:
            file_size = Path(local_path).stat().st_size
            
            # Prepare extra args
            extra_args = {
                'StorageClass': self.default_storage_class,
                'Metadata': {
                    'opskit-sync': 'true',
                    'original-mtime': str(int(Path(local_path).stat().st_mtime))
                }
            }
            
            # Add encryption if enabled
            if self.encryption_enabled:
                extra_args['ServerSideEncryption'] = 'AES256'
            
            # Add content type
            content_type, _ = mimetypes.guess_type(local_path)
            if content_type:
                extra_args['ContentType'] = content_type
            
            # Create progress callback
            if show_progress and TQDM_AVAILABLE and file_size > 1024*1024:  # > 1MB
                pbar = tqdm.tqdm(
                    total=file_size, 
                    unit='B', 
                    unit_scale=True,
                    desc=f"Uploading {Path(local_path).name}"
                )
                
                def progress_callback(bytes_transferred):
                    pbar.update(bytes_transferred)
                
                callback = progress_callback
            else:
                callback = None
                pbar = None
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would upload: {local_path} → s3://{bucket}/{s3_key}")
                if pbar:
                    pbar.close()
                return True
            
            # Perform upload
            self.s3_client.upload_file(
                local_path, 
                bucket, 
                s3_key,
                ExtraArgs=extra_args,
                Config=self.transfer_config,
                Callback=callback
            )
            
            if pbar:
                pbar.close()
            
            logger.info(f"✅ Uploaded: {local_path} → s3://{bucket}/{s3_key}")
            self.stats.uploaded += 1
            self.stats.total_size += file_size
            return True
            
        except Exception as e:
            logger.error(f"❌ Upload failed: {local_path} → s3://{bucket}/{s3_key}: {e}")
            self.stats.errors += 1
            return False
    
    def download_file(self, bucket: str, s3_key: str, local_path: str,
                     show_progress: bool = True) -> bool:
        """Download file from S3 with progress tracking"""
        try:
            # Get object info
            response = self.s3_client.head_object(Bucket=bucket, Key=s3_key)
            file_size = response['ContentLength']
            
            # Create local directory if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Create progress callback
            if show_progress and TQDM_AVAILABLE and file_size > 1024*1024:  # > 1MB
                pbar = tqdm.tqdm(
                    total=file_size, 
                    unit='B', 
                    unit_scale=True,
                    desc=f"Downloading {Path(local_path).name}"
                )
                
                def progress_callback(bytes_transferred):
                    pbar.update(bytes_transferred)
                
                callback = progress_callback
            else:
                callback = None
                pbar = None
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would download: s3://{bucket}/{s3_key} → {local_path}")
                if pbar:
                    pbar.close()
                return True
            
            # Perform download
            self.s3_client.download_file(
                bucket, 
                s3_key, 
                local_path,
                Config=self.transfer_config,
                Callback=callback
            )
            
            if pbar:
                pbar.close()
            
            # Restore timestamp from metadata if available
            try:
                metadata = response.get('Metadata', {})
                if 'original-mtime' in metadata:
                    mtime = int(metadata['original-mtime'])
                    os.utime(local_path, (mtime, mtime))
            except Exception as e:
                logger.warning(f"Failed to restore timestamp for {local_path}: {e}")
            
            logger.info(f"✅ Downloaded: s3://{bucket}/{s3_key} → {local_path}")
            self.stats.downloaded += 1
            self.stats.total_size += file_size
            return True
            
        except Exception as e:
            logger.error(f"❌ Download failed: s3://{bucket}/{s3_key} → {local_path}: {e}")
            self.stats.errors += 1
            return False
    
    def resolve_conflicts(self, conflicts: List[Tuple[FileInfo, FileInfo, str]]) -> Dict[str, str]:
        """Interactive conflict resolution"""
        resolutions = {}
        
        if not conflicts:
            return resolutions
        
        print(f"\n{Fore.YELLOW}=== Conflict Resolution ==={Style.RESET_ALL}")
        print(f"Found {len(conflicts)} files with conflicts")
        
        for i, (local_file, s3_file, action) in enumerate(conflicts, 1):
            print(f"\n{Fore.CYAN}Conflict {i}/{len(conflicts)}: {local_file.path}{Style.RESET_ALL}")
            print(f"  Local:  {local_file.modified.strftime('%Y-%m-%d %H:%M:%S')} ({self.format_size(local_file.size)})")
            print(f"  S3:     {s3_file.modified.strftime('%Y-%m-%d %H:%M:%S')} ({self.format_size(s3_file.size)})")
            
            while True:
                choice = get_input(
                    "Resolution: (l)ocal, (s)3, (r)ename local, (sk)ip",
                    validator=lambda x: x.lower() in ['l', 'local', 's', 's3', 'r', 'rename', 'sk', 'skip'],
                    error_message="Choose: l, s, r, or sk"
                ).lower()
                
                if choice in ['l', 'local']:
                    resolutions[local_file.path] = 'upload'
                    print(f"  {Fore.GREEN}→ Using local version{Style.RESET_ALL}")
                    break
                elif choice in ['s', 's3']:
                    resolutions[local_file.path] = 'download'
                    print(f"  {Fore.GREEN}→ Using S3 version{Style.RESET_ALL}")
                    break
                elif choice in ['r', 'rename']:
                    resolutions[local_file.path] = 'rename'
                    print(f"  {Fore.GREEN}→ Renaming local file{Style.RESET_ALL}")
                    break
                elif choice in ['sk', 'skip']:
                    resolutions[local_file.path] = 'skip'
                    print(f"  {Fore.YELLOW}→ Skipping file{Style.RESET_ALL}")
                    break
        
        return resolutions
    
    def sync_directory(self, local_dir: str, bucket: str, prefix: str = '', 
                      direction: str = 'upload') -> bool:
        """Synchronize directory with S3"""
        logger.info(f"Starting {direction} sync: {local_dir} ↔ s3://{bucket}/{prefix}")
        
        self.stats = SyncStats()
        self.stats.start_time = datetime.now(timezone.utc)
        
        try:
            # Get file lists
            local_files = {f.path: f for f in self.list_local_files(local_dir)}
            s3_objects = {f.path[len(prefix):].lstrip('/'): f for f in self.list_s3_objects(bucket, prefix)}
            
            # Plan operations
            operations = {'upload': [], 'download': [], 'delete': [], 'conflicts': []}
            
            if direction in ['upload', 'bidirectional']:
                # Check local files
                for rel_path, local_file in local_files.items():
                    if rel_path in s3_objects:
                        # File exists in both locations
                        s3_file = s3_objects[rel_path]
                        comparison = self.compare_files(local_file, s3_file, local_dir)
                        
                        if comparison == 'upload':
                            operations['upload'].append((local_file, rel_path))
                        elif comparison == 'conflict' and direction == 'bidirectional':
                            operations['conflicts'].append((local_file, s3_file, 'conflict'))
                    else:
                        # Local file doesn't exist in S3
                        operations['upload'].append((local_file, rel_path))
                
                # Check for S3 objects to delete locally
                if self.delete_removed:
                    for rel_path in s3_objects:
                        if rel_path not in local_files:
                            operations['delete'].append(('s3', rel_path))
            
            if direction in ['download', 'bidirectional']:
                # Check S3 objects
                for rel_path, s3_file in s3_objects.items():
                    if rel_path in local_files:
                        # Already handled in upload section for bidirectional
                        if direction == 'download':
                            local_file = local_files[rel_path]
                            comparison = self.compare_files(local_file, s3_file, local_dir)
                            
                            if comparison == 'download':
                                operations['download'].append((s3_file, rel_path))
                            elif comparison == 'conflict':
                                operations['conflicts'].append((local_files[rel_path], s3_file, 'conflict'))
                    else:
                        # S3 object doesn't exist locally
                        operations['download'].append((s3_file, rel_path))
                
                # Check for local files to delete
                if self.delete_removed:
                    for rel_path in local_files:
                        if rel_path not in s3_objects:
                            operations['delete'].append(('local', rel_path))
            
            # Resolve conflicts
            conflict_resolutions = {}
            if operations['conflicts']:
                conflict_resolutions = self.resolve_conflicts(operations['conflicts'])
                
                # Apply conflict resolutions
                for file_path, resolution in conflict_resolutions.items():
                    if resolution == 'upload':
                        operations['upload'].append((local_files[file_path], file_path))
                    elif resolution == 'download':
                        operations['download'].append((s3_objects[file_path], file_path))
                    elif resolution == 'rename':
                        # Rename local file and download S3 version
                        local_path = Path(local_dir) / file_path
                        backup_path = local_path.with_suffix(local_path.suffix + '.backup')
                        if not self.dry_run:
                            local_path.rename(backup_path)
                        operations['download'].append((s3_objects[file_path], file_path))
            
            # Show operation summary
            self.show_sync_summary(operations, bucket, prefix, local_dir)
            
            if not self.dry_run and not confirm("Execute these operations?", default=True):
                logger.info("Sync cancelled by user")
                return False
            
            # Execute operations
            success = True
            
            # Execute uploads
            if operations['upload']:
                logger.info(f"Uploading {len(operations['upload'])} files...")
                for local_file, rel_path in operations['upload']:
                    local_path = Path(local_dir) / rel_path
                    s3_key = prefix + rel_path if prefix else rel_path
                    if not self.upload_file(str(local_path), bucket, s3_key):
                        success = False
            
            # Execute downloads
            if operations['download']:
                logger.info(f"Downloading {len(operations['download'])} files...")
                for s3_file, rel_path in operations['download']:
                    local_path = Path(local_dir) / rel_path
                    s3_key = prefix + rel_path if prefix else rel_path
                    if not self.download_file(bucket, s3_key, str(local_path)):
                        success = False
            
            # Execute deletions
            if operations['delete'] and self.delete_removed:
                logger.info(f"Deleting {len(operations['delete'])} items...")
                for location, rel_path in operations['delete']:
                    if location == 'local':
                        local_path = Path(local_dir) / rel_path
                        if not self.dry_run:
                            try:
                                local_path.unlink()
                                logger.info(f"🗑️  Deleted local: {local_path}")
                                self.stats.deleted += 1
                            except Exception as e:
                                logger.error(f"❌ Failed to delete local file {local_path}: {e}")
                                self.stats.errors += 1
                                success = False
                        else:
                            logger.info(f"[DRY RUN] Would delete local: {local_path}")
                    else:  # S3 deletion
                        s3_key = prefix + rel_path if prefix else rel_path
                        if not self.dry_run:
                            try:
                                self.s3_client.delete_object(Bucket=bucket, Key=s3_key)
                                logger.info(f"🗑️  Deleted S3: s3://{bucket}/{s3_key}")
                                self.stats.deleted += 1
                            except Exception as e:
                                logger.error(f"❌ Failed to delete S3 object s3://{bucket}/{s3_key}: {e}")
                                self.stats.errors += 1
                                success = False
                        else:
                            logger.info(f"[DRY RUN] Would delete S3: s3://{bucket}/{s3_key}")
            
            self.stats.end_time = datetime.now(timezone.utc)
            self.show_sync_results()
            
            return success
            
        except Exception as e:
            logger.error(f"Sync operation failed: {e}")
            return False
    
    def show_sync_summary(self, operations: Dict, bucket: str, prefix: str, local_dir: str):
        """Show sync operation summary"""
        print(f"\n{Fore.CYAN}=== Sync Summary ==={Style.RESET_ALL}")
        print(f"Local:  {local_dir}")
        print(f"S3:     s3://{bucket}/{prefix}")
        
        upload_count = len(operations['upload'])
        download_count = len(operations['download'])
        delete_count = len(operations['delete'])
        conflict_count = len(operations['conflicts'])
        
        if upload_count > 0:
            print(f"\n{Fore.GREEN}Will upload {upload_count} files:{Style.RESET_ALL}")
            for local_file, rel_path in operations['upload'][:5]:  # Show first 5
                size_str = self.format_size(local_file.size)
                print(f"  + {rel_path} ({size_str})")
            if upload_count > 5:
                print(f"  ... and {upload_count - 5} more files")
        
        if download_count > 0:
            print(f"\n{Fore.BLUE}Will download {download_count} files:{Style.RESET_ALL}")
            for s3_file, rel_path in operations['download'][:5]:  # Show first 5
                size_str = self.format_size(s3_file.size)
                print(f"  - {rel_path} ({size_str})")
            if download_count > 5:
                print(f"  ... and {download_count - 5} more files")
        
        if delete_count > 0:
            print(f"\n{Fore.RED}Will delete {delete_count} items:{Style.RESET_ALL}")
            for location, rel_path in operations['delete'][:5]:  # Show first 5
                prefix_char = "×" if location == "local" else "⊗"
                print(f"  {prefix_char} {rel_path}")
            if delete_count > 5:
                print(f"  ... and {delete_count - 5} more items")
        
        if conflict_count > 0:
            print(f"\n{Fore.YELLOW}Conflicts to resolve: {conflict_count}{Style.RESET_ALL}")
        
        total_ops = upload_count + download_count + delete_count
        if total_ops == 0:
            print(f"\n{Fore.GREEN}✅ Everything is already in sync!{Style.RESET_ALL}")
    
    def show_sync_results(self):
        """Show sync operation results"""
        duration = self.stats.duration()
        
        print(f"\n{Fore.CYAN}=== Sync Results ==={Style.RESET_ALL}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Total size: {self.format_size(self.stats.total_size)}")
        
        if self.stats.uploaded > 0:
            print(f"✅ Uploaded: {self.stats.uploaded} files")
        
        if self.stats.downloaded > 0:
            print(f"✅ Downloaded: {self.stats.downloaded} files")
        
        if self.stats.deleted > 0:
            print(f"🗑️  Deleted: {self.stats.deleted} items")
        
        if self.stats.skipped > 0:
            print(f"⏭️  Skipped: {self.stats.skipped} files")
        
        if self.stats.errors > 0:
            print(f"❌ Errors: {self.stats.errors}")
        
        # Calculate transfer rate
        if duration > 0 and self.stats.total_size > 0:
            rate = self.stats.total_size / duration
            print(f"Transfer rate: {self.format_size(int(rate))}/s")
    
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def interactive_setup(self) -> Optional[Dict[str, str]]:
        """Interactive sync setup"""
        print(f"\n{Fore.BLUE}{Style.BRIGHT}=== {self.tool_name} ==={Style.RESET_ALL}")
        print(f"{Style.DIM}{self.description}{Style.RESET_ALL}\n")
        
        # Get sync direction
        directions = {
            '1': ('upload', 'Upload (Local → S3)'),
            '2': ('download', 'Download (S3 → Local)'),
            '3': ('bidirectional', 'Bidirectional sync')
        }
        
        print(f"{Fore.CYAN}=== Sync Direction ==={Style.RESET_ALL}")
        for key, (_, desc) in directions.items():
            print(f"{key}. {desc}")
        
        direction_choice = get_input(
            "Select sync direction",
            default="1",
            validator=lambda x: x in directions,
            error_message="Choose 1, 2, or 3"
        )
        direction = directions[direction_choice][0]
        
        # Get local directory
        local_dir = get_input(
            "Local directory path",
            default=".",
            validator=lambda x: Path(x).exists() or confirm(f"Create directory {x}?", default=True),
            error_message="Directory must exist or you must confirm creation"
        )
        
        # Create directory if it doesn't exist
        local_path = Path(local_dir).resolve()
        if not local_path.exists():
            local_path.mkdir(parents=True, exist_ok=True)
            print(f"{Fore.GREEN}Created directory: {local_path}{Style.RESET_ALL}")
        
        # Get S3 bucket and prefix
        bucket = get_input(
            "S3 bucket name",
            validator=lambda x: len(x) > 0 and x.replace('-', '').replace('.', '').isalnum(),
            error_message="Bucket name must be valid S3 bucket name"
        )
        
        prefix = get_input(
            "S3 prefix (optional)",
            default="",
        ).strip('/')
        
        if prefix:
            prefix = prefix + '/'
        
        # Configure options
        print(f"\n{Fore.CYAN}=== Sync Options ==={Style.RESET_ALL}")
        
        delete_removed = confirm("Delete files not present in source?", default=self.delete_removed)
        dry_run = confirm("Dry run mode (preview only)?", default=self.dry_run)
        
        # Set up exclusion patterns
        exclusions = get_input(
            "Additional exclusion patterns (comma-separated)",
            default=""
        )
        
        if exclusions:
            patterns = [p.strip() for p in exclusions.split(',') if p.strip()]
            for pattern in patterns:
                self.exclusion_manager.add_pattern(pattern)
        
        return {
            'direction': direction,
            'local_dir': str(local_path),
            'bucket': bucket,
            'prefix': prefix,
            'delete_removed': delete_removed,
            'dry_run': dry_run
        }
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        try:
            # Test AWS credentials
            if not self.setup_aws_session():
                return False
            
            logger.info("✅ All dependencies available")
            return True
            
        except Exception as e:
            logger.error(f"❌ Dependency check failed: {e}")
            return False
    
    def run(self):
        """Main tool execution"""
        try:
            # Check dependencies
            if not self.check_dependencies():
                sys.exit(1)
            
            # Check for command arguments
            if len(sys.argv) > 1:
                command = sys.argv[1]
                if command == 'help':
                    self.show_help()
                    return
                else:
                    print(f"{Fore.RED}Unknown command: {command}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Available commands: help{Style.RESET_ALL}")
                    return
            
            # Interactive setup
            config = self.interactive_setup()
            if not config:
                logger.info("Setup cancelled")
                return
            
            # Apply configuration
            self.delete_removed = config['delete_removed']
            self.dry_run = config['dry_run']
            
            # Execute sync
            success = self.sync_directory(
                config['local_dir'],
                config['bucket'],
                config['prefix'],
                config['direction']
            )
            
            if success:
                logger.info("🎉 Sync completed successfully")
            else:
                logger.error("❌ Sync completed with errors")
                sys.exit(1)
                
        except KeyboardInterrupt:
            logger.info("❌ Operation cancelled by user")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            sys.exit(1)
    
    def show_help(self):
        """Display help information"""
        print(f"\n{Fore.CYAN}=== S3 Sync Tool Help ==={Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}Commands:{Style.RESET_ALL}")
        print(f"  help                                 # Show this help")
        
        print(f"\n{Fore.YELLOW}Sync Directions:{Style.RESET_ALL}")
        print(f"  • Upload: Sync local files to S3")
        print(f"  • Download: Sync S3 objects to local")
        print(f"  • Bidirectional: Two-way sync with conflict resolution")
        
        print(f"\n{Fore.YELLOW}AWS Credentials:{Style.RESET_ALL}")
        print(f"  • Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        print(f"  • AWS credentials file: ~/.aws/credentials")
        print(f"  • IAM instance profile (for EC2)")
        print(f"  • AWS CLI: aws configure")
        
        print(f"\n{Fore.YELLOW}Features:{Style.RESET_ALL}")
        print(f"  • Intelligent file comparison (size, timestamp, checksum)")
        print(f"  • Multipart uploads for large files")
        print(f"  • Progress tracking and resume capability")
        print(f"  • Exclusion patterns (.gitignore style)")
        print(f"  • Dry run mode for preview")
        print(f"  • Interactive conflict resolution")
        
        print(f"\n{Fore.YELLOW}Environment Variables:{Style.RESET_ALL}")
        print(f"  AWS_DEFAULT_REGION=us-east-1        # Default AWS region")
        print(f"  PARALLEL_UPLOADS=4                  # Concurrent uploads")
        print(f"  DELETE_REMOVED=false                # Delete files not in source")
        print(f"  VERIFY_CHECKSUMS=true               # Enable ETag verification")
        print(f"  DEFAULT_STORAGE_CLASS=STANDARD      # S3 storage class")
        print(f"  ENCRYPTION_ENABLED=false            # Enable server-side encryption")
        print(f"  DRY_RUN=false                       # Enable dry run mode by default")
        print(f"  DEBUG=false                         # Enable debug logging")


@click.command()
@click.option('--help-tool', is_flag=True, help='Show tool help')
def main(help_tool: bool):
    """S3 synchronization tool with intelligent bidirectional sync"""
    if help_tool:
        sys.argv.append('help')
    
    tool = S3SyncTool()
    tool.run()


if __name__ == '__main__':
    # Let Click handle command line arguments properly
    main()
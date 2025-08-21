#!/usr/bin/env python3
"""
S3 Sync Tool - OpsKit Version
Synchronize S3 buckets across different AWS environments with advanced features
"""

import os
import sys
import json
import base64
import getpass
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from pathlib import Path

# Import OpsKit common libraries
sys.path.insert(0, os.path.join(os.environ['OPSKIT_BASE_PATH'], 'common/python'))

from logger import get_logger
from storage import get_storage  
from utils import run_command, timestamp, get_env_var
from interactive import get_interactive

# Third-party imports
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound, ParamValidationError
    from botocore.config import Config
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please ensure all dependencies are installed: pip install boto3")
    sys.exit(1)

# Initialize OpsKit components
logger = get_logger(__name__)
interactive = get_interactive(__name__, 's3-sync')
storage = get_storage('s3-sync')


class S3SyncTool:
    """S3 bucket synchronization tool with OpsKit integration"""
    
    def __init__(self):
        # Tool metadata
        self.tool_name = "S3 Sync Tool"
        self.description = "Synchronize S3 buckets across different AWS environments"
        
        # Load configuration from environment variables
        self.max_workers = get_env_var('MAX_WORKERS', 10, int)
        self.max_retries = get_env_var('MAX_RETRIES', 5, int)
        self.retry_delay = get_env_var('RETRY_DELAY', 2, int)
        self.cache_connections = get_env_var('CACHE_CONNECTIONS', True, bool)
        self.confirm_destructive = get_env_var('CONFIRM_DESTRUCTIVE', True, bool)
        
        # Get tool temp directory for storing configurations
        self.temp_dir = get_env_var('OPSKIT_TOOL_TEMP_DIR')
        if self.temp_dir:
            self.connections_file = os.path.join(self.temp_dir, 'connections.json')
        else:
            # Fallback to current directory if temp dir not available
            self.connections_file = 'connections.json'
        
        interactive.info(f"🚀 Starting {self.tool_name}")
        interactive.debug(f"Configuration - max_workers: {self.max_workers}, max_retries: {self.max_retries}")
        
        # Load cached connections if enabled
        self.connections = self._load_connections() if self.cache_connections else {}
    
    def _load_connections(self) -> Dict:
        """Load saved connection configurations"""
        if os.path.exists(self.connections_file):
            try:
                with open(self.connections_file, 'r') as f:
                    connections = json.load(f)
                    interactive.cache_operation("loaded", f"{len(connections)} connections")
                    return connections
            except (json.JSONDecodeError, IOError) as e:
                interactive.warning_msg(f"Error loading connections: {e}")
                return {}
        return {}
    
    def _save_connections(self):
        """Save connection configurations to file"""
        if not self.cache_connections:
            return
            
        try:
            # Ensure temp directory exists
            if self.temp_dir:
                os.makedirs(self.temp_dir, exist_ok=True)
                
            with open(self.connections_file, 'w') as f:
                json.dump(self.connections, f, indent=2)
            interactive.cache_operation("saved", f"{len(self.connections)} connections")
        except IOError as e:
            interactive.failure(f"Failed to save connections: {e}")
    
    def _validate_s3_endpoint(self, endpoint: str) -> str:
        """Validate and normalize S3 endpoint URL"""
        if not endpoint:
            return ''
        
        try:
            parsed = urlparse(endpoint)
            
            if parsed.scheme not in ['http', 'https']:
                interactive.failure(f"Invalid endpoint: {endpoint}. Must start with http:// or https://")
                return ''
            
            if not parsed.netloc:
                interactive.failure(f"Invalid endpoint: {endpoint}. Must include a valid host.")
                return ''
            
            return endpoint.rstrip('/')
        
        except Exception as e:
            interactive.failure(f"Error parsing endpoint: {e}")
            return ''
    
    def _input_connection_details(self, connection_type: str) -> Dict:
        """Interactively input AWS connection details"""
        interactive.subsection(f"{connection_type.capitalize()} Connection Configuration")
        
        # Check for saved connections
        saved_connections = list(self.connections.keys())
        if saved_connections:
            interactive.display_list("Saved Connections", saved_connections)
            
            options = saved_connections + ["Create New Connection"]
            selected_index = interactive.select_from_list(
                options, 
                f"Select {connection_type} connection"
            )
            
            if selected_index is not None and selected_index < len(saved_connections):
                selected_conn = saved_connections[selected_index]
                interactive.info(f"Using saved connection: {selected_conn}")
                return self.connections[selected_conn]
        
        # Create new connection
        while True:
            conn_name = interactive.get_input(
                "Enter a name for this connection",
                validator=lambda x: len(x.strip()) > 0,
                error_message="Connection name cannot be empty"
            )
            
            if not conn_name:
                continue
            
            # AWS Access Key input  
            aws_access_key = interactive.get_input(
                "AWS Access Key ID (leave blank to use default profile)",
                required=False
            )
            
            if aws_access_key:
                # AWS Secret Key input (hidden)
                aws_secret_key = interactive.get_input(
                    "AWS Secret Access Key",
                    password=True,
                    validator=lambda x: len(x.strip()) > 0,
                    error_message="Secret key cannot be empty"
                )
                
                # Optional region input
                aws_region = interactive.get_input(
                    "AWS Region",
                    default='us-east-1',
                    required=False
                ) or 'us-east-1'
                
                # Optional S3 endpoint input
                s3_endpoint = interactive.get_input(
                    "S3 Endpoint URL (leave blank for AWS)",
                    required=False
                )
                s3_endpoint = self._validate_s3_endpoint(s3_endpoint)
                
                # Test connection with a lightweight operation
                interactive.progress("Testing connection...")
                
                try:
                    session_kwargs = {
                        'aws_access_key_id': aws_access_key,
                        'aws_secret_access_key': aws_secret_key,
                        'region_name': aws_region
                    }
                    session = boto3.Session(**{k: v for k, v in session_kwargs.items() if v})
                    
                    client_kwargs = {
                        'service_name': 's3',
                        'config': Config(signature_version='s3v4')
                    }
                    
                    if s3_endpoint:
                        client_kwargs['endpoint_url'] = s3_endpoint
                    
                    s3_client = session.client(**client_kwargs)
                    
                    # Use a lightweight operation to test the connection
                    # Try STS first (AWS), fallback to S3 head_bucket test
                    connection_valid = False
                    
                    try:
                        # Try STS get_caller_identity (works for AWS)
                        sts_client = session.client('sts')
                        if s3_endpoint:
                            # Skip STS for non-AWS endpoints
                            raise ClientError({'Error': {'Code': 'NoSuchService'}}, 'GetCallerIdentity')
                        sts_client.get_caller_identity()
                        connection_valid = True
                        interactive.debug("Connection validated using STS")
                    except (ClientError, Exception):
                        # STS not available, try S3 head_bucket with non-existent bucket
                        try:
                            # This should fail with 403/404, indicating valid connection
                            s3_client.head_bucket(Bucket='opskit-connection-test-nonexistent-bucket-' + str(hash(aws_access_key))[-6:])
                        except ClientError as e:
                            error_code = e.response['Error']['Code']
                            # These error codes indicate the connection works but bucket doesn't exist/no permission
                            if error_code in ['403', '404', 'NoSuchBucket', 'Forbidden', 'AccessDenied']:
                                connection_valid = True
                                interactive.debug(f"Connection validated using head_bucket (got {error_code})")
                            else:
                                interactive.debug(f"head_bucket test failed with: {error_code}")
                                raise
                        except Exception as e:
                            interactive.debug(f"head_bucket test failed: {e}")
                            raise
                    
                    if not connection_valid:
                        raise ClientError({'Error': {'Code': 'ConnectionTestFailed'}}, 'TestConnection')
                    
                    # Connection successful
                    connection_details = {
                        'name': conn_name,
                        'aws_access_key': aws_access_key,
                        'aws_secret_key': base64.b64encode(aws_secret_key.encode()).decode(),
                        'aws_region': aws_region,
                        's3_endpoint': s3_endpoint
                    }
                    
                    if self.cache_connections:
                        self.connections[conn_name] = connection_details
                        self._save_connections()
                        interactive.success(f"Connection '{conn_name}' saved successfully")
                    else:
                        interactive.success(f"Connection '{conn_name}' validated successfully")
                    
                    return connection_details
                
                except (ClientError, NoCredentialsError) as e:
                    interactive.failure(f"Connection failed: {e}")
                    if not interactive.confirm("Try again?", default=True):
                        return None
            else:
                # Use default profile
                interactive.info("Using AWS default profile")
                return {
                    'name': conn_name,
                    'aws_access_key': '',
                    'aws_secret_key': '',
                    'aws_region': 'us-east-1',
                    's3_endpoint': ''
                }
    
    def _get_s3_client(self, connection_details: Optional[Dict] = None) -> boto3.client:
        """Create S3 client with optional credentials and endpoint"""
        try:
            session_kwargs = {}
            client_kwargs = {
                'service_name': 's3',
                'config': Config(signature_version='s3v4')
            }
            
            if connection_details:
                if connection_details.get('aws_access_key'):
                    session_kwargs.update({
                        'aws_access_key_id': connection_details['aws_access_key'],
                        'aws_secret_access_key': base64.b64decode(connection_details['aws_secret_key']).decode(),
                    })
                
                if connection_details.get('aws_region'):
                    session_kwargs['region_name'] = connection_details['aws_region']
                
                if connection_details.get('s3_endpoint'):
                    client_kwargs['endpoint_url'] = connection_details['s3_endpoint']
            
            session = boto3.Session(**{k: v for k, v in session_kwargs.items() if v})
            return session.client(**client_kwargs)
        
        except (ProfileNotFound, NoCredentialsError, ParamValidationError) as e:
            interactive.failure(f"AWS credentials error: {e}")
            raise
    
    def list_buckets(self, connection_details: Optional[Dict] = None) -> Tuple[List[str], bool]:
        """List available S3 buckets
        
        Returns:
            Tuple of (bucket_list, success_flag)
        """
        try:
            client = self._get_s3_client(connection_details)
            response = client.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            interactive.debug(f"Found {len(buckets)} buckets")
            return buckets, True
        except Exception as e:
            interactive.warning_msg(f"Cannot list buckets: {e}")
            interactive.info("This might be due to insufficient permissions for ListAllMyBuckets")
            return [], False
    
    def _interactive_bucket_selection(self, buckets: List[str], select_type: str = 'source', 
                                      list_success: bool = True) -> List[str]:
        """Interactive bucket selection with manual input fallback"""
        
        # If we have buckets from listing, offer selection
        if buckets and list_success:
            interactive.display_list(f"Available {select_type.capitalize()} Buckets", buckets)
            
            # Add manual input option
            options = buckets + ["Enter bucket names manually"]
            
            if select_type == 'source':
                # For source, allow multiple selection
                selected_indices = interactive.select_multiple_from_list(
                    options,
                    "Select source buckets (multiple allowed)"
                )
                
                if selected_indices:
                    # Check if manual input was selected
                    manual_index = len(buckets)  # Index of "Enter bucket names manually"
                    if manual_index in selected_indices:
                        return self._manual_bucket_input(select_type)
                    else:
                        return [buckets[i] for i in selected_indices if i < len(buckets)]
                else:
                    return []
            else:
                # For target, single selection
                selected_index = interactive.select_from_list(
                    options,
                    f"Select {select_type} bucket"
                )
                
                if selected_index is not None:
                    if selected_index == len(buckets):  # Manual input option
                        manual_buckets = self._manual_bucket_input(select_type)
                        return manual_buckets[:1]  # Only first bucket for target
                    else:
                        return [buckets[selected_index]]
                else:
                    return []
        
        # If no buckets from listing or listing failed, go to manual input
        else:
            if not list_success:
                interactive.info("Since bucket listing failed, you'll need to enter bucket names manually")
            return self._manual_bucket_input(select_type)
    
    def _manual_bucket_input(self, select_type: str = 'source') -> List[str]:
        """Get bucket names through manual input"""
        buckets = []
        
        if select_type == 'source':
            interactive.info("Enter source bucket names (one per line, empty line to finish):")
            while True:
                bucket = interactive.get_input(
                    f"Source bucket #{len(buckets) + 1} (or press Enter to finish)",
                    required=False
                )
                if not bucket.strip():
                    break
                
                bucket = bucket.strip()
                if bucket and bucket not in buckets:
                    buckets.append(bucket)
                    interactive.success(f"Added bucket: {bucket}")
                elif bucket in buckets:
                    interactive.warning_msg(f"Bucket {bucket} already added")
        else:
            # For target, only need one bucket
            bucket = interactive.get_input(
                "Enter target bucket name",
                validator=lambda x: len(x.strip()) > 0,
                error_message="Bucket name cannot be empty"
            )
            if bucket.strip():
                buckets.append(bucket.strip())
        
        if buckets:
            interactive.display_list(f"Selected {select_type} buckets", buckets)
        else:
            interactive.warning_msg(f"No {select_type} buckets specified")
        
        return buckets
    
    def _copy_object(self, source_client, target_client, src_bucket: str, 
                     target_bucket: str, key: str) -> Tuple[bool, str, Optional[str]]:
        """Copy a single object between buckets with retry support"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Download object from source
                response = source_client.get_object(Bucket=src_bucket, Key=key)
                body = response['Body'].read()
                
                # Upload to target bucket
                target_client.put_object(Bucket=target_bucket, Key=key, Body=body)
                
                if attempt > 0:
                    interactive.debug(f"Successfully copied {key} after {attempt} retries")
                
                return True, key, None
            
            except ClientError as obj_error:
                last_error = str(obj_error)
                if attempt < self.max_retries:
                    interactive.retry_attempt(attempt + 1, self.max_retries + 1, f"copy {key}")
                    import time
                    time.sleep(self.retry_delay ** attempt)  # Exponential backoff
                else:
                    interactive.failure(f"Failed to copy {key} after {self.max_retries + 1} attempts")
                    return False, key, last_error
            except Exception as e:
                last_error = str(e)
                interactive.failure(f"Unexpected error copying {key}: {last_error}")
                return False, key, last_error
    
    def sync_buckets(self, source_connection: Dict, target_connection: Dict, 
                     source_buckets: List[str]):
        """Synchronize buckets across S3 endpoints with parallel processing"""
        source_client = self._get_s3_client(source_connection)
        target_client = self._get_s3_client(target_connection)
        
        total_objects = 0
        successful_objects = 0
        failed_objects = 0
        
        interactive.section("S3 Bucket Synchronization")
        
        for src_bucket in source_buckets:
            target_bucket = src_bucket  # Use same bucket name
            
            try:
                interactive.step(
                    source_buckets.index(src_bucket) + 1, 
                    len(source_buckets),
                    f"Processing bucket: {src_bucket} → {target_bucket}"
                )
                
                # Check if target bucket exists
                try:
                    target_client.head_bucket(Bucket=target_bucket)
                    interactive.success(f"Target bucket {target_bucket} exists")
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        interactive.info(f"Creating target bucket: {target_bucket}")
                        target_client.create_bucket(
                            Bucket=target_bucket,
                            CreateBucketConfiguration={
                                'LocationConstraint': target_connection.get('aws_region', 'us-east-1')
                            }
                        )
                        interactive.success(f"Successfully created bucket: {target_bucket}")
                    else:
                        raise
                
                # List objects
                interactive.progress(f"Listing objects in {src_bucket}")
                
                paginator = source_client.get_paginator('list_objects_v2')
                object_keys = []
                for result in paginator.paginate(Bucket=src_bucket):
                    object_keys.extend([obj['Key'] for obj in result.get('Contents', [])])
                
                if not object_keys:
                    interactive.warning_msg(f"No objects found in {src_bucket}")
                    continue
                
                total_objects += len(object_keys)
                interactive.progress(f"Found {len(object_keys)} objects in {src_bucket}")
                
                # Parallel copying with progress
                interactive.info(f"Starting parallel sync with {self.max_workers} workers")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_key = {
                        executor.submit(
                            self._copy_object,
                            source_client,
                            target_client,
                            src_bucket,
                            target_bucket,
                            key
                        ): key for key in object_keys
                    }
                    
                    # Track progress
                    completed = 0
                    for future in concurrent.futures.as_completed(future_to_key):
                        key = future_to_key[future]
                        try:
                            success, _, error = future.result()
                            completed += 1
                            
                            if success:
                                successful_objects += 1
                            else:
                                failed_objects += 1
                                interactive.failure(f"Error copying {key}: {error}")
                            
                            # Progress update every 100 objects
                            if completed % 100 == 0:
                                interactive.progress(f"Progress: {completed}/{len(object_keys)} objects processed")
                        except Exception as exc:
                            failed_objects += 1
                            interactive.failure(f"Unexpected error copying {key}: {exc}")
                
                # Bucket summary
                bucket_success = successful_objects - (total_objects - len(object_keys))
                interactive.subsection(f"Bucket sync completed: {src_bucket}")
                interactive.display_info("Summary", {
                    "Objects processed": len(object_keys),
                    "Successful": bucket_success,
                    "Failed": failed_objects
                })
            
            except ClientError as e:
                interactive.failure(f"Error syncing {src_bucket}: {e}")
        
        # Final summary
        interactive.section("SYNC OPERATION COMPLETED")
        interactive.display_info("Final Results", {
            "Total objects": total_objects,
            "Successfully synced": successful_objects, 
            "Failed objects": failed_objects,
            "Success rate": f"{(successful_objects/total_objects*100):.1f}%" if total_objects > 0 else "0%"
        })
        
        return total_objects, successful_objects, failed_objects
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        try:
            import boto3
            interactive.debug("boto3 dependency check passed")
            return True
        except ImportError:
            interactive.failure("boto3 package not found. Please install: pip install boto3")
            return False
    
    def run(self):
        """Main tool execution"""
        try:
            if not self.check_dependencies():
                sys.exit(1)
            
            interactive.section("S3 Bucket Synchronization Tool")
            
            # Source connection and buckets
            source_connection = self._input_connection_details('source')
            if not source_connection:
                interactive.user_cancelled("source configuration")
                return
            
            source_buckets, list_success = self.list_buckets(source_connection)
            
            selected_source_buckets = self._interactive_bucket_selection(
                source_buckets, 'source', list_success
            )
            if not selected_source_buckets:
                interactive.user_cancelled("source bucket selection")
                return
            
            # Target connection  
            target_connection = self._input_connection_details('target')
            if not target_connection:
                interactive.user_cancelled("target configuration")
                return
            
            # Configuration summary
            interactive.section("S3 SYNC CONFIGURATION")
            interactive.display_info("SOURCE", {
                "Connection": source_connection.get('name', 'Default Profile'),
                "Endpoint": source_connection.get('s3_endpoint', 'AWS Default'),
                "Region": source_connection.get('aws_region', 'us-east-1'),
                "Buckets": ', '.join(selected_source_buckets)
            })
            
            interactive.display_info("TARGET", {
                "Connection": target_connection.get('name', 'Default Profile'), 
                "Endpoint": target_connection.get('s3_endpoint', 'AWS Default'),
                "Region": target_connection.get('aws_region', 'us-east-1')
            })
            
            # Final confirmation
            if self.confirm_destructive:
                if not interactive.confirm("Proceed with sync operation?", default=False):
                    interactive.user_cancelled("sync operation")
                    return
            
            # Perform sync
            total, successful, failed = self.sync_buckets(
                source_connection=source_connection,
                target_connection=target_connection,
                source_buckets=selected_source_buckets
            )
            
            interactive.success("Sync completed successfully")
            
        except KeyboardInterrupt:
            interactive.user_cancelled("sync operation")
        except Exception as e:
            interactive.failure(f"Unexpected error: {e}")
            sys.exit(1)


def main():
    """Entry point"""
    tool = S3SyncTool()
    tool.run()


if __name__ == '__main__':
    main()
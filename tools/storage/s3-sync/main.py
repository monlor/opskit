#!/usr/bin/env python3
"""
S3 Bucket Synchronization Tool - OpsKit Version
Provides safe, interactive bucket-to-bucket sync operations with support for both AWS S3 and custom S3-compatible endpoints.
"""

import os
import sys
import json
import base64
import getpass
import argparse
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound, ParamValidationError
from botocore.config import Config

# Get OpsKit environment variables
OPSKIT_TOOL_TEMP_DIR = os.environ.get('OPSKIT_TOOL_TEMP_DIR', os.path.join(os.getcwd(), '.s3-sync-temp'))
OPSKIT_BASE_PATH = os.environ.get('OPSKIT_BASE_PATH', os.path.expanduser('~/.opskit'))
OPSKIT_WORKING_DIR = os.environ.get('OPSKIT_WORKING_DIR', os.getcwd())
TOOL_NAME = os.environ.get('TOOL_NAME', 's3-sync')
TOOL_VERSION = os.environ.get('TOOL_VERSION', '1.0.0')


class S3SyncTool:
    def __init__(self, max_workers: int = 10):
        """
        Initialize S3SyncTool with OpsKit configuration management
        
        :param max_workers: Maximum number of concurrent workers for parallel processing
        """
        # Use OpsKit environment variables for directory configuration
        self.config_dir = OPSKIT_TOOL_TEMP_DIR
        self.connections_file = os.path.join(self.config_dir, 'connections.json')
        self.max_workers = max_workers
        
        # Create necessary directories
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Load or initialize connections
        self.connections = self._load_connections()
    
    def _load_connections(self) -> Dict:
        """
        Load saved connection configurations
        
        :return: Dictionary of saved connections
        """
        if os.path.exists(self.connections_file):
            try:
                with open(self.connections_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ Error loading connections: {e}")
                return {}
        return {}
    
    def _save_connections(self):
        """Save connection configurations to file"""
        try:
            with open(self.connections_file, 'w') as f:
                json.dump(self.connections, f, indent=2)
        except IOError as e:
            print(f"❌ Failed to save connections: {e}")
    
    def _validate_s3_endpoint(self, endpoint: str) -> str:
        """
        Validate and normalize S3 endpoint URL
        
        :param endpoint: Endpoint URL to validate
        :return: Normalized endpoint URL or empty string
        """
        if not endpoint:
            return ''
        
        try:
            # Validate URL structure
            parsed = urlparse(endpoint)
            
            # Ensure it's a valid http/https URL
            if parsed.scheme not in ['http', 'https']:
                print(f"Invalid endpoint: {endpoint}. Must start with http:// or https://")
                return ''
            
            # Ensure host is present
            if not parsed.netloc:
                print(f"Invalid endpoint: {endpoint}. Must include a valid host.")
                return ''
            
            # Normalize by removing trailing slashes
            return endpoint.rstrip('/')
        
        except Exception as e:
            print(f"Error parsing endpoint: {e}")
            return ''
    
    def _input_connection_details(self, connection_type: str) -> Dict:
        """
        Interactively input AWS connection details
        
        :param connection_type: 'source' or 'target'
        :return: Connection details dictionary
        """
        print(f"\n🔗 {connection_type.capitalize()} Connection Configuration")
        
        # Check if there are saved connections
        saved_connections = list(self.connections.keys())
        if saved_connections:
            print("\n💾 Saved Connections:")
            for i, conn in enumerate(saved_connections, 1):
                print(f"{i}. {conn}")
            print("0. Create New Connection")
            
            while True:
                try:
                    choice = input("Select a connection or 0 to create new: ").strip()
                    if choice == '0':
                        break
                    
                    selected_conn = saved_connections[int(choice) - 1]
                    return self.connections[selected_conn]
                except (ValueError, IndexError):
                    print("Invalid selection. Try again.")
        
        # Create new connection
        while True:
            conn_name = input("Enter a name for this connection: ").strip()
            if not conn_name:
                print("Connection name cannot be empty.")
                continue
            
            # AWS Access Key input
            while True:
                aws_access_key = input("AWS Access Key ID (leave blank to use default profile): ").strip()
                if not aws_access_key:
                    break
                
                # AWS Secret Key input (hidden)
                aws_secret_key = getpass.getpass("AWS Secret Access Key: ").strip()
                
                # Optional region input
                aws_region = input("AWS Region (optional, default: us-east-1): ").strip() or 'us-east-1'
                
                # Optional S3 endpoint input
                s3_endpoint = input("S3 Endpoint URL (optional, leave blank for AWS): ").strip()
                s3_endpoint = self._validate_s3_endpoint(s3_endpoint)
                
                # Validate connection
                try:
                    # Try to create S3 client with provided credentials
                    session_kwargs = {
                        'aws_access_key_id': aws_access_key, 
                        'aws_secret_access_key': aws_secret_key,
                        'region_name': aws_region
                    }
                    session = boto3.Session(**{k: v for k, v in session_kwargs.items() if v})
                    
                    # Create S3 client with configuration
                    client_kwargs = {
                        'service_name': 's3',
                        'config': Config(signature_version='s3v4')
                    }
                    
                    # Add endpoint if specified
                    if s3_endpoint:
                        client_kwargs['endpoint_url'] = s3_endpoint
                    
                    s3_client = session.client(**client_kwargs)
                    
                    # Test connection by listing buckets
                    s3_client.list_buckets()
                    
                    # Prepare connection details
                    connection_details = {
                        'name': conn_name,
                        'aws_access_key': aws_access_key,
                        'aws_secret_key': base64.b64encode(aws_secret_key.encode()).decode(),
                        'aws_region': aws_region,
                        's3_endpoint': s3_endpoint
                    }
                    
                    # Save connection
                    self.connections[conn_name] = connection_details
                    self._save_connections()
                    
                    print(f"✅ Connection '{conn_name}' saved successfully.")
                    return connection_details
                
                except (ClientError, NoCredentialsError) as e:
                    print(f"Connection failed: {e}")
                    retry = input("Try again? (y/n): ").strip().lower()
                    if retry != 'y':
                        break
    
    def _get_s3_client(self, connection_details: Optional[Dict] = None) -> boto3.client:
        """
        Create S3 client with optional credentials and endpoint
        
        :param connection_details: Optional connection details dictionary
        :return: boto3 S3 client
        """
        try:
            # Create session parameters
            session_kwargs = {}
            client_kwargs = {
                'service_name': 's3',
                'config': Config(signature_version='s3v4')
            }
            
            if connection_details:
                # Add credentials if provided
                if connection_details.get('aws_access_key'):
                    session_kwargs.update({
                        'aws_access_key_id': connection_details['aws_access_key'],
                        'aws_secret_access_key': base64.b64decode(connection_details['aws_secret_key']).decode(),
                    })
                
                # Add region if specified
                if connection_details.get('aws_region'):
                    session_kwargs['region_name'] = connection_details['aws_region']
                
                # Add endpoint if specified
                if connection_details.get('s3_endpoint'):
                    client_kwargs['endpoint_url'] = connection_details['s3_endpoint']
            
            # Create session
            session = boto3.Session(**{k: v for k, v in session_kwargs.items() if v})
            
            # Create S3 client
            return session.client(**client_kwargs)
        
        except (ProfileNotFound, NoCredentialsError, ParamValidationError) as e:
            print(f"❌ AWS credentials error: {e}")
            raise
    
    def list_buckets(self, connection_details: Optional[Dict] = None) -> List[str]:
        """
        List available S3 buckets, with fallback to manual input if list permission is unavailable
        
        :param connection_details: Optional connection details
        :return: List of bucket names
        """
        try:
            client = self._get_s3_client(connection_details)
            response = client.list_buckets()
            return [bucket['Name'] for bucket in response['Buckets']]
        except Exception as e:
            print(f"⚠️ Unable to list buckets automatically: {e}")
            print("🔐 This might be due to insufficient ListBucket permissions.")
            
            # Fallback to manual bucket input
            return self._manual_bucket_input()
    
    def _manual_bucket_input(self) -> List[str]:
        """
        Allow user to manually input bucket names when list_buckets fails
        
        :return: List of manually entered bucket names
        """
        print("\n📝 Manual Bucket Input")
        print("You can enter bucket names manually (one per line or comma-separated)")
        print("Examples:")
        print("  Single: my-bucket")
        print("  Multiple: bucket1,bucket2,bucket3")
        print("  Multiple lines: Enter each bucket name and press Enter, then empty line to finish")
        
        bucket_names = []
        
        while True:
            try:
                user_input = input("\nEnter bucket name(s) (or press Enter to finish): ").strip()
                
                if not user_input:
                    if bucket_names:
                        break
                    else:
                        print("⚠️ Please enter at least one bucket name.")
                        continue
                
                # Handle comma-separated input
                if ',' in user_input:
                    new_buckets = [name.strip() for name in user_input.split(',') if name.strip()]
                    bucket_names.extend(new_buckets)
                    print(f"✅ Added buckets: {', '.join(new_buckets)}")
                else:
                    # Single bucket name
                    bucket_names.append(user_input)
                    print(f"✅ Added bucket: {user_input}")
                
                print(f"📋 Current bucket list: {', '.join(bucket_names)}")
                
                # Ask if user wants to continue adding more buckets
                if input("Add more buckets? (y/n): ").strip().lower() != 'y':
                    break
                    
            except KeyboardInterrupt:
                print("\n❌ Manual bucket input cancelled.")
                return []
        
        if bucket_names:
            print(f"\n📦 Final bucket list: {', '.join(bucket_names)}")
            return bucket_names
        else:
            print("⚠️ No buckets entered.")
            return []
    
    def _validate_bucket_access(self, client, bucket_name: str) -> bool:
        """
        Validate if a bucket exists and is accessible
        
        :param client: S3 client
        :param bucket_name: Bucket name to validate
        :return: True if bucket is accessible, False otherwise
        """
        try:
            client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"❌ Bucket '{bucket_name}' does not exist or is not accessible")
            elif error_code == '403':
                print(f"⚠️ Access denied to bucket '{bucket_name}' (insufficient permissions)")
            else:
                print(f"❌ Error accessing bucket '{bucket_name}': {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error validating bucket '{bucket_name}': {e}")
            return False
    
    def _interactive_bucket_selection(self, buckets: List[str], select_type: str = 'source', 
                                      manual_input: bool = False) -> List[str]:
        """
        Interactive bucket selection with support for manual input
        
        :param buckets: List of available buckets
        :param select_type: 'source' or 'target'
        :param manual_input: True if buckets were manually entered
        :return: Selected buckets
        """
        if not buckets:
            print(f"⚠️ No {select_type} buckets available.")
            return []
        
        # If buckets were manually entered, ask if user wants to use all or select specific ones
        if manual_input:
            print(f"\n📦 Manually entered {select_type.capitalize()} Buckets:")
            for i, bucket in enumerate(buckets, 1):
                print(f"{i}. {bucket}")
            
            if len(buckets) == 1:
                print(f"✅ Using single bucket: {buckets[0]}")
                return buckets
            
            use_all = input(f"\nUse all {len(buckets)} buckets? (y/n): ").strip().lower()
            if use_all == 'y':
                return buckets
        else:
            print(f"\n📦 Available {select_type.capitalize()} Buckets:")
            for i, bucket in enumerate(buckets, 1):
                print(f"{i}. {bucket}")
        
        while True:
            try:
                if select_type == 'source':
                    prompt = "\nEnter bucket numbers (e.g., 1,3,5 or 'all'): "
                else:
                    prompt = "\nEnter target bucket number: "
                    
                selection = input(prompt).strip().lower()
                
                if select_type == 'source' and selection == 'all':
                    return buckets
                
                selected = []
                for part in selection.split(','):
                    part = part.strip()
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        selected.extend(buckets[start-1:end])
                    else:
                        selected.append(buckets[int(part)-1])
                
                return selected
            
            except (ValueError, IndexError):
                print("Invalid selection. Please try again.")
    
    def _copy_object(self, source_client, target_client, src_bucket: str, target_bucket: str, key: str, max_retries: int = 5):
        """
        Copy a single object between buckets with retry support
        
        :param source_client: Source S3 client
        :param target_client: Target S3 client
        :param src_bucket: Source bucket name
        :param target_bucket: Target bucket name
        :param key: Object key to copy
        :param max_retries: Maximum number of retry attempts
        :return: Tuple of (success boolean, key, error message if any)
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Download object from source
                response = source_client.get_object(Bucket=src_bucket, Key=key)
                body = response['Body'].read()
                
                # Upload to target bucket (overwrite if exists)
                target_client.put_object(Bucket=target_bucket, Key=key, Body=body)
                
                if attempt > 0:
                    print(f"ℹ️ Successfully copied {key} after {attempt} retries")
                
                return True, key, None
            
            except ClientError as obj_error:
                last_error = str(obj_error)
                if attempt < max_retries:
                    print(f"⚠️ Attempt {attempt + 1}/{max_retries + 1} failed for {key}: {last_error}")
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"❌ Failed to copy {key} after {max_retries + 1} attempts: {last_error}")
                    return False, key, last_error
            except Exception as e:
                last_error = str(e)
                print(f"❌ Unexpected error copying {key}: {last_error}")
                return False, key, last_error

    def sync_buckets(self, source_connection: Dict, target_connection: Dict, 
                     source_buckets: List[str]):
        """
        Synchronize buckets across S3 endpoints with parallel processing
        
        :param source_connection: Source AWS connection details
        :param target_connection: Target AWS connection details
        :param source_buckets: List of source buckets
        """
        source_client = self._get_s3_client(source_connection)
        target_client = self._get_s3_client(target_connection)
        
        total_objects = 0
        successful_objects = 0
        failed_objects = 0
        
        print("=" * 60)
        print("🚀 Starting S3 bucket synchronization")
        print("=" * 60)
        
        for src_bucket in source_buckets:
            bucket_successful = 0
            bucket_failed = 0
            target_bucket = src_bucket  # Use same bucket name as source
            
            try:
                print(f"📦 Processing bucket: {src_bucket} → {target_bucket}")
                
                # Check if target bucket exists, create if not
                try:
                    target_client.head_bucket(Bucket=target_bucket)
                    print(f"✅ Target bucket {target_bucket} exists")
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        # Bucket doesn't exist, create it
                        print(f"🆕 Creating target bucket: {target_bucket}")
                        
                        # Handle region-specific bucket creation
                        create_bucket_kwargs = {'Bucket': target_bucket}
                        region = target_connection.get('aws_region', 'us-east-1')
                        if region != 'us-east-1':
                            create_bucket_kwargs['CreateBucketConfiguration'] = {
                                'LocationConstraint': region
                            }
                        
                        target_client.create_bucket(**create_bucket_kwargs)
                        print(f"✅ Successfully created bucket: {target_bucket}")
                    else:
                        raise
                
                print(f"🔍 Listing objects in {src_bucket}...")
                
                # List all objects in source bucket
                paginator = source_client.get_paginator('list_objects_v2')
                object_keys = []
                for result in paginator.paginate(Bucket=src_bucket):
                    object_keys.extend([obj['Key'] for obj in result.get('Contents', [])])
                
                if not object_keys:
                    print(f"No objects found in {src_bucket}")
                    continue
                
                total_objects += len(object_keys)
                print(f"📊 Found {len(object_keys)} objects in {src_bucket}")
                
                # Parallel object copying
                print(f"⚡ Starting parallel sync with {self.max_workers} workers...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit copy tasks for all objects
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
                    
                    # Process results
                    for future in concurrent.futures.as_completed(future_to_key):
                        key = future_to_key[future]
                        try:
                            success, _, error = future.result()
                            if success:
                                successful_objects += 1
                                bucket_successful += 1
                                if bucket_successful % 100 == 0:
                                    print(f"📈 Progress: {bucket_successful}/{len(object_keys)} objects copied from {src_bucket}")
                            else:
                                failed_objects += 1
                                bucket_failed += 1
                                print(f"❌ Error copying object {key}: {error}")
                        except Exception as exc:
                            failed_objects += 1
                            bucket_failed += 1
                            print(f"❌ Unexpected error copying {key}: {exc}")
                
                # Sync summary for this bucket
                print("-" * 50)
                print(f"🎉 Bucket sync completed: {src_bucket}")
                print(f"📋 Objects processed: {len(object_keys)}")
                print(f"✅ Successful: {bucket_successful}")
                print(f"❌ Failed: {bucket_failed}")
                print("-" * 50)
            
            except ClientError as e:
                print(f"❌ Error syncing {src_bucket}: {e}")
        
        # Return results without printing final summary here
        # (final summary will be printed in the run method)
        return total_objects, successful_objects, failed_objects
    
    def run(self):
        """Main interactive sync workflow with global concurrency support"""
        try:
            print("🚀 S3 Bucket Synchronization Tool")
            
            # Source connection and buckets
            source_connection = self._input_connection_details('source')
            
            # Try to list buckets, with fallback to manual input
            source_buckets = []
            manual_input = False
            
            try:
                client = self._get_s3_client(source_connection)
                response = client.list_buckets()
                source_buckets = [bucket['Name'] for bucket in response['Buckets']]
            except Exception as e:
                print(f"⚠️ Unable to list buckets automatically: {e}")
                print("🔐 This might be due to insufficient ListBucket permissions.")
                source_buckets = self._manual_bucket_input()
                manual_input = True
            
            if not source_buckets:
                print("⚠️ No source buckets available.")
                return
            
            selected_source_buckets = self._interactive_bucket_selection(source_buckets, 'source', manual_input)
            
            if not selected_source_buckets:
                print("⚠️ No source buckets selected.")
                return
            
            # Validate manually entered buckets if needed
            if manual_input:
                print("\n🔍 Validating manually entered buckets...")
                client = self._get_s3_client(source_connection)
                valid_buckets = []
                
                for bucket in selected_source_buckets:
                    if self._validate_bucket_access(client, bucket):
                        print(f"✅ Bucket '{bucket}' is accessible")
                        valid_buckets.append(bucket)
                    else:
                        # Ask user if they want to continue without this bucket
                        continue_without = input(f"Continue without bucket '{bucket}'? (y/n): ").strip().lower()
                        if continue_without != 'y':
                            print("❌ Sync operation cancelled.")
                            return
                
                if not valid_buckets:
                    print("❌ No valid source buckets available.")
                    return
                
                selected_source_buckets = valid_buckets
                print(f"✅ Using validated buckets: {', '.join(selected_source_buckets)}")
            
            # Target connection
            target_connection = self._input_connection_details('target')
            
            # Confirmation
            print("\n" + "=" * 50)
            print("📝 S3 SYNC CONFIGURATION")
            print("=" * 50)
            print(f"📤 SOURCE:")
            print(f"   🔗 Connection: {source_connection.get('name', 'Default Profile')}")
            print(f"   🌐 Endpoint: {source_connection.get('s3_endpoint', 'AWS Default')}")
            print(f"   📦 Buckets:   {', '.join(selected_source_buckets)}")
            print("\n" + "-" * 50)
            print(f"📥 TARGET:")
            print(f"   🔗 Connection: {target_connection.get('name', 'Default Profile')}")
            print(f"   🌐 Endpoint: {target_connection.get('s3_endpoint', 'AWS Default')}")
            print("\n" + "=" * 50)
            
            confirm = input("\n❓ Type 'YES' to proceed with sync: ").strip()
            if confirm != 'YES':
                print("❌ Sync cancelled.")
                return
            
            # Perform sync
            total, successful, failed = self.sync_buckets(
                source_connection=source_connection, 
                target_connection=target_connection, 
                source_buckets=selected_source_buckets
            )
            
            # Final summary
            print("\n" + "=" * 60)
            print("🎉 SYNC OPERATION COMPLETED")
            print("=" * 60)
            print(f"📊 Total Objects: {total}")
            print(f"✅ Successfully Synced: {successful}")
            print(f"❌ Failed Objects: {failed}")
            print("=" * 60)
        
        except KeyboardInterrupt:
            print("\n❌ Sync operation cancelled by user.")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='S3 Bucket Synchronization Tool')
    parser.add_argument('--workers', '-w', type=int, default=10, 
                       help='Number of concurrent upload workers (default: 10)')
    
    args = parser.parse_args()
    
    # Check dependencies
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        print("❌ Missing dependency: boto3")
        print("Please run: pip install boto3")
        sys.exit(1)
    
    sync_tool = S3SyncTool(max_workers=args.workers)
    sync_tool.run()
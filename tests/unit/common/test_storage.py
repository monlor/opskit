"""Tests for common/python/storage.py"""

import pytest
import sqlite3
import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the storage module
import sys
import os

# Add the common/python directory to the path for testing
TEST_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(TEST_DIR / 'common' / 'python'))

from storage import OpsKitStorage, get_storage, cleanup_storage, get_all_storage_info


class TestOpsKitStorage:
    """Test cases for OpsKitStorage"""
    
    def test_init_with_custom_db_path(self, tmp_path):
        """Test storage initialization with custom database path"""
        db_path = tmp_path / 'test.db'
        storage = OpsKitStorage('test_namespace', str(db_path))
        
        assert storage.namespace == 'test_namespace'
        assert storage.db_path == db_path
        assert storage.table_name == 'storage_test_namespace'
    
    def test_init_with_auto_path(self):
        """Test storage initialization with automatic path detection"""
        with patch('pathlib.Path.mkdir'):
            storage = OpsKitStorage('test_namespace')
            
            assert storage.namespace == 'test_namespace'
            assert 'storage.db' in str(storage.db_path)
            assert storage.table_name == 'storage_test_namespace'
    
    def test_init_with_hyphens_in_namespace(self, tmp_path):
        """Test storage initialization with hyphens in namespace"""
        db_path = tmp_path / 'test.db'
        storage = OpsKitStorage('mysql-sync', str(db_path))
        
        assert storage.table_name == 'storage_mysql_sync'
    
    def test_serialize_value_string(self, tmp_path):
        """Test serializing string values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        value, type_name = storage._serialize_value('hello')
        assert value == 'hello'
        assert type_name == 'string'
    
    def test_serialize_value_number(self, tmp_path):
        """Test serializing number values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        # Integer
        value, type_name = storage._serialize_value(42)
        assert value == '42'
        assert type_name == 'number'
        
        # Float
        value, type_name = storage._serialize_value(3.14)
        assert value == '3.14'
        assert type_name == 'number'
    
    def test_serialize_value_boolean(self, tmp_path):
        """Test serializing boolean values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        value, type_name = storage._serialize_value(True)
        assert value == 'True'
        assert type_name == 'boolean'
        
        value, type_name = storage._serialize_value(False)
        assert value == 'False'
        assert type_name == 'boolean'
    
    def test_serialize_value_none(self, tmp_path):
        """Test serializing None values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        value, type_name = storage._serialize_value(None)
        assert value == ''
        assert type_name == 'null'
    
    def test_serialize_value_complex(self, tmp_path):
        """Test serializing complex values (JSON)"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        test_dict = {'name': 'test', 'count': 5}
        value, type_name = storage._serialize_value(test_dict)
        assert json.loads(value) == test_dict
        assert type_name == 'json'
    
    def test_deserialize_value_string(self, tmp_path):
        """Test deserializing string values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        result = storage._deserialize_value('hello', 'string')
        assert result == 'hello'
    
    def test_deserialize_value_number(self, tmp_path):
        """Test deserializing number values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        # Integer
        result = storage._deserialize_value('42', 'number')
        assert result == 42
        assert isinstance(result, int)
        
        # Negative integer
        result = storage._deserialize_value('-10', 'number')
        assert result == -10
        assert isinstance(result, int)
        
        # Float
        result = storage._deserialize_value('3.14', 'number')
        assert result == 3.14
        assert isinstance(result, float)
    
    def test_deserialize_value_boolean(self, tmp_path):
        """Test deserializing boolean values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        result = storage._deserialize_value('True', 'boolean')
        assert result is True
        
        result = storage._deserialize_value('False', 'boolean')
        assert result is False
        
        result = storage._deserialize_value('true', 'boolean')
        assert result is True
    
    def test_deserialize_value_null(self, tmp_path):
        """Test deserializing null values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        result = storage._deserialize_value('', 'null')
        assert result is None
    
    def test_deserialize_value_json(self, tmp_path):
        """Test deserializing JSON values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        test_dict = {'name': 'test', 'count': 5}
        json_str = json.dumps(test_dict)
        result = storage._deserialize_value(json_str, 'json')
        assert result == test_dict
    
    def test_set_and_get_string(self, tmp_path):
        """Test setting and getting string values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        storage.set('test_key', 'test_value')
        result = storage.get('test_key')
        
        assert result == 'test_value'
    
    def test_set_and_get_number(self, tmp_path):
        """Test setting and getting number values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        storage.set('int_key', 42)
        storage.set('float_key', 3.14)
        
        assert storage.get('int_key') == 42
        assert storage.get('float_key') == 3.14
    
    def test_set_and_get_boolean(self, tmp_path):
        """Test setting and getting boolean values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        storage.set('true_key', True)
        storage.set('false_key', False)
        
        assert storage.get('true_key') is True
        assert storage.get('false_key') is False
    
    def test_set_and_get_none(self, tmp_path):
        """Test setting and getting None values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        storage.set('null_key', None)
        result = storage.get('null_key')
        
        assert result is None
    
    def test_set_and_get_complex(self, tmp_path):
        """Test setting and getting complex values"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        test_data = {
            'name': 'test_tool',
            'settings': {
                'timeout': 30,
                'retries': 3
            },
            'features': ['auth', 'sync', 'backup']
        }
        
        storage.set('config', test_data)
        result = storage.get('config')
        
        assert result == test_data
    
    def test_get_with_default(self, tmp_path):
        """Test getting non-existent key with default value"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        result = storage.get('nonexistent_key', 'default_value')
        assert result == 'default_value'
        
        result = storage.get('nonexistent_key')
        assert result is None
    
    def test_delete_existing_key(self, tmp_path):
        """Test deleting existing key"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        storage.set('delete_me', 'value')
        assert storage.exists('delete_me') is True
        
        result = storage.delete('delete_me')
        assert result is True
        assert storage.exists('delete_me') is False
    
    def test_delete_nonexistent_key(self, tmp_path):
        """Test deleting non-existent key"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        result = storage.delete('nonexistent_key')
        assert result is False
    
    def test_exists(self, tmp_path):
        """Test key existence check"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        assert storage.exists('test_key') is False
        
        storage.set('test_key', 'value')
        assert storage.exists('test_key') is True
        
        storage.delete('test_key')
        assert storage.exists('test_key') is False
    
    def test_keys_all(self, tmp_path):
        """Test getting all keys"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        storage.set('key1', 'value1')
        storage.set('key2', 'value2')
        storage.set('config_setting', 'value3')
        
        keys = storage.keys()
        assert sorted(keys) == ['config_setting', 'key1', 'key2']
    
    def test_keys_with_pattern(self, tmp_path):
        """Test getting keys with pattern matching"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        storage.set('config_timeout', 30)
        storage.set('config_retries', 3)
        storage.set('data_sync', True)
        storage.set('config_enabled', True)
        
        config_keys = storage.keys('config_%')
        assert sorted(config_keys) == ['config_enabled', 'config_retries', 'config_timeout']
    
    def test_items_all(self, tmp_path):
        """Test getting all key-value pairs"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        storage.set('string_key', 'string_value')
        storage.set('int_key', 42)
        storage.set('bool_key', True)
        
        items = storage.items()
        expected = {
            'string_key': 'string_value',
            'int_key': 42,
            'bool_key': True
        }
        
        assert items == expected
    
    def test_items_with_pattern(self, tmp_path):
        """Test getting key-value pairs with pattern"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        storage.set('config_timeout', 30)
        storage.set('config_retries', 3)
        storage.set('data_sync', True)
        
        config_items = storage.items('config_%')
        expected = {
            'config_timeout': 30,
            'config_retries': 3
        }
        
        assert config_items == expected
    
    def test_clear_all(self, tmp_path):
        """Test clearing all storage"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        storage.set('key1', 'value1')
        storage.set('key2', 'value2')
        storage.set('key3', 'value3')
        
        assert storage.size() == 3
        
        deleted_count = storage.clear()
        assert deleted_count == 3
        assert storage.size() == 0
    
    def test_clear_with_pattern(self, tmp_path):
        """Test clearing storage with pattern"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        storage.set('config_timeout', 30)
        storage.set('config_retries', 3)
        storage.set('data_sync', True)
        
        deleted_count = storage.clear('config_%')
        assert deleted_count == 2
        assert storage.size() == 1
        assert storage.exists('data_sync') is True
    
    def test_size(self, tmp_path):
        """Test getting storage size"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        assert storage.size() == 0
        
        storage.set('key1', 'value1')
        assert storage.size() == 1
        
        storage.set('key2', 'value2')
        assert storage.size() == 2
        
        storage.delete('key1')
        assert storage.size() == 1
    
    def test_info(self, tmp_path):
        """Test getting storage information"""
        db_path = tmp_path / 'test.db'
        storage = OpsKitStorage('test_namespace', str(db_path))
        
        storage.set('test_key', 'test_value')
        
        info = storage.info()
        
        assert info['namespace'] == 'test_namespace'
        assert info['database_path'] == str(db_path)
        assert info['total_keys'] == 1
        assert info['database_size'] > 0
        assert info['oldest_entry'] is not None
        assert info['newest_entry'] is not None
    
    def test_backup(self, tmp_path):
        """Test creating storage backup"""
        db_path = tmp_path / 'test.db'
        backup_path = tmp_path / 'backup.db'
        storage = OpsKitStorage('test', str(db_path))
        
        storage.set('test_key', 'test_value')
        
        result = storage.backup(str(backup_path))
        assert result is True
        assert backup_path.exists()
        
        # Verify backup contains data
        backup_storage = OpsKitStorage('test', str(backup_path))
        assert backup_storage.get('test_key') == 'test_value'
    
    def test_close(self, tmp_path):
        """Test closing storage connection"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        
        # Access connection to create it
        storage.set('test_key', 'test_value')
        
        # Close connection
        storage.close()
        
        # Should be able to use storage again (new connection will be created)
        result = storage.get('test_key')
        assert result == 'test_value'
    
    def test_thread_safety(self, tmp_path):
        """Test thread-safe operations"""
        storage = OpsKitStorage('test', str(tmp_path / 'test.db'))
        results = []
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(10):
                    key = f'thread_{thread_id}_key_{i}'
                    value = f'thread_{thread_id}_value_{i}'
                    storage.set(key, value)
                    retrieved = storage.get(key)
                    assert retrieved == value
                    results.append(f'{thread_id}_{i}')
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 50  # 5 threads * 10 operations each
        assert storage.size() == 50


class TestStorageConvenienceFunctions:
    """Test cases for convenience functions"""
    
    def test_get_storage_singleton(self, tmp_path):
        """Test that get_storage returns same instance for same namespace"""
        with patch('storage.Path') as mock_path:
            mock_path.return_value.resolve.return_value.parent.parent.parent = tmp_path
            mock_path.return_value.mkdir = Mock()
            mock_path.return_value.exists.return_value = True
            
            storage1 = get_storage('test_namespace')
            storage2 = get_storage('test_namespace')
            
            assert storage1 is storage2
    
    def test_get_storage_different_namespaces(self, tmp_path):
        """Test that get_storage returns different instances for different namespaces"""
        with patch('storage.Path') as mock_path:
            mock_path.return_value.resolve.return_value.parent.parent.parent = tmp_path
            mock_path.return_value.mkdir = Mock()
            mock_path.return_value.exists.return_value = True
            
            storage1 = get_storage('namespace1')
            storage2 = get_storage('namespace2')
            
            assert storage1 is not storage2
            assert storage1.namespace == 'namespace1'
            assert storage2.namespace == 'namespace2'
    
    def test_cleanup_storage(self, tmp_path):
        """Test cleaning up old storage entries"""
        db_path = tmp_path / 'storage.db'
        
        # Create test database with old entries
        conn = sqlite3.connect(str(db_path))
        conn.execute('''
            CREATE TABLE storage_test (
                key TEXT PRIMARY KEY,
                value TEXT,
                type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert old and new entries
        old_time = time.time() - (40 * 24 * 60 * 60)  # 40 days ago
        recent_time = time.time() - (10 * 24 * 60 * 60)  # 10 days ago
        
        conn.execute(
            'INSERT INTO storage_test (key, value, type, updated_at) VALUES (?, ?, ?, datetime(?, "unixepoch"))',
            ('old_key', 'old_value', 'string', old_time)
        )
        conn.execute(
            'INSERT INTO storage_test (key, value, type, updated_at) VALUES (?, ?, ?, datetime(?, "unixepoch"))',
            ('recent_key', 'recent_value', 'string', recent_time)
        )
        
        conn.commit()
        conn.close()
        
        with patch('storage.Path') as mock_path:
            mock_path.return_value.resolve.return_value.parent.parent.parent = tmp_path
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.__truediv__.return_value.__truediv__.return_value = db_path
            
            result = cleanup_storage(days=30)
            
            assert 'test' in result
            assert result['test'] == 1  # Only old entry was removed
    
    def test_get_all_storage_info(self, tmp_path):
        """Test getting information about all storage namespaces"""
        db_path = tmp_path / 'storage.db'
        
        # Create test database with multiple namespaces
        conn = sqlite3.connect(str(db_path))
        
        # Create tables for different namespaces
        for namespace in ['mysql_sync', 'port_scanner']:
            table_name = f'storage_{namespace}'
            conn.execute(f'''
                CREATE TABLE {table_name} (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute(f'INSERT INTO {table_name} (key, value, type) VALUES (?, ?, ?)',
                        ('test_key', 'test_value', 'string'))
        
        conn.commit()
        conn.close()
        
        with patch('storage.Path') as mock_path:
            mock_path.return_value.resolve.return_value.parent.parent.parent = tmp_path
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.__truediv__.return_value.__truediv__.return_value = db_path
            
            result = get_all_storage_info()
            
            assert 'mysql-sync' in result
            assert 'port-scanner' in result
            assert result['mysql-sync']['total_keys'] == 1
            assert result['port-scanner']['total_keys'] == 1


@pytest.mark.integration
class TestStorageIntegration:
    """Integration tests for storage functionality"""
    
    def test_full_storage_workflow(self, tmp_path):
        """Test complete storage workflow"""
        db_path = tmp_path / 'integration_test.db'
        storage = OpsKitStorage('integration_test', str(db_path))
        
        # Test various data types
        test_data = {
            'string_val': 'hello world',
            'int_val': 42,
            'float_val': 3.14159,
            'bool_val': True,
            'null_val': None,
            'dict_val': {'nested': {'key': 'value'}},
            'list_val': [1, 2, 3, 'four', True],
        }
        
        # Store all test data
        for key, value in test_data.items():
            storage.set(key, value)
        
        # Retrieve and verify
        for key, expected_value in test_data.items():
            retrieved_value = storage.get(key)
            assert retrieved_value == expected_value
        
        # Test pattern operations
        storage.set('config_timeout', 30)
        storage.set('config_retries', 3)
        storage.set('data_last_sync', '2023-01-01')
        
        config_keys = storage.keys('config_%')
        assert len(config_keys) == 2
        assert 'config_timeout' in config_keys
        assert 'config_retries' in config_keys
        
        config_items = storage.items('config_%')
        assert config_items['config_timeout'] == 30
        assert config_items['config_retries'] == 3
        
        # Test cleanup
        initial_size = storage.size()
        assert initial_size > 0
        
        deleted_count = storage.clear('config_%')
        assert deleted_count == 2
        assert storage.size() == initial_size - 2
        
        # Test info and backup
        info = storage.info()
        assert info['namespace'] == 'integration_test'
        assert info['total_keys'] > 0
        
        backup_path = tmp_path / 'backup.db'
        assert storage.backup(str(backup_path)) is True
        assert backup_path.exists()
    
    def test_multiple_namespaces(self, tmp_path):
        """Test multiple storage namespaces sharing same database"""
        db_path = tmp_path / 'shared.db'
        
        storage1 = OpsKitStorage('namespace1', str(db_path))
        storage2 = OpsKitStorage('namespace2', str(db_path))
        
        # Store data in different namespaces
        storage1.set('shared_key', 'value_from_ns1')
        storage2.set('shared_key', 'value_from_ns2')
        
        # Verify isolation
        assert storage1.get('shared_key') == 'value_from_ns1'
        assert storage2.get('shared_key') == 'value_from_ns2'
        
        # Cross-namespace operations should not interfere
        storage1.set('unique_key1', 'unique_value1')
        storage2.set('unique_key2', 'unique_value2')
        
        assert storage1.exists('unique_key1') is True
        assert storage1.exists('unique_key2') is False
        assert storage2.exists('unique_key1') is False
        assert storage2.exists('unique_key2') is True
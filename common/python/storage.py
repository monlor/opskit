"""
Key-Value Storage System

Provides lightweight persistent storage using SQLite backend with:
- Simple key-value interface
- JSON serialization for complex data types
- Tool-specific storage namespaces
- Automatic database management
"""

import os
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager
from datetime import datetime


class OpsKitStorage:
    """Thread-safe key-value storage with SQLite backend"""
    
    _instances: Dict[str, 'OpsKitStorage'] = {}
    _lock = threading.Lock()
    
    def __init__(self, namespace: str, db_path: Optional[str] = None):
        """
        Initialize storage for a specific namespace
        
        Args:
            namespace: Storage namespace (usually tool name)
            db_path: Custom database path (auto-detected if None)
        """
        self.namespace = namespace
        
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Auto-detect OpsKit root and set data directory
            current_file = Path(__file__).resolve()
            opskit_root = current_file.parent.parent.parent
            data_dir = opskit_root / 'data'
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / 'storage.db'
        
        self.table_name = f"storage_{namespace.replace('-', '_')}"
        self._local = threading.local()
        
        # Initialize database
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False
            )
            self._local.connection.execute('PRAGMA journal_mode=WAL')
            self._local.connection.execute('PRAGMA synchronous=NORMAL')
            self._local.connection.execute('PRAGMA cache_size=1000')
        
        return self._local.connection
    
    def _init_database(self) -> None:
        """Initialize the database and table"""
        with self._get_connection() as conn:
            conn.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for faster queries
            conn.execute(f'''
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_updated 
                ON {self.table_name} (updated_at)
            ''')
            
            conn.commit()
    
    @contextmanager
    def _transaction(self):
        """Context manager for database transactions"""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _serialize_value(self, value: Any) -> tuple[str, str]:
        """
        Serialize a value for storage
        
        Returns:
            Tuple of (serialized_value, type_name)
        """
        if isinstance(value, str):
            return value, 'string'
        elif isinstance(value, (int, float)):
            return str(value), 'number'
        elif isinstance(value, bool):
            return str(value), 'boolean'
        elif value is None:
            return '', 'null'
        else:
            # JSON serialize complex types
            return json.dumps(value, default=str), 'json'
    
    def _deserialize_value(self, value: str, type_name: str) -> Any:
        """
        Deserialize a value from storage
        
        Args:
            value: Stored value string
            type_name: Value type name
        
        Returns:
            Deserialized value
        """
        if type_name == 'string':
            return value
        elif type_name == 'number':
            return int(value) if value.isdigit() or (value.startswith('-') and value[1:].isdigit()) else float(value)
        elif type_name == 'boolean':
            return value.lower() == 'true'
        elif type_name == 'null':
            return None
        elif type_name == 'json':
            return json.loads(value) if value else None
        else:
            return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Store a key-value pair
        
        Args:
            key: Storage key
            value: Value to store (will be JSON serialized if complex)
        """
        serialized_value, type_name = self._serialize_value(value)
        
        with self._transaction() as conn:
            conn.execute(f'''
                INSERT OR REPLACE INTO {self.table_name} 
                (key, value, type, updated_at) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, serialized_value, type_name))
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value by key
        
        Args:
            key: Storage key
            default: Default value if key not found
        
        Returns:
            Stored value or default
        """
        conn = self._get_connection()
        cursor = conn.execute(
            f'SELECT value, type FROM {self.table_name} WHERE key = ?',
            (key,)
        )
        
        row = cursor.fetchone()
        if row is None:
            return default
        
        value, type_name = row
        return self._deserialize_value(value, type_name)
    
    def delete(self, key: str) -> bool:
        """
        Delete a key-value pair
        
        Args:
            key: Storage key to delete
        
        Returns:
            True if key existed and was deleted
        """
        with self._transaction() as conn:
            cursor = conn.execute(
                f'DELETE FROM {self.table_name} WHERE key = ?',
                (key,)
            )
            return cursor.rowcount > 0
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists
        
        Args:
            key: Storage key to check
        
        Returns:
            True if key exists
        """
        conn = self._get_connection()
        cursor = conn.execute(
            f'SELECT 1 FROM {self.table_name} WHERE key = ? LIMIT 1',
            (key,)
        )
        return cursor.fetchone() is not None
    
    def keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        Get all keys, optionally matching a pattern
        
        Args:
            pattern: SQL LIKE pattern (e.g., 'config_%')
        
        Returns:
            List of matching keys
        """
        conn = self._get_connection()
        
        if pattern:
            cursor = conn.execute(
                f'SELECT key FROM {self.table_name} WHERE key LIKE ? ORDER BY key',
                (pattern,)
            )
        else:
            cursor = conn.execute(
                f'SELECT key FROM {self.table_name} ORDER BY key'
            )
        
        return [row[0] for row in cursor.fetchall()]
    
    def items(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all key-value pairs as dictionary
        
        Args:
            pattern: SQL LIKE pattern for keys
        
        Returns:
            Dictionary of matching key-value pairs
        """
        conn = self._get_connection()
        
        if pattern:
            cursor = conn.execute(
                f'SELECT key, value, type FROM {self.table_name} WHERE key LIKE ? ORDER BY key',
                (pattern,)
            )
        else:
            cursor = conn.execute(
                f'SELECT key, value, type FROM {self.table_name} ORDER BY key'
            )
        
        result = {}
        for row in cursor.fetchall():
            key, value, type_name = row
            result[key] = self._deserialize_value(value, type_name)
        
        return result
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear storage, optionally matching a pattern
        
        Args:
            pattern: SQL LIKE pattern for keys to delete
        
        Returns:
            Number of keys deleted
        """
        with self._transaction() as conn:
            if pattern:
                cursor = conn.execute(
                    f'DELETE FROM {self.table_name} WHERE key LIKE ?',
                    (pattern,)
                )
            else:
                cursor = conn.execute(f'DELETE FROM {self.table_name}')
            
            return cursor.rowcount
    
    def size(self) -> int:
        """
        Get the number of stored keys
        
        Returns:
            Number of stored keys
        """
        conn = self._get_connection()
        cursor = conn.execute(f'SELECT COUNT(*) FROM {self.table_name}')
        return cursor.fetchone()[0]
    
    def info(self) -> Dict[str, Any]:
        """
        Get storage information
        
        Returns:
            Dictionary with storage statistics
        """
        conn = self._get_connection()
        
        # Get basic stats
        cursor = conn.execute(f'''
            SELECT 
                COUNT(*) as total_keys,
                MIN(created_at) as oldest_entry,
                MAX(updated_at) as newest_entry
            FROM {self.table_name}
        ''')
        
        stats = cursor.fetchone()
        
        # Get database file size
        db_size = 0
        try:
            if self.db_path.exists():
                db_size = self.db_path.stat().st_size
        except Exception:
            pass
        
        return {
            'namespace': self.namespace,
            'database_path': str(self.db_path),
            'database_size': db_size,
            'total_keys': stats[0] if stats else 0,
            'oldest_entry': stats[1] if stats else None,
            'newest_entry': stats[2] if stats else None
        }
    
    def backup(self, backup_path: str) -> bool:
        """
        Create a backup of the storage
        
        Args:
            backup_path: Path for backup file
        
        Returns:
            True if backup was successful
        """
        try:
            backup_path = Path(backup_path)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup using SQLite backup API
            source_conn = self._get_connection()
            backup_conn = sqlite3.connect(str(backup_path))
            
            source_conn.backup(backup_conn)
            backup_conn.close()
            
            return True
        except Exception:
            return False
    
    def close(self) -> None:
        """Close database connection"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection


# Global storage registry
_storage_registry: Dict[str, OpsKitStorage] = {}
_registry_lock = threading.Lock()


def get_storage(namespace: str, db_path: Optional[str] = None) -> OpsKitStorage:
    """
    Get a storage instance for a specific namespace
    
    Args:
        namespace: Storage namespace (usually tool name)
        db_path: Custom database path (optional)
    
    Returns:
        Storage instance
    
    Example:
        storage = get_storage('mysql-sync')
        storage.set('last_sync_time', datetime.now())
        last_sync = storage.get('last_sync_time')
    """
    with _registry_lock:
        if namespace not in _storage_registry:
            _storage_registry[namespace] = OpsKitStorage(namespace, db_path)
        return _storage_registry[namespace]


def cleanup_storage(days: int = 30) -> Dict[str, int]:
    """
    Clean up old storage entries across all namespaces
    
    Args:
        days: Remove entries older than this many days
    
    Returns:
        Dictionary of namespace -> number of cleaned entries
    """
    result = {}
    cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    # Find all storage instances
    current_file = Path(__file__).resolve()
    opskit_root = current_file.parent.parent.parent
    data_dir = opskit_root / 'data'
    db_path = data_dir / 'storage.db'
    
    if not db_path.exists():
        return result
    
    try:
        conn = sqlite3.connect(str(db_path))
        
        # Get all tables that look like storage tables
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'storage_%'"
        )
        
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            # Clean old entries
            cursor = conn.execute(f'''
                DELETE FROM {table} 
                WHERE datetime(updated_at) < datetime(?, 'unixepoch')
            ''', (cutoff_date,))
            
            namespace = table.replace('storage_', '').replace('_', '-')
            result[namespace] = cursor.rowcount
        
        conn.commit()
        conn.close()
        
    except Exception:
        pass
    
    return result


def get_all_storage_info() -> Dict[str, Dict[str, Any]]:
    """
    Get information about all storage namespaces
    
    Returns:
        Dictionary of namespace -> storage info
    """
    result = {}
    
    # Find database
    current_file = Path(__file__).resolve()
    opskit_root = current_file.parent.parent.parent
    data_dir = opskit_root / 'data'
    db_path = data_dir / 'storage.db'
    
    if not db_path.exists():
        return result
    
    try:
        conn = sqlite3.connect(str(db_path))
        
        # Get all storage tables
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'storage_%'"
        )
        
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            namespace = table.replace('storage_', '').replace('_', '-')
            
            # Get table stats
            stats_cursor = conn.execute(f'''
                SELECT 
                    COUNT(*) as total_keys,
                    MIN(created_at) as oldest_entry,
                    MAX(updated_at) as newest_entry
                FROM {table}
            ''')
            
            stats = stats_cursor.fetchone()
            result[namespace] = {
                'total_keys': stats[0] if stats else 0,
                'oldest_entry': stats[1] if stats else None,
                'newest_entry': stats[2] if stats else None
            }
        
        conn.close()
        
    except Exception:
        pass
    
    return result
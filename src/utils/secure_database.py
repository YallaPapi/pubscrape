"""
Secure Database Operations Module

Provides secure database interactions with parameterized queries,
connection pooling, and protection against SQL injection attacks.
"""

import sqlite3
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager
from pathlib import Path
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class QueryResult:
    """Result of database query execution"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    affected_rows: int = 0
    error_message: Optional[str] = None
    execution_time: float = 0.0


class SecureDatabaseManager:
    """
    Secure database manager with parameterized queries and connection pooling
    """
    
    def __init__(self, database_path: str, max_connections: int = 10):
        self.database_path = Path(database_path)
        self.max_connections = max_connections
        self.logger = logging.getLogger(__name__)
        self._connection_pool = []
        self._pool_lock = threading.Lock()
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database with security settings"""
        # Ensure database directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create initial connection with secure settings
        with self._get_connection() as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Set secure journal mode
            conn.execute("PRAGMA journal_mode = WAL")
            
            # Enable secure delete (overwrite deleted data)
            conn.execute("PRAGMA secure_delete = ON")
            
            # Set reasonable timeout
            conn.execute("PRAGMA busy_timeout = 30000")
            
            conn.commit()
        
        self.logger.info(f"Database initialized: {self.database_path}")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection from pool"""
        conn = None
        try:
            with self._pool_lock:
                if self._connection_pool:
                    conn = self._connection_pool.pop()
                else:
                    conn = sqlite3.connect(
                        self.database_path,
                        timeout=30.0,
                        check_same_thread=False
                    )
                    conn.row_factory = sqlite3.Row
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                with self._pool_lock:
                    if len(self._connection_pool) < self.max_connections:
                        self._connection_pool.append(conn)
                    else:
                        conn.close()
    
    def execute_query(
        self, 
        query: str, 
        parameters: Optional[Union[Tuple, Dict]] = None,
        fetch_results: bool = True
    ) -> QueryResult:
        """
        Execute a parameterized query safely
        
        Args:
            query: SQL query with parameter placeholders
            parameters: Parameters to bind to query
            fetch_results: Whether to fetch and return results
            
        Returns:
            QueryResult object with execution details
        """
        start_time = datetime.now()
        
        # Validate query for dangerous patterns
        if not self._validate_query_safety(query):
            return QueryResult(
                success=False,
                error_message="Query contains potentially dangerous patterns",
                execution_time=0.0
            )
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Execute with parameters (prevents SQL injection)
                if parameters:
                    if isinstance(parameters, dict):
                        cursor.execute(query, parameters)
                    else:
                        cursor.execute(query, parameters)
                else:
                    cursor.execute(query)
                
                # Fetch results if requested
                data = None
                if fetch_results:
                    rows = cursor.fetchall()
                    data = [dict(row) for row in rows] if rows else []
                
                affected_rows = cursor.rowcount
                conn.commit()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                self.logger.debug(f"Query executed successfully in {execution_time:.3f}s: {query[:100]}...")
                
                return QueryResult(
                    success=True,
                    data=data,
                    affected_rows=affected_rows,
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            
            self.logger.error(f"Query execution failed after {execution_time:.3f}s: {error_msg}")
            
            return QueryResult(
                success=False,
                error_message=error_msg,
                execution_time=execution_time
            )
    
    def _validate_query_safety(self, query: str) -> bool:
        """
        Validate query for dangerous patterns that could indicate SQL injection
        """
        query_lower = query.lower().strip()
        
        # Allow only safe query types
        safe_start_patterns = [
            'select', 'insert', 'update', 'delete', 'create table', 'create index',
            'drop table', 'drop index', 'alter table', 'pragma', 'with'
        ]
        
        if not any(query_lower.startswith(pattern) for pattern in safe_start_patterns):
            self.logger.warning(f"Query does not start with safe pattern: {query[:50]}...")
            return False
        
        # Check for dangerous patterns
        dangerous_patterns = [
            # Multiple statement execution
            r';\s*(select|insert|update|delete|drop|create|alter)',
            # Comment-based injection
            r'--\s*$',
            r'/\*.*\*/',
            # Union-based injection
            r'union\s+all\s+select',
            r'union\s+select',
            # System functions
            r'(load_extension|sqlite_master|sqlite_temp_master)',
            # Dangerous pragmas
            r'pragma\s+(table_info|database_list|foreign_key_check)',
        ]
        
        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE | re.MULTILINE):
                self.logger.warning(f"Dangerous pattern detected in query: {pattern}")
                return False
        
        return True
    
    def select(
        self, 
        table: str, 
        columns: Optional[List[str]] = None,
        where_conditions: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> QueryResult:
        """
        Execute a secure SELECT query
        
        Args:
            table: Table name
            columns: List of columns to select (None for all)
            where_conditions: Dictionary of column:value conditions
            order_by: ORDER BY clause
            limit: LIMIT value
            
        Returns:
            QueryResult object
        """
        # Validate table name (no injection)
        if not self._is_safe_identifier(table):
            return QueryResult(
                success=False,
                error_message="Invalid table name"
            )
        
        # Build column list
        if columns:
            # Validate column names
            for col in columns:
                if not self._is_safe_identifier(col):
                    return QueryResult(
                        success=False,
                        error_message=f"Invalid column name: {col}"
                    )
            columns_str = ', '.join(columns)
        else:
            columns_str = '*'
        
        # Build query
        query_parts = [f"SELECT {columns_str} FROM {table}"]
        parameters = {}
        
        # Add WHERE clause
        if where_conditions:
            where_parts = []
            for i, (column, value) in enumerate(where_conditions.items()):
                if not self._is_safe_identifier(column):
                    return QueryResult(
                        success=False,
                        error_message=f"Invalid column name in WHERE: {column}"
                    )
                param_name = f"param_{i}"
                where_parts.append(f"{column} = :{param_name}")
                parameters[param_name] = value
            
            if where_parts:
                query_parts.append(f"WHERE {' AND '.join(where_parts)}")
        
        # Add ORDER BY
        if order_by:
            if not self._is_safe_identifier(order_by):
                return QueryResult(
                    success=False,
                    error_message="Invalid ORDER BY column"
                )
            query_parts.append(f"ORDER BY {order_by}")
        
        # Add LIMIT
        if limit:
            if not isinstance(limit, int) or limit <= 0:
                return QueryResult(
                    success=False,
                    error_message="Invalid LIMIT value"
                )
            query_parts.append(f"LIMIT {limit}")
        
        query = ' '.join(query_parts)
        return self.execute_query(query, parameters)
    
    def insert(
        self, 
        table: str, 
        data: Dict[str, Any],
        on_conflict: Optional[str] = None
    ) -> QueryResult:
        """
        Execute a secure INSERT query
        
        Args:
            table: Table name
            data: Dictionary of column:value pairs
            on_conflict: ON CONFLICT clause (e.g., 'REPLACE', 'IGNORE')
            
        Returns:
            QueryResult object
        """
        if not self._is_safe_identifier(table):
            return QueryResult(
                success=False,
                error_message="Invalid table name"
            )
        
        if not data:
            return QueryResult(
                success=False,
                error_message="No data provided for insert"
            )
        
        # Validate column names
        for column in data.keys():
            if not self._is_safe_identifier(column):
                return QueryResult(
                    success=False,
                    error_message=f"Invalid column name: {column}"
                )
        
        columns = list(data.keys())
        placeholders = [f":{col}" for col in columns]
        
        query = f"INSERT"
        if on_conflict == 'REPLACE':
            query = "INSERT OR REPLACE"
        elif on_conflict == 'IGNORE':
            query = "INSERT OR IGNORE"
        
        query += f" INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        
        return self.execute_query(query, data, fetch_results=False)
    
    def update(
        self, 
        table: str, 
        data: Dict[str, Any],
        where_conditions: Dict[str, Any]
    ) -> QueryResult:
        """
        Execute a secure UPDATE query
        
        Args:
            table: Table name
            data: Dictionary of column:value pairs to update
            where_conditions: Dictionary of column:value conditions for WHERE clause
            
        Returns:
            QueryResult object
        """
        if not self._is_safe_identifier(table):
            return QueryResult(
                success=False,
                error_message="Invalid table name"
            )
        
        if not data:
            return QueryResult(
                success=False,
                error_message="No data provided for update"
            )
        
        if not where_conditions:
            return QueryResult(
                success=False,
                error_message="WHERE conditions required for update"
            )
        
        # Validate column names
        all_columns = list(data.keys()) + list(where_conditions.keys())
        for column in all_columns:
            if not self._is_safe_identifier(column):
                return QueryResult(
                    success=False,
                    error_message=f"Invalid column name: {column}"
                )
        
        # Build SET clause
        set_parts = []
        parameters = {}
        
        for i, (column, value) in enumerate(data.items()):
            param_name = f"set_param_{i}"
            set_parts.append(f"{column} = :{param_name}")
            parameters[param_name] = value
        
        # Build WHERE clause
        where_parts = []
        for i, (column, value) in enumerate(where_conditions.items()):
            param_name = f"where_param_{i}"
            where_parts.append(f"{column} = :{param_name}")
            parameters[param_name] = value
        
        query = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {' AND '.join(where_parts)}"
        
        return self.execute_query(query, parameters, fetch_results=False)
    
    def delete(self, table: str, where_conditions: Dict[str, Any]) -> QueryResult:
        """
        Execute a secure DELETE query
        
        Args:
            table: Table name
            where_conditions: Dictionary of column:value conditions for WHERE clause
            
        Returns:
            QueryResult object
        """
        if not self._is_safe_identifier(table):
            return QueryResult(
                success=False,
                error_message="Invalid table name"
            )
        
        if not where_conditions:
            return QueryResult(
                success=False,
                error_message="WHERE conditions required for delete"
            )
        
        # Validate column names
        for column in where_conditions.keys():
            if not self._is_safe_identifier(column):
                return QueryResult(
                    success=False,
                    error_message=f"Invalid column name: {column}"
                )
        
        # Build WHERE clause
        where_parts = []
        parameters = {}
        
        for i, (column, value) in enumerate(where_conditions.items()):
            param_name = f"param_{i}"
            where_parts.append(f"{column} = :{param_name}")
            parameters[param_name] = value
        
        query = f"DELETE FROM {table} WHERE {' AND '.join(where_parts)}"
        
        return self.execute_query(query, parameters, fetch_results=False)
    
    def _is_safe_identifier(self, identifier: str) -> bool:
        """
        Check if an identifier (table/column name) is safe to use
        """
        if not identifier or not isinstance(identifier, str):
            return False
        
        # Check for valid identifier pattern
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            return False
        
        # Check against SQL keywords (basic list)
        sql_keywords = {
            'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'table', 'database', 'index', 'view', 'trigger', 'procedure',
            'function', 'union', 'where', 'having', 'group', 'order', 'by',
            'from', 'into', 'values', 'set', 'join', 'inner', 'outer', 'left',
            'right', 'full', 'cross', 'on', 'using', 'natural', 'as', 'case',
            'when', 'then', 'else', 'end', 'if', 'null', 'not', 'and', 'or',
            'in', 'exists', 'between', 'like', 'is', 'distinct', 'all', 'any',
            'some', 'union', 'intersect', 'except', 'minus'
        }
        
        if identifier.lower() in sql_keywords:
            return False
        
        return True
    
    def create_table(self, table_name: str, schema: Dict[str, str]) -> QueryResult:
        """
        Create a table with the given schema
        
        Args:
            table_name: Name of the table
            schema: Dictionary mapping column names to their SQL types
            
        Returns:
            QueryResult object
        """
        if not self._is_safe_identifier(table_name):
            return QueryResult(
                success=False,
                error_message="Invalid table name"
            )
        
        # Validate column definitions
        columns = []
        for col_name, col_type in schema.items():
            if not self._is_safe_identifier(col_name):
                return QueryResult(
                    success=False,
                    error_message=f"Invalid column name: {col_name}"
                )
            
            # Basic type validation
            valid_types = [
                'TEXT', 'INTEGER', 'REAL', 'BLOB', 'NUMERIC',
                'VARCHAR', 'CHAR', 'BOOLEAN', 'DATE', 'DATETIME', 'TIMESTAMP'
            ]
            
            base_type = col_type.upper().split('(')[0].split()[0]
            if base_type not in valid_types:
                return QueryResult(
                    success=False,
                    error_message=f"Invalid column type: {col_type}"
                )
            
            columns.append(f"{col_name} {col_type}")
        
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        return self.execute_query(query, fetch_results=False)
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        if not self._is_safe_identifier(table_name):
            return False
        
        result = self.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        
        return result.success and result.data and len(result.data) > 0
    
    def get_table_info(self, table_name: str) -> QueryResult:
        """Get information about a table's structure"""
        if not self._is_safe_identifier(table_name):
            return QueryResult(
                success=False,
                error_message="Invalid table name"
            )
        
        return self.execute_query(f"PRAGMA table_info({table_name})")
    
    def close_connections(self):
        """Close all pooled connections"""
        with self._pool_lock:
            while self._connection_pool:
                conn = self._connection_pool.pop()
                try:
                    conn.close()
                except:
                    pass
        
        self.logger.info("All database connections closed")


# Example usage and security best practices
class SecureLeadStorage:
    """
    Example secure storage class for lead data
    """
    
    def __init__(self, database_path: str):
        self.db = SecureDatabaseManager(database_path)
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Initialize database schema"""
        # Create leads table
        leads_schema = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'business_name': 'TEXT NOT NULL',
            'email': 'TEXT',
            'phone': 'TEXT',
            'website': 'TEXT',
            'address': 'TEXT',
            'city': 'TEXT',
            'state': 'TEXT',
            'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP'
        }
        
        result = self.db.create_table('leads', leads_schema)
        if not result.success:
            raise Exception(f"Failed to create leads table: {result.error_message}")
    
    def add_lead(self, lead_data: Dict[str, Any]) -> QueryResult:
        """Add a new lead (with input validation)"""
        from .validators import validator
        
        # Validate input data
        validation_rules = {
            'business_name': {'type': 'string', 'min_length': 1, 'max_length': 200},
            'email': {'type': 'email'} if lead_data.get('email') else None,
            'website': {'type': 'url'} if lead_data.get('website') else None,
            'phone': {'type': 'string', 'max_length': 20} if lead_data.get('phone') else None,
        }
        
        # Remove None values from validation rules
        validation_rules = {k: v for k, v in validation_rules.items() if v is not None}
        
        validation_results = validator.validate_batch(lead_data, validation_rules)
        
        # Check for validation errors
        for field_name, result in validation_results.items():
            if not result.is_valid:
                return QueryResult(
                    success=False,
                    error_message=f"Validation failed for {field_name}: {', '.join(result.errors)}"
                )
        
        # Use sanitized values
        clean_data = {}
        for field_name, result in validation_results.items():
            clean_data[field_name] = result.sanitized_value
        
        # Add any fields that weren't validated
        for key, value in lead_data.items():
            if key not in clean_data and key in ['address', 'city', 'state']:
                # Basic sanitization for unvalidated fields
                clean_data[key] = str(value).strip() if value else None
        
        return self.db.insert('leads', clean_data)
    
    def get_leads(self, filters: Optional[Dict[str, Any]] = None) -> QueryResult:
        """Get leads with optional filters"""
        return self.db.select('leads', where_conditions=filters, order_by='created_at DESC')
    
    def update_lead(self, lead_id: int, update_data: Dict[str, Any]) -> QueryResult:
        """Update an existing lead"""
        # Add timestamp
        update_data['updated_at'] = datetime.now().isoformat()
        
        return self.db.update('leads', update_data, {'id': lead_id})
    
    def delete_lead(self, lead_id: int) -> QueryResult:
        """Delete a lead"""
        return self.db.delete('leads', {'id': lead_id})
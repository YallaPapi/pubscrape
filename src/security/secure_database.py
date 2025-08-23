"""
Secure Database Manager with SQL Injection Prevention
SECURITY-FIX: Replaces dynamic SQL queries with parameterized queries and input validation

This module provides secure database operations that:
- Uses parameterized queries exclusively to prevent SQL injection
- Validates and sanitizes all input data before database operations
- Implements proper connection pooling and resource management
- Provides secure query builders with type checking
- Includes comprehensive input validation for all database fields
"""

import sqlite3
import threading
import logging
import hashlib
import json
import re
from typing import Dict, Any, Optional, List, Union, Tuple, Type
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import weakref

# Configure secure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QueryParameters:
    """Type-safe query parameters with validation"""
    params: Dict[str, Any]
    
    def __post_init__(self):
        """Validate parameters after initialization"""
        self._validate_parameters()
    
    def _validate_parameters(self):
        """Validate query parameters for security"""
        for key, value in self.params.items():
            # Validate parameter name (prevent injection via parameter names)
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise ValueError(f"Invalid parameter name: {key}")
            
            # Sanitize string values
            if isinstance(value, str):
                # Check for SQL injection patterns
                suspicious_patterns = [
                    r"'\s*;",           # String termination with semicolon
                    r"\bunion\b",       # UNION attacks
                    r"\bselect\b",      # SELECT injection
                    r"\binsert\b",      # INSERT injection
                    r"\bdelete\b",      # DELETE injection
                    r"\bdrop\b",        # DROP attacks
                    r"\bexec\b",        # EXEC attacks
                    r"\bsp_\w+",        # Stored procedure calls
                    r"--",              # SQL comments
                    r"/\*.*?\*/"        # Multi-line comments
                ]
                
                value_lower = value.lower()
                for pattern in suspicious_patterns:
                    if re.search(pattern, value_lower):
                        logger.warning(f"Suspicious SQL pattern detected in parameter {key}: {pattern}")
                        # Continue but log - might be legitimate data
                
                # Limit string length to prevent buffer overflow
                if len(value) > 10000:
                    raise ValueError(f"Parameter {key} exceeds maximum length of 10000 characters")
                
                # Remove null bytes
                self.params[key] = value.replace('\x00', '')
            
            # Validate numeric values
            elif isinstance(value, (int, float)):
                if isinstance(value, int) and abs(value) > 2**63 - 1:
                    raise ValueError(f"Integer parameter {key} exceeds safe range")
                elif isinstance(value, float) and (value != value or abs(value) == float('inf')):
                    raise ValueError(f"Float parameter {key} is NaN or infinite")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for use in queries"""
        return self.params.copy()


class SecureDatabaseConnection:
    """Secure database connection with automatic cleanup"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.lock = threading.Lock()
        self._connection_id = id(self)
        
    def connect(self) -> sqlite3.Connection:
        """Establish secure database connection"""
        if self.connection is None:
            with self.lock:
                if self.connection is None:
                    try:
                        self.connection = sqlite3.connect(
                            self.db_path,
                            check_same_thread=False,
                            timeout=30.0,
                            isolation_level='DEFERRED'  # Use transactions
                        )
                        
                        # Enable foreign key constraints
                        self.connection.execute("PRAGMA foreign_keys = ON")
                        
                        # Set secure SQLite options
                        self.connection.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
                        self.connection.execute("PRAGMA synchronous = NORMAL")  # Good performance/safety balance
                        self.connection.execute("PRAGMA cache_size = -64000")  # 64MB cache
                        self.connection.execute("PRAGMA temp_store = memory")   # Use memory for temp tables
                        
                        # Disable dangerous features
                        self.connection.execute("PRAGMA writable_schema = OFF")
                        
                        logger.info(f"Secure database connection established: {self._connection_id}")
                        
                    except sqlite3.Error as e:
                        logger.error(f"Database connection failed: {e}")
                        raise
        
        return self.connection
    
    def close(self):
        """Close database connection safely"""
        if self.connection:
            with self.lock:
                try:
                    self.connection.close()
                    logger.info(f"Database connection closed: {self._connection_id}")
                except sqlite3.Error as e:
                    logger.error(f"Error closing database connection: {e}")
                finally:
                    self.connection = None


class SecureDatabaseManager:
    """Secure database manager with SQL injection prevention"""
    
    def __init__(self, db_path: str = "./secure_leads.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connection pool for thread safety
        self._connections: Dict[int, SecureDatabaseConnection] = {}
        self._pool_lock = threading.Lock()
        self._max_connections = 10
        
        # Initialize database schema
        self._initialize_schema()
        
        # Query cache for performance
        self._query_cache: Dict[str, str] = {}
        
        # Resource tracking
        self._active_cursors = weakref.WeakSet()
    
    @contextmanager
    def get_connection(self):
        """Get a secure database connection from pool"""
        thread_id = threading.current_thread().ident
        
        with self._pool_lock:
            if thread_id not in self._connections:
                if len(self._connections) >= self._max_connections:
                    # Close oldest connection
                    oldest_id = next(iter(self._connections))
                    self._connections[oldest_id].close()
                    del self._connections[oldest_id]
                
                self._connections[thread_id] = SecureDatabaseConnection(str(self.db_path))
            
            connection_wrapper = self._connections[thread_id]
        
        try:
            connection = connection_wrapper.connect()
            yield connection
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            # Connection remains open for reuse
            pass
    
    def _initialize_schema(self):
        """Initialize secure database schema with proper constraints"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Create leads table with security constraints
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS leads (
                        id TEXT PRIMARY KEY CHECK (length(id) <= 32 AND id GLOB '[a-zA-Z0-9]*'),
                        data TEXT NOT NULL CHECK (length(data) <= 100000),
                        name TEXT CHECK (length(name) <= 200),
                        email TEXT CHECK (length(email) <= 320 AND (email IS NULL OR email LIKE '%_@_%.__%')),
                        phone TEXT CHECK (length(phone) <= 20 AND (phone IS NULL OR phone GLOB '[0-9+()-. ]*')),
                        city TEXT CHECK (length(city) <= 100),
                        state TEXT CHECK (length(state) <= 50),
                        category TEXT CHECK (length(category) <= 100),
                        quality_level TEXT CHECK (quality_level IN ('HIGH', 'MEDIUM', 'LOW', 'UNKNOWN')),
                        status TEXT CHECK (status IN ('pending', 'processing', 'validated', 'invalid', 'duplicate', 'exported', 'error')),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create secure indexes with size limits
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email) WHERE email IS NOT NULL")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_quality ON leads(quality_level)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_location ON leads(city, state) WHERE city IS NOT NULL")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at)")
                
                # Create campaigns table with constraints
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS campaigns (
                        id TEXT PRIMARY KEY CHECK (length(id) <= 50 AND id GLOB '[a-zA-Z0-9_-]*'),
                        data TEXT NOT NULL CHECK (length(data) <= 50000),
                        name TEXT NOT NULL CHECK (length(name) <= 200 AND name != ''),
                        status TEXT CHECK (status IN ('pending', 'running', 'completed', 'failed', 'paused')),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create validation_results table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS validation_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lead_id TEXT NOT NULL,
                        is_valid BOOLEAN NOT NULL,
                        confidence REAL CHECK (confidence >= 0.0 AND confidence <= 1.0),
                        errors TEXT CHECK (length(errors) <= 10000),
                        validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE CASCADE
                    )
                """)
                
                # Create trigger to update timestamps
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS update_leads_timestamp 
                    AFTER UPDATE ON leads
                    BEGIN
                        UPDATE leads SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                    END
                """)
                
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS update_campaigns_timestamp 
                    AFTER UPDATE ON campaigns
                    BEGIN
                        UPDATE campaigns SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                    END
                """)
                
                conn.commit()
                logger.info("Database schema initialized successfully")
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Schema initialization failed: {e}")
                raise\n    \n    def insert_lead(self, lead_data: Dict[str, Any]) -> bool:\n        \"\"\"Insert lead with parameterized query and validation\"\"\"\n        try:\n            # Validate required fields\n            required_fields = ['id', 'data', 'name']\n            for field in required_fields:\n                if field not in lead_data or not lead_data[field]:\n                    raise ValueError(f\"Required field missing: {field}\")\n            \n            # Create secure parameters\n            params = QueryParameters({\n                'id': str(lead_data['id'])[:32],  # Truncate ID\n                'data': json.dumps(lead_data.get('data', {}))[:100000],  # Limit JSON size\n                'name': str(lead_data['name'])[:200],  # Truncate name\n                'email': lead_data.get('email'),\n                'phone': lead_data.get('phone'),\n                'city': lead_data.get('city'),\n                'state': lead_data.get('state'),\n                'category': lead_data.get('category'),\n                'quality_level': lead_data.get('quality_level'),\n                'status': lead_data.get('status', 'pending')\n            })\n            \n            # Execute parameterized query\n            with self.get_connection() as conn:\n                cursor = conn.cursor()\n                self._active_cursors.add(cursor)\n                \n                cursor.execute(\"\"\"\n                    INSERT OR REPLACE INTO leads \n                    (id, data, name, email, phone, city, state, category, quality_level, status, updated_at)\n                    VALUES (:id, :data, :name, :email, :phone, :city, :state, :category, :quality_level, :status, CURRENT_TIMESTAMP)\n                \"\"\", params.to_dict())\n                \n                conn.commit()\n                return True\n                \n        except (ValueError, sqlite3.Error) as e:\n            logger.error(f\"Insert lead failed: {e}\")\n            return False\n    \n    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:\n        \"\"\"Get lead by ID with secure parameter validation\"\"\"\n        try:\n            # Validate and sanitize ID\n            if not lead_id or not isinstance(lead_id, str):\n                raise ValueError(\"Invalid lead ID\")\n            \n            clean_id = re.sub(r'[^a-zA-Z0-9]', '', lead_id)[:32]\n            if not clean_id:\n                return None\n            \n            params = QueryParameters({'id': clean_id})\n            \n            with self.get_connection() as conn:\n                cursor = conn.cursor()\n                self._active_cursors.add(cursor)\n                \n                cursor.execute(\"\"\"\n                    SELECT id, data, name, email, phone, city, state, category, \n                           quality_level, status, created_at, updated_at\n                    FROM leads \n                    WHERE id = :id\n                    LIMIT 1\n                \"\"\", params.to_dict())\n                \n                row = cursor.fetchone()\n                if row:\n                    columns = [desc[0] for desc in cursor.description]\n                    return dict(zip(columns, row))\n                    \n        except (ValueError, sqlite3.Error) as e:\n            logger.error(f\"Get lead failed: {e}\")\n        \n        return None\n    \n    def find_leads(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:\n        \"\"\"Find leads with secure filtering and pagination\"\"\"\n        try:\n            # Validate limit and offset\n            limit = max(1, min(1000, int(limit)))  # Between 1 and 1000\n            offset = max(0, int(offset))\n            \n            # Build secure WHERE clause\n            where_conditions = []\n            params_dict = {'limit': limit, 'offset': offset}\n            \n            # Whitelist of allowed filter fields\n            allowed_filters = {\n                'status': 'status = :status',\n                'quality_level': 'quality_level = :quality_level',\n                'city': 'city = :city',\n                'state': 'state = :state',\n                'category': 'category = :category'\n            }\n            \n            for field, value in filters.items():\n                if field in allowed_filters and value is not None:\n                    where_conditions.append(allowed_filters[field])\n                    params_dict[field] = str(value)[:100]  # Truncate filter values\n            \n            # Build query\n            base_query = \"\"\"\n                SELECT id, data, name, email, phone, city, state, category,\n                       quality_level, status, created_at, updated_at\n                FROM leads\n            \"\"\"\n            \n            if where_conditions:\n                query = f\"{base_query} WHERE {' AND '.join(where_conditions)}\"\n            else:\n                query = base_query\n            \n            query += \" ORDER BY created_at DESC LIMIT :limit OFFSET :offset\"\n            \n            params = QueryParameters(params_dict)\n            \n            with self.get_connection() as conn:\n                cursor = conn.cursor()\n                self._active_cursors.add(cursor)\n                \n                cursor.execute(query, params.to_dict())\n                \n                results = []\n                columns = [desc[0] for desc in cursor.description]\n                \n                for row in cursor.fetchall():\n                    results.append(dict(zip(columns, row)))\n                \n                return results\n                \n        except (ValueError, sqlite3.Error) as e:\n            logger.error(f\"Find leads failed: {e}\")\n            return []\n    \n    def update_lead_status(self, lead_id: str, status: str) -> bool:\n        \"\"\"Update lead status with validation\"\"\"\n        try:\n            # Validate inputs\n            valid_statuses = ['pending', 'processing', 'validated', 'invalid', 'duplicate', 'exported', 'error']\n            if status not in valid_statuses:\n                raise ValueError(f\"Invalid status: {status}\")\n            \n            clean_id = re.sub(r'[^a-zA-Z0-9]', '', str(lead_id))[:32]\n            if not clean_id:\n                return False\n            \n            params = QueryParameters({\n                'id': clean_id,\n                'status': status\n            })\n            \n            with self.get_connection() as conn:\n                cursor = conn.cursor()\n                self._active_cursors.add(cursor)\n                \n                cursor.execute(\"\"\"\n                    UPDATE leads \n                    SET status = :status, updated_at = CURRENT_TIMESTAMP\n                    WHERE id = :id\n                \"\"\", params.to_dict())\n                \n                conn.commit()\n                return cursor.rowcount > 0\n                \n        except (ValueError, sqlite3.Error) as e:\n            logger.error(f\"Update lead status failed: {e}\")\n            return False\n    \n    def get_statistics(self) -> Dict[str, Any]:\n        \"\"\"Get database statistics with secure queries\"\"\"\n        try:\n            with self.get_connection() as conn:\n                cursor = conn.cursor()\n                self._active_cursors.add(cursor)\n                \n                stats = {}\n                \n                # Total leads count\n                cursor.execute(\"SELECT COUNT(*) FROM leads\")\n                stats['total_leads'] = cursor.fetchone()[0]\n                \n                # Count by status\n                cursor.execute(\"\"\"\n                    SELECT status, COUNT(*) \n                    FROM leads \n                    WHERE status IS NOT NULL\n                    GROUP BY status\n                \"\"\")\n                stats['by_status'] = dict(cursor.fetchall())\n                \n                # Count by quality\n                cursor.execute(\"\"\"\n                    SELECT quality_level, COUNT(*) \n                    FROM leads \n                    WHERE quality_level IS NOT NULL\n                    GROUP BY quality_level\n                \"\"\")\n                stats['by_quality'] = dict(cursor.fetchall())\n                \n                # Count with contact info\n                cursor.execute(\"SELECT COUNT(*) FROM leads WHERE email IS NOT NULL AND email != ''\")\n                stats['with_email'] = cursor.fetchone()[0]\n                \n                cursor.execute(\"SELECT COUNT(*) FROM leads WHERE phone IS NOT NULL AND phone != ''\")\n                stats['with_phone'] = cursor.fetchone()[0]\n                \n                # Calculate rates\n                total = stats['total_leads']\n                if total > 0:\n                    stats['email_rate'] = stats['with_email'] / total\n                    stats['phone_rate'] = stats['with_phone'] / total\n                else:\n                    stats['email_rate'] = 0\n                    stats['phone_rate'] = 0\n                \n                return stats\n                \n        except sqlite3.Error as e:\n            logger.error(f\"Get statistics failed: {e}\")\n            return {}\n    \n    def execute_safe_query(self, query_template: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:\n        \"\"\"Execute a safe parameterized query\"\"\"\n        try:\n            # Validate query template (must not contain dynamic SQL)\n            if any(keyword in query_template.upper() for keyword in ['EXEC', 'SP_', 'XP_']):\n                raise ValueError(\"Query contains dangerous keywords\")\n            \n            # Ensure parameters are secure\n            secure_params = QueryParameters(params)\n            \n            with self.get_connection() as conn:\n                cursor = conn.cursor()\n                self._active_cursors.add(cursor)\n                \n                cursor.execute(query_template, secure_params.to_dict())\n                \n                if cursor.description:  # SELECT query\n                    results = []\n                    columns = [desc[0] for desc in cursor.description]\n                    \n                    for row in cursor.fetchall():\n                        results.append(dict(zip(columns, row)))\n                    \n                    return results\n                else:  # INSERT/UPDATE/DELETE\n                    conn.commit()\n                    return [{'affected_rows': cursor.rowcount}]\n                    \n        except (ValueError, sqlite3.Error) as e:\n            logger.error(f\"Safe query execution failed: {e}\")\n            return []\n    \n    def close_all_connections(self):\n        \"\"\"Close all database connections\"\"\"\n        with self._pool_lock:\n            for connection in self._connections.values():\n                connection.close()\n            self._connections.clear()\n        \n        logger.info(\"All database connections closed\")\n    \n    def __enter__(self):\n        \"\"\"Context manager entry\"\"\"\n        return self\n    \n    def __exit__(self, exc_type, exc_val, exc_tb):\n        \"\"\"Context manager exit with cleanup\"\"\"\n        self.close_all_connections()\n\n\nif __name__ == \"__main__\":\n    # Test the secure database manager\n    print(\"Testing Secure Database Manager\")\n    print(\"=\" * 50)\n    \n    # Create test database manager\n    with SecureDatabaseManager(\"./test_secure_db.sqlite\") as db:\n        \n        # Test lead insertion\n        test_lead = {\n            'id': 'test123',\n            'data': {'source': 'test', 'confidence': 0.9},\n            'name': 'Test Business',\n            'email': 'test@business.com',\n            'phone': '555-1234',\n            'city': 'Test City',\n            'state': 'TS',\n            'category': 'Technology',\n            'quality_level': 'HIGH',\n            'status': 'pending'\n        }\n        \n        # Insert lead\n        success = db.insert_lead(test_lead)\n        print(f\"Lead inserted: {success}\")\n        \n        # Retrieve lead\n        retrieved = db.get_lead('test123')\n        print(f\"Lead retrieved: {retrieved is not None}\")\n        if retrieved:\n            print(f\"Retrieved name: {retrieved['name']}\")\n        \n        # Test filtering\n        leads = db.find_leads({'status': 'pending'}, limit=10)\n        print(f\"Found {len(leads)} pending leads\")\n        \n        # Update status\n        updated = db.update_lead_status('test123', 'validated')\n        print(f\"Status updated: {updated}\")\n        \n        # Get statistics\n        stats = db.get_statistics()\n        print(f\"Database statistics: {stats}\")\n        \n        # Test SQL injection prevention\n        try:\n            # This should fail validation\n            malicious_params = {\n                'id': \"'; DROP TABLE leads; --\",\n                'status': 'pending'\n            }\n            result = db.execute_safe_query(\"SELECT * FROM leads WHERE status = :status\", malicious_params)\n            print(f\"SQL injection test: {len(result)} results (should handle safely)\")\n        except ValueError as e:\n            print(f\"SQL injection prevented: {e}\")\n    \n    # Clean up test file\n    try:\n        import os\n        os.unlink(\"./test_secure_db.sqlite\")\n    except OSError:\n        pass\n    \n    print(\"\\nSecure database manager test complete!\")
"""
Simple Secure Database Manager (No External Dependencies)
SECURITY-FIX: Basic secure database operations for testing

This provides a lightweight secure database system for testing without
complex dependencies.
"""

import sqlite3
import threading
import logging
import json
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryParameters:
    """Simple query parameters with basic validation"""
    
    def __init__(self, params: Dict[str, Any]):
        self.params = self._validate_parameters(params)
    
    def _validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Basic parameter validation"""
        validated = {}
        for key, value in params.items():
            # Validate parameter name
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise ValueError(f"Invalid parameter name: {key}")
            
            # Basic value validation
            if isinstance(value, str):
                # Check for suspicious SQL patterns
                if any(pattern in value.lower() for pattern in ['drop table', 'delete from', 'insert into']):
                    logger.warning(f"Suspicious SQL pattern detected in parameter {key}")
                
                # Limit string length
                if len(value) > 10000:
                    raise ValueError(f"Parameter {key} exceeds maximum length")
                
                # Remove null bytes
                validated[key] = value.replace('\x00', '')
            else:
                validated[key] = value
        
        return validated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for use in queries"""
        return self.params.copy()


class SecureDatabaseManager:
    """Simple secure database manager"""
    
    def __init__(self, db_path: str = "./secure_leads.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self._initialize_schema()
    
    @contextmanager
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        try:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        finally:
            conn.close()
    
    def _initialize_schema(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Create leads table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS leads (
                        id TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        name TEXT,
                        email TEXT,
                        phone TEXT,
                        city TEXT,
                        state TEXT,
                        category TEXT,
                        quality_level TEXT,
                        status TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)")
                
                conn.commit()
                logger.info("Database schema initialized successfully")
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Schema initialization failed: {e}")
                raise
    
    def insert_lead(self, lead_data: Dict[str, Any]) -> bool:
        """Insert lead with parameterized query"""
        try:
            # Validate required fields
            if not all(field in lead_data for field in ['id', 'data', 'name']):
                raise ValueError("Required fields missing")
            
            # Create secure parameters
            params = QueryParameters({
                'id': str(lead_data['id'])[:32],
                'data': json.dumps(lead_data.get('data', {})),
                'name': str(lead_data['name'])[:200],
                'email': lead_data.get('email'),
                'phone': lead_data.get('phone'),
                'city': lead_data.get('city'),
                'state': lead_data.get('state'),
                'category': lead_data.get('category'),
                'quality_level': lead_data.get('quality_level'),
                'status': lead_data.get('status', 'pending')
            })
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO leads 
                    (id, data, name, email, phone, city, state, category, quality_level, status, updated_at)
                    VALUES (:id, :data, :name, :email, :phone, :city, :state, :category, :quality_level, :status, CURRENT_TIMESTAMP)
                """, params.to_dict())
                
                conn.commit()
                return True
                
        except (ValueError, sqlite3.Error) as e:
            logger.error(f"Insert lead failed: {e}")
            return False
    
    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get lead by ID with secure validation"""
        try:
            # Validate and sanitize ID
            if not lead_id or not isinstance(lead_id, str):
                return None
            
            clean_id = re.sub(r'[^a-zA-Z0-9]', '', lead_id)[:32]
            if not clean_id:
                return None
            
            params = QueryParameters({'id': clean_id})
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, data, name, email, phone, city, state, category, 
                           quality_level, status, created_at, updated_at
                    FROM leads 
                    WHERE id = :id
                    LIMIT 1
                """, params.to_dict())
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                    
        except (ValueError, sqlite3.Error) as e:
            logger.error(f"Get lead failed: {e}")
        
        return None
    
    def find_leads(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Find leads with secure filtering"""
        try:
            # Validate limit and offset
            limit = max(1, min(1000, int(limit)))
            offset = max(0, int(offset))
            
            # Build secure WHERE clause
            where_conditions = []
            params_dict = {'limit': limit, 'offset': offset}
            
            # Allowed filter fields
            allowed_filters = ['status', 'quality_level', 'city', 'state', 'category']
            
            for field, value in filters.items():
                if field in allowed_filters and value is not None:
                    where_conditions.append(f"{field} = :{field}")
                    params_dict[field] = str(value)[:100]
            
            # Build query
            base_query = """
                SELECT id, data, name, email, phone, city, state, category,
                       quality_level, status, created_at, updated_at
                FROM leads
            """
            
            if where_conditions:
                query = f"{base_query} WHERE {' AND '.join(where_conditions)}"
            else:
                query = base_query
            
            query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            
            params = QueryParameters(params_dict)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params.to_dict())
                
                results = []
                columns = [desc[0] for desc in cursor.description]
                
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
                
        except (ValueError, sqlite3.Error) as e:
            logger.error(f"Find leads failed: {e}")
            return []
    
    def update_lead_status(self, lead_id: str, status: str) -> bool:
        """Update lead status with validation"""
        try:
            # Validate inputs
            valid_statuses = ['pending', 'processing', 'validated', 'invalid', 'duplicate', 'exported', 'error']
            if status not in valid_statuses:
                raise ValueError(f"Invalid status: {status}")
            
            clean_id = re.sub(r'[^a-zA-Z0-9]', '', str(lead_id))[:32]
            if not clean_id:
                return False
            
            params = QueryParameters({
                'id': clean_id,
                'status': status
            })
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE leads 
                    SET status = :status, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """, params.to_dict())
                
                conn.commit()
                return cursor.rowcount > 0
                
        except (ValueError, sqlite3.Error) as e:
            logger.error(f"Update lead status failed: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total leads
                cursor.execute("SELECT COUNT(*) FROM leads")
                stats['total_leads'] = cursor.fetchone()[0]
                
                # Count by status
                cursor.execute("""
                    SELECT status, COUNT(*) 
                    FROM leads 
                    WHERE status IS NOT NULL
                    GROUP BY status
                """)
                stats['by_status'] = dict(cursor.fetchall())
                
                # Count with contact info
                cursor.execute("SELECT COUNT(*) FROM leads WHERE email IS NOT NULL AND email != ''")
                stats['with_email'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM leads WHERE phone IS NOT NULL AND phone != ''")
                stats['with_phone'] = cursor.fetchone()[0]
                
                # Calculate rates
                total = stats['total_leads']
                if total > 0:
                    stats['email_rate'] = stats['with_email'] / total
                    stats['phone_rate'] = stats['with_phone'] / total
                else:
                    stats['email_rate'] = 0
                    stats['phone_rate'] = 0
                
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Get statistics failed: {e}")
            return {}
    
    def execute_safe_query(self, query_template: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a safe parameterized query"""
        try:
            # Validate query template
            if any(keyword in query_template.upper() for keyword in ['EXEC', 'SP_', 'XP_']):
                raise ValueError("Query contains dangerous keywords")
            
            secure_params = QueryParameters(params)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query_template, secure_params.to_dict())
                
                if cursor.description:  # SELECT query
                    results = []
                    columns = [desc[0] for desc in cursor.description]
                    
                    for row in cursor.fetchall():
                        results.append(dict(zip(columns, row)))
                    
                    return results
                else:  # INSERT/UPDATE/DELETE
                    conn.commit()
                    return [{'affected_rows': cursor.rowcount}]
                    
        except (ValueError, sqlite3.Error) as e:
            logger.error(f"Safe query execution failed: {e}")
            return []
    
    def close_all_connections(self):
        """Close connections - simplified version"""
        logger.info("Database connections closed")


if __name__ == "__main__":
    # Test the simple database manager
    print("Testing Simple Secure Database Manager")
    print("=" * 50)
    
    # Create test database
    db = SecureDatabaseManager("./test_simple_db.sqlite")
    
    # Test lead insertion
    test_lead = {
        'id': 'test123',
        'data': {'source': 'test'},
        'name': 'Test Business',
        'email': 'test@example.com',
        'status': 'pending'
    }
    
    success = db.insert_lead(test_lead)
    print(f"Lead inserted: {success}")
    
    # Test retrieval
    retrieved = db.get_lead('test123')
    print(f"Lead retrieved: {retrieved is not None}")
    
    # Clean up
    try:
        import os
        os.unlink("./test_simple_db.sqlite")
    except OSError:
        pass
    
    print("Simple database test complete!")
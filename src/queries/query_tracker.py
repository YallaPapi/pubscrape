"""
Query Tracker - Track processed queries, results, and performance metrics

Features:
- Track query execution history
- Store query results and metadata
- Performance metrics and analytics
- Duplicate query detection
- Query effectiveness scoring
- Export results to various formats
"""
import json
import logging
import sqlite3
import threading
from typing import Dict, List, Optional, Set, Union, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import statistics
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Represents the result of a processed query"""
    query_id: str
    query: str
    engine: str
    location: Optional[str] = None
    business_type: Optional[str] = None
    category: Optional[str] = None
    
    # Execution details
    executed_at: datetime = field(default_factory=datetime.now)
    processing_time: float = 0.0
    status: str = "completed"
    
    # Results
    result_count: int = 0
    unique_results: int = 0
    businesses_found: List[Dict[str, Any]] = field(default_factory=list)
    
    # Quality metrics
    relevance_score: float = 0.0
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    overall_score: float = 0.0
    
    # Error tracking
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Calculate derived metrics"""
        if self.result_count > 0 and self.overall_score == 0.0:
            self.calculate_overall_score()
    
    def calculate_overall_score(self):
        """Calculate overall effectiveness score"""
        # Weight different aspects
        weights = {
            'relevance': 0.4,
            'completeness': 0.3,
            'accuracy': 0.3
        }
        
        self.overall_score = (
            self.relevance_score * weights['relevance'] +
            self.completeness_score * weights['completeness'] + 
            self.accuracy_score * weights['accuracy']
        )
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate (0-1)"""
        if self.status == "completed" and self.result_count > 0:
            return min(1.0, self.result_count / 50)  # Assume 50 is good result count
        return 0.0
    
    @property
    def query_hash(self) -> str:
        """Generate hash for duplicate detection"""
        content = f"{self.query.lower()}|{self.engine}|{self.location or ''}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class QueryAnalytics:
    """Analytics data for query performance"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    
    # Performance metrics
    avg_processing_time: float = 0.0
    avg_result_count: float = 0.0
    avg_score: float = 0.0
    
    # Time-based metrics
    queries_per_hour: float = 0.0
    queries_per_day: float = 0.0
    
    # Engine performance
    engine_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Category performance
    category_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Location performance
    location_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)


class QueryTracker:
    """
    Track and analyze query execution results
    """
    
    def __init__(self, db_path: str = "data/query_tracker.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # In-memory caches
        self._recent_queries: Dict[str, QueryResult] = {}
        self._query_hashes: Set[str] = set()
        
        # Initialize database
        self._init_database()
        
        # Load recent queries into cache (only if tables exist)
        try:
            self._load_recent_queries()
        except Exception as e:
            logger.debug(f"Could not load recent queries (expected for new database): {e}")
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            # Main query results table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS query_results (
                    query_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    location TEXT,
                    business_type TEXT,
                    category TEXT,
                    executed_at TIMESTAMP NOT NULL,
                    processing_time REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'completed',
                    result_count INTEGER DEFAULT 0,
                    unique_results INTEGER DEFAULT 0,
                    relevance_score REAL DEFAULT 0.0,
                    completeness_score REAL DEFAULT 0.0,
                    accuracy_score REAL DEFAULT 0.0,
                    overall_score REAL DEFAULT 0.0,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    tags TEXT,
                    notes TEXT,
                    query_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Business results table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS business_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id TEXT NOT NULL,
                    business_name TEXT,
                    business_address TEXT,
                    business_phone TEXT,
                    business_website TEXT,
                    business_email TEXT,
                    business_category TEXT,
                    latitude REAL,
                    longitude REAL,
                    rating REAL,
                    review_count INTEGER,
                    source_url TEXT,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (query_id) REFERENCES query_results (query_id)
                )
            ''')
            
            # Query patterns table for learning
            conn.execute('''
                CREATE TABLE IF NOT EXISTS query_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    avg_result_count REAL DEFAULT 0.0,
                    avg_score REAL DEFAULT 0.0,
                    usage_count INTEGER DEFAULT 0,
                    last_used TIMESTAMP,
                    effectiveness_rank INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Performance metrics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_date DATE NOT NULL,
                    engine TEXT,
                    category TEXT,
                    location TEXT,
                    query_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    avg_processing_time REAL DEFAULT 0.0,
                    avg_result_count REAL DEFAULT 0.0,
                    avg_score REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_query_executed_at ON query_results(executed_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_query_engine ON query_results(engine)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_query_category ON query_results(category)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_query_hash ON query_results(query_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_business_query_id ON business_results(query_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_metrics_date ON performance_metrics(metric_date)')
            
            conn.commit()
            logger.info(f"Initialized query tracker database: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _load_recent_queries(self, days: int = 7):
        """Load recent queries into memory cache"""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM query_results 
                WHERE executed_at > ? 
                ORDER BY executed_at DESC
            ''', (cutoff,))
            
            for row in cursor:
                result = self._row_to_query_result(row)
                self._recent_queries[result.query_id] = result
                self._query_hashes.add(result.query_hash)
        
        logger.info(f"Loaded {len(self._recent_queries)} recent queries into cache")
    
    def _row_to_query_result(self, row: sqlite3.Row) -> QueryResult:
        """Convert database row to QueryResult object"""
        # Parse tags
        tags = []
        if row['tags']:
            try:
                tags = json.loads(row['tags'])
            except:
                tags = []
        
        return QueryResult(
            query_id=row['query_id'],
            query=row['query'],
            engine=row['engine'],
            location=row['location'],
            business_type=row['business_type'],
            category=row['category'],
            executed_at=datetime.fromisoformat(row['executed_at']),
            processing_time=row['processing_time'] or 0.0,
            status=row['status'],
            result_count=row['result_count'] or 0,
            unique_results=row['unique_results'] or 0,
            relevance_score=row['relevance_score'] or 0.0,
            completeness_score=row['completeness_score'] or 0.0,
            accuracy_score=row['accuracy_score'] or 0.0,
            overall_score=row['overall_score'] or 0.0,
            error_message=row['error_message'],
            retry_count=row['retry_count'] or 0,
            tags=tags,
            notes=row['notes']
        )
    
    def track_query(self, result: QueryResult) -> bool:
        """
        Track a query result
        
        Args:
            result: QueryResult object to track
            
        Returns:
            True if tracked successfully, False if duplicate
        """
        with self._lock:
            # Check for duplicates
            if result.query_hash in self._query_hashes:
                logger.debug(f"Duplicate query hash detected: {result.query}")
                return False
            
            try:
                with self._get_connection() as conn:
                    # Insert query result
                    conn.execute('''
                        INSERT INTO query_results (
                            query_id, query, engine, location, business_type, category,
                            executed_at, processing_time, status, result_count, unique_results,
                            relevance_score, completeness_score, accuracy_score, overall_score,
                            error_message, retry_count, tags, notes, query_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result.query_id, result.query, result.engine, result.location,
                        result.business_type, result.category, result.executed_at.isoformat(),
                        result.processing_time, result.status, result.result_count,
                        result.unique_results, result.relevance_score, result.completeness_score,
                        result.accuracy_score, result.overall_score, result.error_message,
                        result.retry_count, json.dumps(result.tags), result.notes, result.query_hash
                    ))
                    
                    # Insert business results if any
                    if result.businesses_found:
                        self._insert_business_results(conn, result)
                    
                    conn.commit()
                
                # Update cache
                self._recent_queries[result.query_id] = result
                self._query_hashes.add(result.query_hash)
                
                logger.debug(f"Tracked query result: {result.query_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to track query result: {e}")
                return False
    
    def _insert_business_results(self, conn: sqlite3.Connection, result: QueryResult):
        """Insert business results for a query"""
        for business in result.businesses_found:
            conn.execute('''
                INSERT INTO business_results (
                    query_id, business_name, business_address, business_phone,
                    business_website, business_email, business_category,
                    latitude, longitude, rating, review_count, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.query_id,
                business.get('name'),
                business.get('address'),
                business.get('phone'),
                business.get('website'),
                business.get('email'),
                business.get('category'),
                business.get('latitude'),
                business.get('longitude'),
                business.get('rating'),
                business.get('review_count'),
                business.get('source_url')
            ))
    
    def is_duplicate(self, query: str, engine: str, location: Optional[str] = None) -> bool:
        """Check if a query is a duplicate"""
        query_hash = hashlib.md5(f"{query.lower()}|{engine}|{location or ''}".encode()).hexdigest()
        return query_hash in self._query_hashes
    
    def get_query_result(self, query_id: str) -> Optional[QueryResult]:
        """Get a specific query result"""
        # Check cache first
        if query_id in self._recent_queries:
            return self._recent_queries[query_id]
        
        # Query database
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT * FROM query_results WHERE query_id = ?', (query_id,))
            row = cursor.fetchone()
            
            if row:
                result = self._row_to_query_result(row)
                # Load business results
                business_cursor = conn.execute(
                    'SELECT * FROM business_results WHERE query_id = ?', (query_id,)
                )
                businesses = []
                for business_row in business_cursor:
                    businesses.append({
                        'name': business_row['business_name'],
                        'address': business_row['business_address'],
                        'phone': business_row['business_phone'],
                        'website': business_row['business_website'],
                        'email': business_row['business_email'],
                        'category': business_row['business_category'],
                        'latitude': business_row['latitude'],
                        'longitude': business_row['longitude'],
                        'rating': business_row['rating'],
                        'review_count': business_row['review_count'],
                        'source_url': business_row['source_url']
                    })
                result.businesses_found = businesses
                return result
        
        return None
    
    def get_query_history(self, limit: int = 100, engine: Optional[str] = None,
                         category: Optional[str] = None, days: Optional[int] = None) -> List[QueryResult]:
        """Get query history with optional filters"""
        conditions = []
        params = []
        
        if engine:
            conditions.append("engine = ?")
            params.append(engine)
        
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            conditions.append("executed_at > ?")
            params.append(cutoff.isoformat())
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        with self._get_connection() as conn:
            cursor = conn.execute(f'''
                SELECT * FROM query_results 
                {where_clause}
                ORDER BY executed_at DESC 
                LIMIT ?
            ''', params + [limit])
            
            results = []
            for row in cursor:
                results.append(self._row_to_query_result(row))
            
            return results
    
    def get_analytics(self, days: int = 30) -> QueryAnalytics:
        """Get analytics for the specified time period"""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._get_connection() as conn:
            # Basic stats
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_queries,
                    SUM(CASE WHEN status = 'completed' AND result_count > 0 THEN 1 ELSE 0 END) as successful_queries,
                    SUM(CASE WHEN status = 'failed' OR result_count = 0 THEN 1 ELSE 0 END) as failed_queries,
                    AVG(processing_time) as avg_processing_time,
                    AVG(CASE WHEN result_count > 0 THEN result_count ELSE NULL END) as avg_result_count,
                    AVG(CASE WHEN overall_score > 0 THEN overall_score ELSE NULL END) as avg_score
                FROM query_results 
                WHERE executed_at > ?
            ''', (cutoff.isoformat(),))
            
            row = cursor.fetchone()
            
            analytics = QueryAnalytics(
                total_queries=row['total_queries'] or 0,
                successful_queries=row['successful_queries'] or 0,
                failed_queries=row['failed_queries'] or 0,
                avg_processing_time=row['avg_processing_time'] or 0.0,
                avg_result_count=row['avg_result_count'] or 0.0,
                avg_score=row['avg_score'] or 0.0
            )
            
            # Calculate rates
            if analytics.total_queries > 0:
                analytics.queries_per_hour = analytics.total_queries / (days * 24)
                analytics.queries_per_day = analytics.total_queries / days
            
            # Engine stats
            cursor = conn.execute('''
                SELECT 
                    engine,
                    COUNT(*) as count,
                    AVG(processing_time) as avg_time,
                    AVG(CASE WHEN result_count > 0 THEN result_count ELSE NULL END) as avg_results,
                    AVG(CASE WHEN overall_score > 0 THEN overall_score ELSE NULL END) as avg_score,
                    SUM(CASE WHEN status = 'completed' AND result_count > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
                FROM query_results 
                WHERE executed_at > ?
                GROUP BY engine
            ''', (cutoff.isoformat(),))
            
            for row in cursor:
                analytics.engine_stats[row['engine']] = {
                    'count': row['count'],
                    'avg_time': row['avg_time'] or 0.0,
                    'avg_results': row['avg_results'] or 0.0,
                    'avg_score': row['avg_score'] or 0.0,
                    'success_rate': row['success_rate'] or 0.0
                }
            
            # Category stats
            cursor = conn.execute('''
                SELECT 
                    category,
                    COUNT(*) as count,
                    AVG(CASE WHEN result_count > 0 THEN result_count ELSE NULL END) as avg_results,
                    AVG(CASE WHEN overall_score > 0 THEN overall_score ELSE NULL END) as avg_score
                FROM query_results 
                WHERE executed_at > ? AND category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
                LIMIT 20
            ''', (cutoff.isoformat(),))
            
            for row in cursor:
                analytics.category_stats[row['category']] = {
                    'count': row['count'],
                    'avg_results': row['avg_results'] or 0.0,
                    'avg_score': row['avg_score'] or 0.0
                }
            
            return analytics
    
    def get_top_performing_queries(self, limit: int = 20, days: int = 30) -> List[Dict[str, Any]]:
        """Get top performing queries by score and result count"""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    query, engine, category, location,
                    AVG(overall_score) as avg_score,
                    AVG(result_count) as avg_results,
                    COUNT(*) as usage_count,
                    MAX(executed_at) as last_used
                FROM query_results 
                WHERE executed_at > ? AND status = 'completed' AND result_count > 0
                GROUP BY query, engine
                ORDER BY avg_score DESC, avg_results DESC
                LIMIT ?
            ''', (cutoff.isoformat(), limit))
            
            results = []
            for row in cursor:
                results.append({
                    'query': row['query'],
                    'engine': row['engine'],
                    'category': row['category'],
                    'location': row['location'],
                    'avg_score': row['avg_score'],
                    'avg_results': row['avg_results'],
                    'usage_count': row['usage_count'],
                    'last_used': row['last_used']
                })
            
            return results
    
    def get_low_performing_queries(self, limit: int = 20, days: int = 30) -> List[Dict[str, Any]]:
        """Get low performing queries that need optimization"""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    query, engine, category, location,
                    AVG(overall_score) as avg_score,
                    AVG(result_count) as avg_results,
                    COUNT(*) as usage_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failure_count
                FROM query_results 
                WHERE executed_at > ?
                GROUP BY query, engine
                HAVING avg_results < 5 OR avg_score < 0.3 OR failure_count > 0
                ORDER BY avg_score ASC, avg_results ASC
                LIMIT ?
            ''', (cutoff.isoformat(), limit))
            
            results = []
            for row in cursor:
                results.append({
                    'query': row['query'],
                    'engine': row['engine'],
                    'category': row['category'],
                    'location': row['location'],
                    'avg_score': row['avg_score'],
                    'avg_results': row['avg_results'],
                    'usage_count': row['usage_count'],
                    'failure_count': row['failure_count']
                })
            
            return results
    
    def export_results(self, output_file: str, format: str = "json", 
                      days: Optional[int] = None, engine: Optional[str] = None):
        """Export query results to file"""
        queries = self.get_query_history(limit=10000, engine=engine, days=days)
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump([asdict(q) for q in queries], f, indent=2, default=str)
        
        elif format.lower() == "csv":
            import csv
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                if queries:
                    writer = csv.DictWriter(f, fieldnames=asdict(queries[0]).keys())
                    writer.writeheader()
                    for query in queries:
                        row = asdict(query)
                        # Convert complex fields to strings
                        row['businesses_found'] = json.dumps(row['businesses_found'])
                        row['tags'] = json.dumps(row['tags'])
                        writer.writerow(row)
        
        logger.info(f"Exported {len(queries)} query results to {output_path}")
    
    def cleanup_old_data(self, days: int = 90):
        """Remove old query data to manage database size"""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._get_connection() as conn:
            # Remove old business results first (foreign key constraint)
            cursor = conn.execute('''
                DELETE FROM business_results 
                WHERE query_id IN (
                    SELECT query_id FROM query_results WHERE executed_at < ?
                )
            ''', (cutoff.isoformat(),))
            business_deleted = cursor.rowcount
            
            # Remove old query results
            cursor = conn.execute(
                'DELETE FROM query_results WHERE executed_at < ?', 
                (cutoff.isoformat(),)
            )
            queries_deleted = cursor.rowcount
            
            # Remove old performance metrics
            cursor = conn.execute(
                'DELETE FROM performance_metrics WHERE metric_date < ?',
                (cutoff.date(),)
            )
            metrics_deleted = cursor.rowcount
            
            conn.commit()
        
        logger.info(f"Cleaned up old data: {queries_deleted} queries, "
                   f"{business_deleted} business results, {metrics_deleted} metrics")
        
        # Update cache
        self._load_recent_queries()


# Convenience functions
def create_tracker(db_path: str = "data/query_tracker.db") -> QueryTracker:
    """Create a query tracker with default settings"""
    return QueryTracker(db_path)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    tracker = create_tracker()
    
    # Track a sample query
    result = QueryResult(
        query_id="test-123",
        query="restaurants near Seattle",
        engine="bing",
        location="Seattle, WA",
        category="restaurants",
        result_count=45,
        relevance_score=0.8,
        completeness_score=0.7,
        accuracy_score=0.9,
        processing_time=2.5
    )
    
    success = tracker.track_query(result)
    print(f"Tracked query: {success}")
    
    # Get analytics
    analytics = tracker.get_analytics(days=7)
    print(f"Analytics: {analytics.total_queries} total queries")
    
    # Get top performing queries
    top_queries = tracker.get_top_performing_queries(limit=5)
    print(f"Found {len(top_queries)} top performing queries")
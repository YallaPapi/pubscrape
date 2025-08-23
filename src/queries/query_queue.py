"""
Query Queue - Manage query queue with prioritization and processing tracking

Features:
- Priority-based queue management
- Query scheduling and batching
- Rate limiting and throttling
- Progress tracking and statistics
- Queue persistence and recovery
- Duplicate detection and filtering
"""
import heapq
import json
import logging
import threading
import time
from typing import Dict, List, Optional, Set, Union, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import pickle

logger = logging.getLogger(__name__)


class QueryStatus(Enum):
    """Query processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class QueuePriority(Enum):
    """Queue priority levels"""
    URGENT = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class QueuedQuery:
    """Represents a queued query with metadata"""
    id: str
    query: str
    engine: str
    priority: QueuePriority
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: QueryStatus = QueryStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    
    # Metadata
    category: Optional[str] = None
    location: Optional[str] = None
    business_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Results tracking
    result_count: int = 0
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    
    # Rate limiting
    rate_limit_group: Optional[str] = None
    delay_until: Optional[datetime] = None
    
    def __lt__(self, other):
        """For priority queue ordering"""
        # Lower priority number = higher priority
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        
        # If same priority, schedule time wins
        if self.scheduled_at and other.scheduled_at:
            return self.scheduled_at < other.scheduled_at
        elif self.scheduled_at:
            return True
        elif other.scheduled_at:
            return False
        
        # Finally, creation time
        return self.created_at < other.created_at
    
    @property
    def is_ready(self) -> bool:
        """Check if query is ready to process"""
        if self.status != QueryStatus.PENDING:
            return False
        
        now = datetime.now()
        
        # Check scheduling
        if self.scheduled_at and now < self.scheduled_at:
            return False
        
        # Check rate limiting
        if self.delay_until and now < self.delay_until:
            return False
        
        return True
    
    @property
    def age_seconds(self) -> float:
        """Age of query in seconds"""
        return (datetime.now() - self.created_at).total_seconds()


@dataclass
class RateLimitRule:
    """Rate limiting rule for query groups"""
    group: str
    max_requests: int
    time_window: timedelta
    cooldown: timedelta = timedelta(seconds=1)
    
    def __post_init__(self):
        self.request_times: List[datetime] = []
        self.last_request: Optional[datetime] = None
    
    def can_process(self) -> bool:
        """Check if group can process another request"""
        now = datetime.now()
        
        # Clean old requests outside time window
        cutoff = now - self.time_window
        self.request_times = [t for t in self.request_times if t > cutoff]
        
        # Check if under limit
        if len(self.request_times) >= self.max_requests:
            return False
        
        # Check cooldown
        if self.last_request and now - self.last_request < self.cooldown:
            return False
        
        return True
    
    def record_request(self):
        """Record a request for rate limiting"""
        now = datetime.now()
        self.request_times.append(now)
        self.last_request = now
    
    def next_available_time(self) -> datetime:
        """Calculate when next request can be made"""
        now = datetime.now()
        
        # Check cooldown
        cooldown_time = now
        if self.last_request:
            cooldown_time = self.last_request + self.cooldown
        
        # Check rate limit
        if self.request_times:
            # Time when oldest request in window expires
            oldest_expires = self.request_times[0] + self.time_window
            rate_limit_time = oldest_expires if len(self.request_times) >= self.max_requests else now
        else:
            rate_limit_time = now
        
        return max(cooldown_time, rate_limit_time)


class QueryQueue:
    """
    Priority-based query queue with rate limiting and processing tracking
    """
    
    def __init__(self, persistence_file: Optional[str] = None):
        self._queue: List[QueuedQuery] = []
        self._processing: Dict[str, QueuedQuery] = {}
        self._completed: Dict[str, QueuedQuery] = {}
        self._failed: Dict[str, QueuedQuery] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Rate limiting
        self._rate_limits: Dict[str, RateLimitRule] = {}
        
        # Query tracking
        self._query_hashes: Set[str] = set()  # For duplicate detection
        self._stats = {
            'total_added': 0,
            'total_processed': 0,
            'total_completed': 0,
            'total_failed': 0,
            'duplicates_filtered': 0
        }
        
        # Persistence
        self.persistence_file = Path(persistence_file) if persistence_file else None
        
        # Load persisted data
        self._load_from_file()
        
        # Processing callbacks
        self._pre_process_callbacks: List[Callable] = []
        self._post_process_callbacks: List[Callable] = []
    
    def add_rate_limit(self, rule: RateLimitRule):
        """Add a rate limiting rule"""
        with self._lock:
            self._rate_limits[rule.group] = rule
        logger.info(f"Added rate limit rule for group '{rule.group}': {rule.max_requests} requests per {rule.time_window}")
    
    def add_query(self, query: str, engine: str, priority: QueuePriority = QueuePriority.NORMAL,
                  category: Optional[str] = None, location: Optional[str] = None,
                  business_type: Optional[str] = None, tags: Optional[List[str]] = None,
                  scheduled_at: Optional[datetime] = None, 
                  rate_limit_group: Optional[str] = None,
                  check_duplicates: bool = True) -> Optional[str]:
        """
        Add a query to the queue
        
        Returns:
            Query ID if added, None if duplicate filtered
        """
        with self._lock:
            # Check for duplicates
            if check_duplicates:
                query_hash = self._generate_query_hash(query, engine, location)
                if query_hash in self._query_hashes:
                    self._stats['duplicates_filtered'] += 1
                    logger.debug(f"Filtered duplicate query: {query}")
                    return None
                self._query_hashes.add(query_hash)
            
            # Create queued query
            queued_query = QueuedQuery(
                id=str(uuid.uuid4()),
                query=query,
                engine=engine,
                priority=priority,
                category=category,
                location=location,
                business_type=business_type,
                tags=tags or [],
                scheduled_at=scheduled_at,
                rate_limit_group=rate_limit_group
            )
            
            # Add to queue
            heapq.heappush(self._queue, queued_query)
            self._stats['total_added'] += 1
            
            logger.debug(f"Added query to queue: {query} (ID: {queued_query.id})")
            
            # Persist if enabled
            self._save_to_file()
            
            return queued_query.id
    
    def add_batch(self, queries: List[Dict[str, Any]], check_duplicates: bool = True) -> List[str]:
        """
        Add multiple queries in batch
        
        Args:
            queries: List of query dictionaries with keys matching add_query parameters
            check_duplicates: Whether to filter duplicates
            
        Returns:
            List of query IDs that were added
        """
        added_ids = []
        
        for query_data in queries:
            query_id = self.add_query(check_duplicates=check_duplicates, **query_data)
            if query_id:
                added_ids.append(query_id)
        
        logger.info(f"Added batch of {len(added_ids)} queries (filtered {len(queries) - len(added_ids)} duplicates)")
        return added_ids
    
    def _generate_query_hash(self, query: str, engine: str, location: Optional[str] = None) -> str:
        """Generate hash for duplicate detection"""
        import hashlib
        
        # Normalize query
        normalized_query = query.lower().strip()
        hash_input = f"{normalized_query}|{engine}|{location or ''}"
        
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def get_next_query(self, respect_rate_limits: bool = True) -> Optional[QueuedQuery]:
        """
        Get the next query to process
        
        Args:
            respect_rate_limits: Whether to check rate limits
            
        Returns:
            Next query to process or None if queue empty/rate limited
        """
        with self._lock:
            if not self._queue:
                return None
            
            # Find next ready query
            ready_queries = []
            temp_queue = []
            
            # Check all queries in priority order
            while self._queue:
                query = heapq.heappop(self._queue)
                
                if not query.is_ready:
                    temp_queue.append(query)
                    continue
                
                # Check rate limits
                if respect_rate_limits and query.rate_limit_group:
                    rate_limit = self._rate_limits.get(query.rate_limit_group)
                    if rate_limit and not rate_limit.can_process():
                        # Schedule for later
                        query.delay_until = rate_limit.next_available_time()
                        temp_queue.append(query)
                        continue
                
                # Found ready query
                ready_queries.append(query)
                break
            
            # Put remaining queries back
            for query in temp_queue:
                heapq.heappush(self._queue, query)
            
            # Return first ready query
            if ready_queries:
                query = ready_queries[0]
                
                # Mark as processing
                query.status = QueryStatus.PROCESSING
                query.started_at = datetime.now()
                self._processing[query.id] = query
                
                # Record rate limit usage
                if query.rate_limit_group and query.rate_limit_group in self._rate_limits:
                    self._rate_limits[query.rate_limit_group].record_request()
                
                self._stats['total_processed'] += 1
                
                # Run pre-process callbacks
                for callback in self._pre_process_callbacks:
                    try:
                        callback(query)
                    except Exception as e:
                        logger.error(f"Pre-process callback failed: {e}")
                
                logger.debug(f"Retrieved query for processing: {query.query} (ID: {query.id})")
                return query
            
            return None
    
    def complete_query(self, query_id: str, result_count: int = 0, 
                      processing_time: Optional[float] = None):
        """Mark a query as completed"""
        with self._lock:
            if query_id not in self._processing:
                logger.warning(f"Query {query_id} not in processing queue")
                return
            
            query = self._processing.pop(query_id)
            query.status = QueryStatus.COMPLETED
            query.completed_at = datetime.now()
            query.result_count = result_count
            query.processing_time = processing_time
            
            self._completed[query_id] = query
            self._stats['total_completed'] += 1
            
            # Run post-process callbacks
            for callback in self._post_process_callbacks:
                try:
                    callback(query)
                except Exception as e:
                    logger.error(f"Post-process callback failed: {e}")
            
            logger.debug(f"Completed query: {query.query} (ID: {query_id})")
            self._save_to_file()
    
    def fail_query(self, query_id: str, error_message: str, retry: bool = True):
        """Mark a query as failed"""
        with self._lock:
            if query_id not in self._processing:
                logger.warning(f"Query {query_id} not in processing queue")
                return
            
            query = self._processing.pop(query_id)
            query.attempts += 1
            query.error_message = error_message
            
            # Check if should retry
            if retry and query.attempts < query.max_attempts:
                query.status = QueryStatus.RETRYING
                # Add delay for retry
                query.delay_until = datetime.now() + timedelta(
                    seconds=min(300, 60 * (2 ** (query.attempts - 1)))  # Exponential backoff
                )
                heapq.heappush(self._queue, query)
                logger.info(f"Retrying query {query_id} (attempt {query.attempts}/{query.max_attempts})")
            else:
                query.status = QueryStatus.FAILED
                query.completed_at = datetime.now()
                self._failed[query_id] = query
                self._stats['total_failed'] += 1
                logger.warning(f"Failed query after {query.attempts} attempts: {query.query}")
            
            self._save_to_file()
    
    def cancel_query(self, query_id: str) -> bool:
        """Cancel a pending query"""
        with self._lock:
            # Check processing queue first
            if query_id in self._processing:
                query = self._processing.pop(query_id)
                query.status = QueryStatus.CANCELLED
                query.completed_at = datetime.now()
                self._failed[query_id] = query
                return True
            
            # Search pending queue
            temp_queue = []
            found = False
            
            while self._queue:
                query = heapq.heappop(self._queue)
                if query.id == query_id:
                    query.status = QueryStatus.CANCELLED
                    query.completed_at = datetime.now()
                    self._failed[query_id] = query
                    found = True
                    break
                else:
                    temp_queue.append(query)
            
            # Restore queue
            for query in temp_queue:
                heapq.heappush(self._queue, query)
            
            if found:
                logger.info(f"Cancelled query: {query_id}")
                self._save_to_file()
            
            return found
    
    def get_query_status(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a query"""
        with self._lock:
            # Check all queues
            for query_dict in [self._processing, self._completed, self._failed]:
                if query_id in query_dict:
                    query = query_dict[query_id]
                    return {
                        'id': query.id,
                        'query': query.query,
                        'status': query.status.value,
                        'priority': query.priority.value,
                        'attempts': query.attempts,
                        'created_at': query.created_at.isoformat(),
                        'started_at': query.started_at.isoformat() if query.started_at else None,
                        'completed_at': query.completed_at.isoformat() if query.completed_at else None,
                        'result_count': query.result_count,
                        'processing_time': query.processing_time,
                        'error_message': query.error_message
                    }
            
            # Check pending queue
            for query in self._queue:
                if query.id == query_id:
                    return {
                        'id': query.id,
                        'query': query.query,
                        'status': query.status.value,
                        'priority': query.priority.value,
                        'scheduled_at': query.scheduled_at.isoformat() if query.scheduled_at else None,
                        'delay_until': query.delay_until.isoformat() if query.delay_until else None
                    }
            
            return None
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self._lock:
            return {
                'pending': len(self._queue),
                'processing': len(self._processing),
                'completed': len(self._completed),
                'failed': len(self._failed),
                'total_added': self._stats['total_added'],
                'total_processed': self._stats['total_processed'],
                'total_completed': self._stats['total_completed'],
                'total_failed': self._stats['total_failed'],
                'duplicates_filtered': self._stats['duplicates_filtered'],
                'success_rate': (
                    self._stats['total_completed'] / max(1, self._stats['total_processed']) * 100
                )
            }
    
    def get_pending_queries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of pending queries"""
        with self._lock:
            queries = sorted(self._queue, key=lambda x: (x.priority.value, x.created_at))
            
            if limit:
                queries = queries[:limit]
            
            return [{
                'id': q.id,
                'query': q.query,
                'engine': q.engine,
                'priority': q.priority.value,
                'category': q.category,
                'location': q.location,
                'age_seconds': q.age_seconds,
                'is_ready': q.is_ready
            } for q in queries]
    
    def clear_completed(self):
        """Clear completed and failed queries from memory"""
        with self._lock:
            count_completed = len(self._completed)
            count_failed = len(self._failed)
            
            self._completed.clear()
            self._failed.clear()
            
            logger.info(f"Cleared {count_completed} completed and {count_failed} failed queries")
            self._save_to_file()
    
    def purge_old_queries(self, max_age: timedelta = timedelta(days=7)):
        """Remove old completed/failed queries"""
        with self._lock:
            cutoff = datetime.now() - max_age
            
            # Remove old completed queries
            old_completed = {
                qid: q for qid, q in self._completed.items() 
                if q.completed_at and q.completed_at < cutoff
            }
            for qid in old_completed:
                del self._completed[qid]
            
            # Remove old failed queries
            old_failed = {
                qid: q for qid, q in self._failed.items()
                if q.completed_at and q.completed_at < cutoff
            }
            for qid in old_failed:
                del self._failed[qid]
            
            total_purged = len(old_completed) + len(old_failed)
            if total_purged > 0:
                logger.info(f"Purged {total_purged} old queries")
                self._save_to_file()
    
    def add_pre_process_callback(self, callback: Callable[[QueuedQuery], None]):
        """Add callback to run before processing query"""
        self._pre_process_callbacks.append(callback)
    
    def add_post_process_callback(self, callback: Callable[[QueuedQuery], None]):
        """Add callback to run after processing query"""
        self._post_process_callbacks.append(callback)
    
    def _save_to_file(self):
        """Save queue state to file"""
        if not self.persistence_file:
            return
        
        try:
            # Create directory if needed
            self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data for serialization
            data = {
                'queue': list(self._queue),
                'processing': dict(self._processing),
                'completed': dict(self._completed),
                'failed': dict(self._failed),
                'stats': self._stats.copy(),
                'query_hashes': list(self._query_hashes),
                'saved_at': datetime.now().isoformat()
            }
            
            # Save to file
            with open(self.persistence_file, 'wb') as f:
                pickle.dump(data, f)
            
        except Exception as e:
            logger.error(f"Failed to save queue state: {e}")
    
    def _load_from_file(self):
        """Load queue state from file"""
        if not self.persistence_file or not self.persistence_file.exists():
            return
        
        try:
            with open(self.persistence_file, 'rb') as f:
                data = pickle.load(f)
            
            # Restore queue state
            self._queue = data.get('queue', [])
            self._processing = data.get('processing', {})
            self._completed = data.get('completed', {})
            self._failed = data.get('failed', {})
            self._stats.update(data.get('stats', {}))
            self._query_hashes = set(data.get('query_hashes', []))
            
            # Rebuild heap (pickle might not preserve heap property)
            heapq.heapify(self._queue)
            
            logger.info(f"Loaded queue state from {self.persistence_file}")
            logger.info(f"Restored: {len(self._queue)} pending, {len(self._processing)} processing, "
                       f"{len(self._completed)} completed, {len(self._failed)} failed")
            
        except Exception as e:
            logger.error(f"Failed to load queue state: {e}")


# Convenience functions
def create_search_queue(rate_limits: Optional[List[Dict[str, Any]]] = None,
                      persistence_file: Optional[str] = "data/query_queue.pkl") -> QueryQueue:
    """Create a search query queue with common rate limits"""
    queue = QueryQueue(persistence_file)
    
    # Default rate limits
    default_limits = [
        {
            'group': 'bing',
            'max_requests': 100,
            'time_window': timedelta(minutes=1),
            'cooldown': timedelta(seconds=1)
        },
        {
            'group': 'google',
            'max_requests': 100,
            'time_window': timedelta(minutes=1),
            'cooldown': timedelta(seconds=2)
        },
        {
            'group': 'duckduckgo',
            'max_requests': 50,
            'time_window': timedelta(minutes=1),
            'cooldown': timedelta(seconds=3)
        }
    ]
    
    # Use provided limits or defaults
    limits = rate_limits or default_limits
    
    for limit_config in limits:
        rule = RateLimitRule(
            group=limit_config['group'],
            max_requests=limit_config['max_requests'],
            time_window=limit_config['time_window'],
            cooldown=limit_config.get('cooldown', timedelta(seconds=1))
        )
        queue.add_rate_limit(rule)
    
    return queue


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    queue = create_search_queue()
    
    # Add some queries
    queries = [
        {"query": "restaurants near Seattle", "engine": "bing", "priority": QueuePriority.HIGH, "rate_limit_group": "bing"},
        {"query": "cafes in Portland", "engine": "google", "priority": QueuePriority.NORMAL, "rate_limit_group": "google"},
        {"query": "bars in San Francisco", "engine": "duckduckgo", "priority": QueuePriority.LOW, "rate_limit_group": "duckduckgo"}
    ]
    
    query_ids = queue.add_batch(queries)
    print(f"Added {len(query_ids)} queries to queue")
    
    # Process a query
    next_query = queue.get_next_query()
    if next_query:
        print(f"Processing: {next_query.query}")
        
        # Simulate processing
        time.sleep(1)
        
        # Mark as completed
        queue.complete_query(next_query.id, result_count=25, processing_time=1.0)
    
    # Show queue stats
    stats = queue.get_queue_stats()
    print(f"Queue statistics: {stats}")
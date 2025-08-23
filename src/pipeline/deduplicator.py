"""
Cross-Session Deduplication System

Handles deduplication of records across multiple scraping sessions
using multiple matching strategies and persistent storage.
"""

import json
import logging
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
import re


@dataclass
class DedupeResult:
    """Result of duplicate check"""
    is_duplicate: bool
    duplicate_id: Optional[str]
    matching_fields: List[str]
    similarity_score: float
    match_type: str  # 'exact', 'fuzzy', 'domain', 'phone', 'email'
    original_record_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class DedupeStats:
    """Deduplication statistics"""
    total_checked: int
    duplicates_found: int
    unique_records: int
    match_types: Dict[str, int]
    processing_time: float


class DedupeStrategy:
    """Base class for deduplication strategies"""
    
    def check_duplicate(self, record: Dict, existing_records: List[Dict]) -> Optional[DedupeResult]:
        raise NotImplementedError


class ExactMatchStrategy(DedupeStrategy):
    """Exact field matching strategy"""
    
    def __init__(self, fields: List[str] = None):
        self.fields = fields or ['primary_email', 'primary_phone', 'website']
    
    def check_duplicate(self, record: Dict, existing_records: List[Dict]) -> Optional[DedupeResult]:
        for existing in existing_records:
            matching_fields = []
            
            for field in self.fields:
                record_value = self._normalize_value(record.get(field))
                existing_value = self._normalize_value(existing.get(field))
                
                if record_value and existing_value and record_value == existing_value:
                    matching_fields.append(field)
            
            if matching_fields:
                return DedupeResult(
                    is_duplicate=True,
                    duplicate_id=existing.get('lead_id'),
                    matching_fields=matching_fields,
                    similarity_score=1.0,
                    match_type='exact',
                    original_record_id=record.get('lead_id')
                )
        
        return None
    
    def _normalize_value(self, value: Any) -> Optional[str]:
        """Normalize value for comparison"""
        if not value:
            return None
        
        value_str = str(value).strip().lower()
        
        # Remove common formatting
        value_str = re.sub(r'[\s\-\(\)\.]', '', value_str)
        
        return value_str if value_str else None


class FuzzyMatchStrategy(DedupeStrategy):
    """Fuzzy matching for business names and addresses"""
    
    def __init__(self, threshold: float = 0.8, fields: List[str] = None):
        self.threshold = threshold
        self.fields = fields or ['business_name']
    
    def check_duplicate(self, record: Dict, existing_records: List[Dict]) -> Optional[DedupeResult]:
        best_match = None
        best_score = 0.0
        
        for existing in existing_records:
            total_score = 0.0
            matching_fields = []
            
            for field in self.fields:
                record_value = self._normalize_text(record.get(field))
                existing_value = self._normalize_text(existing.get(field))
                
                if record_value and existing_value:
                    similarity = SequenceMatcher(None, record_value, existing_value).ratio()
                    
                    if similarity >= self.threshold:
                        matching_fields.append(field)
                        total_score += similarity
            
            if matching_fields:
                avg_score = total_score / len(matching_fields)
                
                if avg_score > best_score:
                    best_score = avg_score
                    best_match = DedupeResult(
                        is_duplicate=True,
                        duplicate_id=existing.get('lead_id'),
                        matching_fields=matching_fields,
                        similarity_score=avg_score,
                        match_type='fuzzy',
                        original_record_id=record.get('lead_id')
                    )
        
        return best_match
    
    def _normalize_text(self, text: Any) -> Optional[str]:
        """Normalize text for fuzzy comparison"""
        if not text:
            return None
        
        text_str = str(text).lower().strip()
        
        # Remove common business suffixes/prefixes
        business_terms = [
            r'\b(inc|llc|ltd|corp|corporation|company|co|llp)\b',
            r'\b(the|a|an)\b',
        ]
        
        for term in business_terms:
            text_str = re.sub(term, '', text_str, flags=re.IGNORECASE)
        
        # Remove extra whitespace and punctuation
        text_str = re.sub(r'[^\w\s]', '', text_str)
        text_str = re.sub(r'\s+', ' ', text_str).strip()
        
        return text_str if text_str else None


class DomainMatchStrategy(DedupeStrategy):
    """Match records by website domain"""
    
    def check_duplicate(self, record: Dict, existing_records: List[Dict]) -> Optional[DedupeResult]:
        record_domain = self._extract_domain(record.get('website'))
        
        if not record_domain:
            return None
        
        for existing in existing_records:
            existing_domain = self._extract_domain(existing.get('website'))
            
            if existing_domain and record_domain == existing_domain:
                return DedupeResult(
                    is_duplicate=True,
                    duplicate_id=existing.get('lead_id'),
                    matching_fields=['website_domain'],
                    similarity_score=1.0,
                    match_type='domain',
                    original_record_id=record.get('lead_id')
                )
        
        return None
    
    def _extract_domain(self, url: Any) -> Optional[str]:
        """Extract domain from URL"""
        if not url:
            return None
        
        url_str = str(url).lower().strip()
        
        # Remove protocol
        url_str = re.sub(r'^https?://', '', url_str)
        
        # Remove www
        url_str = re.sub(r'^www\.', '', url_str)
        
        # Extract domain (everything before first slash or query)
        domain = url_str.split('/')[0].split('?')[0]
        
        return domain if domain else None


class Deduplicator:
    """Main deduplication manager"""
    
    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path or "data/dedupe_storage.db")
        self.logger = logging.getLogger(__name__)
        
        # Initialize strategies
        self.strategies = [
            ExactMatchStrategy(),
            FuzzyMatchStrategy(threshold=0.85),
            DomainMatchStrategy(),
        ]
        
        # Initialize storage
        self._init_storage()
        
        # Cache for performance
        self._session_cache = {}
    
    def _init_storage(self):
        """Initialize SQLite storage for deduplication"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dedupe_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                record_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(record_id, session_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dedupe_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT NOT NULL,
                duplicate_id TEXT NOT NULL,
                match_type TEXT NOT NULL,
                similarity_score REAL NOT NULL,
                matching_fields TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_hash ON dedupe_records(record_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON dedupe_records(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_id ON dedupe_matches(record_id)')
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Deduplication storage initialized at {self.storage_path}")
    
    def check_duplicate(self, record: Dict, session_id: str) -> DedupeResult:
        """Check if record is a duplicate"""
        record_id = record.get('lead_id', self._generate_record_id(record))
        
        # Check if already processed in this session
        if session_id in self._session_cache:
            session_records = self._session_cache[session_id]
        else:
            session_records = self._load_session_records(session_id)
            self._session_cache[session_id] = session_records
        
        # Get all existing records for comparison
        all_records = self._get_all_records()
        
        # Try each strategy
        for strategy in self.strategies:
            result = strategy.check_duplicate(record, all_records)
            
            if result:
                result.session_id = session_id
                
                # Store match result
                self._store_match_result(result)
                
                self.logger.debug(f"Duplicate found: {record_id} matches {result.duplicate_id} "
                                f"({result.match_type}, score={result.similarity_score:.3f})")
                
                return result
        
        # No duplicate found, store record
        self._store_record(record, session_id)
        
        # Add to session cache
        if session_id not in self._session_cache:
            self._session_cache[session_id] = []
        self._session_cache[session_id].append(record)
        
        return DedupeResult(
            is_duplicate=False,
            duplicate_id=None,
            matching_fields=[],
            similarity_score=0.0,
            match_type='none',
            original_record_id=record_id,
            session_id=session_id
        )
    
    def _generate_record_id(self, record: Dict) -> str:
        """Generate unique record ID based on content"""
        content = json.dumps(record, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _load_session_records(self, session_id: str) -> List[Dict]:
        """Load records from specific session"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT record_data FROM dedupe_records WHERE session_id = ?",
            (session_id,)
        )
        
        records = []
        for row in cursor.fetchall():
            try:
                record_data = json.loads(row[0])
                records.append(record_data)
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse record data for session {session_id}")
        
        conn.close()
        return records
    
    def _get_all_records(self, limit: int = 10000) -> List[Dict]:
        """Get all existing records for comparison"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT record_data FROM dedupe_records ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        
        records = []
        for row in cursor.fetchall():
            try:
                record_data = json.loads(row[0])
                records.append(record_data)
            except json.JSONDecodeError:
                continue
        
        conn.close()
        return records
    
    def _store_record(self, record: Dict, session_id: str):
        """Store record in deduplication storage"""
        record_id = record.get('lead_id', self._generate_record_id(record))
        record_data = json.dumps(record, default=str)
        record_hash = hashlib.md5(record_data.encode()).hexdigest()
        
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO dedupe_records 
                (record_id, session_id, record_hash, record_data)
                VALUES (?, ?, ?, ?)
            ''', (record_id, session_id, record_hash, record_data))
            
            conn.commit()
            
        except sqlite3.Error as e:
            self.logger.error(f"Failed to store record {record_id}: {str(e)}")
        finally:
            conn.close()
    
    def _store_match_result(self, result: DedupeResult):
        """Store duplicate match result"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO dedupe_matches 
                (record_id, duplicate_id, match_type, similarity_score, matching_fields)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                result.original_record_id,
                result.duplicate_id,
                result.match_type,
                result.similarity_score,
                json.dumps(result.matching_fields)
            ))
            
            conn.commit()
            
        except sqlite3.Error as e:
            self.logger.error(f"Failed to store match result: {str(e)}")
        finally:
            conn.close()
    
    def get_dedupe_stats(self, session_id: str = None) -> DedupeStats:
        """Get deduplication statistics"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        if session_id:
            # Stats for specific session
            cursor.execute(
                "SELECT COUNT(*) FROM dedupe_records WHERE session_id = ?",
                (session_id,)
            )
            total_records = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) FROM dedupe_matches WHERE record_id IN "
                "(SELECT record_id FROM dedupe_records WHERE session_id = ?)",
                (session_id,)
            )
            duplicates = cursor.fetchone()[0]
            
        else:
            # Overall stats
            cursor.execute("SELECT COUNT(*) FROM dedupe_records")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM dedupe_matches")
            duplicates = cursor.fetchone()[0]
        
        # Match type distribution
        cursor.execute("SELECT match_type, COUNT(*) FROM dedupe_matches GROUP BY match_type")
        match_types = dict(cursor.fetchall())
        
        conn.close()
        
        return DedupeStats(
            total_checked=total_records,
            duplicates_found=duplicates,
            unique_records=total_records - duplicates,
            match_types=match_types,
            processing_time=0.0  # Would be calculated during actual processing
        )
    
    def get_duplicate_groups(self, session_id: str = None) -> List[List[Dict]]:
        """Get groups of duplicate records"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute('''
                SELECT m.duplicate_id, r.record_data 
                FROM dedupe_matches m
                JOIN dedupe_records r ON m.record_id = r.record_id
                WHERE r.session_id = ?
                ORDER BY m.duplicate_id
            ''', (session_id,))
        else:
            cursor.execute('''
                SELECT m.duplicate_id, r.record_data 
                FROM dedupe_matches m
                JOIN dedupe_records r ON m.record_id = r.record_id
                ORDER BY m.duplicate_id
            ''')
        
        groups = {}
        for duplicate_id, record_data in cursor.fetchall():
            if duplicate_id not in groups:
                groups[duplicate_id] = []
            
            try:
                record = json.loads(record_data)
                groups[duplicate_id].append(record)
            except json.JSONDecodeError:
                continue
        
        conn.close()
        return list(groups.values())
    
    def cleanup_old_records(self, days: int = 30):
        """Clean up old deduplication records"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM dedupe_records WHERE created_at < datetime('now', '-? days')",
            (days,)
        )
        
        cursor.execute(
            "DELETE FROM dedupe_matches WHERE created_at < datetime('now', '-? days')",
            (days,)
        )
        
        deleted_records = cursor.rowcount
        conn.commit()
        conn.close()
        
        self.logger.info(f"Cleaned up {deleted_records} old deduplication records")
        return deleted_records
    
    def export_dedupe_report(self, output_file: str, session_id: str = None):
        """Export deduplication report"""
        stats = self.get_dedupe_stats(session_id)
        duplicate_groups = self.get_duplicate_groups(session_id)
        
        report = {
            'stats': {
                'total_checked': stats.total_checked,
                'duplicates_found': stats.duplicates_found,
                'unique_records': stats.unique_records,
                'match_types': stats.match_types
            },
            'duplicate_groups': duplicate_groups,
            'generated_at': datetime.now().isoformat(),
            'session_id': session_id
        }
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Deduplication report exported to {output_path}")
    
    def close(self):
        """Clean up resources"""
        self._session_cache.clear()
        self.logger.info("Deduplicator closed")
"""
Core Data Models and Storage Implementation
TASK-F003: Database schema and core data models with validation

Provides comprehensive data models for lead generation with:
- Business/Lead data structures
- Campaign management models
- Validation and quality scoring
- In-memory processing pipeline
"""

import os
from typing import Optional, List, Dict, Any, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json
import re
import hashlib
from pathlib import Path
import sqlite3
import threading
from queue import Queue


class LeadStatus(Enum):
    """Lead processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    VALIDATED = "validated"
    INVALID = "invalid"
    DUPLICATE = "duplicate"
    EXPORTED = "exported"
    ERROR = "error"


class DataQuality(Enum):
    """Data quality levels"""
    HIGH = "high"          # 90-100% confidence
    MEDIUM = "medium"      # 70-89% confidence
    LOW = "low"           # 50-69% confidence
    UNKNOWN = "unknown"    # <50% confidence


@dataclass
class ContactInfo:
    """Contact information with validation"""
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    social_media: Dict[str, str] = field(default_factory=dict)
    
    def validate_email(self) -> bool:
        """SECURITY FIX: Enhanced email validation with sanitization"""
        if not self.email:
            return False
        
        # Sanitize email - remove null bytes and excessive whitespace
        clean_email = re.sub(r'\s+', '', str(self.email).replace('\x00', ''))
        
        # Length check to prevent buffer overflow
        if len(clean_email) > 320:  # RFC 5321 limit
            return False
        
        # Enhanced email pattern with security considerations
        pattern = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        
        if not re.match(pattern, clean_email):
            return False
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.{2,}',      # Multiple consecutive dots
            r'^\.|\.$',     # Starting or ending with dot
            r'@.*@',        # Multiple @ symbols
        ]
        
        for suspicious in suspicious_patterns:
            if re.search(suspicious, clean_email):
                return False
        
        # Update with cleaned email
        self.email = clean_email
        return True
    
    def validate_phone(self) -> bool:
        """SECURITY FIX: Enhanced phone validation with sanitization"""
        if not self.phone:
            return False
        
        # Sanitize phone - remove null bytes and excessive whitespace
        clean_phone = str(self.phone).replace('\x00', '').strip()
        
        # Length check to prevent buffer overflow
        if len(clean_phone) > 50:
            return False
        
        # Allow only valid phone characters
        if not re.match(r'^[0-9+\-\(\)\.\s]+$', clean_phone):
            return False
        
        # Extract digits for validation
        digits = re.sub(r'\D', '', clean_phone)
        
        # Validate digit count (international range)
        if not (7 <= len(digits) <= 15):
            return False
        
        # Check for suspicious patterns
        if re.search(r'(.)\1{6,}', digits):  # Too many repeated digits
            return False
        
        # Update with cleaned phone
        self.phone = clean_phone
        return True
    
    def completeness_score(self) -> float:
        """Calculate contact info completeness (0-1)"""
        score = 0.0
        weights = {
            'email': 0.4,
            'phone': 0.3,
            'website': 0.2,
            'social_media': 0.1
        }
        
        if self.email and self.validate_email():
            score += weights['email']
        if self.phone and self.validate_phone():
            score += weights['phone']
        if self.website:
            score += weights['website']
        if self.social_media:
            score += weights['social_media']
            
        return score


@dataclass
class Address:
    """Physical address information"""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "USA"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    def to_string(self) -> str:
        """Format address as string"""
        parts = []
        if self.street:
            parts.append(self.street)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        if self.country != "USA":
            parts.append(self.country)
        return ", ".join(parts)
    
    def is_complete(self) -> bool:
        """Check if address has minimum required fields"""
        return bool(self.city and (self.state or self.country))


@dataclass
class BusinessLead:
    """Core business lead data model"""
    # Identification
    id: str = field(default_factory=lambda: None)
    source: str = "google_maps"
    source_id: Optional[str] = None
    
    # Business information
    name: str = ""
    category: Optional[str] = None
    subcategory: Optional[str] = None
    description: Optional[str] = None
    
    # Contact information
    contact: ContactInfo = field(default_factory=ContactInfo)
    
    # Location
    address: Address = field(default_factory=Address)
    
    # Additional data
    rating: Optional[float] = None
    review_count: Optional[int] = None
    price_range: Optional[str] = None
    hours: Optional[Dict[str, str]] = None
    
    # Metadata
    scraped_at: datetime = field(default_factory=datetime.now)
    validated_at: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Quality metrics
    confidence_score: float = 0.0
    quality_level: DataQuality = DataQuality.UNKNOWN
    validation_errors: List[str] = field(default_factory=list)
    
    # Processing status
    status: LeadStatus = LeadStatus.PENDING
    
    def __post_init__(self):
        """Generate ID if not provided"""
        if not self.id:
            self.id = self.generate_id()
    
    def generate_id(self) -> str:
        """Generate unique ID for the lead"""
        data = f"{self.name}_{self.contact.email or ''}_{self.address.to_string()}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    def calculate_confidence(self) -> float:
        """Calculate overall confidence score"""
        scores = []
        
        # Name and category (30%)
        if self.name:
            scores.append(0.15)
        if self.category:
            scores.append(0.15)
            
        # Contact info (40%)
        contact_score = self.contact.completeness_score() * 0.4
        scores.append(contact_score)
        
        # Address (20%)
        if self.address.is_complete():
            scores.append(0.2)
            
        # Additional info (10%)
        if self.rating is not None:
            scores.append(0.05)
        if self.description:
            scores.append(0.05)
            
        self.confidence_score = sum(scores)
        
        # Set quality level
        if self.confidence_score >= 0.9:
            self.quality_level = DataQuality.HIGH
        elif self.confidence_score >= 0.7:
            self.quality_level = DataQuality.MEDIUM
        elif self.confidence_score >= 0.5:
            self.quality_level = DataQuality.LOW
        else:
            self.quality_level = DataQuality.UNKNOWN
            
        return self.confidence_score
    
    def validate(self) -> bool:
        """Validate lead data"""
        self.validation_errors.clear()
        
        # Required fields
        if not self.name:
            self.validation_errors.append("Missing business name")
            
        # Contact validation
        if not self.contact.email and not self.contact.phone:
            self.validation_errors.append("No contact information")
        
        if self.contact.email and not self.contact.validate_email():
            self.validation_errors.append("Invalid email format")
            
        if self.contact.phone and not self.contact.validate_phone():
            self.validation_errors.append("Invalid phone format")
            
        # Address validation
        if not self.address.is_complete():
            self.validation_errors.append("Incomplete address")
            
        # Update status
        if self.validation_errors:
            self.status = LeadStatus.INVALID
            return False
        else:
            self.status = LeadStatus.VALIDATED
            self.validated_at = datetime.now()
            return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert enums to strings
        data['status'] = self.status.value
        data['quality_level'] = self.quality_level.value
        # Convert datetime to ISO format
        data['scraped_at'] = self.scraped_at.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        if self.validated_at:
            data['validated_at'] = self.validated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BusinessLead':
        """Create instance from dictionary"""
        # Convert string dates back to datetime
        if 'scraped_at' in data:
            data['scraped_at'] = datetime.fromisoformat(data['scraped_at'])
        if 'last_updated' in data:
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        if 'validated_at' in data and data['validated_at']:
            data['validated_at'] = datetime.fromisoformat(data['validated_at'])
            
        # Convert status and quality strings to enums
        if 'status' in data:
            data['status'] = LeadStatus(data['status'])
        if 'quality_level' in data:
            data['quality_level'] = DataQuality(data['quality_level'])
            
        # Create nested objects
        if 'contact' in data and isinstance(data['contact'], dict):
            data['contact'] = ContactInfo(**data['contact'])
        if 'address' in data and isinstance(data['address'], dict):
            data['address'] = Address(**data['address'])
            
        return cls(**data)


@dataclass
class Campaign:
    """Campaign management model"""
    id: str
    name: str
    description: Optional[str] = None
    
    # Search parameters
    search_queries: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    
    # Configuration
    max_results: int = 1000
    quality_threshold: float = 0.7
    enable_email_validation: bool = True
    enable_deduplication: bool = True
    
    # Status tracking
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    total_leads: int = 0
    validated_leads: int = 0
    exported_leads: int = 0
    error_count: int = 0
    
    # Metrics
    extraction_rate: float = 0.0  # leads per hour
    validation_rate: float = 0.0  # percentage validated
    email_extraction_rate: float = 0.0  # percentage with emails
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def calculate_metrics(self, leads: List[BusinessLead]):
        """Calculate campaign metrics from leads"""
        self.total_leads = len(leads)
        
        if not leads:
            return
            
        # Validation rate
        validated = [l for l in leads if l.status == LeadStatus.VALIDATED]
        self.validated_leads = len(validated)
        self.validation_rate = self.validated_leads / self.total_leads
        
        # Email extraction rate
        with_email = [l for l in leads if l.contact.email]
        self.email_extraction_rate = len(with_email) / self.total_leads
        
        # Extraction rate (leads per hour)
        if self.started_at and self.completed_at:
            duration_hours = (self.completed_at - self.started_at).total_seconds() / 3600
            if duration_hours > 0:
                self.extraction_rate = self.total_leads / duration_hours


@dataclass
class ValidationResult:
    """Result of lead validation"""
    lead_id: str
    is_valid: bool
    confidence: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Detailed validation results
    email_valid: Optional[bool] = None
    email_deliverable: Optional[bool] = None
    email_mx_valid: Optional[bool] = None
    phone_valid: Optional[bool] = None
    phone_type: Optional[str] = None
    address_valid: Optional[bool] = None
    
    validated_at: datetime = field(default_factory=datetime.now)


class LeadDatabase:
    """SECURITY FIX: Secure database with parameterized queries and input validation"""
    
    def __init__(self, db_path: str = "./secure_leads.db"):
        self.db_path = Path(db_path)
        
        # Import secure database manager
        try:
            from ..security.secure_database import SecureDatabaseManager
        except ImportError:
            # Fallback for standalone usage
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'security'))
            from secure_database import SecureDatabaseManager
        
        # Use secure database manager instead of direct SQLite
        self.secure_db = SecureDatabaseManager(str(db_path))
        self.lock = threading.Lock()
        
        # In-memory cache for performance (with size limit for security)
        self.cache: Dict[str, BusinessLead] = {}
        self.dirty_ids: set = set()  # IDs that need to be persisted
        self._max_cache_size = 10000  # Prevent memory exhaustion
        
    def _validate_cache_size(self):
        """Ensure cache doesn't exceed memory limits"""
        if len(self.cache) > self._max_cache_size:
            # Remove oldest entries (simple LRU approximation)
            excess_count = len(self.cache) - self._max_cache_size + 100
            oldest_ids = list(self.cache.keys())[:excess_count]
            for old_id in oldest_ids:
                if old_id not in self.dirty_ids:  # Don't remove unsaved entries
                    del self.cache[old_id]
    
    def save_lead(self, lead: BusinessLead) -> bool:
        """SECURITY FIX: Save lead using secure database manager"""
        with self.lock:
            try:
                # Validate lead data before saving
                if not lead.validate():
                    print(f"Lead validation failed: {lead.validation_errors}")
                    return False
                
                # Update cache with size validation
                self.cache[lead.id] = lead
                self.dirty_ids.add(lead.id)
                self._validate_cache_size()
                
                # Prepare secure data for database
                lead_data = {
                    'id': lead.id,
                    'data': lead.to_dict(),
                    'name': lead.name,
                    'email': lead.contact.email,
                    'phone': lead.contact.phone,
                    'city': lead.address.city,
                    'state': lead.address.state,
                    'category': lead.category,
                    'quality_level': lead.quality_level.value,
                    'status': lead.status.value
                }
                
                # Use secure database manager
                success = self.secure_db.insert_lead(lead_data)
                if success:
                    self.dirty_ids.discard(lead.id)
                
                return success
                
            except Exception as e:
                print(f"Error saving lead: {e}")
                return False
    
    def get_lead(self, lead_id: str) -> Optional[BusinessLead]:
        """SECURITY FIX: Get lead using secure database manager"""
        # Input validation
        if not lead_id or not isinstance(lead_id, str):
            return None
            
        # Check cache first
        if lead_id in self.cache:
            return self.cache[lead_id]
            
        with self.lock:
            # Use secure database manager
            lead_data = self.secure_db.get_lead(lead_id)
            
            if lead_data and lead_data.get('data'):
                try:
                    # Parse JSON data safely
                    if isinstance(lead_data['data'], str):
                        parsed_data = json.loads(lead_data['data'])
                    else:
                        parsed_data = lead_data['data']
                    
                    lead = BusinessLead.from_dict(parsed_data)
                    
                    # Cache with size validation
                    self.cache[lead_id] = lead
                    self._validate_cache_size()
                    
                    return lead
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error parsing lead data: {e}")
                    return None
                
        return None
    
    def find_duplicates(self, lead: BusinessLead) -> List[BusinessLead]:
        """SECURITY FIX: Find duplicates using secure queries"""
        duplicates = []
        
        try:
            with self.lock:
                # Check by email using secure query
                if lead.contact.email:
                    email_leads = self.secure_db.execute_safe_query(
                        "SELECT data FROM leads WHERE email = :email AND id != :id LIMIT 100",
                        {'email': lead.contact.email, 'id': lead.id}
                    )
                    
                    for lead_data in email_leads:
                        try:
                            if 'data' in lead_data:
                                parsed_data = json.loads(lead_data['data']) if isinstance(lead_data['data'], str) else lead_data['data']
                                duplicates.append(BusinessLead.from_dict(parsed_data))
                        except (json.JSONDecodeError, ValueError):
                            continue
                
                # Check by phone if no email duplicates found
                if lead.contact.phone and not duplicates:
                    phone_leads = self.secure_db.execute_safe_query(
                        "SELECT data FROM leads WHERE phone = :phone AND id != :id LIMIT 100",
                        {'phone': lead.contact.phone, 'id': lead.id}
                    )
                    
                    for lead_data in phone_leads:
                        try:
                            if 'data' in lead_data:
                                parsed_data = json.loads(lead_data['data']) if isinstance(lead_data['data'], str) else lead_data['data']
                                duplicates.append(BusinessLead.from_dict(parsed_data))
                        except (json.JSONDecodeError, ValueError):
                            continue
                            
        except Exception as e:
            print(f"Error finding duplicates: {e}")
            
        return duplicates
    
    def query_leads(self, 
                   status: Optional[LeadStatus] = None,
                   quality: Optional[DataQuality] = None,
                   city: Optional[str] = None,
                   limit: int = 100) -> List[BusinessLead]:
        """SECURITY FIX: Query leads using secure database manager"""
        try:
            with self.lock:
                # Build secure filters
                filters = {}
                
                if status:
                    filters['status'] = status.value
                    
                if quality:
                    filters['quality_level'] = quality.value
                    
                if city:
                    filters['city'] = str(city)[:100]  # Limit city length
                
                # Use secure query method
                lead_records = self.secure_db.find_leads(filters, limit=min(limit, 1000))
                
                leads = []
                for record in lead_records:
                    try:
                        if 'data' in record:
                            parsed_data = json.loads(record['data']) if isinstance(record['data'], str) else record['data']
                            leads.append(BusinessLead.from_dict(parsed_data))
                    except (json.JSONDecodeError, ValueError):
                        continue
                        
                return leads
                
        except Exception as e:
            print(f"Error querying leads: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """SECURITY FIX: Get statistics using secure database manager"""
        try:
            with self.lock:
                return self.secure_db.get_statistics()
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}
    
    def close(self):
        """SECURITY FIX: Close database connections safely"""
        try:
            # Save any dirty cache entries
            for lead_id in list(self.dirty_ids):  # Create copy to avoid modification during iteration
                if lead_id in self.cache:
                    self.save_lead(self.cache[lead_id])
            
            # Close secure database connections
            if hasattr(self, 'secure_db'):
                self.secure_db.close_all_connections()
                
            # Clear caches
            self.cache.clear()
            self.dirty_ids.clear()
            
        except Exception as e:
            print(f"Error closing database: {e}")


class InMemoryPipeline:
    """High-performance in-memory processing pipeline"""
    
    def __init__(self, max_size: int = 10000):
        self.queue = Queue(maxsize=max_size)
        self.processed = []
        self.failed = []
        self.stats = {
            'total_processed': 0,
            'total_failed': 0,
            'processing_time': 0,
            'avg_processing_time': 0
        }
        
    def add(self, lead: BusinessLead) -> bool:
        """Add lead to processing queue"""
        try:
            self.queue.put_nowait(lead)
            return True
        except:
            return False
    
    def process_batch(self, processor_func, batch_size: int = 100) -> int:
        """Process a batch of leads"""
        batch = []
        
        # Get batch from queue
        for _ in range(min(batch_size, self.queue.qsize())):
            if not self.queue.empty():
                batch.append(self.queue.get())
                
        if not batch:
            return 0
            
        # Process batch
        start_time = datetime.now()
        
        for lead in batch:
            try:
                result = processor_func(lead)
                if result:
                    self.processed.append(lead)
                    self.stats['total_processed'] += 1
                else:
                    self.failed.append(lead)
                    self.stats['total_failed'] += 1
            except Exception as e:
                print(f"Processing error: {e}")
                self.failed.append(lead)
                self.stats['total_failed'] += 1
                
        # Update stats
        processing_time = (datetime.now() - start_time).total_seconds()
        self.stats['processing_time'] += processing_time
        
        total = self.stats['total_processed'] + self.stats['total_failed']
        if total > 0:
            self.stats['avg_processing_time'] = self.stats['processing_time'] / total
            
        return len(batch)
    
    def get_results(self) -> Tuple[List[BusinessLead], List[BusinessLead]]:
        """Get processed and failed leads"""
        return self.processed.copy(), self.failed.copy()
    
    def clear(self):
        """Clear pipeline"""
        while not self.queue.empty():
            self.queue.get()
        self.processed.clear()
        self.failed.clear()


if __name__ == "__main__":
    # Test data models
    print("Testing Core Data Models")
    print("="*50)
    
    # Create test lead
    lead = BusinessLead(
        name="Test Business Inc",
        category="Technology",
        contact=ContactInfo(
            email="contact@testbusiness.com",
            phone="555-1234567",
            website="https://testbusiness.com"
        ),
        address=Address(
            street="123 Main St",
            city="New York",
            state="NY",
            postal_code="10001"
        ),
        rating=4.5,
        review_count=100
    )
    
    # Calculate confidence
    confidence = lead.calculate_confidence()
    print(f"\nLead: {lead.name}")
    print(f"ID: {lead.id}")
    print(f"Confidence: {confidence:.2%}")
    print(f"Quality: {lead.quality_level.value}")
    
    # Validate
    is_valid = lead.validate()
    print(f"Valid: {is_valid}")
    print(f"Status: {lead.status.value}")
    
    # Test database
    print("\nTesting Lead Database:")
    db = LeadDatabase("./test_leads.db")
    
    # Save lead
    saved = db.save_lead(lead)
    print(f"Lead saved: {saved}")
    
    # Retrieve lead
    retrieved = db.get_lead(lead.id)
    print(f"Lead retrieved: {retrieved is not None}")
    
    # Get statistics
    stats = db.get_statistics()
    print(f"Database stats: {json.dumps(stats, indent=2)}")
    
    # Test pipeline
    print("\nTesting In-Memory Pipeline:")
    pipeline = InMemoryPipeline()
    
    # Add leads to pipeline
    for i in range(5):
        test_lead = BusinessLead(
            name=f"Business {i}",
            contact=ContactInfo(email=f"business{i}@example.com")
        )
        pipeline.add(test_lead)
    
    # Process batch
    def validate_processor(lead):
        return lead.validate()
    
    processed_count = pipeline.process_batch(validate_processor)
    print(f"Processed: {processed_count} leads")
    print(f"Pipeline stats: {json.dumps(pipeline.stats, indent=2)}")
    
    # Cleanup
    db.close()
    print("\nData models test complete!")
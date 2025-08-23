"""
Business entity data model with validation for map extractions.
Provides consistent structure for business data from different map sources.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import re
from urllib.parse import urlparse
import hashlib


@dataclass
class BusinessHours:
    """Represents business operating hours."""
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Optional[str]]:
        """Convert to dictionary format."""
        return {
            'monday': self.monday,
            'tuesday': self.tuesday,
            'wednesday': self.wednesday,
            'thursday': self.thursday,
            'friday': self.friday,
            'saturday': self.saturday,
            'sunday': self.sunday
        }
    
    @classmethod
    def from_text(cls, hours_text: str) -> 'BusinessHours':
        """Parse hours from text format."""
        hours = cls()
        if not hours_text:
            return hours
            
        # Handle common formats like "Mon-Fri 9AM-5PM"
        days_mapping = {
            'mon': 'monday', 'tue': 'tuesday', 'wed': 'wednesday',
            'thu': 'thursday', 'fri': 'friday', 'sat': 'saturday', 'sun': 'sunday'
        }
        
        # Simple parsing - can be enhanced based on actual formats
        lines = hours_text.strip().split('\n')
        for line in lines:
            line = line.strip().lower()
            for day_abbr, day_full in days_mapping.items():
                if day_abbr in line:
                    # Extract time portion
                    time_match = re.search(r'(\d+(?::\d+)?(?:am|pm)?.*?(?:\d+(?::\d+)?(?:am|pm)?))', line)
                    if time_match:
                        setattr(hours, day_full, time_match.group(1))
        
        return hours


@dataclass
class BusinessRating:
    """Represents business rating information."""
    score: Optional[float] = None
    max_score: Optional[float] = 5.0
    review_count: Optional[int] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        """Validate rating data."""
        if self.score is not None:
            try:
                self.score = float(self.score)
                if self.score < 0:
                    self.score = None
            except (ValueError, TypeError):
                self.score = None
                
        if self.review_count is not None:
            try:
                self.review_count = int(self.review_count)
                if self.review_count < 0:
                    self.review_count = None
            except (ValueError, TypeError):
                self.review_count = None


@dataclass
class BusinessEntity:
    """
    Standardized business entity model for map extractions.
    Handles validation, normalization, and deduplication.
    """
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[BusinessRating] = None
    hours: Optional[BusinessHours] = None
    category: Optional[str] = None
    description: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    source: str = "unknown"
    source_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize business data."""
        self.name = self._normalize_text(self.name) if self.name else ""
        self.address = self._normalize_text(self.address) if self.address else None
        self.phone = self._normalize_phone(self.phone) if self.phone else None
        self.website = self._normalize_url(self.website) if self.website else None
        self.category = self._normalize_text(self.category) if self.category else None
        self.description = self._normalize_text(self.description) if self.description else None
        
        # Validate coordinates
        if self.coordinates:
            try:
                lat = float(self.coordinates.get('lat', 0))
                lng = float(self.coordinates.get('lng', 0))
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    self.coordinates = {'lat': lat, 'lng': lng}
                else:
                    self.coordinates = None
            except (ValueError, TypeError):
                self.coordinates = None
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text by removing extra whitespace and special characters."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.strip().split())
        # Remove common HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return text
    
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone number format."""
        if not phone:
            return ""
        
        # Remove all non-digit characters
        digits = re.sub(r'[^\d]', '', phone)
        
        # Handle US phone numbers
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            # Return original if not standard format
            return phone.strip()
    
    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL format."""
        if not url:
            return ""
        
        url = url.strip()
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://', 'ftp://')):
            url = 'https://' + url
        
        try:
            parsed = urlparse(url)
            if parsed.netloc:
                return url
        except Exception:
            pass
        
        return ""
    
    def get_unique_id(self) -> str:
        """Generate unique ID for deduplication."""
        # Use name and address for uniqueness
        unique_string = f"{self.name}|{self.address or ''}|{self.phone or ''}"
        return hashlib.md5(unique_string.lower().encode()).hexdigest()
    
    def is_valid(self) -> bool:
        """Check if business entity has minimum required data."""
        return bool(self.name and (self.address or self.phone))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert business entity to dictionary."""
        return {
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'website': self.website,
            'rating': {
                'score': self.rating.score if self.rating else None,
                'max_score': self.rating.max_score if self.rating else None,
                'review_count': self.rating.review_count if self.rating else None,
                'source': self.rating.source if self.rating else None
            } if self.rating else None,
            'hours': self.hours.to_dict() if self.hours else None,
            'category': self.category,
            'description': self.description,
            'coordinates': self.coordinates,
            'source': self.source,
            'source_url': self.source_url,
            'unique_id': self.get_unique_id()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BusinessEntity':
        """Create business entity from dictionary."""
        rating_data = data.get('rating')
        rating = None
        if rating_data:
            rating = BusinessRating(
                score=rating_data.get('score'),
                max_score=rating_data.get('max_score', 5.0),
                review_count=rating_data.get('review_count'),
                source=rating_data.get('source')
            )
        
        hours_data = data.get('hours')
        hours = None
        if hours_data:
            hours = BusinessHours(**hours_data)
        
        return cls(
            name=data.get('name', ''),
            address=data.get('address'),
            phone=data.get('phone'),
            website=data.get('website'),
            rating=rating,
            hours=hours,
            category=data.get('category'),
            description=data.get('description'),
            coordinates=data.get('coordinates'),
            source=data.get('source', 'unknown'),
            source_url=data.get('source_url'),
            raw_data=data.get('raw_data', {})
        )
    
    def similarity_score(self, other: 'BusinessEntity') -> float:
        """Calculate similarity score with another business entity."""
        if not isinstance(other, BusinessEntity):
            return 0.0
        
        score = 0.0
        weight_sum = 0.0
        
        # Name similarity (most important)
        if self.name and other.name:
            name_similarity = self._text_similarity(self.name.lower(), other.name.lower())
            score += name_similarity * 0.5
            weight_sum += 0.5
        
        # Address similarity
        if self.address and other.address:
            addr_similarity = self._text_similarity(self.address.lower(), other.address.lower())
            score += addr_similarity * 0.3
            weight_sum += 0.3
        
        # Phone similarity
        if self.phone and other.phone:
            # Normalize phones for comparison
            phone1 = re.sub(r'[^\d]', '', self.phone)
            phone2 = re.sub(r'[^\d]', '', other.phone)
            phone_match = 1.0 if phone1 == phone2 else 0.0
            score += phone_match * 0.2
            weight_sum += 0.2
        
        return score / weight_sum if weight_sum > 0 else 0.0
    
    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """Calculate text similarity using Jaccard similarity."""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


class BusinessEntityCollection:
    """Collection class for managing multiple business entities with deduplication."""
    
    def __init__(self, similarity_threshold: float = 0.8):
        self.entities: List[BusinessEntity] = []
        self.similarity_threshold = similarity_threshold
        self._entity_map: Dict[str, BusinessEntity] = {}
    
    def add_entity(self, entity: BusinessEntity) -> bool:
        """Add entity with automatic deduplication."""
        if not entity.is_valid():
            return False
        
        # Check for duplicates
        unique_id = entity.get_unique_id()
        if unique_id in self._entity_map:
            # Merge with existing entity
            existing = self._entity_map[unique_id]
            self._merge_entities(existing, entity)
            return False
        
        # Check similarity with existing entities
        for existing_entity in self.entities:
            if entity.similarity_score(existing_entity) >= self.similarity_threshold:
                self._merge_entities(existing_entity, entity)
                return False
        
        # Add new entity
        self.entities.append(entity)
        self._entity_map[unique_id] = entity
        return True
    
    def _merge_entities(self, existing: BusinessEntity, new_entity: BusinessEntity):
        """Merge new entity data into existing entity."""
        # Update missing fields from new entity
        if not existing.phone and new_entity.phone:
            existing.phone = new_entity.phone
        if not existing.website and new_entity.website:
            existing.website = new_entity.website
        if not existing.rating and new_entity.rating:
            existing.rating = new_entity.rating
        if not existing.hours and new_entity.hours:
            existing.hours = new_entity.hours
        if not existing.category and new_entity.category:
            existing.category = new_entity.category
        if not existing.coordinates and new_entity.coordinates:
            existing.coordinates = new_entity.coordinates
        
        # Merge raw data
        existing.raw_data.update(new_entity.raw_data)
    
    def get_entities(self) -> List[BusinessEntity]:
        """Get all unique entities."""
        return self.entities.copy()
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert all entities to list of dictionaries."""
        return [entity.to_dict() for entity in self.entities]
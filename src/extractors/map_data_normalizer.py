"""
Map data normalizer for consolidating and deduplicating business data
from different map sources (Bing Maps, Google Maps).
"""
from typing import List, Dict, Any, Optional, Set, Tuple
import re
import logging
from difflib import SequenceMatcher
from collections import defaultdict

from ..models.business_entity import BusinessEntity, BusinessEntityCollection, BusinessRating, BusinessHours


class MapDataNormalizer:
    """
    Normalizes and deduplicates business data from multiple map sources.
    Handles merging duplicate entries and standardizing data formats.
    """
    
    def __init__(self, similarity_threshold: float = 0.8, strict_deduplication: bool = False):
        """
        Initialize normalizer with configuration.
        
        Args:
            similarity_threshold: Minimum similarity score for duplicate detection
            strict_deduplication: If True, uses stricter matching criteria
        """
        self.similarity_threshold = similarity_threshold
        self.strict_deduplication = strict_deduplication
        self.logger = logging.getLogger(__name__)
        
        # Compile regex patterns for efficiency
        self.phone_pattern = re.compile(r'[^\d+\-\(\)\s\.]')
        self.address_patterns = [
            re.compile(r'\b(?:suite|ste|apt|apartment|unit|floor|#)\s*\w+\b', re.IGNORECASE),
            re.compile(r'\b(?:street|st|avenue|ave|road|rd|lane|ln|drive|dr|boulevard|blvd|way|pkwy|plaza|pl)\b', re.IGNORECASE),
            re.compile(r'\b[A-Z]{2}\s*\d{5}(?:-\d{4})?\b')
        ]
    
    def normalize_and_deduplicate(self, business_lists: List[List[BusinessEntity]]) -> List[BusinessEntity]:
        """
        Normalize and deduplicate business entities from multiple sources.
        
        Args:
            business_lists: List of business entity lists from different sources
            
        Returns:
            Deduplicated and normalized list of business entities
        """
        if not business_lists:
            return []
        
        # Flatten all business lists
        all_businesses = []
        for business_list in business_lists:
            all_businesses.extend(business_list)
        
        if not all_businesses:
            return []
        
        self.logger.info(f"Starting normalization of {len(all_businesses)} businesses")
        
        # Step 1: Basic normalization
        normalized_businesses = []
        for business in all_businesses:
            normalized = self._normalize_single_business(business)
            if normalized and normalized.is_valid():
                normalized_businesses.append(normalized)
        
        self.logger.info(f"After normalization: {len(normalized_businesses)} valid businesses")
        
        # Step 2: Deduplication
        deduplicated_businesses = self._deduplicate_businesses(normalized_businesses)
        
        self.logger.info(f"After deduplication: {len(deduplicated_businesses)} unique businesses")
        
        # Step 3: Final quality checks and sorting
        final_businesses = self._final_quality_check(deduplicated_businesses)
        
        return final_businesses
    
    def _normalize_single_business(self, business: BusinessEntity) -> Optional[BusinessEntity]:
        """Normalize a single business entity."""
        try:
            # Create a copy to avoid modifying original
            normalized = BusinessEntity(
                name=self._normalize_business_name(business.name),
                address=self._normalize_address(business.address),
                phone=self._normalize_phone_number(business.phone),
                website=self._normalize_website_url(business.website),
                rating=self._normalize_rating(business.rating),
                hours=self._normalize_hours(business.hours),
                category=self._normalize_category(business.category),
                description=self._normalize_description(business.description),
                coordinates=business.coordinates,
                source=business.source,
                source_url=business.source_url,
                raw_data=business.raw_data
            )
            
            return normalized if normalized.is_valid() else None
            
        except Exception as e:
            self.logger.warning(f"Failed to normalize business {business.name}: {e}")
            return None
    
    def _normalize_business_name(self, name: str) -> str:
        """Normalize business name."""
        if not name:
            return ""
        
        # Remove extra whitespace
        name = ' '.join(name.strip().split())
        
        # Remove common suffixes that might cause duplicate issues
        name = re.sub(r'\s*-\s*Google\s*Maps?$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*-\s*Bing\s*Maps?$', '', name, flags=re.IGNORECASE)
        
        # Standardize common business entity types
        entity_replacements = {
            r'\bllc\b': 'LLC',
            r'\binc\b': 'Inc',
            r'\bcorp\b': 'Corp',
            r'\bltd\b': 'Ltd',
            r'\s+': ' '
        }
        
        for pattern, replacement in entity_replacements.items():
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)
        
        return name.strip()
    
    def _normalize_address(self, address: str) -> Optional[str]:
        """Normalize address format."""
        if not address:
            return None
        
        # Remove extra whitespace
        address = ' '.join(address.strip().split())
        
        # Standardize common abbreviations
        address_replacements = {
            r'\bstreet\b': 'St',
            r'\bavenue\b': 'Ave',
            r'\broad\b': 'Rd',
            r'\blane\b': 'Ln',
            r'\bdrive\b': 'Dr',
            r'\bboulevard\b': 'Blvd',
            r'\bparkway\b': 'Pkwy',
            r'\bsuite\b': 'Ste',
            r'\bapartment\b': 'Apt',
            r'\bnorth\b': 'N',
            r'\bsouth\b': 'S',
            r'\beast\b': 'E',
            r'\bwest\b': 'W'
        }
        
        for pattern, replacement in address_replacements.items():
            address = re.sub(pattern, replacement, address, flags=re.IGNORECASE)
        
        # Ensure proper capitalization
        address = ' '.join(word.capitalize() for word in address.split())
        
        return address.strip()
    
    def _normalize_phone_number(self, phone: str) -> Optional[str]:
        """Normalize phone number format."""
        if not phone:
            return None
        
        # Remove all non-digit characters except + for international
        digits = re.sub(r'[^\d+]', '', phone)
        
        # Handle different phone number formats
        if digits.startswith('+1'):
            digits = digits[2:]  # Remove +1 for US numbers
        elif digits.startswith('1') and len(digits) == 11:
            digits = digits[1:]  # Remove leading 1 for US numbers
        
        # Format US phone numbers
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            # Return original format for international or non-standard numbers
            return phone.strip()
    
    def _normalize_website_url(self, website: str) -> Optional[str]:
        """Normalize website URL."""
        if not website:
            return None
        
        website = website.strip().lower()
        
        # Add protocol if missing
        if not website.startswith(('http://', 'https://')):
            website = 'https://' + website
        
        # Remove trailing slashes and common tracking parameters
        website = re.sub(r'/$', '', website)
        website = re.sub(r'[?&](?:utm_|gclid|fbclid)', '', website)
        
        return website
    
    def _normalize_rating(self, rating: BusinessRating) -> Optional[BusinessRating]:
        """Normalize rating information."""
        if not rating:
            return None
        
        # Ensure score is within valid range
        if rating.score is not None:
            rating.score = max(0.0, min(5.0, rating.score))
        
        # Ensure review count is non-negative
        if rating.review_count is not None:
            rating.review_count = max(0, rating.review_count)
        
        return rating
    
    def _normalize_hours(self, hours: BusinessHours) -> Optional[BusinessHours]:
        """Normalize business hours."""
        if not hours:
            return None
        
        # Standardize time format
        time_pattern = re.compile(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', re.IGNORECASE)
        
        normalized_hours = BusinessHours()
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            day_hours = getattr(hours, day)
            if day_hours:
                # Standardize time format
                normalized_time = self._normalize_time_string(day_hours)
                setattr(normalized_hours, day, normalized_time)
        
        return normalized_hours
    
    def _normalize_time_string(self, time_str: str) -> str:
        """Normalize time string format."""
        if not time_str:
            return ""
        
        # Handle common time formats
        time_patterns = [
            (r'(\d{1,2}):(\d{2})\s*(am|pm)', r'\1:\2 \3'),
            (r'(\d{1,2})\s*(am|pm)', r'\1:00 \2'),
            (r'24\s*hours?', '24 hours'),
            (r'closed', 'Closed')
        ]
        
        result = time_str.lower()
        for pattern, replacement in time_patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result.strip()
    
    def _normalize_category(self, category: str) -> Optional[str]:
        """Normalize business category."""
        if not category:
            return None
        
        category = category.strip()
        
        # Standardize common categories
        category_mappings = {
            'restaurant': 'Restaurant',
            'cafe': 'Cafe',
            'hotel': 'Hotel',
            'gas station': 'Gas Station',
            'pharmacy': 'Pharmacy',
            'grocery store': 'Grocery Store',
            'shopping mall': 'Shopping Mall',
            'bank': 'Bank'
        }
        
        category_lower = category.lower()
        for key, value in category_mappings.items():
            if key in category_lower:
                return value
        
        # Capitalize first letter of each word
        return ' '.join(word.capitalize() for word in category.split())
    
    def _normalize_description(self, description: str) -> Optional[str]:
        """Normalize business description."""
        if not description:
            return None
        
        # Remove extra whitespace and limit length
        description = ' '.join(description.strip().split())
        
        # Limit description length
        max_length = 500
        if len(description) > max_length:
            description = description[:max_length].rsplit(' ', 1)[0] + '...'
        
        return description.strip()
    
    def _deduplicate_businesses(self, businesses: List[BusinessEntity]) -> List[BusinessEntity]:
        """Deduplicate business entities using similarity matching."""
        if not businesses:
            return []
        
        # Create collection for automatic deduplication
        collection = BusinessEntityCollection(similarity_threshold=self.similarity_threshold)
        
        # Group businesses by normalized name for faster comparison
        name_groups = defaultdict(list)
        for business in businesses:
            normalized_name = self._get_normalized_name_key(business.name)
            name_groups[normalized_name].append(business)
        
        # Process each group
        for group_businesses in name_groups.values():
            if len(group_businesses) == 1:
                # Single business, add directly
                collection.add_entity(group_businesses[0])
            else:
                # Multiple businesses with similar names, need detailed comparison
                self._deduplicate_business_group(group_businesses, collection)
        
        return collection.get_entities()
    
    def _get_normalized_name_key(self, name: str) -> str:
        """Get normalized name key for grouping."""
        if not name:
            return ""
        
        # Remove common words and punctuation for grouping
        key = re.sub(r'[^\w\s]', '', name.lower())
        key = re.sub(r'\b(?:the|and|of|in|at|on|for|with|by)\b', '', key)
        key = re.sub(r'\s+', ' ', key).strip()
        
        return key
    
    def _deduplicate_business_group(self, businesses: List[BusinessEntity], collection: BusinessEntityCollection):
        """Deduplicate a group of businesses with similar names."""
        # Sort by data completeness (more complete entries first)
        businesses.sort(key=self._get_data_completeness_score, reverse=True)
        
        for business in businesses:
            collection.add_entity(business)
    
    def _get_data_completeness_score(self, business: BusinessEntity) -> float:
        """Calculate data completeness score for prioritizing during deduplication."""
        score = 0.0
        
        # Core data fields
        if business.name:
            score += 2.0
        if business.address:
            score += 1.5
        if business.phone:
            score += 1.0
        if business.website:
            score += 1.0
        
        # Additional data fields
        if business.rating and business.rating.score is not None:
            score += 0.5
        if business.hours:
            score += 0.3
        if business.category:
            score += 0.2
        if business.description:
            score += 0.2
        if business.coordinates:
            score += 0.3
        
        return score
    
    def _final_quality_check(self, businesses: List[BusinessEntity]) -> List[BusinessEntity]:
        """Perform final quality checks and sorting."""
        quality_businesses = []
        
        for business in businesses:
            # Skip businesses with insufficient data
            if not self._meets_quality_standards(business):
                continue
            
            quality_businesses.append(business)
        
        # Sort by data completeness and rating
        quality_businesses.sort(key=lambda b: (
            self._get_data_completeness_score(b),
            b.rating.score if b.rating and b.rating.score else 0.0
        ), reverse=True)
        
        return quality_businesses
    
    def _meets_quality_standards(self, business: BusinessEntity) -> bool:
        """Check if business meets minimum quality standards."""
        # Must have name
        if not business.name or len(business.name) < 2:
            return False
        
        # Must have at least one contact method
        if not any([business.address, business.phone, business.website]):
            return False
        
        # Check for obvious spam patterns
        spam_patterns = [
            r'test\s*business',
            r'fake\s*company',
            r'sample\s*data',
            r'^\d+$',  # Just numbers
            r'^[a-z]+$'  # All lowercase single word
        ]
        
        name_lower = business.name.lower()
        for pattern in spam_patterns:
            if re.search(pattern, name_lower):
                return False
        
        return True
    
    def analyze_duplicate_statistics(self, business_lists: List[List[BusinessEntity]]) -> Dict[str, Any]:
        """Analyze duplicate statistics across sources."""
        all_businesses = []
        for business_list in business_lists:
            all_businesses.extend(business_list)
        
        if not all_businesses:
            return {'error': 'No businesses to analyze'}
        
        # Group by source
        source_stats = defaultdict(int)
        for business in all_businesses:
            source_stats[business.source] += 1
        
        # Find potential duplicates
        potential_duplicates = []
        for i, business1 in enumerate(all_businesses):
            for j, business2 in enumerate(all_businesses[i+1:], i+1):
                similarity = business1.similarity_score(business2)
                if similarity >= self.similarity_threshold:
                    potential_duplicates.append({
                        'business1': business1.name,
                        'business2': business2.name,
                        'similarity': similarity,
                        'source1': business1.source,
                        'source2': business2.source
                    })
        
        # Deduplicate to get final count
        deduplicated = self.normalize_and_deduplicate(business_lists)
        
        return {
            'total_input_businesses': len(all_businesses),
            'source_breakdown': dict(source_stats),
            'potential_duplicates': len(potential_duplicates),
            'duplicate_details': potential_duplicates[:10],  # First 10 examples
            'final_unique_businesses': len(deduplicated),
            'deduplication_rate': (len(all_businesses) - len(deduplicated)) / len(all_businesses) if all_businesses else 0
        }
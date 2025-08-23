"""
Business Categories - Define business types and categories for query generation

Features:
- Hierarchical business categories
- Industry classifications
- Search term variations and synonyms
- Category-specific query patterns
- Business type validation and normalization
"""
import json
import logging
from typing import Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class BusinessTier(Enum):
    """Business tiers for prioritization"""
    ENTERPRISE = "enterprise"
    MEDIUM = "medium" 
    SMALL = "small"
    MICRO = "micro"
    ALL = "all"


@dataclass
class BusinessCategory:
    """Represents a business category with metadata"""
    name: str
    parent: Optional[str] = None
    tier: BusinessTier = BusinessTier.ALL
    keywords: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    excluded_terms: List[str] = field(default_factory=list)
    typical_size: Optional[str] = None
    industry_code: Optional[str] = None  # NAICS code
    search_priority: int = 1  # 1-5, higher = more important
    
    def __post_init__(self):
        """Initialize keywords with name if empty"""
        if not self.keywords:
            self.keywords = [self.name.lower()]
    
    @property
    def all_terms(self) -> List[str]:
        """Get all search terms including name, keywords, and synonyms"""
        terms = [self.name]
        terms.extend(self.keywords)
        terms.extend(self.synonyms)
        return list(set(terms))


@dataclass  
class BusinessType:
    """Specific business type within a category"""
    name: str
    category: str
    variations: List[str] = field(default_factory=list)
    common_suffixes: List[str] = field(default_factory=list)
    search_patterns: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize default patterns"""
        if not self.search_patterns:
            self.search_patterns = [
                self.name,
                f"{self.name} near me",
                f"best {self.name}",
                f"top {self.name}"
            ]


class BusinessCategoryManager:
    """
    Manage business categories and types for query generation
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.categories: Dict[str, BusinessCategory] = {}
        self.types: Dict[str, BusinessType] = {}
        self._category_index: Dict[str, Set[str]] = {}
        self._type_index: Dict[str, Set[str]] = {}
        
        self._load_default_categories()
        self._load_default_types()
        self._build_indices()
    
    def _load_default_categories(self):
        """Load default business categories"""
        default_categories = [
            # Food & Dining
            BusinessCategory(
                "restaurants", tier=BusinessTier.ALL, 
                keywords=["restaurant", "dining", "eatery", "bistro"],
                synonyms=["food", "cuisine", "meals", "diner"],
                search_priority=5
            ),
            BusinessCategory(
                "cafes", parent="restaurants", tier=BusinessTier.SMALL,
                keywords=["cafe", "coffee shop", "coffee house"],
                synonyms=["coffee", "espresso", "java"],
                search_priority=4
            ),
            BusinessCategory(
                "bars", parent="restaurants", tier=BusinessTier.SMALL,
                keywords=["bar", "pub", "tavern", "lounge"],
                synonyms=["drinks", "cocktails", "brewery"],
                search_priority=3
            ),
            BusinessCategory(
                "fast_food", parent="restaurants", tier=BusinessTier.MEDIUM,
                keywords=["fast food", "quick service", "drive thru"],
                synonyms=["takeout", "delivery", "grab and go"],
                search_priority=4
            ),
            
            # Retail
            BusinessCategory(
                "retail", tier=BusinessTier.ALL,
                keywords=["store", "shop", "retail", "shopping"],
                synonyms=["merchandise", "goods", "products"],
                search_priority=5
            ),
            BusinessCategory(
                "clothing", parent="retail", tier=BusinessTier.ALL,
                keywords=["clothing", "apparel", "fashion"],
                synonyms=["clothes", "garments", "wear"],
                search_priority=4
            ),
            BusinessCategory(
                "electronics", parent="retail", tier=BusinessTier.MEDIUM,
                keywords=["electronics", "tech", "gadgets"],
                synonyms=["computers", "phones", "devices"],
                search_priority=4
            ),
            BusinessCategory(
                "grocery", parent="retail", tier=BusinessTier.MEDIUM,
                keywords=["grocery", "supermarket", "food store"],
                synonyms=["market", "provisions", "groceries"],
                search_priority=5
            ),
            
            # Services
            BusinessCategory(
                "professional_services", tier=BusinessTier.ALL,
                keywords=["services", "professional", "consulting"],
                synonyms=["consultant", "advisor", "expert"],
                search_priority=4
            ),
            BusinessCategory(
                "legal", parent="professional_services", tier=BusinessTier.MEDIUM,
                keywords=["lawyer", "attorney", "legal"],
                synonyms=["law firm", "counsel", "advocate"],
                search_priority=3
            ),
            BusinessCategory(
                "accounting", parent="professional_services", tier=BusinessTier.SMALL,
                keywords=["accountant", "accounting", "bookkeeping"],
                synonyms=["CPA", "tax", "financial"],
                search_priority=3
            ),
            BusinessCategory(
                "real_estate", parent="professional_services", tier=BusinessTier.MEDIUM,
                keywords=["real estate", "realtor", "property"],
                synonyms=["homes", "houses", "agent"],
                search_priority=4
            ),
            
            # Healthcare
            BusinessCategory(
                "healthcare", tier=BusinessTier.ALL,
                keywords=["healthcare", "medical", "health"],
                synonyms=["medicine", "clinic", "doctor"],
                search_priority=5
            ),
            BusinessCategory(
                "dental", parent="healthcare", tier=BusinessTier.SMALL,
                keywords=["dentist", "dental", "teeth"],
                synonyms=["oral health", "orthodontist", "hygienist"],
                search_priority=4
            ),
            BusinessCategory(
                "veterinary", parent="healthcare", tier=BusinessTier.SMALL,
                keywords=["veterinarian", "vet", "animal hospital"],
                synonyms=["pet care", "animal clinic", "veterinary"],
                search_priority=3
            ),
            
            # Automotive
            BusinessCategory(
                "automotive", tier=BusinessTier.MEDIUM,
                keywords=["automotive", "car", "auto"],
                synonyms=["vehicle", "automobile", "motor"],
                search_priority=4
            ),
            BusinessCategory(
                "auto_repair", parent="automotive", tier=BusinessTier.SMALL,
                keywords=["auto repair", "mechanic", "garage"],
                synonyms=["car repair", "service center", "maintenance"],
                search_priority=4
            ),
            BusinessCategory(
                "car_dealers", parent="automotive", tier=BusinessTier.MEDIUM,
                keywords=["car dealer", "auto sales", "dealership"],
                synonyms=["car lot", "auto dealer", "vehicles"],
                search_priority=3
            ),
            
            # Beauty & Wellness
            BusinessCategory(
                "beauty", tier=BusinessTier.SMALL,
                keywords=["beauty", "salon", "spa"],
                synonyms=["cosmetics", "wellness", "treatment"],
                search_priority=3
            ),
            BusinessCategory(
                "hair_salon", parent="beauty", tier=BusinessTier.SMALL,
                keywords=["hair salon", "hairdresser", "barber"],
                synonyms=["hair stylist", "haircut", "styling"],
                search_priority=4
            ),
            
            # Finance
            BusinessCategory(
                "finance", tier=BusinessTier.MEDIUM,
                keywords=["bank", "finance", "financial"],
                synonyms=["banking", "money", "credit"],
                search_priority=4
            ),
            BusinessCategory(
                "insurance", parent="finance", tier=BusinessTier.MEDIUM,
                keywords=["insurance", "coverage", "policy"],
                synonyms=["protection", "claims", "agent"],
                search_priority=3
            ),
            
            # Education
            BusinessCategory(
                "education", tier=BusinessTier.ALL,
                keywords=["education", "school", "learning"],
                synonyms=["academy", "institute", "training"],
                search_priority=4
            ),
            
            # Entertainment
            BusinessCategory(
                "entertainment", tier=BusinessTier.ALL,
                keywords=["entertainment", "fun", "recreation"],
                synonyms=["leisure", "activity", "venue"],
                search_priority=3
            ),
            BusinessCategory(
                "fitness", parent="entertainment", tier=BusinessTier.SMALL,
                keywords=["gym", "fitness", "workout"],
                synonyms=["exercise", "health club", "training"],
                search_priority=4
            ),
        ]
        
        for category in default_categories:
            self.add_category(category)
    
    def _load_default_types(self):
        """Load default business types"""
        default_types = [
            # Restaurant types
            BusinessType(
                "pizza restaurant", "restaurants",
                variations=["pizza", "pizzeria", "pizza place"],
                common_suffixes=["restaurant", "place", "shop"]
            ),
            BusinessType(
                "chinese restaurant", "restaurants",
                variations=["chinese food", "chinese cuisine", "asian restaurant"]
            ),
            BusinessType(
                "italian restaurant", "restaurants",
                variations=["italian food", "italian cuisine"]
            ),
            BusinessType(
                "mexican restaurant", "restaurants", 
                variations=["mexican food", "mexican cuisine", "taco shop"]
            ),
            
            # Retail types
            BusinessType(
                "department store", "retail",
                variations=["department stores", "big box store"]
            ),
            BusinessType(
                "shoe store", "clothing",
                variations=["shoes", "footwear", "shoe shop"]
            ),
            
            # Service types
            BusinessType(
                "plumber", "professional_services",
                variations=["plumbing", "plumbing service", "pipe repair"]
            ),
            BusinessType(
                "electrician", "professional_services",
                variations=["electrical", "electrical service", "wiring"]
            ),
            BusinessType(
                "contractor", "professional_services",
                variations=["general contractor", "construction", "builder"]
            ),
            
            # Healthcare types
            BusinessType(
                "family doctor", "healthcare",
                variations=["family physician", "primary care", "GP"]
            ),
            BusinessType(
                "specialist", "healthcare",
                variations=["medical specialist", "doctor specialist"]
            ),
        ]
        
        for btype in default_types:
            self.add_type(btype)
    
    def _build_indices(self):
        """Build search indices for fast lookups"""
        self._category_index.clear()
        self._type_index.clear()
        
        # Build category index
        for name, category in self.categories.items():
            for term in category.all_terms:
                normalized_term = self._normalize_term(term)
                if normalized_term not in self._category_index:
                    self._category_index[normalized_term] = set()
                self._category_index[normalized_term].add(name)
        
        # Build type index
        for name, btype in self.types.items():
            terms = [btype.name] + btype.variations
            for term in terms:
                normalized_term = self._normalize_term(term)
                if normalized_term not in self._type_index:
                    self._type_index[normalized_term] = set()
                self._type_index[normalized_term].add(name)
    
    def _normalize_term(self, term: str) -> str:
        """Normalize term for indexing"""
        import re
        return re.sub(r'[^\w\s]', '', term.lower().strip())
    
    def add_category(self, category: BusinessCategory):
        """Add a business category"""
        self.categories[category.name] = category
        logger.debug(f"Added category: {category.name}")
    
    def add_type(self, business_type: BusinessType):
        """Add a business type"""
        self.types[business_type.name] = business_type
        logger.debug(f"Added business type: {business_type.name}")
    
    def get_category(self, name: str) -> Optional[BusinessCategory]:
        """Get a category by name"""
        return self.categories.get(name)
    
    def get_type(self, name: str) -> Optional[BusinessType]:
        """Get a business type by name"""
        return self.types.get(name)
    
    def search_categories(self, query: str, limit: int = 10) -> List[BusinessCategory]:
        """Search for categories matching query"""
        normalized_query = self._normalize_term(query)
        matching_names = set()
        
        # Exact matches
        if normalized_query in self._category_index:
            matching_names.update(self._category_index[normalized_query])
        
        # Partial matches
        for term, category_names in self._category_index.items():
            if normalized_query in term or term in normalized_query:
                matching_names.update(category_names)
        
        # Convert to objects and sort by search priority
        results = [self.categories[name] for name in matching_names if name in self.categories]
        results.sort(key=lambda x: x.search_priority, reverse=True)
        
        return results[:limit]
    
    def search_types(self, query: str, limit: int = 10) -> List[BusinessType]:
        """Search for business types matching query"""
        normalized_query = self._normalize_term(query)
        matching_names = set()
        
        # Exact matches
        if normalized_query in self._type_index:
            matching_names.update(self._type_index[normalized_query])
        
        # Partial matches
        for term, type_names in self._type_index.items():
            if normalized_query in term or term in normalized_query:
                matching_names.update(type_names)
        
        results = [self.types[name] for name in matching_names if name in self.types]
        return results[:limit]
    
    def get_categories_by_tier(self, tier: BusinessTier) -> List[BusinessCategory]:
        """Get categories filtered by business tier"""
        if tier == BusinessTier.ALL:
            return list(self.categories.values())
        
        return [cat for cat in self.categories.values() if cat.tier == tier]
    
    def get_category_hierarchy(self, category_name: str) -> List[BusinessCategory]:
        """Get category hierarchy (parent chain)"""
        hierarchy = []
        current = self.get_category(category_name)
        
        while current:
            hierarchy.insert(0, current)
            if current.parent:
                current = self.get_category(current.parent)
            else:
                break
        
        return hierarchy
    
    def get_subcategories(self, parent_name: str) -> List[BusinessCategory]:
        """Get all subcategories of a parent category"""
        return [cat for cat in self.categories.values() if cat.parent == parent_name]
    
    def get_types_in_category(self, category_name: str) -> List[BusinessType]:
        """Get all business types in a category"""
        return [btype for btype in self.types.values() if btype.category == category_name]
    
    def generate_search_terms(self, business_query: str, 
                            include_variations: bool = True,
                            include_suffixes: bool = True) -> List[str]:
        """
        Generate search terms for a business query
        
        Args:
            business_query: Base business search term
            include_variations: Include variations and synonyms
            include_suffixes: Include common business suffixes
            
        Returns:
            List of search terms
        """
        terms = [business_query]
        
        # Find matching categories and types
        categories = self.search_categories(business_query, limit=3)
        types = self.search_types(business_query, limit=3)
        
        if include_variations:
            # Add category terms
            for category in categories:
                terms.extend(category.all_terms)
            
            # Add type variations
            for btype in types:
                terms.extend([btype.name] + btype.variations)
        
        if include_suffixes:
            # Add common business suffixes
            common_suffixes = [
                "business", "company", "service", "services", 
                "shop", "store", "center", "clinic"
            ]
            
            for suffix in common_suffixes:
                if not any(suffix in term.lower() for term in terms):
                    terms.append(f"{business_query} {suffix}")
        
        # Remove duplicates and normalize
        unique_terms = []
        seen = set()
        
        for term in terms:
            normalized = term.lower().strip()
            if normalized and normalized not in seen:
                unique_terms.append(term)
                seen.add(normalized)
        
        return unique_terms
    
    def load_from_csv(self, csv_file: str, type_field: str = "categories"):
        """
        Load business categories/types from CSV
        
        Expected CSV format:
        name,category,keywords,synonyms,tier,priority
        """
        csv_path = self.data_dir / csv_file
        if not csv_path.exists():
            logger.warning(f"CSV file not found: {csv_path}")
            return
        
        import csv
        
        loaded_count = 0
        try:
            with open(csv_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        if type_field == "categories":
                            self._create_category_from_row(row)
                        else:
                            self._create_type_from_row(row)
                        loaded_count += 1
                    except Exception as e:
                        logger.error(f"Error processing row {loaded_count + 1}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error reading CSV file {csv_path}: {e}")
            return
        
        logger.info(f"Loaded {loaded_count} {type_field} from {csv_file}")
        self._build_indices()
    
    def _create_category_from_row(self, row: Dict[str, str]):
        """Create BusinessCategory from CSV row"""
        name = row.get('name', '').strip()
        if not name:
            return
        
        keywords = [k.strip() for k in row.get('keywords', '').split(',') if k.strip()]
        synonyms = [s.strip() for s in row.get('synonyms', '').split(',') if s.strip()]
        
        try:
            tier = BusinessTier(row.get('tier', 'all').lower())
        except ValueError:
            tier = BusinessTier.ALL
        
        try:
            priority = int(row.get('priority', '1'))
        except ValueError:
            priority = 1
        
        category = BusinessCategory(
            name=name,
            parent=row.get('parent') or None,
            tier=tier,
            keywords=keywords,
            synonyms=synonyms,
            search_priority=priority
        )
        
        self.add_category(category)
    
    def _create_type_from_row(self, row: Dict[str, str]):
        """Create BusinessType from CSV row"""
        name = row.get('name', '').strip()
        category = row.get('category', '').strip()
        
        if not name or not category:
            return
        
        variations = [v.strip() for v in row.get('variations', '').split(',') if v.strip()]
        suffixes = [s.strip() for s in row.get('suffixes', '').split(',') if s.strip()]
        
        business_type = BusinessType(
            name=name,
            category=category,
            variations=variations,
            common_suffixes=suffixes
        )
        
        self.add_type(business_type)
    
    def export_to_csv(self, filename: str, export_type: str = "categories"):
        """Export categories or types to CSV file"""
        output_path = self.data_dir / filename
        
        import csv
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            if export_type == "categories":
                writer.writerow(['name', 'parent', 'tier', 'keywords', 'synonyms', 'priority'])
                for category in sorted(self.categories.values(), key=lambda x: x.name):
                    writer.writerow([
                        category.name,
                        category.parent or '',
                        category.tier.value,
                        ','.join(category.keywords),
                        ','.join(category.synonyms),
                        category.search_priority
                    ])
            else:
                writer.writerow(['name', 'category', 'variations', 'suffixes'])
                for btype in sorted(self.types.values(), key=lambda x: x.name):
                    writer.writerow([
                        btype.name,
                        btype.category,
                        ','.join(btype.variations),
                        ','.join(btype.common_suffixes)
                    ])
        
        logger.info(f"Exported {export_type} to {output_path}")
    
    def get_statistics(self) -> Dict[str, Union[int, Dict]]:
        """Get statistics about categories and types"""
        stats = {
            'total_categories': len(self.categories),
            'total_types': len(self.types),
            'by_tier': {},
            'by_parent': {},
            'top_categories': []
        }
        
        # Count by tier
        for category in self.categories.values():
            tier = category.tier.value
            stats['by_tier'][tier] = stats['by_tier'].get(tier, 0) + 1
        
        # Count by parent
        for category in self.categories.values():
            parent = category.parent or 'root'
            stats['by_parent'][parent] = stats['by_parent'].get(parent, 0) + 1
        
        # Top categories by priority
        top_categories = sorted(self.categories.values(), 
                              key=lambda x: x.search_priority, reverse=True)[:10]
        stats['top_categories'] = [(cat.name, cat.search_priority) for cat in top_categories]
        
        return stats


# Convenience functions
def create_default_manager(data_dir: str = "data") -> BusinessCategoryManager:
    """Create manager with default categories loaded"""
    manager = BusinessCategoryManager(data_dir)
    
    # Try to load from CSV files
    try:
        manager.load_from_csv("business_types.csv", "categories")
    except Exception as e:
        logger.debug(f"Could not load business_types.csv: {e}")
    
    return manager


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    manager = BusinessCategoryManager()
    
    # Search for categories
    restaurants = manager.search_categories("food")
    print(f"Found {len(restaurants)} food-related categories")
    
    # Search for types
    pizza_types = manager.search_types("pizza")
    print(f"Found {len(pizza_types)} pizza-related types")
    
    # Generate search terms
    terms = manager.generate_search_terms("pizza restaurant")
    print(f"Generated {len(terms)} search terms for pizza restaurant")
    
    # Show statistics
    stats = manager.get_statistics()
    print(f"Manager statistics: {stats}")
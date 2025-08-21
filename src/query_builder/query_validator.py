"""
Query Validation System

Validates search queries for format, content, safety, and optimization.
Ensures queries meet search engine requirements and quality standards.
"""

import logging
import re
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import string
from urllib.parse import quote

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"       # Query is invalid and should not be used
    WARNING = "warning"   # Query may work but has issues
    INFO = "info"        # Informational notice about query


@dataclass
class ValidationResult:
    """Result of query validation."""
    
    query: str
    is_valid: bool
    issues: List[Tuple[ValidationSeverity, str]]
    suggestions: List[str]
    optimized_query: Optional[str] = None
    
    def has_errors(self) -> bool:
        """Check if validation found any errors."""
        return any(severity == ValidationSeverity.ERROR for severity, _ in self.issues)
    
    def has_warnings(self) -> bool:
        """Check if validation found any warnings."""
        return any(severity == ValidationSeverity.WARNING for severity, _ in self.issues)
    
    def get_error_messages(self) -> List[str]:
        """Get all error messages."""
        return [msg for severity, msg in self.issues if severity == ValidationSeverity.ERROR]
    
    def get_warning_messages(self) -> List[str]:
        """Get all warning messages."""
        return [msg for severity, msg in self.issues if severity == ValidationSeverity.WARNING]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            'query': self.query,
            'is_valid': self.is_valid,
            'issues': [(severity.value, msg) for severity, msg in self.issues],
            'suggestions': self.suggestions,
            'optimized_query': self.optimized_query
        }


class QueryValidator:
    """
    Comprehensive query validation system for search queries.
    
    Validates queries for:
    - Basic format and syntax
    - Search engine compatibility
    - Content safety and appropriateness  
    - Length and complexity limits
    - Optimization opportunities
    """
    
    def __init__(self):
        """Initialize query validator with validation rules."""
        self.max_query_length = 500
        self.max_words = 50
        self.max_operators = 20
        
        # Prohibited content patterns
        self.prohibited_patterns = [
            r'\b(porn|xxx|adult)\b',
            r'\b(hack|crack|pirate)\b',
            r'\b(illegal|drugs)\b',
            r'\b(spam|scam)\b'
        ]
        
        # Search operator patterns
        self.search_operators = {
            'site': r'site:[^\s]+',
            'filetype': r'filetype:[^\s]+',
            'inurl': r'inurl:[^\s]+',
            'intitle': r'intitle:[^\s]+',
            'intext': r'intext:[^\s]+',
            'related': r'related:[^\s]+',
            'cache': r'cache:[^\s]+',
            'define': r'define:[^\s]+',
            'stocks': r'stocks:[^\s]+',
            'weather': r'weather:[^\s]+',
            'info': r'info:[^\s]+',
            'link': r'link:[^\s]+',
            'OR': r'\bOR\b',
            'AND': r'\bAND\b',
            'NOT': r'\bNOT\b'
        }
        
        # Common query quality issues
        self.quality_patterns = {
            'too_many_quotes': r'"[^"]*".*"[^"]*".*"[^"]*"',  # 3+ quoted phrases
            'excessive_operators': r'(site:|filetype:|inurl:|intitle:).*?(site:|filetype:|inurl:|intitle:).*?(site:|filetype:|inurl:|intitle:)',
            'redundant_words': r'\b(\w+)\s+\1\b',  # Repeated words
            'too_many_ands': r'\bAND\b.*?\bAND\b.*?\bAND\b',  # 3+ ANDs
            'empty_quotes': r'""',
            'unmatched_quotes': r'(?:^|[^"])("[^"]*(?:"[^"]*"[^"]*)*[^"]*)(?:[^"]|$)',
            'trailing_operators': r'(AND|OR|NOT)\s*$',
            'leading_operators': r'^\s*(AND|OR)',
            'excessive_wildcards': r'\*.*?\*.*?\*'  # 3+ wildcards
        }
        
        logger.info("QueryValidator initialized with validation rules")
    
    def validate_query(self, query: str) -> ValidationResult:
        """
        Perform comprehensive validation of a search query.
        
        Args:
            query: Search query to validate
            
        Returns:
            ValidationResult with issues and suggestions
        """
        issues = []
        suggestions = []
        optimized_query = None
        
        # Basic format validation
        basic_issues, basic_suggestions = self._validate_basic_format(query)
        issues.extend(basic_issues)
        suggestions.extend(basic_suggestions)
        
        # Content safety validation
        safety_issues, safety_suggestions = self._validate_content_safety(query)
        issues.extend(safety_issues)
        suggestions.extend(safety_suggestions)
        
        # Search operator validation
        operator_issues, operator_suggestions = self._validate_search_operators(query)
        issues.extend(operator_issues)
        suggestions.extend(operator_suggestions)
        
        # Quality validation
        quality_issues, quality_suggestions = self._validate_query_quality(query)
        issues.extend(quality_issues)
        suggestions.extend(quality_suggestions)
        
        # Search engine compatibility
        compat_issues, compat_suggestions = self._validate_search_engine_compatibility(query)
        issues.extend(compat_issues)
        suggestions.extend(compat_suggestions)
        
        # Generate optimized query if possible
        if not any(severity == ValidationSeverity.ERROR for severity, _ in issues):
            optimized_query = self._optimize_query(query)
        
        # Determine if query is valid (no errors)
        is_valid = not any(severity == ValidationSeverity.ERROR for severity, _ in issues)
        
        return ValidationResult(
            query=query,
            is_valid=is_valid,
            issues=issues,
            suggestions=suggestions,
            optimized_query=optimized_query
        )
    
    def _validate_basic_format(self, query: str) -> Tuple[List[Tuple[ValidationSeverity, str]], List[str]]:
        """Validate basic query format and structure."""
        issues = []
        suggestions = []
        
        # Check if query is empty or whitespace only
        if not query or not query.strip():
            issues.append((ValidationSeverity.ERROR, "Query is empty"))
            suggestions.append("Provide a non-empty search query")
            return issues, suggestions
        
        # Check query length
        if len(query) > self.max_query_length:
            issues.append((ValidationSeverity.ERROR, f"Query exceeds maximum length of {self.max_query_length} characters"))
            suggestions.append("Shorten the query by removing unnecessary words")
        
        # Check word count
        words = query.split()
        if len(words) > self.max_words:
            issues.append((ValidationSeverity.WARNING, f"Query has {len(words)} words, consider reducing for better performance"))
            suggestions.append("Reduce the number of words for more focused results")
        
        # Check for control characters and unusual unicode
        if any(ord(c) < 32 or ord(c) > 126 for c in query if c not in string.printable):
            issues.append((ValidationSeverity.WARNING, "Query contains non-printable or unusual characters"))
            suggestions.append("Remove special characters that may cause search issues")
        
        # Check for excessive whitespace
        if re.search(r'\s{3,}', query):
            issues.append((ValidationSeverity.INFO, "Query contains excessive whitespace"))
            suggestions.append("Remove extra spaces for cleaner formatting")
        
        return issues, suggestions
    
    def _validate_content_safety(self, query: str) -> Tuple[List[Tuple[ValidationSeverity, str]], List[str]]:
        """Validate query content for safety and appropriateness."""
        issues = []
        suggestions = []
        
        query_lower = query.lower()
        
        # Check for prohibited content
        for pattern in self.prohibited_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                issues.append((ValidationSeverity.ERROR, f"Query contains prohibited content matching pattern: {pattern}"))
                suggestions.append("Remove inappropriate or prohibited terms")
        
        # Check for potential injection attempts
        if re.search(r'[<>\'";\\]', query):
            issues.append((ValidationSeverity.WARNING, "Query contains characters that might cause parsing issues"))
            suggestions.append("Avoid special characters that could be interpreted as code")
        
        return issues, suggestions
    
    def _validate_search_operators(self, query: str) -> Tuple[List[Tuple[ValidationSeverity, str]], List[str]]:
        """Validate search operators and their usage."""
        issues = []
        suggestions = []
        
        # Count total operators
        operator_count = 0
        used_operators = []
        
        for operator_name, pattern in self.search_operators.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                operator_count += len(matches)
                used_operators.append(operator_name)
        
        # Check for excessive operators
        if operator_count > self.max_operators:
            issues.append((ValidationSeverity.WARNING, f"Query uses {operator_count} operators, which may be excessive"))
            suggestions.append("Consider simplifying the query by reducing the number of operators")
        
        # Check for malformed operators
        operator_patterns = [
            (r'site:\s', "site: operator should not have space after colon"),
            (r'filetype:\s', "filetype: operator should not have space after colon"),
            (r'inurl:\s', "inurl: operator should not have space after colon"),
            (r'intitle:\s', "intitle: operator should not have space after colon"),
        ]
        
        for pattern, message in operator_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                issues.append((ValidationSeverity.WARNING, message))
                suggestions.append("Remove spaces after operator colons")
        
        # Check for conflicting operators
        if 'site' in used_operators and query.count('site:') > 3:
            issues.append((ValidationSeverity.WARNING, "Multiple site: operators may limit results too much"))
            suggestions.append("Consider using fewer site restrictions")
        
        return issues, suggestions
    
    def _validate_query_quality(self, query: str) -> Tuple[List[Tuple[ValidationSeverity, str]], List[str]]:
        """Validate query quality and effectiveness."""
        issues = []
        suggestions = []
        
        # Check for quality issues
        for issue_name, pattern in self.quality_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                if issue_name == 'too_many_quotes':
                    issues.append((ValidationSeverity.WARNING, "Query has multiple quoted phrases which may be too restrictive"))
                    suggestions.append("Consider reducing the number of quoted phrases")
                
                elif issue_name == 'excessive_operators':
                    issues.append((ValidationSeverity.WARNING, "Query has excessive search operators"))
                    suggestions.append("Simplify by using fewer operators")
                
                elif issue_name == 'redundant_words':
                    issues.append((ValidationSeverity.INFO, "Query contains repeated words"))
                    suggestions.append("Remove duplicate words for cleaner query")
                
                elif issue_name == 'empty_quotes':
                    issues.append((ValidationSeverity.ERROR, "Query contains empty quotes"))
                    suggestions.append("Remove empty quote pairs")
                
                elif issue_name == 'unmatched_quotes':
                    issues.append((ValidationSeverity.ERROR, "Query has unmatched quotes"))
                    suggestions.append("Ensure all quotes are properly paired")
                
                elif issue_name == 'trailing_operators':
                    issues.append((ValidationSeverity.ERROR, "Query ends with boolean operator"))
                    suggestions.append("Remove trailing AND/OR/NOT operators")
                
                elif issue_name == 'leading_operators':
                    issues.append((ValidationSeverity.ERROR, "Query starts with boolean operator"))
                    suggestions.append("Remove leading AND/OR operators")
        
        # Check for very short queries that might be too broad
        meaningful_words = [w for w in query.split() if len(w) > 2 and not re.match(r'^(and|or|not|the|a|an|in|on|at|to|for|of|with|by)$', w.lower())]
        if len(meaningful_words) < 2:
            issues.append((ValidationSeverity.INFO, "Query may be too broad with few meaningful terms"))
            suggestions.append("Add more specific terms to narrow results")
        
        return issues, suggestions
    
    def _validate_search_engine_compatibility(self, query: str) -> Tuple[List[Tuple[ValidationSeverity, str]], List[str]]:
        """Validate compatibility with search engines."""
        issues = []
        suggestions = []
        
        # Check URL encoding requirements
        if any(c in query for c in ['&', '=', '?', '#', '%']):
            issues.append((ValidationSeverity.INFO, "Query contains characters that need URL encoding"))
            suggestions.append("Query will be automatically URL-encoded when submitted")
        
        # Check for Bing-specific considerations
        if re.search(r'\+[^+\s]', query):
            issues.append((ValidationSeverity.INFO, "Query uses + operator (Bing interprets + as AND)"))
            suggestions.append("Consider using explicit AND operator for clarity")
        
        # Check for Google-specific operators that may not work on Bing
        google_specific = ['cache:', 'define:', 'stocks:', 'weather:']
        for operator in google_specific:
            if operator in query.lower():
                issues.append((ValidationSeverity.WARNING, f"Operator {operator} may not work as expected on Bing"))
                suggestions.append("Remove Google-specific operators for Bing compatibility")
        
        return issues, suggestions
    
    def _optimize_query(self, query: str) -> str:
        """Generate optimized version of the query."""
        optimized = query
        
        # Remove excessive whitespace
        optimized = re.sub(r'\s+', ' ', optimized).strip()
        
        # Remove empty quotes
        optimized = re.sub(r'""', '', optimized)
        
        # Fix operator spacing
        optimized = re.sub(r'(site|filetype|inurl|intitle):\s+', r'\1:', optimized, flags=re.IGNORECASE)
        
        # Remove trailing operators
        optimized = re.sub(r'\s+(AND|OR|NOT)\s*$', '', optimized, flags=re.IGNORECASE)
        
        # Remove leading operators
        optimized = re.sub(r'^\s*(AND|OR)\s+', '', optimized, flags=re.IGNORECASE)
        
        # Remove duplicate words (simple case)
        words = optimized.split()
        unique_words = []
        seen = set()
        for word in words:
            word_lower = word.lower()
            if word_lower not in seen:
                unique_words.append(word)
                seen.add(word_lower)
        optimized = ' '.join(unique_words)
        
        return optimized
    
    def validate_query_batch(self, queries: List[str]) -> List[ValidationResult]:
        """Validate multiple queries efficiently."""
        results = []
        for query in queries:
            result = self.validate_query(query)
            results.append(result)
        return results
    
    def filter_valid_queries(self, queries: List[str]) -> List[str]:
        """Filter list to only include valid queries."""
        valid_queries = []
        for query in queries:
            result = self.validate_query(query)
            if result.is_valid:
                valid_queries.append(result.optimized_query or query)
        return valid_queries
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Get summary statistics for validation results."""
        total_queries = len(results)
        valid_queries = sum(1 for r in results if r.is_valid)
        error_count = sum(1 for r in results if r.has_errors())
        warning_count = sum(1 for r in results if r.has_warnings())
        
        # Count issue types
        issue_counts = {}
        for result in results:
            for severity, message in result.issues:
                issue_counts[severity.value] = issue_counts.get(severity.value, 0) + 1
        
        return {
            'total_queries': total_queries,
            'valid_queries': valid_queries,
            'invalid_queries': total_queries - valid_queries,
            'validation_rate': round((valid_queries / total_queries) * 100, 2) if total_queries > 0 else 0,
            'queries_with_errors': error_count,
            'queries_with_warnings': warning_count,
            'issue_distribution': issue_counts
        }
    
    def suggest_query_improvements(self, query: str) -> List[str]:
        """Suggest specific improvements for a query."""
        suggestions = []
        
        # Analyze query structure
        words = query.split()
        
        # Suggest more specific terms
        generic_words = ['business', 'company', 'service', 'professional', 'best', 'top', 'good']
        if any(word.lower() in generic_words for word in words):
            suggestions.append("Replace generic terms with more specific industry or service terms")
        
        # Suggest adding location if missing
        if not any(re.search(r'\b(city|state|\w+ville|\w+ton|\w+berg)\b', query, re.IGNORECASE)):
            suggestions.append("Consider adding location terms for more targeted results")
        
        # Suggest adding contact intent
        contact_terms = ['contact', 'email', 'phone', 'address']
        if not any(term in query.lower() for term in contact_terms):
            suggestions.append("Add contact-specific terms like 'email', 'contact', or 'phone'")
        
        # Suggest using quotes for phrases
        if len(words) > 1 and '"' not in query:
            suggestions.append("Consider using quotes around specific phrases")
        
        return suggestions
    
    def export_validation_rules(self) -> Dict[str, Any]:
        """Export current validation rules for documentation."""
        return {
            'max_query_length': self.max_query_length,
            'max_words': self.max_words,
            'max_operators': self.max_operators,
            'prohibited_patterns': self.prohibited_patterns,
            'supported_operators': list(self.search_operators.keys()),
            'quality_checks': list(self.quality_patterns.keys())
        }
"""
Email Deduplication Tool

Agency Swarm tool for advanced email deduplication and contact record merging.
Handles complex deduplication scenarios including similar domains, name variations,
and contact record consolidation.
"""

import logging
import time
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict, Counter
from dataclasses import asdict
from pydantic import Field

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

from agents.validator_dedupe_agent import EmailDeduplicator, ContactRecord


class EmailDeduplicationTool(BaseTool):
    """
    Tool for deduplicating email addresses and merging contact records.
    
    Provides advanced deduplication logic that handles variations in email
    addresses, domains, and associated contact information.
    """
    
    contacts: List[Dict[str, Any]] = Field(
        ...,
        description="List of contact records with email and metadata"
    )
    
    strict_mode: bool = Field(
        default=True,
        description="Enable strict deduplication (exact matches only)"
    )
    
    merge_similar_domains: bool = Field(
        default=True,
        description="Merge contacts from similar domains (e.g., company variations)"
    )
    
    similarity_threshold: float = Field(
        default=0.8,
        description="Similarity threshold for contact merging (0.0-1.0)"
    )
    
    preserve_best_quality: bool = Field(
        default=True,
        description="Preserve the highest quality contact when merging duplicates"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Deduplicate contacts and merge related records.
        
        Returns:
            Dictionary with deduplication results and statistics
        """
        start_time = time.time()
        
        # Configure deduplicator
        config = {
            "strict_deduplication": self.strict_mode,
            "merge_similar_domains": self.merge_similar_domains,
            "similarity_threshold": self.similarity_threshold
        }
        
        deduplicator = EmailDeduplicator(config)
        
        # Track original emails and processing results
        original_emails = []
        processed_contacts = []
        duplicate_groups = []
        merge_log = []
        
        # Process each contact
        for i, contact in enumerate(self.contacts):
            email = contact.get('email', '').strip().lower()
            if not email or '@' not in email:
                continue
            
            original_emails.append(email)
            
            # Create validation result placeholder for deduplication
            from agents.validator_dedupe_agent import ValidationResult, ValidationStatus, EmailQuality
            
            result = ValidationResult(
                email=email,
                status=ValidationStatus.VALID,
                is_valid=True,
                quality=EmailQuality.MEDIUM,
                confidence_score=contact.get('confidence_score', 0.5),
                normalized_email=email
            )
            
            # Check for duplicate
            result, is_duplicate = deduplicator.check_duplicate(email, result, contact)
            
            if is_duplicate:
                duplicate_groups.append({
                    'email': email,
                    'original_index': i,
                    'duplicate_of': self._find_original_email(email, original_emails[:i])
                })
            else:
                processed_contacts.append({
                    'email': email,
                    'original_index': i,
                    'contact_data': contact
                })
        
        # Get final deduplicated contacts
        final_contact_records = deduplicator.get_final_contacts()
        dedup_stats = deduplicator.get_deduplication_stats()
        
        # Generate detailed analysis
        analysis = self._analyze_deduplication_results(
            original_emails, final_contact_records, duplicate_groups
        )
        
        processing_time = time.time() - start_time
        
        return {
            'summary': {
                'original_contacts': len(self.contacts),
                'unique_emails': len(original_emails),
                'final_contacts': len(final_contact_records),
                'duplicates_removed': len(original_emails) - len(final_contact_records),
                'duplicate_rate': dedup_stats.get('duplicate_rate', 0.0),
                'processing_time_seconds': processing_time
            },
            'deduplication_stats': dedup_stats,
            'duplicate_groups': duplicate_groups,
            'final_contacts': [self._contact_record_to_dict(cr) for cr in final_contact_records],
            'analysis': analysis,
            'configuration': {
                'strict_mode': self.strict_mode,
                'merge_similar_domains': self.merge_similar_domains,
                'similarity_threshold': self.similarity_threshold,
                'preserve_best_quality': self.preserve_best_quality
            }
        }
    
    def _find_original_email(self, email: str, previous_emails: List[str]) -> Optional[str]:
        """Find the original email that this is a duplicate of"""
        # For now, just return the first occurrence
        # This could be enhanced with more sophisticated matching
        return previous_emails[0] if previous_emails else None
    
    def _contact_record_to_dict(self, contact_record: ContactRecord) -> Dict[str, Any]:
        """Convert ContactRecord to dictionary"""
        return {
            'primary_email': contact_record.primary_email,
            'all_emails': contact_record.all_emails,
            'names': contact_record.names,
            'titles': contact_record.titles,
            'companies': contact_record.companies,
            'domains': contact_record.domains,
            'phone_numbers': contact_record.phone_numbers,
            'social_profiles': contact_record.social_profiles,
            'source_urls': contact_record.source_urls,
            'discovery_methods': contact_record.discovery_methods,
            'best_confidence': contact_record.best_confidence,
            'total_occurrences': contact_record.total_occurrences,
            'first_seen': contact_record.first_seen,
            'last_seen': contact_record.last_seen
        }
    
    def _analyze_deduplication_results(self, original_emails: List[str], 
                                     final_contacts: List[ContactRecord],
                                     duplicate_groups: List[Dict]) -> Dict[str, Any]:
        """Analyze deduplication results for insights"""
        
        # Domain analysis
        domain_stats = defaultdict(lambda: {
            'original_count': 0,
            'final_count': 0,
            'duplicates_removed': 0
        })
        
        # Count original domains
        for email in original_emails:
            domain = email.split('@')[1] if '@' in email else 'unknown'
            domain_stats[domain]['original_count'] += 1
        
        # Count final domains
        for contact in final_contacts:
            for domain in contact.domains:
                domain_stats[domain]['final_count'] += 1
        
        # Calculate duplicates removed
        for domain, stats in domain_stats.items():
            stats['duplicates_removed'] = stats['original_count'] - stats['final_count']
            stats['duplicate_rate'] = (
                stats['duplicates_removed'] / max(1, stats['original_count'])
            )
        
        # Sort domains by duplicate rate
        domains_by_duplicates = sorted(
            domain_stats.items(),
            key=lambda x: x[1]['duplicate_rate'],
            reverse=True
        )[:10]
        
        # Analyze contact consolidation
        consolidation_stats = {
            'contacts_with_multiple_emails': 0,
            'avg_emails_per_contact': 0,
            'max_emails_per_contact': 0,
            'contacts_with_names': 0,
            'contacts_with_titles': 0,
            'contacts_with_companies': 0,
            'contacts_with_phones': 0
        }
        
        total_emails = 0
        for contact in final_contacts:
            email_count = len(contact.all_emails)
            total_emails += email_count
            
            if email_count > 1:
                consolidation_stats['contacts_with_multiple_emails'] += 1
            
            consolidation_stats['max_emails_per_contact'] = max(
                consolidation_stats['max_emails_per_contact'], email_count
            )
            
            if contact.names:
                consolidation_stats['contacts_with_names'] += 1
            if contact.titles:
                consolidation_stats['contacts_with_titles'] += 1
            if contact.companies:
                consolidation_stats['contacts_with_companies'] += 1
            if contact.phone_numbers:
                consolidation_stats['contacts_with_phones'] += 1
        
        if final_contacts:
            consolidation_stats['avg_emails_per_contact'] = total_emails / len(final_contacts)
        
        return {
            'domain_analysis': {
                'unique_domains': len(domain_stats),
                'domains_with_highest_duplicates': [
                    {'domain': domain, 'stats': stats}
                    for domain, stats in domains_by_duplicates
                ]
            },
            'consolidation_analysis': consolidation_stats,
            'quality_preservation': self._analyze_quality_preservation(final_contacts)
        }
    
    def _analyze_quality_preservation(self, final_contacts: List[ContactRecord]) -> Dict[str, Any]:
        """Analyze how well quality was preserved during deduplication"""
        
        quality_stats = {
            'high_confidence_contacts': 0,
            'medium_confidence_contacts': 0,
            'low_confidence_contacts': 0,
            'avg_confidence': 0.0,
            'contacts_with_multiple_sources': 0
        }
        
        total_confidence = 0.0
        
        for contact in final_contacts:
            confidence = contact.best_confidence
            total_confidence += confidence
            
            if confidence >= 0.7:
                quality_stats['high_confidence_contacts'] += 1
            elif confidence >= 0.4:
                quality_stats['medium_confidence_contacts'] += 1
            else:
                quality_stats['low_confidence_contacts'] += 1
            
            if len(contact.source_urls) > 1:
                quality_stats['contacts_with_multiple_sources'] += 1
        
        if final_contacts:
            quality_stats['avg_confidence'] = total_confidence / len(final_contacts)
        
        return quality_stats


class AdvancedDeduplicationTool(BaseTool):
    """
    Advanced deduplication tool with machine learning-based similarity detection.
    
    Uses more sophisticated algorithms to detect potential duplicates based on
    name similarity, domain relationships, and contact patterns.
    """
    
    contacts: List[Dict[str, Any]] = Field(
        ...,
        description="List of contact records to deduplicate"
    )
    
    name_similarity_threshold: float = Field(
        default=0.85,
        description="Threshold for name-based duplicate detection"
    )
    
    company_similarity_threshold: float = Field(
        default=0.90,
        description="Threshold for company-based duplicate detection"
    )
    
    domain_similarity_enabled: bool = Field(
        default=True,
        description="Enable domain-based similarity detection"
    )
    
    fuzzy_matching_enabled: bool = Field(
        default=True,
        description="Enable fuzzy string matching for names and companies"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Perform advanced deduplication with ML-based similarity detection.
        
        Returns:
            Dictionary with advanced deduplication results
        """
        start_time = time.time()
        
        # Build similarity graph
        similarity_graph = self._build_similarity_graph()
        
        # Find connected components (duplicate groups)
        duplicate_groups = self._find_duplicate_groups(similarity_graph)
        
        # Merge duplicate groups
        final_contacts = self._merge_duplicate_groups(duplicate_groups)
        
        processing_time = time.time() - start_time
        
        return {
            'summary': {
                'original_contacts': len(self.contacts),
                'duplicate_groups_found': len(duplicate_groups),
                'final_unique_contacts': len(final_contacts),
                'duplicates_removed': len(self.contacts) - len(final_contacts),
                'duplicate_rate': 1.0 - (len(final_contacts) / max(1, len(self.contacts))),
                'processing_time_seconds': processing_time
            },
            'duplicate_groups': [
                {
                    'group_id': i,
                    'contacts': group,
                    'merge_reasons': self._analyze_merge_reasons(group)
                }
                for i, group in enumerate(duplicate_groups)
            ],
            'final_contacts': final_contacts,
            'similarity_analysis': self._analyze_similarity_patterns(similarity_graph),
            'configuration': {
                'name_similarity_threshold': self.name_similarity_threshold,
                'company_similarity_threshold': self.company_similarity_threshold,
                'domain_similarity_enabled': self.domain_similarity_enabled,
                'fuzzy_matching_enabled': self.fuzzy_matching_enabled
            }
        }
    
    def _build_similarity_graph(self) -> Dict[int, Set[int]]:
        """Build graph of similar contacts"""
        graph = defaultdict(set)
        
        for i in range(len(self.contacts)):
            for j in range(i + 1, len(self.contacts)):
                if self._are_similar_contacts(self.contacts[i], self.contacts[j]):
                    graph[i].add(j)
                    graph[j].add(i)
        
        return dict(graph)
    
    def _are_similar_contacts(self, contact1: Dict[str, Any], 
                            contact2: Dict[str, Any]) -> bool:
        """Determine if two contacts are similar enough to be considered duplicates"""
        
        # Email similarity (exact match for different domains)
        email1 = contact1.get('email', '').lower()
        email2 = contact2.get('email', '').lower()
        
        if email1 == email2:
            return True
        
        # Extract local parts for comparison
        local1 = email1.split('@')[0] if '@' in email1 else email1
        local2 = email2.split('@')[0] if '@' in email2 else email2
        
        if local1 == local2 and self.domain_similarity_enabled:
            domain1 = email1.split('@')[1] if '@' in email1 else ''
            domain2 = email2.split('@')[1] if '@' in email2 else ''
            
            if self._are_similar_domains(domain1, domain2):
                return True
        
        # Name similarity
        name1 = contact1.get('name', '').lower().strip()
        name2 = contact2.get('name', '').lower().strip()
        
        if name1 and name2:
            name_similarity = self._calculate_string_similarity(name1, name2)
            if name_similarity >= self.name_similarity_threshold:
                return True
        
        # Company similarity
        company1 = contact1.get('company', '').lower().strip()
        company2 = contact2.get('company', '').lower().strip()
        
        if company1 and company2:
            company_similarity = self._calculate_string_similarity(company1, company2)
            if company_similarity >= self.company_similarity_threshold:
                # Additional check: same company + similar names
                if name1 and name2:
                    name_similarity = self._calculate_string_similarity(name1, name2)
                    if name_similarity >= 0.7:  # Lower threshold for same company
                        return True
        
        return False
    
    def _are_similar_domains(self, domain1: str, domain2: str) -> bool:
        """Check if domains are similar (same company, different subdomains)"""
        if not domain1 or not domain2:
            return False
        
        # Extract main domain (remove subdomains)
        def get_main_domain(domain):
            parts = domain.split('.')
            if len(parts) >= 2:
                return '.'.join(parts[-2:])
            return domain
        
        main1 = get_main_domain(domain1)
        main2 = get_main_domain(domain2)
        
        return main1 == main2
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        if not str1 or not str2:
            return 0.0
        
        if not self.fuzzy_matching_enabled:
            return 1.0 if str1 == str2 else 0.0
        
        # Use Jaccard similarity for simplicity
        # In production, could use more sophisticated algorithms like Levenshtein
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _find_duplicate_groups(self, similarity_graph: Dict[int, Set[int]]) -> List[List[Dict[str, Any]]]:
        """Find connected components in similarity graph"""
        visited = set()
        groups = []
        
        def dfs(node, current_group):
            visited.add(node)
            current_group.append(self.contacts[node])
            
            for neighbor in similarity_graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, current_group)
        
        for i in range(len(self.contacts)):
            if i not in visited:
                group = []
                dfs(i, group)
                if len(group) > 1:  # Only include actual duplicate groups
                    groups.append(group)
        
        return groups
    
    def _merge_duplicate_groups(self, duplicate_groups: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Merge contacts in duplicate groups"""
        final_contacts = []
        processed_contacts = set()
        
        # Merge each duplicate group
        for group in duplicate_groups:
            merged_contact = self._merge_contact_group(group)
            final_contacts.append(merged_contact)
            
            # Track processed emails
            for contact in group:
                email = contact.get('email', '')
                if email:
                    processed_contacts.add(email.lower())
        
        # Add non-duplicate contacts
        for contact in self.contacts:
            email = contact.get('email', '').lower()
            if email not in processed_contacts:
                final_contacts.append(contact)
        
        return final_contacts
    
    def _merge_contact_group(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge a group of duplicate contacts into one"""
        if not contacts:
            return {}
        
        if len(contacts) == 1:
            return contacts[0]
        
        # Find the best contact to use as base (highest confidence or most complete)
        best_contact = max(contacts, key=lambda c: (
            c.get('confidence_score', 0.0),
            len(c.get('name', '')),
            len(c.get('company', '')),
            len(c.get('title', ''))
        ))
        
        # Merge all information
        merged = best_contact.copy()
        
        # Collect all unique values
        all_emails = []
        all_names = []
        all_companies = []
        all_titles = []
        all_phones = []
        all_sources = []
        
        for contact in contacts:
            # Emails
            email = contact.get('email', '').strip()
            if email and email not in all_emails:
                all_emails.append(email)
            
            # Names
            name = contact.get('name', '').strip()
            if name and name not in all_names:
                all_names.append(name)
            
            # Companies
            company = contact.get('company', '').strip()
            if company and company not in all_companies:
                all_companies.append(company)
            
            # Titles
            title = contact.get('title', '').strip()
            if title and title not in all_titles:
                all_titles.append(title)
            
            # Phones
            phone = contact.get('phone', '').strip()
            if phone and phone not in all_phones:
                all_phones.append(phone)
            
            # Sources
            source = contact.get('source_url', '').strip()
            if source and source not in all_sources:
                all_sources.append(source)
        
        # Update merged contact
        merged.update({
            'all_emails': all_emails,
            'all_names': all_names,
            'all_companies': all_companies,
            'all_titles': all_titles,
            'all_phones': all_phones,
            'all_sources': all_sources,
            'merge_count': len(contacts),
            'confidence_score': max(c.get('confidence_score', 0.0) for c in contacts)
        })
        
        return merged
    
    def _analyze_merge_reasons(self, group: List[Dict[str, Any]]) -> List[str]:
        """Analyze why contacts in a group were merged"""
        if len(group) < 2:
            return []
        
        reasons = []
        
        # Check for exact email matches
        emails = [c.get('email', '').lower() for c in group]
        if len(set(emails)) < len(emails):
            reasons.append("Exact email match")
        
        # Check for name similarity
        names = [c.get('name', '').lower().strip() for c in group if c.get('name')]
        if len(names) >= 2:
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    similarity = self._calculate_string_similarity(names[i], names[j])
                    if similarity >= self.name_similarity_threshold:
                        reasons.append(f"Name similarity ({similarity:.2f})")
                        break
        
        # Check for company similarity
        companies = [c.get('company', '').lower().strip() for c in group if c.get('company')]
        if len(companies) >= 2:
            for i in range(len(companies)):
                for j in range(i + 1, len(companies)):
                    similarity = self._calculate_string_similarity(companies[i], companies[j])
                    if similarity >= self.company_similarity_threshold:
                        reasons.append(f"Company similarity ({similarity:.2f})")
                        break
        
        # Check for domain similarity
        domains = []
        for contact in group:
            email = contact.get('email', '')
            if '@' in email:
                domain = email.split('@')[1].lower()
                domains.append(domain)
        
        if len(domains) >= 2:
            for i in range(len(domains)):
                for j in range(i + 1, len(domains)):
                    if self._are_similar_domains(domains[i], domains[j]):
                        reasons.append("Similar domains")
                        break
        
        return list(set(reasons))  # Remove duplicates
    
    def _analyze_similarity_patterns(self, similarity_graph: Dict[int, Set[int]]) -> Dict[str, Any]:
        """Analyze patterns in the similarity graph"""
        
        # Count similarity types
        similarity_reasons = Counter()
        
        for i, neighbors in similarity_graph.items():
            for j in neighbors:
                if i < j:  # Avoid double counting
                    contact1 = self.contacts[i]
                    contact2 = self.contacts[j]
                    
                    reasons = self._analyze_merge_reasons([contact1, contact2])
                    for reason in reasons:
                        similarity_reasons[reason] += 1
        
        # Graph statistics
        total_edges = sum(len(neighbors) for neighbors in similarity_graph.values()) // 2
        connected_nodes = len([node for node, neighbors in similarity_graph.items() if neighbors])
        
        return {
            'total_similarity_connections': total_edges,
            'connected_contacts': connected_nodes,
            'similarity_reasons': dict(similarity_reasons.most_common()),
            'avg_connections_per_contact': total_edges / max(1, len(self.contacts))
        }
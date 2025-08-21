"""
Domain Classification Tool for Agency Swarm

Tool for processing domain lists through the DomainClassifier system.
Handles deduplication, normalization, and basic metadata setup.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from agency_swarm.tools import BaseTool
from pydantic import Field

from agents.domain_classifier_agent import DomainClassifier, WebsiteType, PlatformType, PriorityLevel

logger = logging.getLogger(__name__)


class DomainClassificationTool(BaseTool):
    """
    Tool for classifying and deduplicating domains.
    
    This tool handles the initial processing of domain lists including:
    - Domain normalization and deduplication
    - Basic metadata initialization
    - Statistics collection
    - Export functionality
    """
    
    domains: List[str] = Field(
        ...,
        description="List of domain names or URLs to classify and deduplicate"
    )
    
    strip_www: bool = Field(
        default=True,
        description="Whether to strip 'www.' prefix from domains"
    )
    
    preserve_subdomain: bool = Field(
        default=True,
        description="Whether to preserve subdomains other than 'www'"
    )
    
    max_domain_length: int = Field(
        default=253,
        description="Maximum allowed domain length"
    )
    
    export_format: str = Field(
        default="json",
        description="Export format for results ('json', 'csv_data', 'list')"
    )
    
    log_level: str = Field(
        default="INFO",
        description="Logging level for the classification process"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def run(self) -> Dict[str, Any]:
        """
        Process domains through the classification system.
        
        Returns:
            Dictionary containing classification results and statistics
        """
        start_time = time.time()
        
        # Set up logging level
        log_level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        
        # Initialize domain classifier with configuration
        config = {
            "strip_www": self.strip_www,
            "preserve_subdomain": self.preserve_subdomain,
            "max_domain_length": self.max_domain_length,
            "case_sensitive": False,
            "log_level": log_level_map.get(self.log_level.upper(), logging.INFO)
        }
        
        classifier = DomainClassifier(config)
        
        logger.info(f"Starting domain classification for {len(self.domains)} domains")
        
        try:
            # Add domains to classifier
            add_result = classifier.add_domains(self.domains)
            
            # Get comprehensive statistics
            stats = classifier.get_statistics()
            
            # Export domains in requested format
            export_data = classifier.export_domains(self.export_format)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Domain classification completed: {add_result['added_domains']} unique domains processed in {processing_time:.2f}s")
            
            return {
                "success": True,
                "processing_summary": {
                    "total_input_domains": len(self.domains),
                    "unique_domains_added": add_result["added_domains"],
                    "duplicate_domains": add_result["duplicate_domains"],
                    "invalid_domains": add_result["invalid_domains"],
                    "processing_time_seconds": processing_time
                },
                "domain_statistics": stats,
                "export_data": export_data,
                "detailed_results": add_result,
                "configuration": config
            }
            
        except Exception as e:
            logger.error(f"Error during domain classification: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_seconds": time.time() - start_time,
                "partial_results": None
            }


class UpdateDomainMetadataTool(BaseTool):
    """
    Tool for updating metadata of classified domains.
    
    Allows bulk updates to domain metadata including website type,
    platform type, business score, and priority level.
    """
    
    domain_updates: List[Dict[str, Any]] = Field(
        ...,
        description="List of domain update dictionaries with 'domain' key and update fields"
    )
    
    batch_size: int = Field(
        default=100,
        description="Maximum number of domains to update in a single batch"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def run(self) -> Dict[str, Any]:
        """
        Update metadata for multiple domains.
        
        Returns:
            Dictionary containing update results and statistics
        """
        start_time = time.time()
        
        # Initialize classifier (in real implementation, this would likely
        # use a shared classifier instance or load from storage)
        classifier = DomainClassifier()
        
        successful_updates = []
        failed_updates = []
        
        logger.info(f"Starting metadata update for {len(self.domain_updates)} domains")
        
        for i, update_data in enumerate(self.domain_updates):
            try:
                if "domain" not in update_data:
                    failed_updates.append({
                        "index": i,
                        "error": "Missing 'domain' field",
                        "data": update_data
                    })
                    continue
                
                domain = update_data["domain"]
                updates = {k: v for k, v in update_data.items() if k != "domain"}
                
                # Convert string enums to enum objects if needed
                if "website_type" in updates:
                    if isinstance(updates["website_type"], str):
                        try:
                            updates["website_type"] = WebsiteType(updates["website_type"])
                        except ValueError:
                            failed_updates.append({
                                "index": i,
                                "domain": domain,
                                "error": f"Invalid website_type: {updates['website_type']}",
                                "data": update_data
                            })
                            continue
                
                if "platform_type" in updates:
                    if isinstance(updates["platform_type"], str):
                        try:
                            updates["platform_type"] = PlatformType(updates["platform_type"])
                        except ValueError:
                            failed_updates.append({
                                "index": i,
                                "domain": domain,
                                "error": f"Invalid platform_type: {updates['platform_type']}",
                                "data": update_data
                            })
                            continue
                
                if "priority_level" in updates:
                    if isinstance(updates["priority_level"], str):
                        try:
                            updates["priority_level"] = PriorityLevel(updates["priority_level"])
                        except ValueError:
                            failed_updates.append({
                                "index": i,
                                "domain": domain,
                                "error": f"Invalid priority_level: {updates['priority_level']}",
                                "data": update_data
                            })
                            continue
                
                # Attempt to update the domain
                success = classifier.update_domain_metadata(domain, updates)
                
                if success:
                    successful_updates.append({
                        "index": i,
                        "domain": domain,
                        "updated_fields": list(updates.keys())
                    })
                else:
                    failed_updates.append({
                        "index": i,
                        "domain": domain,
                        "error": "Domain not found in classifier",
                        "data": update_data
                    })
                
            except Exception as e:
                failed_updates.append({
                    "index": i,
                    "domain": update_data.get("domain", "unknown"),
                    "error": str(e),
                    "data": update_data
                })
        
        processing_time = time.time() - start_time
        
        logger.info(f"Metadata update completed: {len(successful_updates)} successful, "
                   f"{len(failed_updates)} failed in {processing_time:.2f}s")
        
        return {
            "success": True,
            "update_summary": {
                "total_updates_attempted": len(self.domain_updates),
                "successful_updates": len(successful_updates),
                "failed_updates": len(failed_updates),
                "processing_time_seconds": processing_time
            },
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
            "updated_statistics": classifier.get_statistics()
        }


class QueryDomainsTool(BaseTool):
    """
    Tool for querying and filtering classified domains.
    
    Provides flexible querying capabilities to retrieve domains based on
    various criteria including type, platform, priority, and custom filters.
    """
    
    filter_type: Optional[str] = Field(
        default=None,
        description="Filter by website type (business, personal, blog, etc.)"
    )
    
    filter_platform: Optional[str] = Field(
        default=None,
        description="Filter by platform type (wordpress, shopify, custom, etc.)"
    )
    
    filter_priority: Optional[str] = Field(
        default=None,
        description="Filter by priority level (critical, high, medium, low, skip)"
    )
    
    min_business_score: Optional[float] = Field(
        default=None,
        description="Minimum business score threshold"
    )
    
    max_business_score: Optional[float] = Field(
        default=None,
        description="Maximum business score threshold"
    )
    
    min_crawl_budget: Optional[int] = Field(
        default=None,
        description="Minimum crawl budget"
    )
    
    only_accessible: bool = Field(
        default=False,
        description="Only return accessible domains"
    )
    
    sort_by: str = Field(
        default="business_score",
        description="Field to sort by (business_score, priority_level, created_at, etc.)"
    )
    
    sort_desc: bool = Field(
        default=True,
        description="Sort in descending order"
    )
    
    limit: Optional[int] = Field(
        default=None,
        description="Maximum number of domains to return"
    )
    
    export_format: str = Field(
        default="json",
        description="Export format for results ('json', 'csv_data', 'list')"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def run(self) -> Dict[str, Any]:
        """
        Query classified domains based on filters.
        
        Returns:
            Dictionary containing filtered domains and query statistics
        """
        start_time = time.time()
        
        # Initialize classifier (in real implementation, this would likely
        # use a shared classifier instance or load from storage)
        classifier = DomainClassifier()
        
        logger.info(f"Querying domains with filters: type={self.filter_type}, "
                   f"platform={self.filter_platform}, priority={self.filter_priority}")
        
        try:
            # Get all domains
            all_domains = classifier.get_all_domains()
            
            # Apply filters
            filtered_domains = all_domains
            
            if self.filter_type:
                try:
                    website_type = WebsiteType(self.filter_type)
                    filtered_domains = [d for d in filtered_domains if d.website_type == website_type]
                except ValueError:
                    return {
                        "success": False,
                        "error": f"Invalid website type: {self.filter_type}",
                        "valid_types": [t.value for t in WebsiteType]
                    }
            
            if self.filter_platform:
                try:
                    platform_type = PlatformType(self.filter_platform)
                    filtered_domains = [d for d in filtered_domains if d.platform_type == platform_type]
                except ValueError:
                    return {
                        "success": False,
                        "error": f"Invalid platform type: {self.filter_platform}",
                        "valid_platforms": [p.value for p in PlatformType]
                    }
            
            if self.filter_priority:
                try:
                    priority_level = PriorityLevel(self.filter_priority)
                    filtered_domains = [d for d in filtered_domains if d.priority_level == priority_level]
                except ValueError:
                    return {
                        "success": False,
                        "error": f"Invalid priority level: {self.filter_priority}",
                        "valid_priorities": [p.value for p in PriorityLevel]
                    }
            
            if self.min_business_score is not None:
                filtered_domains = [d for d in filtered_domains if d.business_score >= self.min_business_score]
            
            if self.max_business_score is not None:
                filtered_domains = [d for d in filtered_domains if d.business_score <= self.max_business_score]
            
            if self.min_crawl_budget is not None:
                filtered_domains = [d for d in filtered_domains if d.crawl_budget >= self.min_crawl_budget]
            
            if self.only_accessible:
                filtered_domains = [d for d in filtered_domains if d.is_accessible]
            
            # Sort domains
            if self.sort_by and hasattr(filtered_domains[0] if filtered_domains else None, self.sort_by):
                filtered_domains.sort(
                    key=lambda d: getattr(d, self.sort_by),
                    reverse=self.sort_desc
                )
            
            # Apply limit
            if self.limit and self.limit > 0:
                filtered_domains = filtered_domains[:self.limit]
            
            # Export data
            if self.export_format == "json":
                export_data = [asdict(domain) for domain in filtered_domains]
            elif self.export_format == "csv_data":
                export_data = []
                for domain in filtered_domains:
                    export_data.append({
                        "domain": domain.domain,
                        "website_type": domain.website_type.value,
                        "platform_type": domain.platform_type.value,
                        "business_score": domain.business_score,
                        "priority_level": domain.priority_level.value,
                        "crawl_budget": domain.crawl_budget,
                        "is_accessible": domain.is_accessible
                    })
            elif self.export_format == "list":
                export_data = [domain.domain for domain in filtered_domains]
            else:
                export_data = [asdict(domain) for domain in filtered_domains]
            
            processing_time = time.time() - start_time
            
            logger.info(f"Domain query completed: {len(filtered_domains)} domains matched "
                       f"filters in {processing_time:.2f}s")
            
            return {
                "success": True,
                "query_summary": {
                    "total_domains_in_classifier": len(all_domains),
                    "domains_matching_filters": len(filtered_domains),
                    "filters_applied": {
                        "website_type": self.filter_type,
                        "platform_type": self.filter_platform,
                        "priority_level": self.filter_priority,
                        "min_business_score": self.min_business_score,
                        "max_business_score": self.max_business_score,
                        "min_crawl_budget": self.min_crawl_budget,
                        "only_accessible": self.only_accessible
                    },
                    "sort_config": {
                        "sort_by": self.sort_by,
                        "sort_desc": self.sort_desc,
                        "limit": self.limit
                    },
                    "processing_time_seconds": processing_time
                },
                "domains": export_data,
                "export_format": self.export_format
            }
            
        except Exception as e:
            logger.error(f"Error during domain query: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_seconds": time.time() - start_time
            }
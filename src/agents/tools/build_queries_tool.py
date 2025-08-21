"""
Build Queries Tool for Agency Swarm

Tool for building search queries from campaign configurations with
template expansion, regional variations, and validation.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from agency_swarm.tools import BaseTool
from pydantic import Field

from query_builder import QueryBuilder, CampaignConfig, VerticalType, SearchIntent
from query_builder.campaign_parser import CampaignParser

logger = logging.getLogger(__name__)


class BuildQueriesTool(BaseTool):
    """
    Tool for building search queries from campaign configurations.
    
    This tool generates comprehensive search queries by:
    1. Parsing campaign YAML configuration
    2. Expanding templates with service terms
    3. Adding regional variations
    4. Validating and optimizing queries
    5. Saving results to output files
    """
    
    campaign_yaml: str = Field(
        ..., 
        description="Campaign configuration in YAML format containing templates, service terms, and target regions"
    )
    
    output_file: str = Field(
        default="out/planned_queries.txt",
        description="Output file path for generated queries"
    )
    
    validate_queries: bool = Field(
        default=True,
        description="Whether to validate generated queries for quality and format"
    )
    
    deduplicate: bool = Field(
        default=True,
        description="Whether to remove duplicate queries from the output"
    )
    
    max_queries_per_template: Optional[int] = Field(
        default=50,
        description="Maximum number of queries to generate per template"
    )
    
    priority_filter: Optional[int] = Field(
        default=None,
        description="Filter locations by priority level (1=high, 2=medium, 3=low)"
    )
    
    save_metadata: bool = Field(
        default=True,
        description="Whether to save detailed metadata about query generation"
    )
    
    def run(self) -> str:
        """Execute the query building process."""
        try:
            logger.info("Starting query building process")
            
            # Initialize query builder
            query_builder = QueryBuilder()
            
            # Parse campaign configuration
            campaign_parser = CampaignParser()
            campaigns = campaign_parser.parse_campaign_string(self.campaign_yaml)
            
            if not campaigns:
                return "Error: No valid campaigns found in YAML configuration"
            
            logger.info(f"Parsed {len(campaigns)} campaigns from configuration")
            
            # Build queries for all campaigns
            all_queries = []
            all_plans = []
            
            for campaign in campaigns:
                # Apply tool-level overrides
                if self.max_queries_per_template:
                    campaign.max_queries_per_template = self.max_queries_per_template
                
                if self.priority_filter:
                    campaign.priority_filter = self.priority_filter
                
                # Build query plan
                plan = query_builder.build_queries_from_campaign(
                    campaign=campaign,
                    deduplicate=self.deduplicate,
                    validate_queries=self.validate_queries
                )
                
                all_plans.append(plan)
                all_queries.extend(plan.queries)
            
            # Save queries to output file
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for query in all_queries:
                    f.write(f"{query}\n")
            
            # Save metadata if requested
            if self.save_metadata:
                metadata_file = output_path.with_suffix('.json')
                metadata = {
                    'total_queries': len(all_queries),
                    'campaigns': [
                        {
                            'name': plan.campaign_name,
                            'query_count': plan.total_queries,
                            'validation_summary': plan.validation_summary,
                            'geographic_distribution': plan.geographic_distribution,
                            'generation_time': plan.generation_time
                        }
                        for plan in all_plans
                    ],
                    'overall_statistics': self._generate_overall_statistics(all_plans),
                    'query_builder_stats': query_builder.get_statistics()
                }
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Generate result summary
            total_time = sum(plan.generation_time for plan in all_plans)
            unique_states = set()
            unique_locations = set()
            
            for plan in all_plans:
                geo_dist = plan.geographic_distribution
                unique_states.update(geo_dist.get('state_distribution', {}).keys())
                unique_locations.update(geo_dist.get('location_distribution', {}).keys())
            
            result_summary = f"""
Query Building Completed Successfully!

📊 Results Summary:
- Total Queries Generated: {len(all_queries)}
- Campaigns Processed: {len(campaigns)}
- Geographic Coverage: {len(unique_states)} states, {len(unique_locations)} locations
- Generation Time: {total_time:.2f} seconds
- Output File: {output_path}

📁 Files Created:
- Queries: {output_path}
"""
            
            if self.save_metadata:
                result_summary += f"- Metadata: {metadata_file}\n"
            
            # Add campaign details
            result_summary += "\n📋 Campaign Details:\n"
            for plan in all_plans:
                validation = plan.validation_summary
                valid_rate = validation.get('validation_rate', 0) if validation else 100
                result_summary += f"- {plan.campaign_name}: {plan.total_queries} queries ({valid_rate:.1f}% valid)\n"
            
            # Add quality metrics if validation was performed
            if self.validate_queries and all_plans:
                overall_validation = self._calculate_overall_validation_rate(all_plans)
                result_summary += f"\n✅ Quality Metrics:\n"
                result_summary += f"- Overall Validation Rate: {overall_validation:.1f}%\n"
                
                error_count = sum(plan.validation_summary.get('queries_with_errors', 0) 
                                for plan in all_plans if plan.validation_summary)
                warning_count = sum(plan.validation_summary.get('queries_with_warnings', 0)
                                  for plan in all_plans if plan.validation_summary)
                
                result_summary += f"- Queries with Errors: {error_count}\n"
                result_summary += f"- Queries with Warnings: {warning_count}\n"
            
            logger.info(f"Query building completed: {len(all_queries)} queries generated")
            return result_summary
            
        except Exception as e:
            error_msg = f"Error building queries: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
    
    def _generate_overall_statistics(self, plans: List) -> Dict[str, Any]:
        """Generate overall statistics across all plans."""
        total_queries = sum(plan.total_queries for plan in plans)
        total_time = sum(plan.generation_time for plan in plans)
        
        # Aggregate geographic distribution
        all_states = set()
        all_locations = set()
        state_totals = {}
        
        for plan in plans:
            geo_dist = plan.geographic_distribution
            states = geo_dist.get('state_distribution', {})
            locations = geo_dist.get('location_distribution', {})
            
            all_states.update(states.keys())
            all_locations.update(locations.keys())
            
            for state, count in states.items():
                state_totals[state] = state_totals.get(state, 0) + count
        
        return {
            'total_queries': total_queries,
            'total_campaigns': len(plans),
            'total_generation_time': total_time,
            'average_time_per_campaign': total_time / len(plans) if plans else 0,
            'unique_states_covered': len(all_states),
            'unique_locations_covered': len(all_locations),
            'top_states_by_queries': sorted(state_totals.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def _calculate_overall_validation_rate(self, plans: List) -> float:
        """Calculate overall validation rate across all plans."""
        total_queries = sum(plan.total_queries for plan in plans)
        if total_queries == 0:
            return 100.0
        
        total_valid = 0
        for plan in plans:
            validation = plan.validation_summary
            if validation:
                valid_queries = validation.get('valid_queries', plan.total_queries)
                total_valid += valid_queries
            else:
                # If no validation summary, assume all queries are valid
                total_valid += plan.total_queries
        
        return (total_valid / total_queries) * 100
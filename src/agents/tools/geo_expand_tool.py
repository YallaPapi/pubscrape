"""
Geographic Expansion Tool for Agency Swarm

Tool for expanding query templates with geographic variations
and regional targeting capabilities.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from agency_swarm.tools import BaseTool
from pydantic import Field

from query_builder.regional_expander import RegionalExpander, GeographicLocation, RegionType
from query_builder.template_manager import TemplateManager

logger = logging.getLogger(__name__)


class GeoExpandTool(BaseTool):
    """
    Tool for geographic expansion of search query templates.
    
    This tool provides geographic expansion capabilities by:
    1. Loading and managing geographic location data
    2. Expanding templates with city/state variations
    3. Filtering by region, population, or priority
    4. Generating regional distribution reports
    5. Optimizing geographic targeting
    """
    
    templates: List[str] = Field(
        ...,
        description="List of query templates to expand geographically (use {city} and {state} placeholders)"
    )
    
    target_states: Optional[List[str]] = Field(
        default=None,
        description="List of state codes to target (e.g., ['CA', 'NY', 'TX']). If not provided, uses all available states"
    )
    
    target_cities: Optional[List[str]] = Field(
        default=None,
        description="List of specific cities to target. If not provided, uses top cities by population"
    )
    
    max_locations: Optional[int] = Field(
        default=50,
        description="Maximum number of locations to expand each template with"
    )
    
    priority_filter: Optional[int] = Field(
        default=None,
        description="Filter locations by priority level (1=high, 2=medium, 3=low)"
    )
    
    min_population: Optional[int] = Field(
        default=None,
        description="Minimum population for cities to include in expansion"
    )
    
    include_variations: bool = Field(
        default=True,
        description="Include location name variations (e.g., 'Los Angeles CA', 'Los Angeles, California')"
    )
    
    deduplicate: bool = Field(
        default=True,
        description="Remove duplicate queries from the expansion results"
    )
    
    output_file: Optional[str] = Field(
        default=None,
        description="Optional file path to save expanded queries"
    )
    
    generate_report: bool = Field(
        default=True,
        description="Generate detailed geographic distribution report"
    )
    
    def run(self) -> str:
        """Execute geographic expansion of templates."""
        try:
            logger.info("Starting geographic expansion process")
            
            # Initialize regional expander
            regional_expander = RegionalExpander()
            
            # Validate templates
            if not self.templates:
                return "Error: No templates provided for expansion"
            
            # Get target locations based on filters
            target_locations = self._get_target_locations(regional_expander)
            
            if not target_locations:
                return "Error: No locations found matching the specified criteria"
            
            logger.info(f"Found {len(target_locations)} target locations for expansion")
            
            # Expand all templates
            all_expanded_queries = []
            template_results = {}
            
            for template in self.templates:
                logger.info(f"Expanding template: {template}")
                
                # Validate template has geographic placeholders
                if '{city}' not in template and '{state}' not in template:
                    logger.warning(f"Template '{template}' has no geographic placeholders")
                    continue
                
                # Expand template with locations
                expanded = self._expand_template_with_locations(template, target_locations)
                
                if self.deduplicate:
                    # Remove duplicates within this template
                    seen = set()
                    deduplicated = []
                    for query, location in expanded:
                        if query.lower() not in seen:
                            seen.add(query.lower())
                            deduplicated.append((query, location))
                    expanded = deduplicated
                
                template_results[template] = expanded
                all_expanded_queries.extend(expanded)
                
                logger.info(f"Template '{template}' expanded to {len(expanded)} queries")
            
            # Final deduplication across all templates
            if self.deduplicate:
                all_expanded_queries = self._deduplicate_across_templates(all_expanded_queries)
            
            # Extract just the query strings
            final_queries = [query for query, _ in all_expanded_queries]
            
            # Generate geographic distribution report
            report_data = None
            if self.generate_report:
                report_data = self._generate_geographic_report(all_expanded_queries, template_results)
            
            # Save to file if requested
            if self.output_file:
                self._save_queries_to_file(final_queries, self.output_file, report_data)
            
            # Generate result summary
            result_summary = self._generate_result_summary(
                final_queries, template_results, target_locations, report_data
            )
            
            logger.info(f"Geographic expansion completed: {len(final_queries)} queries generated")
            return result_summary
            
        except Exception as e:
            error_msg = f"Error during geographic expansion: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
    
    def _get_target_locations(self, regional_expander: RegionalExpander) -> List[GeographicLocation]:
        """Get target locations based on tool parameters."""
        target_locations = []
        
        # Start with all locations
        all_locations = list(regional_expander.locations.values())
        
        # Filter by specific cities if provided
        if self.target_cities:
            city_locations = []
            for city_name in self.target_cities:
                city_key = city_name.lower()
                if city_key in regional_expander.locations:
                    city_locations.append(regional_expander.locations[city_key])
                else:
                    logger.warning(f"City not found: {city_name}")
            target_locations.extend(city_locations)
        
        # Filter by states if provided
        if self.target_states:
            for state_code in self.target_states:
                state_locations = regional_expander.get_locations_by_state(state_code.upper())
                target_locations.extend(state_locations)
        
        # If no specific targeting, use all locations
        if not target_locations:
            target_locations = all_locations
        
        # Apply additional filters
        filtered_locations = []
        
        for location in target_locations:
            # Priority filter
            if self.priority_filter and location.priority != self.priority_filter:
                continue
            
            # Population filter
            if self.min_population and (not location.population or location.population < self.min_population):
                continue
            
            filtered_locations.append(location)
        
        # Sort by priority and population for best results
        filtered_locations.sort(key=lambda x: (x.priority, -(x.population or 0)))
        
        # Limit to max_locations if specified
        if self.max_locations:
            filtered_locations = filtered_locations[:self.max_locations]
        
        return filtered_locations
    
    def _expand_template_with_locations(self, 
                                      template: str, 
                                      locations: List[GeographicLocation]) -> List[tuple]:
        """Expand a single template with all target locations."""
        expanded_queries = []
        
        for location in locations:
            if self.include_variations:
                # Use all search variations for the location
                variations = location.get_search_variations()
            else:
                # Use just the primary name
                variations = [location.name]
            
            for variation in variations:
                try:
                    # Replace geographic placeholders
                    expanded_query = template
                    
                    if '{city}' in expanded_query:
                        expanded_query = expanded_query.replace('{city}', variation)
                    
                    if '{state}' in expanded_query:
                        expanded_query = expanded_query.replace('{state}', location.state_code)
                    
                    expanded_queries.append((expanded_query, location))
                    
                except Exception as e:
                    logger.warning(f"Error expanding template '{template}' with location '{variation}': {e}")
                    continue
        
        return expanded_queries
    
    def _deduplicate_across_templates(self, queries: List[tuple]) -> List[tuple]:
        """Remove duplicate queries across all templates."""
        seen_queries = set()
        deduplicated = []
        
        for query, location in queries:
            query_normalized = query.lower().strip()
            if query_normalized not in seen_queries:
                seen_queries.add(query_normalized)
                deduplicated.append((query, location))
        
        return deduplicated
    
    def _generate_geographic_report(self, 
                                  all_queries: List[tuple], 
                                  template_results: Dict[str, List[tuple]]) -> Dict[str, Any]:
        """Generate comprehensive geographic distribution report."""
        # Overall distribution
        state_distribution = {}
        city_distribution = {}
        metro_area_distribution = {}
        priority_distribution = {}
        population_stats = []
        
        for query, location in all_queries:
            # State distribution
            state = location.state_code
            state_distribution[state] = state_distribution.get(state, 0) + 1
            
            # City distribution
            city = location.name
            city_distribution[city] = city_distribution.get(city, 0) + 1
            
            # Metro area distribution
            if location.metro_area:
                metro = location.metro_area
                metro_area_distribution[metro] = metro_area_distribution.get(metro, 0) + 1
            
            # Priority distribution
            priority = location.priority
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
            
            # Population stats
            if location.population:
                population_stats.append(location.population)
        
        # Template-specific statistics
        template_stats = {}
        for template, results in template_results.items():
            template_states = set(loc.state_code for _, loc in results)
            template_cities = set(loc.name for _, loc in results)
            
            template_stats[template] = {
                'total_queries': len(results),
                'unique_states': len(template_states),
                'unique_cities': len(template_cities),
                'states_covered': list(template_states),
                'top_cities': sorted(
                    [(loc.name, len([q for q, l in results if l.name == loc.name])) 
                     for loc in set(location for _, location in results)],
                    key=lambda x: x[1], reverse=True
                )[:10]
            }
        
        # Population statistics
        pop_stats = {}
        if population_stats:
            pop_stats = {
                'min_population': min(population_stats),
                'max_population': max(population_stats),
                'avg_population': sum(population_stats) / len(population_stats),
                'total_population_covered': sum(population_stats)
            }
        
        return {
            'overview': {
                'total_queries': len(all_queries),
                'unique_states': len(state_distribution),
                'unique_cities': len(city_distribution),
                'unique_metro_areas': len(metro_area_distribution)
            },
            'geographic_distribution': {
                'states': state_distribution,
                'cities': city_distribution,
                'metro_areas': metro_area_distribution,
                'priorities': priority_distribution
            },
            'top_coverage': {
                'states': sorted(state_distribution.items(), key=lambda x: x[1], reverse=True)[:10],
                'cities': sorted(city_distribution.items(), key=lambda x: x[1], reverse=True)[:20],
                'metro_areas': sorted(metro_area_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
            },
            'template_statistics': template_stats,
            'population_statistics': pop_stats
        }
    
    def _save_queries_to_file(self, 
                            queries: List[str], 
                            file_path: str, 
                            report_data: Optional[Dict[str, Any]]):
        """Save queries and optional report to files."""
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save queries
        with open(output_path, 'w', encoding='utf-8') as f:
            for query in queries:
                f.write(f"{query}\n")
        
        # Save report if available
        if report_data:
            report_path = output_path.with_suffix('.json')
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    def _generate_result_summary(self, 
                               queries: List[str],
                               template_results: Dict[str, List[tuple]],
                               target_locations: List[GeographicLocation],
                               report_data: Optional[Dict[str, Any]]) -> str:
        """Generate comprehensive result summary."""
        result_summary = f"""
Geographic Expansion Completed Successfully!

📊 Expansion Results:
- Total Queries Generated: {len(queries)}
- Templates Processed: {len(template_results)}
- Target Locations: {len(target_locations)}
- Include Variations: {self.include_variations}
- Deduplicated: {self.deduplicate}
"""
        
        # Add geographic coverage info
        if report_data:
            overview = report_data['overview']
            result_summary += f"""
🌍 Geographic Coverage:
- States Covered: {overview['unique_states']}
- Cities Covered: {overview['unique_cities']}
- Metro Areas: {overview['unique_metro_areas']}
"""
            
            # Add top coverage areas
            top_coverage = report_data['top_coverage']
            if top_coverage['states']:
                result_summary += f"\n🏆 Top States by Query Count:\n"
                for i, (state, count) in enumerate(top_coverage['states'][:5], 1):
                    result_summary += f"  {i}. {state}: {count} queries\n"
            
            if top_coverage['cities']:
                result_summary += f"\n🏙️ Top Cities by Query Count:\n"
                for i, (city, count) in enumerate(top_coverage['cities'][:5], 1):
                    result_summary += f"  {i}. {city}: {count} queries\n"
        
        # Add template breakdown
        result_summary += f"\n📋 Template Breakdown:\n"
        for template, results in template_results.items():
            result_summary += f"- '{template}': {len(results)} queries\n"
        
        # Add file output info
        if self.output_file:
            result_summary += f"\n📁 Output Files:\n"
            result_summary += f"- Queries: {self.output_file}\n"
            
            if self.generate_report and report_data:
                report_file = Path(self.output_file).with_suffix('.json')
                result_summary += f"- Report: {report_file}\n"
        
        # Add filtering info
        filters_applied = []
        if self.target_states:
            filters_applied.append(f"States: {', '.join(self.target_states)}")
        if self.target_cities:
            filters_applied.append(f"Cities: {', '.join(self.target_cities)}")
        if self.priority_filter:
            filters_applied.append(f"Priority: {self.priority_filter}")
        if self.min_population:
            filters_applied.append(f"Min Population: {self.min_population:,}")
        if self.max_locations:
            filters_applied.append(f"Max Locations: {self.max_locations}")
        
        if filters_applied:
            result_summary += f"\n🎯 Filters Applied:\n"
            for filter_info in filters_applied:
                result_summary += f"- {filter_info}\n"
        
        return result_summary
"""
JSON Statistics Export Tool

Agency Swarm tool for generating and exporting comprehensive JSON statistics
including campaign summaries, proxy performance, and analytics reports.
"""

import os
import json
from typing import Dict, Any, List, Optional
from pydantic import Field
from datetime import datetime

try:
    from agency_swarm.tools import BaseTool
except ImportError:
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


class CampaignSummaryExportTool(BaseTool):
    """
    Tool for generating and exporting campaign summary statistics.
    
    This tool analyzes contact data and generates comprehensive campaign
    summaries including quality distributions, platform analytics,
    and performance metrics.
    """
    
    contact_data: List[Dict[str, Any]] = Field(
        description="List of contact data dictionaries to analyze"
    )
    
    campaign_info: Dict[str, Any] = Field(
        description="Campaign metadata including topic, campaign_id, etc."
    )
    
    output_path: str = Field(
        description="Output file path for the campaign summary JSON"
    )
    
    include_detailed_analytics: bool = Field(
        default=True,
        description="Whether to include detailed analytics and breakdowns"
    )
    
    def run(self) -> str:
        """
        Generate and export campaign summary.
        
        Returns:
            JSON string with export results and summary statistics
        """
        try:
            # Import the exporter here to avoid circular imports
            from agents.exporter_agent import JSONStatsExporter
            
            # Initialize exporter
            exporter = JSONStatsExporter()
            
            # Validate input
            if not self.contact_data:
                return json.dumps({
                    "success": False,
                    "error": "No contact data provided for analysis",
                    "summary_stats": None
                })
            
            # Perform campaign summary export
            metrics = exporter.export_campaign_summary(
                data=self.contact_data,
                campaign_info=self.campaign_info,
                output_path=self.output_path
            )
            
            # Generate additional analytics if requested
            detailed_analytics = {}
            if self.include_detailed_analytics:
                detailed_analytics = self._generate_detailed_analytics()
            
            # Prepare result
            result = {
                "success": metrics.success,
                "error": metrics.error_message,
                "summary_path": self.output_path if metrics.success else None,
                "metrics": {
                    "total_rows_analyzed": metrics.total_rows,
                    "export_duration_ms": metrics.write_duration_ms,
                    "file_size_bytes": metrics.file_size_bytes
                },
                "detailed_analytics": detailed_analytics
            }
            
            if metrics.success:
                result["message"] = f"Campaign summary exported for {metrics.total_rows} contacts"
                
                # Add summary statistics to result
                try:
                    with open(self.output_path, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                        result["summary_preview"] = {
                            "total_contacts": summary_data.get("total_contacts", 0),
                            "high_quality_contacts": summary_data.get("high_quality_contacts", 0),
                            "validation_success_rate": summary_data.get("validation_success_rate", 0.0),
                            "platform_count": len(summary_data.get("platform_distribution", {}))
                        }
                except Exception as e:
                    result["summary_preview_error"] = str(e)
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Campaign summary export failed: {str(e)}",
                "summary_path": None,
                "metrics": None
            })
    
    def _generate_detailed_analytics(self) -> Dict[str, Any]:
        """Generate detailed analytics for the campaign"""
        try:
            analytics = {}
            
            # Quality score distribution
            quality_scores = []
            confidence_levels = {"very_high": 0, "high": 0, "medium": 0, "low": 0, "very_low": 0}
            
            # Contact method breakdown
            contact_methods = {
                "email_only": 0,
                "website_only": 0,
                "social_only": 0,
                "multiple_methods": 0,
                "no_contact": 0
            }
            
            # Platform analytics
            platform_quality = {}
            
            for record in self.contact_data:
                # Quality scores
                try:
                    score = float(record.get('contact_quality_score', 0))
                    if score > 0:
                        quality_scores.append(score)
                except (ValueError, TypeError):
                    pass
                
                # Confidence levels
                confidence = record.get('contact_confidence', '').lower()
                if confidence in confidence_levels:
                    confidence_levels[confidence] += 1
                
                # Contact methods
                has_email = bool(record.get('host_email') or record.get('booking_email'))
                has_website = bool(record.get('podcast_website') or record.get('contact_page_url'))
                has_social = bool(record.get('social_links'))
                
                contact_count = sum([has_email, has_website, has_social])
                
                if contact_count == 0:
                    contact_methods["no_contact"] += 1
                elif contact_count > 1:
                    contact_methods["multiple_methods"] += 1
                elif has_email:
                    contact_methods["email_only"] += 1
                elif has_website:
                    contact_methods["website_only"] += 1
                elif has_social:
                    contact_methods["social_only"] += 1
                
                # Platform quality analysis
                platform = record.get('platform_source', 'Unknown')
                if platform not in platform_quality:
                    platform_quality[platform] = {
                        "count": 0,
                        "high_quality": 0,
                        "with_email": 0,
                        "avg_confidence": 0.0
                    }
                
                platform_quality[platform]["count"] += 1
                
                if confidence in ['very_high', 'high']:
                    platform_quality[platform]["high_quality"] += 1
                
                if has_email:
                    platform_quality[platform]["with_email"] += 1
            
            # Calculate platform averages
            for platform in platform_quality:
                count = platform_quality[platform]["count"]
                if count > 0:
                    platform_quality[platform]["high_quality_rate"] = platform_quality[platform]["high_quality"] / count
                    platform_quality[platform]["email_availability_rate"] = platform_quality[platform]["with_email"] / count
            
            # Quality score statistics
            if quality_scores:
                analytics["quality_score_stats"] = {
                    "count": len(quality_scores),
                    "average": sum(quality_scores) / len(quality_scores),
                    "minimum": min(quality_scores),
                    "maximum": max(quality_scores),
                    "median": sorted(quality_scores)[len(quality_scores) // 2]
                }
            
            analytics.update({
                "confidence_level_distribution": confidence_levels,
                "contact_method_breakdown": contact_methods,
                "platform_quality_analysis": platform_quality,
                "analysis_timestamp": datetime.now().isoformat()
            })
            
            return analytics
            
        except Exception as e:
            return {"analytics_error": str(e)}


class ProxyPerformanceExportTool(BaseTool):
    """
    Tool for generating and exporting proxy performance statistics.
    
    This tool analyzes proxy usage data and generates comprehensive
    performance reports including success rates, error analysis,
    and cost metrics.
    """
    
    proxy_stats: Dict[str, Any] = Field(
        description="Proxy performance statistics and metrics"
    )
    
    output_path: str = Field(
        description="Output file path for the proxy performance JSON"
    )
    
    include_cost_analysis: bool = Field(
        default=True,
        description="Whether to include cost analysis and optimization recommendations"
    )
    
    def run(self) -> str:
        """
        Generate and export proxy performance report.
        
        Returns:
            JSON string with export results and performance metrics
        """
        try:
            # Import the exporter here to avoid circular imports
            from agents.exporter_agent import JSONStatsExporter
            
            # Initialize exporter
            exporter = JSONStatsExporter()
            
            # Validate input
            if not self.proxy_stats:
                return json.dumps({
                    "success": False,
                    "error": "No proxy statistics provided for analysis",
                    "performance_summary": None
                })
            
            # Perform proxy performance export
            metrics = exporter.export_proxy_performance(
                proxy_stats=self.proxy_stats,
                output_path=self.output_path
            )
            
            # Generate cost analysis if requested
            cost_analysis = {}
            if self.include_cost_analysis:
                cost_analysis = self._generate_cost_analysis()
            
            # Prepare result
            result = {
                "success": metrics.success,
                "error": metrics.error_message,
                "performance_path": self.output_path if metrics.success else None,
                "metrics": {
                    "export_duration_ms": metrics.write_duration_ms,
                    "file_size_bytes": metrics.file_size_bytes
                },
                "cost_analysis": cost_analysis
            }
            
            if metrics.success:
                result["message"] = "Proxy performance report exported successfully"
                
                # Add performance preview to result
                try:
                    with open(self.output_path, 'r', encoding='utf-8') as f:
                        performance_data = json.load(f)
                        result["performance_preview"] = {
                            "success_rate": performance_data.get("success_rate", 0.0),
                            "total_requests": performance_data.get("total_requests", 0),
                            "avg_response_time_ms": performance_data.get("avg_response_time_ms", 0.0),
                            "blocked_count": performance_data.get("blocked_count", 0)
                        }
                except Exception as e:
                    result["performance_preview_error"] = str(e)
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Proxy performance export failed: {str(e)}",
                "performance_path": None,
                "metrics": None
            })
    
    def _generate_cost_analysis(self) -> Dict[str, Any]:
        """Generate cost analysis and optimization recommendations"""
        try:
            analysis = {}
            
            # Extract key metrics
            total_requests = self.proxy_stats.get('total_requests', 0)
            successful_requests = self.proxy_stats.get('successful_requests', 0)
            failed_requests = self.proxy_stats.get('failed_requests', 0)
            blocked_count = self.proxy_stats.get('blocked_count', 0)
            bandwidth_mb = self.proxy_stats.get('bandwidth_used_mb', 0.0)
            
            # Calculate efficiency metrics
            if total_requests > 0:
                success_rate = successful_requests / total_requests
                block_rate = blocked_count / total_requests
                waste_rate = failed_requests / total_requests
            else:
                success_rate = block_rate = waste_rate = 0.0
            
            analysis["efficiency_metrics"] = {
                "success_rate": success_rate,
                "block_rate": block_rate,
                "waste_rate": waste_rate,
                "requests_per_mb": total_requests / bandwidth_mb if bandwidth_mb > 0 else 0
            }
            
            # Cost estimates (example rates - should be configurable)
            cost_per_request = 0.001  # $0.001 per request
            cost_per_mb = 0.10       # $0.10 per MB
            
            estimated_costs = {
                "request_cost": total_requests * cost_per_request,
                "bandwidth_cost": bandwidth_mb * cost_per_mb,
                "waste_cost": failed_requests * cost_per_request,
                "total_estimated_cost": (total_requests * cost_per_request) + (bandwidth_mb * cost_per_mb)
            }
            
            analysis["cost_estimates"] = estimated_costs
            
            # Optimization recommendations
            recommendations = []
            
            if block_rate > 0.1:  # More than 10% blocked
                recommendations.append({
                    "priority": "high",
                    "issue": "High block rate detected",
                    "recommendation": "Consider rotating proxies more frequently or using higher quality proxy providers",
                    "potential_savings": f"Could reduce blocks by up to {blocked_count * 0.5:.0f} requests"
                })
            
            if waste_rate > 0.05:  # More than 5% failed
                recommendations.append({
                    "priority": "medium",
                    "issue": "High failure rate",
                    "recommendation": "Implement better error handling and retry logic",
                    "potential_savings": f"Could save ${failed_requests * cost_per_request * 0.7:.2f} in wasted requests"
                })
            
            if bandwidth_mb > 1000 and total_requests / bandwidth_mb < 100:  # Low efficiency
                recommendations.append({
                    "priority": "medium",
                    "issue": "Low request efficiency per MB",
                    "recommendation": "Optimize request payload sizes and enable compression",
                    "potential_savings": f"Could reduce bandwidth costs by up to 30%"
                })
            
            analysis["optimization_recommendations"] = recommendations
            analysis["analysis_timestamp"] = datetime.now().isoformat()
            
            return analysis
            
        except Exception as e:
            return {"cost_analysis_error": str(e)}


class AnalyticsReportTool(BaseTool):
    """
    Tool for generating comprehensive analytics reports with charts and insights.
    
    This tool creates detailed analytical reports combining contact data,
    campaign performance, and actionable insights for podcast outreach.
    """
    
    contact_data: List[Dict[str, Any]] = Field(
        description="Contact data for analysis"
    )
    
    campaign_info: Dict[str, Any] = Field(
        description="Campaign metadata and information"
    )
    
    output_path: str = Field(
        description="Output file path for the analytics report"
    )
    
    include_charts: bool = Field(
        default=True,
        description="Whether to generate chart data for visualization"
    )
    
    include_insights: bool = Field(
        default=True,
        description="Whether to generate AI-powered insights and recommendations"
    )
    
    def run(self) -> str:
        """
        Generate comprehensive analytics report.
        
        Returns:
            JSON string with report results and analytics data
        """
        try:
            # Validate input
            if not self.contact_data:
                return json.dumps({
                    "success": False,
                    "error": "No contact data provided for analytics",
                    "report_path": None
                })
            
            # Generate comprehensive analytics
            analytics_data = self._generate_comprehensive_analytics()
            
            # Generate chart data if requested
            chart_data = {}
            if self.include_charts:
                chart_data = self._generate_chart_data()
            
            # Generate insights if requested
            insights = {}
            if self.include_insights:
                insights = self._generate_insights()
            
            # Compile final report
            report = {
                "report_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "campaign_info": self.campaign_info,
                    "total_contacts_analyzed": len(self.contact_data),
                    "report_version": "1.0"
                },
                "analytics": analytics_data,
                "charts": chart_data,
                "insights": insights
            }
            
            # Write report to file
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            # Calculate file size
            file_size = os.path.getsize(self.output_path)
            
            return json.dumps({
                "success": True,
                "message": f"Analytics report generated for {len(self.contact_data)} contacts",
                "report_path": self.output_path,
                "metrics": {
                    "file_size_bytes": file_size,
                    "sections_generated": len([k for k, v in {"analytics": analytics_data, "charts": chart_data, "insights": insights}.items() if v]),
                    "total_contacts": len(self.contact_data)
                },
                "report_preview": {
                    "high_quality_contacts": analytics_data.get("quality_summary", {}).get("high_quality", 0),
                    "platform_count": len(analytics_data.get("platform_analysis", {})),
                    "top_recommendation": insights.get("top_recommendations", [{}])[0].get("title", "No recommendations") if insights.get("top_recommendations") else "No recommendations"
                }
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Analytics report generation failed: {str(e)}",
                "report_path": None,
                "metrics": None
            })
    
    def _generate_comprehensive_analytics(self) -> Dict[str, Any]:
        """Generate comprehensive analytics from contact data"""
        analytics = {}
        
        # Quality summary
        quality_counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
        confidence_scores = []
        
        # Contact method analysis
        contact_availability = {
            "email": 0,
            "website": 0,
            "social": 0,
            "multiple": 0,
            "none": 0
        }
        
        # Platform analysis
        platform_stats = {}
        
        # Content analysis
        content_types = {}
        interview_styles = {"yes": 0, "no": 0, "unknown": 0}
        
        for record in self.contact_data:
            # Quality analysis
            confidence = record.get('contact_confidence', '').lower()
            if confidence in ['very_high', 'high']:
                quality_counts['high'] += 1
            elif confidence == 'medium':
                quality_counts['medium'] += 1
            elif confidence in ['low', 'very_low']:
                quality_counts['low'] += 1
            else:
                quality_counts['unknown'] += 1
            
            # Confidence scores
            try:
                score = float(record.get('contact_quality_score', 0))
                if score > 0:
                    confidence_scores.append(score)
            except (ValueError, TypeError):
                pass
            
            # Contact availability
            has_email = bool(record.get('host_email') or record.get('booking_email'))
            has_website = bool(record.get('podcast_website') or record.get('contact_page_url'))
            has_social = bool(record.get('social_links'))
            
            contact_methods = sum([has_email, has_website, has_social])
            
            if contact_methods == 0:
                contact_availability['none'] += 1
            elif contact_methods > 1:
                contact_availability['multiple'] += 1
            elif has_email:
                contact_availability['email'] += 1
            elif has_website:
                contact_availability['website'] += 1
            elif has_social:
                contact_availability['social'] += 1
            
            # Platform analysis
            platform = record.get('platform_source', 'Unknown')
            if platform not in platform_stats:
                platform_stats[platform] = {"count": 0, "high_quality": 0}
            platform_stats[platform]["count"] += 1
            if confidence in ['very_high', 'high']:
                platform_stats[platform]["high_quality"] += 1
            
            # Content analysis
            content_type = record.get('content_format_type', 'Unknown')
            content_types[content_type] = content_types.get(content_type, 0) + 1
            
            interview_style = record.get('interview_style', '').lower()
            if interview_style == 'yes':
                interview_styles['yes'] += 1
            elif interview_style == 'no':
                interview_styles['no'] += 1
            else:
                interview_styles['unknown'] += 1
        
        analytics.update({
            "quality_summary": quality_counts,
            "confidence_score_stats": {
                "count": len(confidence_scores),
                "average": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                "min": min(confidence_scores) if confidence_scores else 0,
                "max": max(confidence_scores) if confidence_scores else 0
            },
            "contact_availability": contact_availability,
            "platform_analysis": platform_stats,
            "content_analysis": {
                "content_types": content_types,
                "interview_styles": interview_styles
            }
        })
        
        return analytics
    
    def _generate_chart_data(self) -> Dict[str, Any]:
        """Generate data suitable for chart visualization"""
        charts = {}
        
        # Quality distribution pie chart
        quality_counts = {"High": 0, "Medium": 0, "Low": 0}
        
        # Platform distribution bar chart
        platform_counts = {}
        
        # Contact method distribution
        contact_methods = {"Email": 0, "Website": 0, "Social": 0, "Multiple": 0, "None": 0}
        
        for record in self.contact_data:
            # Quality distribution
            confidence = record.get('contact_confidence', '').lower()
            if confidence in ['very_high', 'high']:
                quality_counts['High'] += 1
            elif confidence == 'medium':
                quality_counts['Medium'] += 1
            else:
                quality_counts['Low'] += 1
            
            # Platform distribution
            platform = record.get('platform_source', 'Unknown')
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            
            # Contact methods
            has_email = bool(record.get('host_email') or record.get('booking_email'))
            has_website = bool(record.get('podcast_website') or record.get('contact_page_url'))
            has_social = bool(record.get('social_links'))
            
            contact_count = sum([has_email, has_website, has_social])
            
            if contact_count == 0:
                contact_methods['None'] += 1
            elif contact_count > 1:
                contact_methods['Multiple'] += 1
            elif has_email:
                contact_methods['Email'] += 1
            elif has_website:
                contact_methods['Website'] += 1
            elif has_social:
                contact_methods['Social'] += 1
        
        charts.update({
            "quality_distribution": {
                "type": "pie",
                "data": quality_counts,
                "title": "Contact Quality Distribution"
            },
            "platform_distribution": {
                "type": "bar",
                "data": platform_counts,
                "title": "Contacts by Platform"
            },
            "contact_method_distribution": {
                "type": "bar",
                "data": contact_methods,
                "title": "Contact Method Availability"
            }
        })
        
        return charts
    
    def _generate_insights(self) -> Dict[str, Any]:
        """Generate AI-powered insights and recommendations"""
        insights = {}
        
        total_contacts = len(self.contact_data)
        
        # Calculate key metrics
        email_contacts = sum(1 for r in self.contact_data if r.get('host_email') or r.get('booking_email'))
        high_quality = sum(1 for r in self.contact_data if r.get('contact_confidence', '').lower() in ['very_high', 'high'])
        
        email_rate = email_contacts / total_contacts if total_contacts > 0 else 0
        quality_rate = high_quality / total_contacts if total_contacts > 0 else 0
        
        # Generate recommendations
        recommendations = []
        
        if email_rate > 0.7:
            recommendations.append({
                "title": "High Email Availability",
                "priority": "high",
                "description": f"Excellent email contact rate ({email_rate:.1%}). Focus on direct email outreach for maximum efficiency.",
                "action_items": [
                    "Prioritize email-based outreach campaigns",
                    "Create personalized email templates",
                    "Set up email tracking and follow-up sequences"
                ]
            })
        elif email_rate < 0.3:
            recommendations.append({
                "title": "Low Email Availability",
                "priority": "medium",
                "description": f"Low email contact rate ({email_rate:.1%}). Consider multi-channel approach.",
                "action_items": [
                    "Develop website contact form strategies",
                    "Build social media engagement campaigns",
                    "Research additional contact discovery methods"
                ]
            })
        
        if quality_rate > 0.5:
            recommendations.append({
                "title": "High Quality Contact Pool",
                "priority": "high",
                "description": f"Strong quality rate ({quality_rate:.1%}). Excellent potential for successful outreach.",
                "action_items": [
                    "Fast-track outreach to high-quality contacts",
                    "Prepare premium pitch materials",
                    "Allocate more resources to follow-up"
                ]
            })
        
        # Platform insights
        platform_analysis = {}
        platform_counts = {}
        
        for record in self.contact_data:
            platform = record.get('platform_source', 'Unknown')
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        if platform_counts:
            top_platform = max(platform_counts, key=platform_counts.get)
            platform_analysis["top_platform"] = {
                "name": top_platform,
                "count": platform_counts[top_platform],
                "percentage": platform_counts[top_platform] / total_contacts
            }
        
        insights.update({
            "summary": {
                "total_contacts": total_contacts,
                "email_availability_rate": email_rate,
                "high_quality_rate": quality_rate,
                "overall_grade": "A" if quality_rate > 0.7 and email_rate > 0.6 else "B" if quality_rate > 0.4 and email_rate > 0.3 else "C"
            },
            "top_recommendations": recommendations,
            "platform_insights": platform_analysis,
            "generated_at": datetime.now().isoformat()
        })
        
        return insights
"""
Comprehensive Export Tool

Agency Swarm tool that orchestrates the complete export process including
CSV generation, JSON statistics, error logging, file validation, and
Google Drive integration for the final podcast contact discovery results.
"""

import os
import json
import time
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


class ComprehensiveExportTool(BaseTool):
    """
    Master tool for comprehensive export of podcast contact discovery results.
    
    This tool orchestrates the entire export process from validated contact data
    to final deliverables including CSV files, analytics reports, error logs,
    file validation, and Google Drive sharing.
    """
    
    contact_data: List[Dict[str, Any]] = Field(
        description="Validated contact data from the discovery process"
    )
    
    campaign_info: Dict[str, Any] = Field(
        description="Campaign metadata including topic, search parameters, etc."
    )
    
    proxy_stats: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional proxy performance statistics"
    )
    
    export_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Export configuration options"
    )
    
    upload_to_drive: bool = Field(
        default=False,
        description="Whether to upload results to Google Drive"
    )
    
    validate_exports: bool = Field(
        default=True,
        description="Whether to validate exported files"
    )
    
    generate_analytics: bool = Field(
        default=True,
        description="Whether to generate comprehensive analytics report"
    )
    
    def run(self) -> str:
        """
        Execute comprehensive export process.
        
        Returns:
            JSON string with complete export results and file locations
        """
        start_time = time.time()
        
        export_results = {
            "export_started": datetime.now().isoformat(),
            "campaign_info": self.campaign_info,
            "input_data": {
                "total_contacts": len(self.contact_data),
                "has_proxy_stats": self.proxy_stats is not None
            },
            "export_phases": {},
            "exported_files": {},
            "validation_results": {},
            "google_drive_results": {},
            "overall_success": False,
            "errors": [],
            "warnings": [],
            "performance_metrics": {}
        }
        
        try:
            # Phase 1: CSV Export
            export_results["export_phases"]["csv_export"] = self._execute_csv_export()
            
            # Phase 2: JSON Statistics Export
            export_results["export_phases"]["json_export"] = self._execute_json_export()
            
            # Phase 3: Analytics Report Generation
            if self.generate_analytics:
                export_results["export_phases"]["analytics"] = self._execute_analytics_generation()
            
            # Phase 4: Error Logging
            export_results["export_phases"]["error_logging"] = self._execute_error_logging()
            
            # Phase 5: File Validation
            if self.validate_exports:
                export_results["export_phases"]["validation"] = self._execute_file_validation()
            
            # Phase 6: Google Drive Upload
            if self.upload_to_drive:
                export_results["export_phases"]["google_drive"] = self._execute_google_drive_upload()
            
            # Calculate overall success
            failed_phases = [
                phase for phase, result in export_results["export_phases"].items()
                if not result.get("success", False)
            ]
            
            export_results["overall_success"] = len(failed_phases) == 0
            
            if failed_phases:
                export_results["errors"].append(f"Failed phases: {', '.join(failed_phases)}")
            
            # Performance metrics
            total_time = time.time() - start_time
            export_results["performance_metrics"] = {
                "total_export_time_seconds": total_time,
                "contacts_per_second": len(self.contact_data) / total_time if total_time > 0 else 0,
                "export_completed": datetime.now().isoformat()
            }
            
            # Generate summary message
            if export_results["overall_success"]:
                message = f"Successfully exported {len(self.contact_data)} contacts with all phases completed"
            else:
                message = f"Export completed with {len(failed_phases)} failed phases out of {len(export_results['export_phases'])}"
            
            return json.dumps({
                "success": export_results["overall_success"],
                "message": message,
                "export_results": export_results
            }, indent=2, default=str)
            
        except Exception as e:
            export_results["errors"].append(f"Critical export failure: {str(e)}")
            export_results["performance_metrics"]["total_export_time_seconds"] = time.time() - start_time
            
            return json.dumps({
                "success": False,
                "message": f"Comprehensive export failed: {str(e)}",
                "export_results": export_results
            }, indent=2, default=str)
    
    def _execute_csv_export(self) -> Dict[str, Any]:
        """Execute CSV export phase"""
        try:
            from .csv_export_tool import CSVExportTool
            
            # Generate output path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            topic_safe = "".join(c for c in self.campaign_info.get('topic', 'unknown') if c.isalnum() or c in (' ', '-', '_')).strip()
            topic_safe = topic_safe.replace(' ', '_')
            
            csv_filename = f"podcast_contacts_{topic_safe}_{timestamp}.csv"
            csv_path = os.path.join(self._get_export_dir(), csv_filename)
            
            # Execute CSV export
            csv_tool = CSVExportTool(
                contact_data=self.contact_data,
                output_path=csv_path,
                validate_schema=True,
                include_metadata=True
            )
            
            result_str = csv_tool.run()
            result = json.loads(result_str)
            
            if result["success"]:
                self.exported_files["csv"] = {
                    "path": csv_path,
                    "metadata_path": result.get("metadata_path"),
                    "size_bytes": result["metrics"]["file_size_bytes"],
                    "row_count": result["metrics"]["total_rows"]
                }
            
            return {
                "success": result["success"],
                "phase": "csv_export",
                "details": result,
                "output_file": csv_path if result["success"] else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "phase": "csv_export",
                "error": str(e)
            }
    
    def _execute_json_export(self) -> Dict[str, Any]:
        """Execute JSON statistics export phase"""
        try:
            from .json_stats_export_tool import CampaignSummaryExportTool, ProxyPerformanceExportTool
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = self._get_export_dir()
            
            results = {"campaign_summary": None, "proxy_performance": None}
            
            # Export campaign summary
            summary_path = os.path.join(export_dir, f"campaign_summary_{timestamp}.json")
            summary_tool = CampaignSummaryExportTool(
                contact_data=self.contact_data,
                campaign_info=self.campaign_info,
                output_path=summary_path,
                include_detailed_analytics=True
            )
            
            summary_result_str = summary_tool.run()
            summary_result = json.loads(summary_result_str)
            results["campaign_summary"] = summary_result
            
            if summary_result["success"]:
                self.exported_files["campaign_summary"] = {
                    "path": summary_path,
                    "size_bytes": summary_result["metrics"]["file_size_bytes"]
                }
            
            # Export proxy performance if data available
            if self.proxy_stats:
                proxy_path = os.path.join(export_dir, f"proxy_performance_{timestamp}.json")
                proxy_tool = ProxyPerformanceExportTool(
                    proxy_stats=self.proxy_stats,
                    output_path=proxy_path,
                    include_cost_analysis=True
                )
                
                proxy_result_str = proxy_tool.run()
                proxy_result = json.loads(proxy_result_str)
                results["proxy_performance"] = proxy_result
                
                if proxy_result["success"]:
                    self.exported_files["proxy_performance"] = {
                        "path": proxy_path,
                        "size_bytes": proxy_result["metrics"]["file_size_bytes"]
                    }
            
            overall_success = all(r["success"] for r in results.values() if r is not None)
            
            return {
                "success": overall_success,
                "phase": "json_export",
                "details": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "phase": "json_export",
                "error": str(e)
            }
    
    def _execute_analytics_generation(self) -> Dict[str, Any]:
        """Execute analytics report generation phase"""
        try:
            from .json_stats_export_tool import AnalyticsReportTool
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            analytics_path = os.path.join(self._get_export_dir(), f"analytics_report_{timestamp}.json")
            
            analytics_tool = AnalyticsReportTool(
                contact_data=self.contact_data,
                campaign_info=self.campaign_info,
                output_path=analytics_path,
                include_charts=True,
                include_insights=True
            )
            
            result_str = analytics_tool.run()
            result = json.loads(result_str)
            
            if result["success"]:
                self.exported_files["analytics"] = {
                    "path": analytics_path,
                    "size_bytes": result["metrics"]["file_size_bytes"]
                }
            
            return {
                "success": result["success"],
                "phase": "analytics_generation",
                "details": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "phase": "analytics_generation",
                "error": str(e)
            }
    
    def _execute_error_logging(self) -> Dict[str, Any]:
        """Execute error logging phase"""
        try:
            # Check if there are any errors to log from previous phases
            errors_to_log = []
            
            # Collect errors from previous phases
            for file_path in getattr(self, 'exported_files', {}).values():
                if isinstance(file_path, dict) and file_path.get('path'):
                    if not os.path.exists(file_path['path']):
                        errors_to_log.append({
                            "error_type": "file_missing",
                            "error_message": f"Exported file not found: {file_path['path']}",
                            "component": "export_verification"
                        })
            
            if errors_to_log:
                from .error_logging_tool import ErrorLogTool
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                error_log_path = os.path.join(self._get_export_dir(), f"error_log_{timestamp}.csv")
                
                # Log each error
                logged_count = 0
                for error in errors_to_log:
                    error_tool = ErrorLogTool(
                        error_log_path=error_log_path,
                        error_type=error["error_type"],
                        error_message=error["error_message"],
                        component=error.get("component", "comprehensive_export"),
                        severity="medium"
                    )
                    
                    result_str = error_tool.run()
                    result = json.loads(result_str)
                    
                    if result["success"]:
                        logged_count += 1
                
                if logged_count > 0:
                    self.exported_files["error_log"] = {
                        "path": error_log_path,
                        "error_count": logged_count
                    }
                
                return {
                    "success": True,
                    "phase": "error_logging",
                    "errors_logged": logged_count,
                    "error_log_path": error_log_path if logged_count > 0 else None
                }
            else:
                return {
                    "success": True,
                    "phase": "error_logging",
                    "errors_logged": 0,
                    "message": "No errors to log"
                }
            
        except Exception as e:
            return {
                "success": False,
                "phase": "error_logging",
                "error": str(e)
            }
    
    def _execute_file_validation(self) -> Dict[str, Any]:
        """Execute file validation phase"""
        try:
            from .file_validation_tool import FileValidationTool
            
            # Get all exported file paths
            file_paths = []
            for file_info in getattr(self, 'exported_files', {}).values():
                if isinstance(file_info, dict) and file_info.get('path'):
                    file_paths.append(file_info['path'])
            
            if not file_paths:
                return {
                    "success": True,
                    "phase": "file_validation",
                    "message": "No files to validate"
                }
            
            # Set up expected schemas
            expected_schemas = {
                "csv": [
                    "podcast_name", "host_name", "podcast_description",
                    "host_email", "booking_email", "alternative_emails"
                ],  # Subset of required columns
                "csv_required": ["podcast_name", "host_name"]
            }
            
            validation_tool = FileValidationTool(
                file_paths=file_paths,
                validation_type="comprehensive",
                expected_schemas=expected_schemas,
                generate_checksums=True
            )
            
            result_str = validation_tool.run()
            result = json.loads(result_str)
            
            self.validation_results = result
            
            return {
                "success": result.get("overall_success", False),
                "phase": "file_validation",
                "details": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "phase": "file_validation",
                "error": str(e)
            }
    
    def _execute_google_drive_upload(self) -> Dict[str, Any]:
        """Execute Google Drive upload phase"""
        try:
            from .google_drive_tool import GoogleDriveUploadTool
            
            # Get all exported file paths
            file_paths = []
            for file_info in getattr(self, 'exported_files', {}).values():
                if isinstance(file_info, dict) and file_info.get('path'):
                    file_paths.append(file_info['path'])
            
            if not file_paths:
                return {
                    "success": True,
                    "phase": "google_drive_upload",
                    "message": "No files to upload"
                }
            
            # Generate folder name with campaign info
            topic = self.campaign_info.get('topic', 'unknown')
            timestamp = datetime.now().strftime("%Y-%m-%d")
            folder_name = f"Podcast Contacts - {topic} - {timestamp}"
            
            drive_tool = GoogleDriveUploadTool(
                file_paths=file_paths,
                folder_name=folder_name,
                create_shareable_links=True,
                share_permissions="view"
            )
            
            result_str = drive_tool.run()
            result = json.loads(result_str)
            
            self.google_drive_results = result
            
            return {
                "success": result["success"],
                "phase": "google_drive_upload",
                "details": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "phase": "google_drive_upload",
                "error": str(e)
            }
    
    def _get_export_dir(self) -> str:
        """Get or create export directory"""
        export_dir = self.export_config.get("output_directory", os.path.join(os.getcwd(), "output", "exports"))
        os.makedirs(export_dir, exist_ok=True)
        return export_dir


class FinalDeliveryTool(BaseTool):
    """
    Tool for preparing final delivery package with all export results.
    
    This tool creates a comprehensive delivery package including all exported
    files, documentation, and instructions for end users.
    """
    
    export_results: Dict[str, Any] = Field(
        description="Results from comprehensive export process"
    )
    
    include_documentation: bool = Field(
        default=True,
        description="Whether to include usage documentation"
    )
    
    create_readme: bool = Field(
        default=True,
        description="Whether to create a README file with instructions"
    )
    
    def run(self) -> str:
        """
        Prepare final delivery package.
        
        Returns:
            JSON string with delivery package information
        """
        try:
            delivery_package = {
                "package_created": datetime.now().isoformat(),
                "campaign_info": self.export_results.get("campaign_info", {}),
                "files_included": {},
                "documentation": {},
                "delivery_summary": {},
                "next_steps": []
            }
            
            # Collect all exported files
            exported_files = self.export_results.get("exported_files", {})
            for file_type, file_info in exported_files.items():
                if isinstance(file_info, dict) and file_info.get("path"):
                    delivery_package["files_included"][file_type] = {
                        "file_path": file_info["path"],
                        "file_name": os.path.basename(file_info["path"]),
                        "size_bytes": file_info.get("size_bytes", 0),
                        "description": self._get_file_description(file_type)
                    }
            
            # Generate documentation if requested
            if self.include_documentation:
                delivery_package["documentation"] = self._generate_documentation()
            
            # Create README if requested
            if self.create_readme:
                readme_content = self._generate_readme()
                readme_path = os.path.join(
                    os.path.dirname(next(iter(exported_files.values())).get("path", "")),
                    "README.md"
                )
                
                try:
                    with open(readme_path, 'w', encoding='utf-8') as f:
                        f.write(readme_content)
                    
                    delivery_package["documentation"]["readme_file"] = readme_path
                except Exception as e:
                    delivery_package["documentation"]["readme_error"] = str(e)
            
            # Generate delivery summary
            total_contacts = self.export_results.get("input_data", {}).get("total_contacts", 0)
            successful_phases = sum(
                1 for phase in self.export_results.get("export_phases", {}).values()
                if phase.get("success", False)
            )
            total_phases = len(self.export_results.get("export_phases", {}))
            
            delivery_package["delivery_summary"] = {
                "total_contacts_exported": total_contacts,
                "export_phases_completed": f"{successful_phases}/{total_phases}",
                "total_files_generated": len(delivery_package["files_included"]),
                "overall_success": self.export_results.get("overall_success", False)
            }
            
            # Generate next steps
            delivery_package["next_steps"] = self._generate_next_steps()
            
            return json.dumps({
                "success": True,
                "message": f"Delivery package prepared with {len(delivery_package['files_included'])} files",
                "delivery_package": delivery_package
            }, indent=2, default=str)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Final delivery tool failed: {str(e)}",
                "delivery_package": None
            })
    
    def _get_file_description(self, file_type: str) -> str:
        """Get description for file type"""
        descriptions = {
            "csv": "Main contact data in CSV format, compatible with Excel and Google Sheets",
            "campaign_summary": "JSON file with campaign statistics and analytics",
            "proxy_performance": "JSON file with proxy usage and performance metrics",
            "analytics": "Comprehensive analytics report with insights and recommendations",
            "error_log": "Log of any errors or issues encountered during processing"
        }
        return descriptions.get(file_type, "Generated file from export process")
    
    def _generate_documentation(self) -> Dict[str, str]:
        """Generate documentation for exported files"""
        return {
            "csv_usage": "Open the CSV file in Excel or Google Sheets to view contact information. Each row represents one podcast contact with all available information.",
            "analytics_usage": "The analytics JSON file contains insights and recommendations. Use a JSON viewer or import into analytics tools.",
            "sharing_guidelines": "Share files according to your organization's data privacy policies. Consider the sensitivity of contact information.",
            "data_quality": "Review the error log if present to understand any data quality issues or processing limitations."
        }
    
    def _generate_readme(self) -> str:
        """Generate README content"""
        campaign_info = self.export_results.get("campaign_info", {})
        topic = campaign_info.get("topic", "Unknown Topic")
        total_contacts = self.export_results.get("input_data", {}).get("total_contacts", 0)
        
        readme = f"""# Podcast Contact Discovery Results

## Campaign Information
- **Topic:** {topic}
- **Total Contacts Found:** {total_contacts}
- **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Files Included

### 📊 Main Contact Data (CSV)
The primary export file containing all discovered podcast contacts with:
- Host names and contact information
- Email addresses (where available)
- Podcast details and platform information
- Quality scores and confidence ratings
- Social media links and website URLs

**Usage:** Open in Excel, Google Sheets, or any spreadsheet application.

### 📈 Campaign Analytics (JSON)
Comprehensive analysis including:
- Contact quality distribution
- Platform analytics
- Response likelihood estimates
- Outreach recommendations

**Usage:** Import into analytics tools or view with JSON viewer.

### 🚨 Error Log (CSV, if present)
Record of any issues encountered during data collection:
- Failed scraping attempts
- Validation errors
- Data quality warnings

## Getting Started

1. **Review the main CSV file** for contact information
2. **Check analytics report** for insights and recommendations
3. **Prioritize contacts** based on quality scores and response likelihood
4. **Plan outreach strategy** using provided recommendations

## Data Quality Notes

- Contacts are scored based on information availability and quality
- Email addresses have been validated where possible
- Social media links and websites are verified for accessibility
- Confidence ratings indicate likelihood of successful contact

## Privacy and Usage Guidelines

- Handle contact information according to your privacy policies
- Respect opt-out requests and communication preferences
- Follow applicable data protection regulations
- Consider the context and appropriateness of outreach

## Support

For questions about this data or the export process, contact your data team.

---
*Generated by Podcast Contact Discovery System*
"""
        return readme
    
    def _generate_next_steps(self) -> List[str]:
        """Generate recommended next steps"""
        steps = [
            "Review the main CSV file to understand available contact data",
            "Check the analytics report for insights and outreach recommendations",
            "Prioritize contacts based on quality scores and response likelihood",
            "Prepare personalized outreach materials for high-priority contacts",
            "Set up tracking system for outreach responses and follow-ups"
        ]
        
        # Add conditional steps based on export results
        if "error_log" in self.export_results.get("exported_files", {}):
            steps.insert(1, "Review error log to understand any data quality limitations")
        
        if self.export_results.get("google_drive_results", {}).get("success"):
            steps.append("Share Google Drive links with relevant team members")
        
        return steps
"""
Error Logging Tool

Agency Swarm tool for comprehensive error logging and failure tracking
during the podcast contact discovery process.
"""

import os
import csv
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


class ErrorLogTool(BaseTool):
    """
    Tool for logging errors to CSV format with comprehensive error details.
    
    This tool appends error information to error_log.csv with proper
    categorization, severity levels, and contextual information for
    debugging and analysis.
    """
    
    error_log_path: str = Field(
        description="Path to the error log CSV file"
    )
    
    error_type: str = Field(
        description="Type/category of error (e.g., 'scraping_error', 'validation_error', 'export_error')"
    )
    
    error_message: str = Field(
        description="Detailed error message"
    )
    
    context: str = Field(
        default="",
        description="Additional context about where/when the error occurred"
    )
    
    severity: str = Field(
        default="medium",
        description="Error severity level: 'low', 'medium', 'high', 'critical'"
    )
    
    component: str = Field(
        default="",
        description="Component or module where the error occurred"
    )
    
    url: str = Field(
        default="",
        description="URL associated with the error (if applicable)"
    )
    
    retry_count: int = Field(
        default=0,
        description="Number of retries attempted for this operation"
    )
    
    additional_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional structured data related to the error"
    )
    
    def run(self) -> str:
        """
        Log error to CSV file.
        
        Returns:
            JSON string with logging results
        """
        try:
            # Import the error logger here to avoid circular imports
            from agents.exporter_agent import ErrorLogManager
            
            # Initialize error logger
            error_logger = ErrorLogManager()
            
            # Validate severity level
            valid_severities = ['low', 'medium', 'high', 'critical']
            if self.severity not in valid_severities:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid severity level '{self.severity}'. Must be one of: {', '.join(valid_severities)}",
                    "logged": False
                })
            
            # Prepare enhanced context with additional data
            enhanced_context = self.context
            if self.additional_data:
                try:
                    additional_json = json.dumps(self.additional_data, default=str)
                    enhanced_context = f"{self.context} | Additional Data: {additional_json}"
                except Exception:
                    # If serialization fails, just use the original context
                    pass
            
            # Log the error
            success = error_logger.append_error(
                error_log_path=self.error_log_path,
                error_type=self.error_type,
                error_message=self.error_message,
                context=enhanced_context,
                severity=self.severity,
                component=self.component,
                url=self.url,
                retry_count=self.retry_count
            )
            
            if success:
                # Get file statistics
                file_size = os.path.getsize(self.error_log_path) if os.path.exists(self.error_log_path) else 0
                
                # Count total errors in log
                error_count = 0
                try:
                    with open(self.error_log_path, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        error_count = sum(1 for row in reader) - 1  # Subtract header row
                except Exception:
                    error_count = 1  # At least the error we just logged
                
                return json.dumps({
                    "success": True,
                    "message": f"Error logged successfully to {self.error_log_path}",
                    "logged": True,
                    "error_details": {
                        "timestamp": datetime.now().isoformat(),
                        "error_type": self.error_type,
                        "severity": self.severity,
                        "component": self.component,
                        "retry_count": self.retry_count
                    },
                    "log_statistics": {
                        "total_errors_in_log": error_count,
                        "log_file_size_bytes": file_size,
                        "log_file_path": self.error_log_path
                    }
                }, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "error": "Failed to write error to log file",
                    "logged": False
                })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error logging tool failed: {str(e)}",
                "logged": False
            })


class ErrorAnalysisTool(BaseTool):
    """
    Tool for analyzing error logs and generating error summaries.
    
    This tool reads error log files and provides analysis including
    error frequency, severity distribution, and trending patterns.
    """
    
    error_log_path: str = Field(
        description="Path to the error log CSV file to analyze"
    )
    
    include_recommendations: bool = Field(
        default=True,
        description="Whether to include error resolution recommendations"
    )
    
    time_window_hours: Optional[int] = Field(
        default=None,
        description="Only analyze errors from the last N hours (if specified)"
    )
    
    def run(self) -> str:
        """
        Analyze error log and generate summary.
        
        Returns:
            JSON string with error analysis results
        """
        try:
            # Check if error log exists
            if not os.path.exists(self.error_log_path):
                return json.dumps({
                    "success": False,
                    "error": f"Error log file not found: {self.error_log_path}",
                    "analysis": None
                })
            
            # Read and parse error log
            errors = []
            try:
                with open(self.error_log_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        errors.append(row)
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to read error log: {str(e)}",
                    "analysis": None
                })
            
            # Filter by time window if specified
            if self.time_window_hours:
                filtered_errors = self._filter_errors_by_time(errors, self.time_window_hours)
            else:
                filtered_errors = errors
            
            # Perform analysis
            analysis = self._analyze_errors(filtered_errors)
            
            # Generate recommendations if requested
            recommendations = []
            if self.include_recommendations:
                recommendations = self._generate_recommendations(analysis)
            
            return json.dumps({
                "success": True,
                "message": f"Analyzed {len(filtered_errors)} errors from {self.error_log_path}",
                "analysis": analysis,
                "recommendations": recommendations,
                "time_window_hours": self.time_window_hours,
                "analysis_timestamp": datetime.now().isoformat()
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error analysis tool failed: {str(e)}",
                "analysis": None
            })
    
    def _filter_errors_by_time(self, errors: List[Dict[str, str]], hours: int) -> List[Dict[str, str]]:
        """Filter errors to only include those from the last N hours"""
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        filtered_errors = []
        
        for error in errors:
            try:
                error_time = datetime.fromisoformat(error.get('timestamp', ''))
                if error_time >= cutoff_time:
                    filtered_errors.append(error)
            except Exception:
                # If timestamp parsing fails, include the error anyway
                filtered_errors.append(error)
        
        return filtered_errors
    
    def _analyze_errors(self, errors: List[Dict[str, str]]) -> Dict[str, Any]:
        """Analyze error patterns and generate statistics"""
        analysis = {
            "total_errors": len(errors),
            "error_type_distribution": {},
            "severity_distribution": {},
            "component_distribution": {},
            "retry_statistics": {},
            "temporal_patterns": {},
            "top_error_messages": {}
        }
        
        if not errors:
            return analysis
        
        # Error type distribution
        for error in errors:
            error_type = error.get('error_type', 'unknown')
            analysis["error_type_distribution"][error_type] = analysis["error_type_distribution"].get(error_type, 0) + 1
        
        # Severity distribution
        for error in errors:
            severity = error.get('severity', 'unknown')
            analysis["severity_distribution"][severity] = analysis["severity_distribution"].get(severity, 0) + 1
        
        # Component distribution
        for error in errors:
            component = error.get('component', 'unknown')
            if component:  # Only count non-empty components
                analysis["component_distribution"][component] = analysis["component_distribution"].get(component, 0) + 1
        
        # Retry statistics
        retry_counts = []
        for error in errors:
            try:
                retry_count = int(error.get('retry_count', 0))
                retry_counts.append(retry_count)
            except (ValueError, TypeError):
                retry_counts.append(0)
        
        if retry_counts:
            analysis["retry_statistics"] = {
                "total_retries": sum(retry_counts),
                "average_retries": sum(retry_counts) / len(retry_counts),
                "max_retries": max(retry_counts),
                "errors_with_retries": sum(1 for count in retry_counts if count > 0)
            }
        
        # Top error messages
        error_messages = {}
        for error in errors:
            message = error.get('error_message', 'unknown')
            # Truncate long messages for grouping
            message_key = message[:100] + "..." if len(message) > 100 else message
            error_messages[message_key] = error_messages.get(message_key, 0) + 1
        
        # Get top 5 most frequent error messages
        sorted_messages = sorted(error_messages.items(), key=lambda x: x[1], reverse=True)
        analysis["top_error_messages"] = dict(sorted_messages[:5])
        
        # Temporal patterns (by hour if timestamps available)
        hourly_distribution = {}
        for error in errors:
            try:
                timestamp = error.get('timestamp', '')
                if timestamp:
                    error_time = datetime.fromisoformat(timestamp)
                    hour = error_time.hour
                    hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
            except Exception:
                pass
        
        if hourly_distribution:
            analysis["temporal_patterns"]["hourly_distribution"] = hourly_distribution
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate recommendations based on error analysis"""
        recommendations = []
        
        total_errors = analysis.get("total_errors", 0)
        severity_dist = analysis.get("severity_distribution", {})
        error_type_dist = analysis.get("error_type_distribution", {})
        retry_stats = analysis.get("retry_statistics", {})
        
        # High error count recommendation
        if total_errors > 100:
            recommendations.append({
                "priority": "high",
                "category": "volume",
                "title": "High Error Volume Detected",
                "description": f"System has logged {total_errors} errors. Consider investigating root causes.",
                "action": "Review error patterns and implement preventive measures"
            })
        
        # Critical errors recommendation
        critical_errors = severity_dist.get("critical", 0)
        if critical_errors > 0:
            recommendations.append({
                "priority": "critical",
                "category": "severity",
                "title": "Critical Errors Present",
                "description": f"{critical_errors} critical errors detected. Immediate attention required.",
                "action": "Address critical errors immediately to prevent system failures"
            })
        
        # High retry recommendation
        avg_retries = retry_stats.get("average_retries", 0)
        if avg_retries > 2:
            recommendations.append({
                "priority": "medium",
                "category": "performance",
                "title": "High Retry Rate",
                "description": f"Average retry count is {avg_retries:.1f}. May indicate reliability issues.",
                "action": "Investigate and improve error handling and retry logic"
            })
        
        # Frequent error type recommendations
        if error_type_dist:
            most_common_error = max(error_type_dist, key=error_type_dist.get)
            most_common_count = error_type_dist[most_common_error]
            
            if most_common_count > total_errors * 0.3:  # More than 30% of errors
                recommendations.append({
                    "priority": "medium",
                    "category": "pattern",
                    "title": f"Frequent {most_common_error} Errors",
                    "description": f"{most_common_error} represents {most_common_count} errors ({most_common_count/total_errors:.1%})",
                    "action": f"Focus on resolving {most_common_error} issues to reduce overall error count"
                })
        
        # No errors recommendation
        if total_errors == 0:
            recommendations.append({
                "priority": "low",
                "category": "status",
                "title": "No Errors Detected",
                "description": "System is running smoothly with no logged errors.",
                "action": "Continue monitoring and maintain current practices"
            })
        
        return recommendations


class ErrorResolutionTool(BaseTool):
    """
    Tool for marking errors as resolved and updating error log status.
    
    This tool allows updating the resolution status of logged errors
    and adding resolution notes for tracking purposes.
    """
    
    error_log_path: str = Field(
        description="Path to the error log CSV file"
    )
    
    resolution_criteria: Dict[str, Any] = Field(
        description="Criteria for identifying errors to mark as resolved (e.g., error_type, component, etc.)"
    )
    
    resolution_status: str = Field(
        default="resolved",
        description="New resolution status ('resolved', 'investigating', 'deferred', etc.)"
    )
    
    resolution_notes: str = Field(
        default="",
        description="Notes about the resolution or current status"
    )
    
    def run(self) -> str:
        """
        Update error resolution status in log file.
        
        Returns:
            JSON string with resolution update results
        """
        try:
            # Check if error log exists
            if not os.path.exists(self.error_log_path):
                return json.dumps({
                    "success": False,
                    "error": f"Error log file not found: {self.error_log_path}",
                    "updated_count": 0
                })
            
            # Read current error log
            rows = []
            try:
                with open(self.error_log_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    fieldnames = reader.fieldnames
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to read error log: {str(e)}",
                    "updated_count": 0
                })
            
            # Update matching rows
            updated_count = 0
            for row in rows:
                if self._matches_criteria(row, self.resolution_criteria):
                    row['resolution_status'] = self.resolution_status
                    if self.resolution_notes:
                        # Add resolution notes to context
                        existing_context = row.get('context', '')
                        row['context'] = f"{existing_context} | Resolution: {self.resolution_notes}".strip(' |')
                    updated_count += 1
            
            # Write updated log back to file
            try:
                with open(self.error_log_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to write updated error log: {str(e)}",
                    "updated_count": 0
                })
            
            return json.dumps({
                "success": True,
                "message": f"Updated resolution status for {updated_count} errors",
                "updated_count": updated_count,
                "resolution_status": self.resolution_status,
                "total_errors_in_log": len(rows),
                "update_timestamp": datetime.now().isoformat()
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error resolution tool failed: {str(e)}",
                "updated_count": 0
            })
    
    def _matches_criteria(self, row: Dict[str, str], criteria: Dict[str, Any]) -> bool:
        """Check if a row matches the resolution criteria"""
        for key, value in criteria.items():
            if key not in row:
                return False
            
            row_value = row[key]
            
            # Handle different comparison types
            if isinstance(value, str):
                if row_value != value:
                    return False
            elif isinstance(value, list):
                if row_value not in value:
                    return False
            elif isinstance(value, dict):
                # Handle range comparisons, regex, etc.
                if 'equals' in value and row_value != value['equals']:
                    return False
                if 'contains' in value and value['contains'] not in row_value:
                    return False
                if 'starts_with' in value and not row_value.startswith(value['starts_with']):
                    return False
        
        return True
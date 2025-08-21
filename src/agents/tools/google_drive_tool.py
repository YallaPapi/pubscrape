"""
Google Drive Integration Tool

Agency Swarm tool for uploading exported files to Google Drive
and generating shareable links for easy distribution.
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


class GoogleDriveUploadTool(BaseTool):
    """
    Tool for uploading files to Google Drive and creating shareable links.
    
    This tool handles the upload of exported contact data files to Google Drive
    for easy sharing and distribution to stakeholders.
    """
    
    file_paths: List[str] = Field(
        description="List of file paths to upload to Google Drive"
    )
    
    folder_name: str = Field(
        default="Podcast Contact Discovery Results",
        description="Name of the Google Drive folder to create/use"
    )
    
    create_shareable_links: bool = Field(
        default=True,
        description="Whether to create shareable links for uploaded files"
    )
    
    share_permissions: str = Field(
        default="view",
        description="Permission level for shared links: 'view', 'comment', 'edit'"
    )
    
    credentials_path: Optional[str] = Field(
        default=None,
        description="Path to Google Drive API credentials JSON file"
    )
    
    def run(self) -> str:
        """
        Upload files to Google Drive and generate shareable links.
        
        Returns:
            JSON string with upload results and share links
        """
        try:
            # Check if Google Drive API is available
            try:
                from googleapiclient.discovery import build
                from google.oauth2.service_account import Credentials
                from googleapiclient.http import MediaFileUpload
            except ImportError:
                return json.dumps({
                    "success": False,
                    "error": "Google Drive API libraries not available. Install google-api-python-client and google-auth.",
                    "upload_results": None
                })
            
            # Validate input files
            missing_files = [path for path in self.file_paths if not os.path.exists(path)]
            if missing_files:
                return json.dumps({
                    "success": False,
                    "error": f"Files not found: {', '.join(missing_files)}",
                    "upload_results": None
                })
            
            # Initialize Google Drive service
            try:
                service = self._initialize_drive_service()
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to initialize Google Drive service: {str(e)}",
                    "upload_results": None,
                    "suggestion": "Verify credentials file and API access"
                })
            
            # Create or find the target folder
            try:
                folder_id = self._create_or_find_folder(service, self.folder_name)
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to create/find folder: {str(e)}",
                    "upload_results": None
                })
            
            # Upload files
            upload_results = {
                "folder_id": folder_id,
                "folder_name": self.folder_name,
                "uploaded_files": {},
                "failed_uploads": {},
                "total_files": len(self.file_paths),
                "successful_uploads": 0,
                "failed_uploads_count": 0,
                "upload_timestamp": datetime.now().isoformat()
            }
            
            for file_path in self.file_paths:
                try:
                    result = self._upload_single_file(service, file_path, folder_id)
                    upload_results["uploaded_files"][file_path] = result
                    upload_results["successful_uploads"] += 1
                except Exception as e:
                    upload_results["failed_uploads"][file_path] = str(e)
                    upload_results["failed_uploads_count"] += 1
            
            # Generate overall success status
            overall_success = upload_results["failed_uploads_count"] == 0
            
            return json.dumps({
                "success": overall_success,
                "message": f"Uploaded {upload_results['successful_uploads']}/{upload_results['total_files']} files to Google Drive",
                "upload_results": upload_results,
                "folder_link": f"https://drive.google.com/drive/folders/{folder_id}"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Google Drive upload tool failed: {str(e)}",
                "upload_results": None
            })
    
    def _initialize_drive_service(self):
        """Initialize Google Drive API service"""
        from googleapiclient.discovery import build
        from google.oauth2.service_account import Credentials
        
        # Determine credentials path
        if self.credentials_path and os.path.exists(self.credentials_path):
            creds_path = self.credentials_path
        else:
            # Look for common credential file locations
            possible_paths = [
                os.path.join(os.getcwd(), "google_drive_credentials.json"),
                os.path.join(os.getcwd(), "credentials.json"),
                os.path.expanduser("~/.config/google_drive_credentials.json")
            ]
            
            creds_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    creds_path = path
                    break
            
            if not creds_path:
                raise Exception(
                    "Google Drive credentials not found. Please provide credentials_path or place "
                    "credentials file at one of: " + ", ".join(possible_paths)
                )
        
        # Initialize credentials and service
        scopes = ['https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
        service = build('drive', 'v3', credentials=credentials)
        
        return service
    
    def _create_or_find_folder(self, service, folder_name: str) -> str:
        """Create or find a folder in Google Drive"""
        # Search for existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query).execute()
        
        items = results.get('files', [])
        
        if items:
            # Folder exists, return its ID
            return items[0]['id']
        else:
            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            return folder.get('id')
    
    def _upload_single_file(self, service, file_path: str, folder_id: str) -> Dict[str, Any]:
        """Upload a single file to Google Drive"""
        from googleapiclient.http import MediaFileUpload
        
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # Determine MIME type based on file extension
        file_extension = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.pdf': 'application/pdf'
        }
        mime_type = mime_types.get(file_extension, 'application/octet-stream')
        
        # File metadata
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        # Upload file
        media = MediaFileUpload(file_path, mimetype=mime_type)
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,size,webViewLink,webContentLink'
        ).execute()
        
        result = {
            "file_id": uploaded_file.get('id'),
            "file_name": uploaded_file.get('name'),
            "file_size_bytes": file_size,
            "upload_size_bytes": int(uploaded_file.get('size', 0)),
            "web_view_link": uploaded_file.get('webViewLink'),
            "download_link": uploaded_file.get('webContentLink')
        }
        
        # Create shareable link if requested
        if self.create_shareable_links:
            try:
                permission = {
                    'type': 'anyone',
                    'role': 'reader' if self.share_permissions == 'view' else 'writer'
                }
                
                service.permissions().create(
                    fileId=uploaded_file.get('id'),
                    body=permission
                ).execute()
                
                result["shareable"] = True
                result["share_permissions"] = self.share_permissions
                
            except Exception as e:
                result["shareable"] = False
                result["share_error"] = str(e)
        
        return result


class GoogleDriveOrganizationTool(BaseTool):
    """
    Tool for organizing exported files in Google Drive with proper folder structure.
    
    This tool creates a well-organized folder structure for podcast contact
    discovery results with appropriate naming and metadata.
    """
    
    campaign_info: Dict[str, Any] = Field(
        description="Campaign information for organizing files"
    )
    
    create_dated_folders: bool = Field(
        default=True,
        description="Whether to create date-based subfolders"
    )
    
    include_metadata_file: bool = Field(
        default=True,
        description="Whether to create a metadata file with campaign information"
    )
    
    def run(self) -> str:
        """
        Create organized folder structure in Google Drive.
        
        Returns:
            JSON string with folder structure results
        """
        try:
            # This is a simplified implementation
            # In practice, this would use the Google Drive API to create
            # a proper folder structure based on campaign information
            
            topic = self.campaign_info.get('topic', 'unknown_topic')
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            
            folder_structure = {
                "main_folder": f"Podcast Contact Discovery - {topic}",
                "subfolders": []
            }
            
            if self.create_dated_folders:
                date_folder = f"Export_{timestamp}"
                folder_structure["subfolders"].append({
                    "name": date_folder,
                    "type": "export_date",
                    "files": ["CSV exports", "JSON reports", "Error logs"]
                })
            
            if self.include_metadata_file:
                metadata = {
                    "campaign_info": self.campaign_info,
                    "export_timestamp": timestamp,
                    "folder_structure": folder_structure
                }
                
                folder_structure["metadata_file"] = {
                    "name": "campaign_metadata.json",
                    "content": metadata
                }
            
            return json.dumps({
                "success": True,
                "message": "Folder structure planned successfully",
                "folder_structure": folder_structure,
                "note": "This is a planning tool. Actual folder creation requires Google Drive API integration."
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Folder organization tool failed: {str(e)}",
                "folder_structure": None
            })


class ShareLinkManagerTool(BaseTool):
    """
    Tool for managing shareable links and access permissions for exported files.
    
    This tool handles the creation and management of shareable links with
    appropriate permissions for different stakeholders.
    """
    
    file_links: List[Dict[str, str]] = Field(
        description="List of file links with their current sharing status"
    )
    
    stakeholder_permissions: Dict[str, str] = Field(
        description="Mapping of stakeholder types to permission levels"
    )
    
    generate_summary_email: bool = Field(
        default=True,
        description="Whether to generate a summary email template with all links"
    )
    
    def run(self) -> str:
        """
        Manage shareable links and permissions.
        
        Returns:
            JSON string with link management results
        """
        try:
            link_summary = {
                "total_files": len(self.file_links),
                "shareable_files": 0,
                "restricted_files": 0,
                "file_access": {},
                "stakeholder_links": {},
                "summary_timestamp": datetime.now().isoformat()
            }
            
            # Process each file link
            for file_info in self.file_links:
                file_name = file_info.get('name', 'unknown')
                is_shareable = file_info.get('shareable', False)
                
                if is_shareable:
                    link_summary["shareable_files"] += 1
                else:
                    link_summary["restricted_files"] += 1
                
                link_summary["file_access"][file_name] = {
                    "shareable": is_shareable,
                    "view_link": file_info.get('web_view_link', ''),
                    "download_link": file_info.get('download_link', ''),
                    "permissions": file_info.get('share_permissions', 'private')
                }
            
            # Generate stakeholder-specific link collections
            for stakeholder, permission in self.stakeholder_permissions.items():
                accessible_files = []
                
                for file_name, access_info in link_summary["file_access"].items():
                    if access_info["shareable"]:
                        accessible_files.append({
                            "file_name": file_name,
                            "link": access_info["view_link"],
                            "permission": permission
                        })
                
                link_summary["stakeholder_links"][stakeholder] = accessible_files
            
            # Generate summary email template if requested
            email_template = None
            if self.generate_summary_email:
                email_template = self._generate_email_template(link_summary)
            
            return json.dumps({
                "success": True,
                "message": f"Managed links for {len(self.file_links)} files",
                "link_summary": link_summary,
                "email_template": email_template
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Share link manager tool failed: {str(e)}",
                "link_summary": None
            })
    
    def _generate_email_template(self, link_summary: Dict[str, Any]) -> str:
        """Generate email template with file links"""
        template = f"""Subject: Podcast Contact Discovery Results - {datetime.now().strftime('%Y-%m-%d')}

Dear Team,

The podcast contact discovery analysis has been completed. Please find the results below:

SUMMARY:
- Total Files: {link_summary['total_files']}
- Shareable Files: {link_summary['shareable_files']}
- Generated: {link_summary['summary_timestamp']}

AVAILABLE FILES:
"""
        
        for file_name, access_info in link_summary["file_access"].items():
            if access_info["shareable"]:
                template += f"""
📄 {file_name}
   View: {access_info['view_link']}
   Download: {access_info['download_link']}
"""
        
        template += """

NEXT STEPS:
1. Review the main CSV file for contact information
2. Check the campaign summary for analytics insights
3. Review any error logs for potential data quality issues

For questions or additional analysis, please contact the data team.

Best regards,
Podcast Contact Discovery System
"""
        
        return template
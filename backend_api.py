#!/usr/bin/env python3
"""
Simple FastAPI backend for VRSEN Lead Generation Frontend
This is a demonstration API that interfaces with the existing lead generation system
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="VRSEN Lead Generation API",
    description="API for managing lead generation campaigns",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class CampaignSettings(BaseModel):
    search_engine: str = "bing"
    language: str = "en"
    country_code: str = "US"
    max_pages_per_query: int = 3
    max_leads_per_query: int = 25
    request_delay_seconds: float = 2.5
    timeout_seconds: int = 20
    headless_mode: bool = True
    use_rotating_user_agents: bool = True
    use_residential_proxies: bool = False
    enable_email_validation: bool = True
    enable_dns_checking: bool = False
    min_email_confidence: float = 0.6
    min_business_score: float = 0.5
    max_concurrent_extractions: int = 3
    include_report: bool = True
    exclude_keywords: List[str] = ["yelp", "reviews", "directory", "wikipedia"]
    output_directory: str = "campaign_output"
    csv_filename: str = ""

class CampaignProgress(BaseModel):
    current_step: str = "pending"
    queries_processed: int = 0
    total_queries: int = 0
    leads_found: int = 0
    pages_scraped: int = 0
    total_pages: int = 0
    emails_extracted: int = 0
    emails_validated: int = 0

class CampaignCreate(BaseModel):
    name: str
    description: str = ""
    business_types: List[str]
    location: str
    search_queries: List[str]
    max_leads: int = 100
    settings: CampaignSettings

class Campaign(BaseModel):
    id: str
    name: str
    description: str
    business_types: List[str]
    location: str
    search_queries: List[str]
    max_leads: int
    status: str = "draft"
    progress: CampaignProgress
    settings: CampaignSettings
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

class Lead(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    specialty: Optional[str] = None
    source: str
    confidence: float
    status: str = "pending"
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class CampaignMetrics(BaseModel):
    total_campaigns: int
    active_campaigns: int
    total_leads: int
    qualified_leads: int
    success_rate: float
    average_leads_per_campaign: float
    recent_activity: List[Dict[str, Any]]

# In-memory storage (replace with database in production)
campaigns_db: Dict[str, Campaign] = {}
leads_db: Dict[str, Lead] = {}
websocket_connections: List[WebSocket] = []

# Initialize sample data
def init_sample_data():
    """Initialize some sample campaigns and leads for demonstration"""
    
    # Sample campaign 1
    campaign1_id = str(uuid.uuid4())
    campaigns_db[campaign1_id] = Campaign(
        id=campaign1_id,
        name="Atlanta Optometrists Campaign",
        description="Lead generation for optometrists in Atlanta area",
        business_types=["optometry", "eye care", "vision"],
        location="Atlanta, GA",
        search_queries=["optometrist Atlanta", "eye doctor Atlanta", "vision care Atlanta"],
        max_leads=100,
        status="completed",
        progress=CampaignProgress(
            current_step="completed",
            queries_processed=3,
            total_queries=3,
            leads_found=47,
            pages_scraped=15,
            total_pages=15,
            emails_extracted=47,
            emails_validated=43
        ),
        settings=CampaignSettings(),
        created_at=datetime.now() - timedelta(days=2),
        updated_at=datetime.now() - timedelta(hours=1),
        completed_at=datetime.now() - timedelta(hours=1)
    )
    
    # Sample campaign 2
    campaign2_id = str(uuid.uuid4())
    campaigns_db[campaign2_id] = Campaign(
        id=campaign2_id,
        name="Denver Dentists Campaign",
        description="Dental practices in Denver metro area",
        business_types=["dentistry", "dental care", "orthodontics"],
        location="Denver, CO",
        search_queries=["dentist Denver", "dental practice Denver", "orthodontist Denver"],
        max_leads=150,
        status="running",
        progress=CampaignProgress(
            current_step="extracting",
            queries_processed=2,
            total_queries=3,
            leads_found=23,
            pages_scraped=8,
            total_pages=12,
            emails_extracted=23,
            emails_validated=18
        ),
        settings=CampaignSettings(),
        created_at=datetime.now() - timedelta(hours=6),
        updated_at=datetime.now() - timedelta(minutes=5)
    )
    
    # Sample leads
    for i in range(47):
        lead_id = str(uuid.uuid4())
        leads_db[lead_id] = Lead(
            id=lead_id,
            name=f"Dr. John Smith {i+1}",
            email=f"doctor{i+1}@eyecare{i+1}.com",
            phone=f"404-555-{1000+i:04d}",
            company=f"Atlanta Eye Care {i+1}",
            website=f"https://atlantaeyecare{i+1}.com",
            address=f"{i+1} Peachtree St, Atlanta, GA 30309",
            specialty="Optometry",
            source="bing_search",
            confidence=0.7 + (i % 3) * 0.1,
            status=["pending", "contacted", "qualified"][i % 3],
            created_at=datetime.now() - timedelta(hours=i),
            updated_at=datetime.now() - timedelta(hours=i)
        )

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Background task to simulate campaign progress
async def simulate_campaign_progress(campaign_id: str):
    """Simulate campaign progress for demonstration"""
    if campaign_id not in campaigns_db:
        return
    
    campaign = campaigns_db[campaign_id]
    if campaign.status != "running":
        return
    
    steps = [
        ("building_queries", 2),
        ("searching", 10),
        ("parsing", 8),
        ("classifying", 5),
        ("extracting", 15),
        ("validating", 10)
    ]
    
    for step_name, duration in steps:
        if campaign.status != "running":
            break
            
        campaign.progress.current_step = step_name
        campaign.updated_at = datetime.now()
        
        # Simulate progress within each step
        for i in range(duration):
            if campaign.status != "running":
                break
                
            # Update progress based on step
            if step_name == "searching":
                campaign.progress.queries_processed = min(i + 1, campaign.progress.total_queries)
            elif step_name == "extracting":
                campaign.progress.leads_found = min(i * 3, campaign.max_leads)
                campaign.progress.emails_extracted = campaign.progress.leads_found
            elif step_name == "validating":
                campaign.progress.emails_validated = min(
                    campaign.progress.emails_extracted - 5, 
                    campaign.progress.emails_extracted
                )
            
            # Broadcast progress update
            await manager.broadcast(json.dumps({
                "type": "campaign_progress",
                "campaign_id": campaign_id,
                "progress": campaign.progress.dict(),
                "status": campaign.status
            }))
            
            await asyncio.sleep(1)  # 1 second per progress update
    
    # Complete the campaign
    if campaign.status == "running":
        campaign.status = "completed"
        campaign.completed_at = datetime.now()
        campaign.progress.current_step = "completed"
        
        await manager.broadcast(json.dumps({
            "type": "campaign_completed",
            "campaign_id": campaign_id,
            "status": "completed"
        }))

# API Routes

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "VRSEN Lead Generation API", "status": "running", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    """API health check"""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/api/metrics")
async def get_metrics():
    """Get campaign metrics"""
    total_campaigns = len(campaigns_db)
    active_campaigns = len([c for c in campaigns_db.values() if c.status in ["running", "paused"]])
    total_leads = len(leads_db)
    qualified_leads = len([l for l in leads_db.values() if l.status == "qualified"])
    
    success_rate = qualified_leads / total_leads if total_leads > 0 else 0
    avg_leads = total_leads / total_campaigns if total_campaigns > 0 else 0
    
    recent_activity = [
        {
            "type": "campaign_completed",
            "message": "Atlanta Optometrists Campaign completed with 47 leads",
            "timestamp": datetime.now() - timedelta(hours=1)
        },
        {
            "type": "campaign_started", 
            "message": "Denver Dentists Campaign started",
            "timestamp": datetime.now() - timedelta(hours=6)
        }
    ]
    
    return {
        "success": True,
        "data": CampaignMetrics(
            total_campaigns=total_campaigns,
            active_campaigns=active_campaigns,
            total_leads=total_leads,
            qualified_leads=qualified_leads,
            success_rate=success_rate,
            average_leads_per_campaign=avg_leads,
            recent_activity=recent_activity
        )
    }

@app.get("/api/campaigns")
async def get_campaigns():
    """Get all campaigns"""
    campaigns = list(campaigns_db.values())
    campaigns.sort(key=lambda x: x.updated_at, reverse=True)
    
    return {
        "data": campaigns,
        "total": len(campaigns),
        "page": 1,
        "limit": 50,
        "totalPages": 1
    }

@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get specific campaign"""
    if campaign_id not in campaigns_db:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {
        "success": True,
        "data": campaigns_db[campaign_id]
    }

@app.post("/api/campaigns")
async def create_campaign(campaign_data: CampaignCreate, background_tasks: BackgroundTasks):
    """Create new campaign"""
    campaign_id = str(uuid.uuid4())
    
    campaign = Campaign(
        id=campaign_id,
        name=campaign_data.name,
        description=campaign_data.description,
        business_types=campaign_data.business_types,
        location=campaign_data.location,
        search_queries=campaign_data.search_queries,
        max_leads=campaign_data.max_leads,
        status="draft",
        progress=CampaignProgress(total_queries=len(campaign_data.search_queries)),
        settings=campaign_data.settings,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    campaigns_db[campaign_id] = campaign
    
    return {
        "success": True,
        "data": campaign
    }

@app.post("/api/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: str, background_tasks: BackgroundTasks):
    """Start campaign"""
    if campaign_id not in campaigns_db:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign = campaigns_db[campaign_id]
    campaign.status = "running"
    campaign.updated_at = datetime.now()
    
    # Start background task to simulate progress
    background_tasks.add_task(simulate_campaign_progress, campaign_id)
    
    return {
        "success": True,
        "data": campaign
    }

@app.post("/api/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    """Pause campaign"""
    if campaign_id not in campaigns_db:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign = campaigns_db[campaign_id]
    campaign.status = "paused"
    campaign.updated_at = datetime.now()
    
    return {
        "success": True,
        "data": campaign
    }

@app.post("/api/campaigns/{campaign_id}/stop")
async def stop_campaign(campaign_id: str):
    """Stop campaign"""
    if campaign_id not in campaigns_db:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign = campaigns_db[campaign_id]
    campaign.status = "completed"
    campaign.updated_at = datetime.now()
    campaign.completed_at = datetime.now()
    
    return {
        "success": True,
        "data": campaign
    }

@app.get("/api/leads")
async def get_leads():
    """Get all leads"""
    leads = list(leads_db.values())
    leads.sort(key=lambda x: x.updated_at, reverse=True)
    
    return {
        "data": leads,
        "total": len(leads),
        "page": 1,
        "limit": 50,
        "totalPages": 1
    }

@app.post("/api/campaigns/{campaign_id}/export")
async def export_leads(campaign_id: str):
    """Export campaign leads"""
    if campaign_id not in campaigns_db:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # In production, generate actual CSV file
    download_url = f"/api/download/campaign_{campaign_id}_leads.csv"
    
    return {
        "success": True,
        "data": {
            "downloadUrl": download_url
        }
    }

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download exported file"""
    # In production, return actual file
    # For demo, return a sample CSV
    return {"message": f"Download {filename} - Feature coming soon"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or handle specific commands
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    # Initialize sample data
    init_sample_data()
    
    # Run the server
    uvicorn.run(
        "backend_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
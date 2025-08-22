#!/usr/bin/env python3
"""
Database Models for VRSEN Lead Generation System
Defines SQLAlchemy models for campaigns, leads, and related entities
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.sqlite import BLOB
from pydantic import BaseModel
import json

Base = declarative_base()

def generate_uuid():
    """Generate a new UUID string"""
    return str(uuid.uuid4())

def utc_now():
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)

class CampaignModel(Base):
    """Campaign database model"""
    __tablename__ = "campaigns"
    
    # Primary fields
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, default="")
    
    # Campaign configuration
    business_types = Column(JSON, default=list)  # List of business types
    location = Column(String(255), default="")
    search_queries = Column(JSON, default=list)  # List of search queries
    max_leads = Column(Integer, default=100)
    
    # Status and progress
    status = Column(String(50), default="draft", index=True)  # draft, running, paused, completed, error
    current_step = Column(String(100), default="pending")
    progress_data = Column(JSON, default=dict)  # Flexible progress tracking
    
    # Campaign settings
    settings = Column(JSON, default=dict)  # CampaignSettings as JSON
    
    # Results
    total_leads_found = Column(Integer, default=0)
    qualified_leads_count = Column(Integer, default=0)
    csv_file_path = Column(String(500), nullable=True)
    report_data = Column(JSON, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    leads = relationship("LeadModel", back_populates="campaign", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'businessTypes': self.business_types or [],
            'location': self.location,
            'searchQueries': self.search_queries or [],
            'maxLeads': self.max_leads,
            'status': self.status,
            'progress': {
                'currentStep': self.current_step,
                'queriesProcessed': self.progress_data.get('queries_processed', 0),
                'totalQueries': len(self.search_queries or []),
                'leadsFound': self.total_leads_found,
                'pagesScraped': self.progress_data.get('pages_scraped', 0),
                'totalPages': self.progress_data.get('total_pages', 0),
                'emailsExtracted': self.progress_data.get('emails_extracted', 0),
                'emailsValidated': self.progress_data.get('emails_validated', 0)
            },
            'settings': self.settings or {},
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
            'completedAt': self.completed_at
        }

class LeadModel(Base):
    """Lead database model"""
    __tablename__ = "leads"
    
    # Primary fields
    id = Column(String, primary_key=True, default=generate_uuid)
    campaign_id = Column(String, ForeignKey('campaigns.id'), nullable=False, index=True)
    
    # Contact information
    name = Column(String(255), default="", index=True)
    email = Column(String(255), default="", index=True)
    phone = Column(String(50), default="")
    company = Column(String(255), default="", index=True)
    website = Column(String(500), default="")
    address = Column(Text, default="")
    specialty = Column(String(255), default="")
    
    # Extended lead data (from comprehensive system)
    business_name = Column(String(255), default="", index=True)
    industry = Column(String(255), default="")
    contact_name = Column(String(255), default="")
    contact_title = Column(String(255), default="")
    
    # Additional contact methods
    secondary_emails = Column(JSON, default=list)
    additional_phones = Column(JSON, default=list)
    
    # Location details
    city = Column(String(255), default="")
    state = Column(String(100), default="")
    country = Column(String(100), default="")
    
    # Social presence
    linkedin_url = Column(String(500), default="")
    facebook_url = Column(String(500), default="")
    twitter_url = Column(String(500), default="")
    other_social = Column(JSON, default=list)
    
    # Quality metrics
    source = Column(String(255), default="", index=True)
    confidence = Column(Float, default=0.0)
    lead_score = Column(Float, default=0.0)
    email_confidence = Column(Float, default=0.0)
    data_completeness = Column(Float, default=0.0)
    is_actionable = Column(Boolean, default=False, index=True)
    
    # Lead management
    status = Column(String(50), default="pending", index=True)  # pending, contacted, qualified, disqualified
    notes = Column(Text, default="")
    
    # Source tracking
    source_url = Column(String(1000), default="")
    source_query = Column(String(500), default="")
    extraction_date = Column(DateTime(timezone=True), default=utc_now)
    last_verified = Column(DateTime(timezone=True), default=utc_now)
    
    # Technical metadata
    extraction_time_ms = Column(Float, default=0.0)
    validation_status = Column(String(100), default="")
    validation_details = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    
    # Relationships
    campaign = relationship("CampaignModel", back_populates="leads")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name or self.contact_name,
            'email': self.email,
            'phone': self.phone,
            'company': self.company or self.business_name,
            'website': self.website,
            'address': self.address,
            'specialty': self.specialty or self.industry,
            'source': self.source,
            'confidence': self.confidence or self.email_confidence,
            'status': self.status,
            'notes': self.notes,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at
        }
    
    def to_comprehensive_dict(self) -> Dict[str, Any]:
        """Convert to comprehensive dictionary with all fields"""
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'company': self.company,
            'website': self.website,
            'address': self.address,
            'specialty': self.specialty,
            'business_name': self.business_name,
            'industry': self.industry,
            'contact_name': self.contact_name,
            'contact_title': self.contact_title,
            'secondary_emails': self.secondary_emails or [],
            'additional_phones': self.additional_phones or [],
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'linkedin_url': self.linkedin_url,
            'facebook_url': self.facebook_url,
            'twitter_url': self.twitter_url,
            'other_social': self.other_social or [],
            'source': self.source,
            'confidence': self.confidence,
            'lead_score': self.lead_score,
            'email_confidence': self.email_confidence,
            'data_completeness': self.data_completeness,
            'is_actionable': self.is_actionable,
            'status': self.status,
            'notes': self.notes,
            'source_url': self.source_url,
            'source_query': self.source_query,
            'extraction_date': self.extraction_date,
            'last_verified': self.last_verified,
            'extraction_time_ms': self.extraction_time_ms,
            'validation_status': self.validation_status,
            'validation_details': self.validation_details,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class CampaignLogModel(Base):
    """Campaign execution log model"""
    __tablename__ = "campaign_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    campaign_id = Column(String, ForeignKey('campaigns.id'), nullable=False, index=True)
    
    level = Column(String(20), default="info", index=True)  # debug, info, warning, error
    step = Column(String(100), default="", index=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'level': self.level,
            'step': self.step,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp
        }

class SystemSettingsModel(Base):
    """System-wide settings model"""
    __tablename__ = "system_settings"
    
    key = Column(String(255), primary_key=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, default="")
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

# Database connection and session management
class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url: str = "sqlite:///./vrsen_leads.db"):
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        """Get database session"""
        session = self.SessionLocal()
        try:
            return session
        except Exception:
            session.close()
            raise
    
    def close_session(self, session):
        """Close database session"""
        session.close()

# Initialize default database manager
db_manager = DatabaseManager()
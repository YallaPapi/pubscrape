"""
Data Normalizer Module
Normalizes channel data, replaces nulls with "NA", and ensures schema compliance.
"""

import logging
from typing import Dict, List, Any, Union

from .config import config

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Normalizes and sanitizes channel data for consistent processing."""
    
    def __init__(self):
        """Initialize data normalizer."""
        self.na_value = "NA"
        self.schema = config.CSV_SCHEMA
    
    def normalize_channel(self, channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a single channel's data.
        
        Args:
            channel_data: Raw channel data from fetcher
            
        Returns:
            Normalized channel data matching schema
        """
        normalized = {}
        
        # Map raw data to schema fields
        field_mapping = {
            "ChannelName": channel_data.get("channel_name", self.na_value),
            "ChannelID": channel_data.get("channel_id", self.na_value),
            "Email": channel_data.get("business_email", "") or channel_data.get("youtube_about_url", self.na_value),
            "ChannelDescription": self._sanitize_text(channel_data.get("channel_description", "")),
            "Website": channel_data.get("website", self.na_value),
            "SocialLinks": channel_data.get("social_links", self.na_value),
            "SubscriberCount": self._normalize_number(channel_data.get("subscriber_count", "0")),
            "GuestScore": self.na_value,  # Will be filled by scorer
            "ScoreReason": self.na_value,  # Will be filled by scorer
            "DraftEmail": self.na_value   # Will be filled by email drafter
        }
        
        # Ensure all schema fields are present
        for field in self.schema:
            if field in field_mapping:
                value = field_mapping[field]
                normalized[field] = value if value else self.na_value
            else:
                normalized[field] = self.na_value
        
        # Add metadata fields (not in CSV but useful for processing)
        normalized["_metadata"] = {
            "view_count": channel_data.get("view_count", "0"),
            "video_count": channel_data.get("video_count", "0"),
            "country": channel_data.get("country", self.na_value),
            "custom_url": channel_data.get("custom_url", self.na_value),
            "published_at": channel_data.get("published_at", self.na_value),
            "thumbnail_url": channel_data.get("thumbnail_url", self.na_value),
            "keywords": channel_data.get("keywords", self.na_value)
        }
        
        return normalized
    
    def normalize_batch(self, channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize a batch of channels.
        
        Args:
            channels: List of raw channel data
            
        Returns:
            List of normalized channel data
        """
        logger.info(f"Normalizing {len(channels)} channels")
        normalized_channels = []
        
        for channel in channels:
            try:
                normalized = self.normalize_channel(channel)
                normalized_channels.append(normalized)
            except Exception as e:
                logger.error(f"Error normalizing channel {channel.get('channel_id', 'unknown')}: {e}")
                # Add a placeholder with error info
                error_channel = {field: self.na_value for field in self.schema}
                error_channel["ChannelName"] = f"ERROR: {channel.get('channel_name', 'Unknown')}"
                error_channel["ChannelID"] = channel.get("channel_id", "ERROR")
                normalized_channels.append(error_channel)
        
        logger.info(f"Successfully normalized {len(normalized_channels)} channels")
        return normalized_channels
    
    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize text fields for CSV compatibility.
        
        Args:
            text: Raw text to sanitize
            
        Returns:
            Sanitized text
        """
        if not text:
            return self.na_value
        
        # Remove or replace problematic characters
        text = str(text)
        
        # Replace newlines with spaces
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        # Replace multiple spaces with single space
        text = ' '.join(text.split())
        
        # Escape quotes for CSV
        text = text.replace('"', '""')
        
        # Limit length to prevent issues
        max_length = 5000
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text if text else self.na_value
    
    def _normalize_number(self, value: Union[str, int, None]) -> str:
        """
        Normalize numeric values.
        
        Args:
            value: Raw numeric value
            
        Returns:
            Normalized number as string
        """
        if value is None or value == "":
            return "0"
        
        try:
            # Convert to int and format with commas
            num = int(str(value))
            return f"{num:,}"
        except (ValueError, TypeError):
            logger.warning(f"Could not normalize number: {value}")
            return "0"
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate that data contains all required schema fields.
        
        Args:
            data: Channel data to validate
            
        Returns:
            True if valid, False otherwise
        """
        for field in self.schema:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return False
        
        return True
    
    def prepare_for_csv(self, channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Final preparation of data for CSV export.
        
        Args:
            channels: List of processed channel data
            
        Returns:
            List of data ready for CSV export
        """
        csv_ready = []
        
        for channel in channels:
            # Remove metadata fields, keep only CSV schema fields
            csv_row = {field: channel.get(field, self.na_value) for field in self.schema}
            
            # Ensure all values are strings for CSV
            for key, value in csv_row.items():
                if value is None:
                    csv_row[key] = self.na_value
                elif not isinstance(value, str):
                    csv_row[key] = str(value)
            
            csv_ready.append(csv_row)
        
        return csv_ready
    
    def get_statistics(self, channels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about the normalized data.
        
        Args:
            channels: List of normalized channels
            
        Returns:
            Statistics dictionary
        """
        total = len(channels)
        has_website = sum(1 for c in channels if c.get("Website", self.na_value) != self.na_value)
        has_social = sum(1 for c in channels if c.get("SocialLinks", self.na_value) != self.na_value)
        
        # Calculate average subscribers
        total_subs = 0
        valid_subs = 0
        for channel in channels:
            try:
                subs = int(channel.get("SubscriberCount", "0").replace(",", ""))
                if subs > 0:
                    total_subs += subs
                    valid_subs += 1
            except:
                pass
        
        avg_subs = total_subs // valid_subs if valid_subs > 0 else 0
        
        return {
            "total_channels": total,
            "channels_with_website": has_website,
            "channels_with_social": has_social,
            "average_subscribers": f"{avg_subs:,}",
            "website_percentage": (has_website / total * 100) if total > 0 else 0,
            "social_percentage": (has_social / total * 100) if total > 0 else 0
        }
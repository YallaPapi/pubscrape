"""
Quota Manager Module
Manages YouTube API quota to prevent exceeding daily limits.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from .config import config

logger = logging.getLogger(__name__)


class QuotaManager:
    """Manages API quota usage and prevents quota exhaustion."""
    
    def __init__(self):
        """Initialize quota manager with persistent storage."""
        self.quota_file = os.path.join(config.OUTPUT_DIR, "quota_status.json")
        self.quota_data = self.load_quota_status()
        self.check_quota_reset()
    
    def load_quota_status(self) -> Dict[str, Any]:
        """Load quota status from persistent storage."""
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load quota status: {e}")
        
        # Initialize new quota tracking
        return {
            "used": 0,
            "date": datetime.now().date().isoformat(),
            "operations": [],
            "last_reset": datetime.now().isoformat()
        }
    
    def save_quota_status(self):
        """Save quota status to persistent storage."""
        try:
            os.makedirs(os.path.dirname(self.quota_file), exist_ok=True)
            with open(self.quota_file, 'w') as f:
                json.dump(self.quota_data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save quota status: {e}")
    
    def check_quota_reset(self):
        """Check if quota should be reset (daily at midnight PT)."""
        current_date = datetime.now().date().isoformat()
        saved_date = self.quota_data.get("date", current_date)
        
        if current_date != saved_date:
            # Reset quota for new day
            logger.info(f"Resetting quota for new day: {current_date}")
            self.quota_data = {
                "used": 0,
                "date": current_date,
                "operations": [],
                "last_reset": datetime.now().isoformat()
            }
            self.save_quota_status()
    
    def can_make_request(self, cost: int) -> bool:
        """
        Check if we have enough quota for a request.
        
        Args:
            cost: Quota units required for the request
            
        Returns:
            True if request can be made, False otherwise
        """
        self.check_quota_reset()
        remaining = config.YOUTUBE_DAILY_QUOTA - self.quota_data["used"]
        can_proceed = cost <= remaining
        
        if not can_proceed:
            logger.warning(f"Insufficient quota: need {cost}, have {remaining}")
            print(f"⚠️  Insufficient quota: need {cost} units, have {remaining} remaining")
        
        return can_proceed
    
    def record_request(self, cost: int, operation: str = ""):
        """
        Record quota usage for a request.
        
        Args:
            cost: Quota units consumed
            operation: Description of the operation
        """
        self.quota_data["used"] += cost
        self.quota_data["operations"].append({
            "timestamp": datetime.now().isoformat(),
            "cost": cost,
            "operation": operation,
            "total_used": self.quota_data["used"]
        })
        
        self.save_quota_status()
        
        remaining = config.YOUTUBE_DAILY_QUOTA - self.quota_data["used"]
        percentage_used = (self.quota_data["used"] / config.YOUTUBE_DAILY_QUOTA) * 100
        
        logger.info(f"Quota used: {self.quota_data['used']}/{config.YOUTUBE_DAILY_QUOTA} ({percentage_used:.1f}%)")
        
        # Warn if quota is running low
        if remaining < 1000 and remaining > 0:
            logger.warning(f"⚠️  Low quota warning: only {remaining} units remaining")
            print(f"⚠️  WARNING: Low quota - only {remaining} units remaining today")
        elif remaining == 0:
            logger.error("❌ Quota exhausted for today")
            print("❌ YouTube API quota exhausted. Please wait for daily reset at midnight PT.")
    
    def get_remaining_quota(self) -> int:
        """Get remaining quota for today."""
        self.check_quota_reset()
        return config.YOUTUBE_DAILY_QUOTA - self.quota_data["used"]
    
    def get_used_quota(self) -> int:
        """Get used quota for today."""
        self.check_quota_reset()
        return self.quota_data["used"]
    
    def handle_quota_exceeded(self):
        """Handle quota exceeded error."""
        self.quota_data["used"] = config.YOUTUBE_DAILY_QUOTA
        self.save_quota_status()
        
        # Calculate time until midnight PT
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        midnight = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        time_until_reset = midnight - now
        hours = time_until_reset.seconds // 3600
        minutes = (time_until_reset.seconds % 3600) // 60
        
        logger.error(f"Quota exceeded. Reset in {hours}h {minutes}m")
        print(f"❌ YouTube API quota exceeded!")
        print(f"⏰ Quota resets in {hours} hours {minutes} minutes")
        print(f"💡 Consider implementing caching or reducing API calls")
    
    def get_quota_status(self) -> Dict[str, Any]:
        """Get detailed quota status."""
        self.check_quota_reset()
        remaining = self.get_remaining_quota()
        used = self.get_used_quota()
        
        return {
            "used": used,
            "remaining": remaining,
            "total": config.YOUTUBE_DAILY_QUOTA,
            "percentage_used": (used / config.YOUTUBE_DAILY_QUOTA) * 100,
            "date": self.quota_data["date"],
            "operations_count": len(self.quota_data["operations"]),
            "can_search": remaining >= config.QUOTA_PER_SEARCH,
            "can_fetch_channel": remaining >= config.QUOTA_PER_CHANNEL
        }
    
    def estimate_operations_available(self) -> Dict[str, int]:
        """Estimate how many operations can still be performed."""
        remaining = self.get_remaining_quota()
        
        return {
            "searches": remaining // config.QUOTA_PER_SEARCH,
            "channel_fetches": remaining // config.QUOTA_PER_CHANNEL,
            "combined": remaining // (config.QUOTA_PER_SEARCH + 10 * config.QUOTA_PER_CHANNEL)
        }
"""
AI Email Drafter Module
Generates personalized outreach emails for potential podcast guests.
"""

import logging
import json
from typing import Dict, List, Any
from openai import OpenAI

from .config import config
from .error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class EmailDrafter:
    """Generates personalized outreach emails using AI."""
    
    def __init__(self, podcast_name: str = "", podcast_topic: str = "", host_name: str = ""):
        """
        Initialize email drafter.
        
        Args:
            podcast_name: Name of the podcast
            podcast_topic: Topic/niche of the podcast
            host_name: Name of the podcast host
        """
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.podcast_name = podcast_name or "Our Podcast"
        self.podcast_topic = podcast_topic or "interesting conversations"
        self.host_name = host_name or "The Host"
        self.error_handler = ErrorHandler()
        
        self.email_prompt_template = """
You are an expert podcast outreach specialist. Write a personalized, compelling outreach email to invite a YouTube creator as a podcast guest.

Podcast Information:
- Podcast Name: {podcast_name}
- Topic/Niche: {podcast_topic}
- Host: {host_name}

Potential Guest Information:
- Channel Name: {channel_name}
- Subscribers: {subscriber_count}
- Channel Description: {description}
- Guest Score: {score}/10
- Score Reason: {score_reason}

Email Requirements:
1. Keep it concise (150-200 words max)
2. Personalize based on their channel content
3. Clearly state the podcast name and topic
4. Explain why they would be a great guest
5. Include a clear call-to-action
6. Be professional but friendly
7. Reference something specific from their channel to show you've done research

Format the email as plain text, ready to send. Do not include subject line or signature block.
Start with "Hi [Channel Name]," and end with a call to action.
"""
    
    def draft_email(self, channel_data: Dict[str, Any]) -> str:
        """
        Draft a personalized outreach email for a channel.
        
        Args:
            channel_data: Channel data with score
            
        Returns:
            Drafted email text
        """
        try:
            # Prepare the prompt
            prompt = self.email_prompt_template.format(
                podcast_name=self.podcast_name,
                podcast_topic=self.podcast_topic,
                host_name=self.host_name,
                channel_name=channel_data.get("ChannelName", "Creator"),
                subscriber_count=channel_data.get("SubscriberCount", "many"),
                description=channel_data.get("ChannelDescription", "Your content")[:500],
                score=channel_data.get("GuestScore", "N/A"),
                score_reason=channel_data.get("ScoreReason", "Great potential guest")
            )
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional podcast outreach specialist. Write compelling, personalized emails."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,  # Higher temperature for more creative emails
                max_tokens=400
            )
            
            email_text = response.choices[0].message.content.strip()
            
            # Clean up the email
            email_text = self._clean_email_text(email_text)
            
            logger.info(f"Drafted email for {channel_data.get('ChannelName')}")
            return email_text
            
        except Exception as e:
            logger.error(f"Error drafting email for {channel_data.get('ChannelID')}: {e}")
            # Return a generic template on error
            return self._get_fallback_email(channel_data)
    
    def draft_batch(self, channels: List[Dict[str, Any]], 
                    podcast_name: str = "", 
                    podcast_topic: str = "",
                    host_name: str = "") -> List[Dict[str, Any]]:
        """
        Draft emails for a batch of channels.
        
        Args:
            channels: List of scored channels
            podcast_name: Name of the podcast
            podcast_topic: Podcast topic
            host_name: Host name
            
        Returns:
            Channels with draft emails added
        """
        # Update podcast info if provided
        if podcast_name:
            self.podcast_name = podcast_name
        if podcast_topic:
            self.podcast_topic = podcast_topic
        if host_name:
            self.host_name = host_name
        
        logger.info(f"Drafting emails for {len(channels)} channels")
        print(f"\n✉️  Generating personalized outreach emails for {len(channels)} channels...")
        
        channels_with_emails = []
        
        for i, channel in enumerate(channels, 1):
            try:
                # Only draft emails for channels with good scores
                if int(channel.get("GuestScore", "0")) >= 6:
                    print(f"  Drafting email {i}/{len(channels)}: {channel.get('ChannelName', 'Unknown')[:50]}...")
                    
                    email = self.draft_email(channel)
                    channel["DraftEmail"] = email
                else:
                    # Skip low-scoring channels
                    channel["DraftEmail"] = "Score too low - no email drafted"
                
                channels_with_emails.append(channel)
                
            except Exception as e:
                logger.error(f"Failed to draft email for {channel.get('ChannelID')}: {e}")
                
                # Handle error with protocol
                if self.error_handler.handle_recoverable_error(e, f"draft_email_{i}"):
                    # Retry
                    try:
                        email = self.draft_email(channel)
                        channel["DraftEmail"] = email
                    except:
                        channel["DraftEmail"] = self._get_fallback_email(channel)
                else:
                    channel["DraftEmail"] = "Error drafting email"
                
                channels_with_emails.append(channel)
        
        print(f"✅ Email drafting complete!")
        return channels_with_emails
    
    def _clean_email_text(self, email: str) -> str:
        """
        Clean and format email text.
        
        Args:
            email: Raw email text
            
        Returns:
            Cleaned email text
        """
        # Remove any subject line if accidentally included
        lines = email.split('\n')
        if lines and lines[0].lower().startswith(('subject:', 're:', 'email:')):
            lines = lines[1:]
        
        email = '\n'.join(lines).strip()
        
        # Remove signature blocks if included
        signature_markers = ['best regards,', 'sincerely,', 'regards,', 'best,', 'thanks,']
        for marker in signature_markers:
            if marker in email.lower():
                # Keep the marker but remove anything after the next line
                parts = email.lower().split(marker)
                if len(parts) > 1:
                    # Find the original case marker position
                    idx = email.lower().find(marker)
                    email = email[:idx + len(marker)]
                    # Add just the host name
                    email += f"\n{self.host_name}"
                break
        
        # Ensure it fits in CSV cell
        if len(email) > 1000:
            email = email[:997] + "..."
        
        return email
    
    def _get_fallback_email(self, channel_data: Dict[str, Any]) -> str:
        """
        Get a fallback generic email template.
        
        Args:
            channel_data: Channel information
            
        Returns:
            Generic email template
        """
        channel_name = channel_data.get("ChannelName", "there")
        
        return f"""Hi {channel_name},

I've been following your YouTube channel and I'm impressed by your content and expertise. I host {self.podcast_name}, a podcast about {self.podcast_topic}, and I think you would be an excellent guest.

Your unique perspective and experience would provide tremendous value to our listeners. We'd love to have you share your insights and story on the show.

The interview would be conducted remotely at your convenience and typically runs 30-45 minutes.

Would you be interested in being a guest on {self.podcast_name}? I'd be happy to share more details and work around your schedule.

Looking forward to hearing from you!

{self.host_name}"""
    
    def customize_email(self, channel_data: Dict[str, Any], custom_template: str) -> str:
        """
        Use a custom email template with variable substitution.
        
        Args:
            channel_data: Channel information
            custom_template: Template with {variables}
            
        Returns:
            Customized email
        """
        try:
            email = custom_template.format(
                channel_name=channel_data.get("ChannelName", "there"),
                subscriber_count=channel_data.get("SubscriberCount", "many"),
                score=channel_data.get("GuestScore", "N/A"),
                podcast_name=self.podcast_name,
                podcast_topic=self.podcast_topic,
                host_name=self.host_name
            )
            return email
        except Exception as e:
            logger.error(f"Error customizing email: {e}")
            return self._get_fallback_email(channel_data)
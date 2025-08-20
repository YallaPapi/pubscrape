"""
AI Guest Scorer Module
Scores YouTube channels for podcast guest suitability using AI.
"""

import logging
import json
from typing import Dict, List, Any, Tuple
from openai import OpenAI

from .config import config
from .error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class GuestScorer:
    """Scores channels for podcast guest suitability using AI."""
    
    def __init__(self, podcast_topic: str = ""):
        """
        Initialize guest scorer with AI client.
        
        Args:
            podcast_topic: The podcast topic/niche for contextual scoring
        """
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.podcast_topic = podcast_topic
        self.error_handler = ErrorHandler()
        
        # Scoring criteria prompt
        self.scoring_prompt_template = """
You are an expert podcast guest evaluator. Score the following YouTube channel creator as a potential podcast guest on a scale of 1-10.

Podcast Topic/Niche: {podcast_topic}

Channel Information:
- Name: {channel_name}
- Subscribers: {subscriber_count}
- Description: {description}
- Website: {website}
- Social Links: {social_links}
- Video Count: {video_count}
- Total Views: {view_count}

Scoring Criteria (weight each appropriately):
1. **Relevance** (30%): How well does their content align with the podcast topic?
2. **Expertise** (25%): Demonstrated knowledge and authority in their field
3. **Audience Size** (20%): Subscriber count and engagement levels
4. **Communication Skills** (15%): Likely ability to articulate ideas based on their content
5. **Uniqueness** (10%): Unique perspective or story that would interest listeners

Provide your response in the following JSON format:
{{
    "score": <integer 1-10>,
    "reason": "<concise 1-2 sentence explanation of the score>",
    "strengths": ["strength1", "strength2"],
    "concerns": ["concern1", "concern2"]
}}

Be objective and consider that smaller channels might have highly specialized expertise.
"""
    
    def score_channel(self, channel_data: Dict[str, Any]) -> Tuple[int, str]:
        """
        Score a single channel for podcast guest suitability.
        
        Args:
            channel_data: Normalized channel data
            
        Returns:
            Tuple of (score, reason)
        """
        try:
            # Prepare the scoring prompt
            metadata = channel_data.get("_metadata", {})
            prompt = self.scoring_prompt_template.format(
                podcast_topic=self.podcast_topic or "general interest podcast",
                channel_name=channel_data.get("ChannelName", "Unknown"),
                subscriber_count=channel_data.get("SubscriberCount", "0"),
                description=channel_data.get("ChannelDescription", "No description"),
                website=channel_data.get("Website", "None"),
                social_links=channel_data.get("SocialLinks", "None"),
                video_count=metadata.get("video_count", "0"),
                view_count=metadata.get("view_count", "0")
            )
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a podcast guest evaluation expert. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=config.AI_TEMPERATURE,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Validate score is in range
            score = max(1, min(10, int(result.get("score", 5))))
            reason = result.get("reason", "Score calculated based on overall assessment")
            
            # Add strengths and concerns to reason if available
            if "strengths" in result and result["strengths"]:
                reason += f" Strengths: {', '.join(result['strengths'][:2])}."
            
            logger.info(f"Scored {channel_data.get('ChannelName')}: {score}/10")
            return score, reason
            
        except Exception as e:
            logger.error(f"Error scoring channel {channel_data.get('ChannelID')}: {e}")
            # Return default score on error
            return 5, "Could not generate AI score - default rating applied"
    
    def score_batch(self, channels: List[Dict[str, Any]], topic: str = "") -> List[Dict[str, Any]]:
        """
        Score a batch of channels.
        
        Args:
            channels: List of normalized channel data
            topic: Podcast topic for scoring context
            
        Returns:
            List of channels with scores and reasons added
        """
        if topic:
            self.podcast_topic = topic
        
        logger.info(f"Scoring {len(channels)} channels for topic: {self.podcast_topic}")
        print(f"\n🤖 AI Scoring {len(channels)} channels for podcast guest suitability...")
        
        scored_channels = []
        
        for i, channel in enumerate(channels, 1):
            try:
                print(f"  Scoring {i}/{len(channels)}: {channel.get('ChannelName', 'Unknown')[:50]}...")
                
                score, reason = self.score_channel(channel)
                
                # Update channel data with score
                channel["GuestScore"] = str(score)
                channel["ScoreReason"] = reason
                
                scored_channels.append(channel)
                
            except Exception as e:
                logger.error(f"Failed to score channel {channel.get('ChannelID')}: {e}")
                
                # Handle error with protocol
                if self.error_handler.handle_recoverable_error(e, f"score_channel_{i}"):
                    # Retry
                    try:
                        score, reason = self.score_channel(channel)
                        channel["GuestScore"] = str(score)
                        channel["ScoreReason"] = reason
                    except:
                        # Use default on second failure
                        channel["GuestScore"] = "5"
                        channel["ScoreReason"] = "Error in scoring - default applied"
                else:
                    # Use default score
                    channel["GuestScore"] = "5"
                    channel["ScoreReason"] = "Scoring error - default rating"
                
                scored_channels.append(channel)
        
        # Sort by score (highest first)
        scored_channels.sort(key=lambda x: int(x.get("GuestScore", "0")), reverse=True)
        
        print(f"✅ Scoring complete! Top channel: {scored_channels[0].get('ChannelName')} (Score: {scored_channels[0].get('GuestScore')})")
        
        return scored_channels
    
    def get_scoring_summary(self, scored_channels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary statistics of scoring results.
        
        Args:
            scored_channels: List of scored channels
            
        Returns:
            Summary statistics
        """
        scores = [int(c.get("GuestScore", "0")) for c in scored_channels]
        
        if not scores:
            return {"error": "No channels scored"}
        
        return {
            "total_scored": len(scores),
            "average_score": sum(scores) / len(scores),
            "highest_score": max(scores),
            "lowest_score": min(scores),
            "excellent_guests": sum(1 for s in scores if s >= 8),
            "good_guests": sum(1 for s in scores if 6 <= s < 8),
            "fair_guests": sum(1 for s in scores if 4 <= s < 6),
            "poor_guests": sum(1 for s in scores if s < 4),
            "score_distribution": {
                str(i): scores.count(i) for i in range(1, 11)
            }
        }
    
    def filter_by_score(self, channels: List[Dict[str, Any]], min_score: int = 6) -> List[Dict[str, Any]]:
        """
        Filter channels by minimum score threshold.
        
        Args:
            channels: List of scored channels
            min_score: Minimum score to include
            
        Returns:
            Filtered list of channels
        """
        filtered = [c for c in channels if int(c.get("GuestScore", "0")) >= min_score]
        logger.info(f"Filtered to {len(filtered)} channels with score >= {min_score}")
        return filtered
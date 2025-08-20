"""
Podcast intelligence and metrics analysis module.
Analyzes podcast popularity, relevance, and host authority.
"""

import re
import logging
import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import feedparser

from .base import PodcastData
from .config import config

logger = logging.getLogger(__name__)


class PodcastIntelligenceAnalyzer:
    """Analyzes podcast intelligence metrics and provides scoring."""
    
    def __init__(self):
        """Initialize intelligence analyzer."""
        self.logger = logging.getLogger(__name__)
        
        # AI/Technology relevance keywords
        self.ai_keywords = [
            'artificial intelligence', 'ai', 'machine learning', 'ml', 'deep learning',
            'neural networks', 'automation', 'robotics', 'chatgpt', 'openai',
            'llm', 'large language model', 'gpt', 'claude', 'anthropic',
            'tech', 'technology', 'startup', 'saas', 'software', 'digital',
            'innovation', 'disruption', 'future', 'algorithms', 'data science'
        ]
        
        # Business relevance keywords  
        self.business_keywords = [
            'business', 'entrepreneur', 'startup', 'founder', 'ceo', 'leadership',
            'marketing', 'sales', 'revenue', 'growth', 'scaling', 'investment',
            'venture capital', 'vc', 'funding', 'strategy', 'management',
            'productivity', 'success', 'innovation', 'disruption'
        ]
        
        # Quality indicators
        self.quality_indicators = [
            'award', 'winner', 'top', 'best', 'featured', 'popular', 'trending',
            'million', 'downloads', 'subscribers', 'listeners', 'audience',
            'exclusive', 'interview', 'expert', 'authority', 'thought leader'
        ]
        
        # Host authority keywords
        self.authority_keywords = [
            'author', 'book', 'bestseller', 'speaker', 'keynote', 'expert',
            'consultant', 'advisor', 'founder', 'ceo', 'executive', 'director',
            'professor', 'phd', 'researcher', 'scientist', 'journalist',
            'investor', 'venture capitalist', 'thought leader', 'influencer'
        ]
    
    def analyze_podcast_intelligence(self, podcast: PodcastData, topic: str = "") -> Dict[str, Any]:
        """
        Perform comprehensive intelligence analysis on a podcast.
        
        Args:
            podcast: PodcastData object to analyze
            topic: Search topic for relevance scoring
            
        Returns:
            Dict with intelligence metrics and scores
        """
        intelligence = {
            'overall_score': 0.0,
            'relevance_score': 0.0,
            'popularity_score': 0.0,
            'authority_score': 0.0,
            'content_quality_score': 0.0,
            'guest_potential_score': 0.0,
            'estimated_downloads': 'Unknown',
            'audience_size_category': 'Unknown',
            'host_authority_level': 'Unknown',
            'content_analysis': {},
            'recommendations': [],
            'risk_factors': []
        }
        
        try:
            # Analyze content relevance
            intelligence['relevance_score'] = self._analyze_relevance(podcast, topic)
            intelligence['content_analysis'] = self._analyze_content(podcast)
            
            # Analyze popularity metrics
            intelligence['popularity_score'] = self._analyze_popularity(podcast)
            intelligence['estimated_downloads'] = self._estimate_downloads(podcast)
            intelligence['audience_size_category'] = self._categorize_audience_size(podcast)
            
            # Analyze host authority
            intelligence['authority_score'] = self._analyze_host_authority(podcast)
            intelligence['host_authority_level'] = self._categorize_authority_level(intelligence['authority_score'])
            
            # Analyze content quality
            intelligence['content_quality_score'] = self._analyze_content_quality(podcast)
            
            # Calculate guest potential
            intelligence['guest_potential_score'] = self._calculate_guest_potential(podcast, intelligence)
            
            # Calculate overall score
            intelligence['overall_score'] = self._calculate_overall_score(intelligence)
            
            # Generate recommendations and identify risks
            intelligence['recommendations'] = self._generate_recommendations(podcast, intelligence)
            intelligence['risk_factors'] = self._identify_risk_factors(podcast, intelligence)
            
            self.logger.info(f"Intelligence analysis completed for {podcast.podcast_name}. Overall score: {intelligence['overall_score']:.1f}")
            
        except Exception as e:
            self.logger.error(f"Error during intelligence analysis for {podcast.podcast_name}: {e}")
        
        return intelligence
    
    def _analyze_relevance(self, podcast: PodcastData, topic: str) -> float:
        """Analyze topic relevance score (0-10)."""
        relevance_score = 0.0
        
        # Combine all text content for analysis
        content_text = " ".join([
            podcast.podcast_name or "",
            podcast.podcast_description or "",
            podcast.host_name or ""
        ]).lower()
        
        if not content_text.strip():
            return 0.0
        
        # Choose keyword set based on topic
        if any(ai_term in topic.lower() for ai_term in ['ai', 'artificial intelligence', 'technology', 'tech']):
            relevant_keywords = self.ai_keywords
        elif any(biz_term in topic.lower() for biz_term in ['business', 'entrepreneur', 'startup']):
            relevant_keywords = self.business_keywords
        else:
            # Use both sets for general topics
            relevant_keywords = self.ai_keywords + self.business_keywords
        
        # Count keyword matches
        keyword_matches = 0
        for keyword in relevant_keywords:
            if keyword in content_text:
                keyword_matches += 1
                # Bonus for exact matches in title
                if keyword in (podcast.podcast_name or "").lower():
                    keyword_matches += 0.5
        
        # Calculate base relevance score
        relevance_score = min(8.0, keyword_matches * 0.8)
        
        # Bonus for topic in title
        if topic.lower() in (podcast.podcast_name or "").lower():
            relevance_score += 2.0
        
        # Bonus for topic in description
        if topic.lower() in (podcast.podcast_description or "").lower():
            relevance_score += 1.0
        
        return round(min(10.0, relevance_score), 1)
    
    def _analyze_popularity(self, podcast: PodcastData) -> float:
        """Analyze popularity score based on available metrics (0-10)."""
        popularity_score = 0.0
        
        # Episode count factor (more episodes = more established)
        if podcast.episode_count:
            if podcast.episode_count >= 500:
                popularity_score += 3.0
            elif podcast.episode_count >= 200:
                popularity_score += 2.5
            elif podcast.episode_count >= 100:
                popularity_score += 2.0
            elif podcast.episode_count >= 50:
                popularity_score += 1.5
            elif podcast.episode_count >= 20:
                popularity_score += 1.0
            else:
                popularity_score += 0.5
        
        # Social media influence factor
        if hasattr(podcast, 'raw_data') and podcast.raw_data:
            social_influence = podcast.raw_data.get('social_influence_score', 0)
            popularity_score += min(3.0, social_influence * 0.3)
        
        # Platform presence factor
        if podcast.apple_podcasts_url:
            popularity_score += 0.5
        if podcast.podcast_website:
            popularity_score += 0.5
        if podcast.social_links and len(podcast.social_links) > 2:
            popularity_score += 1.0
        
        # Rating factor (if available)
        if podcast.rating:
            if podcast.rating >= 4.5:
                popularity_score += 2.0
            elif podcast.rating >= 4.0:
                popularity_score += 1.5
            elif podcast.rating >= 3.5:
                popularity_score += 1.0
            else:
                popularity_score += 0.5
        
        return round(min(10.0, popularity_score), 1)
    
    def _analyze_host_authority(self, podcast: PodcastData) -> float:
        """Analyze host authority score (0-10)."""
        authority_score = 0.0
        
        # Combine host-related text
        host_text = " ".join([
            podcast.host_name or "",
            podcast.podcast_description or ""
        ]).lower()
        
        if not host_text.strip():
            return 0.0
        
        # Count authority keywords
        authority_matches = 0
        for keyword in self.authority_keywords:
            if keyword in host_text:
                authority_matches += 1
        
        authority_score = min(6.0, authority_matches * 0.8)
        
        # Social media authority bonus
        if hasattr(podcast, 'raw_data') and podcast.raw_data:
            social_profiles = podcast.raw_data.get('social_profiles', {})
            for platform, profile_data in social_profiles.items():
                influence = profile_data.get('influence_score', 0)
                authority_score += min(1.0, influence * 0.1)
        
        # Website presence bonus
        if podcast.podcast_website:
            authority_score += 1.0
        
        # Multiple social platforms bonus
        if podcast.social_links and len(podcast.social_links) >= 3:
            authority_score += 1.0
        
        return round(min(10.0, authority_score), 1)
    
    def _analyze_content_quality(self, podcast: PodcastData) -> float:
        """Analyze content quality score (0-10)."""
        quality_score = 0.0
        
        # Description quality
        description = podcast.podcast_description or ""
        if description:
            # Length factor
            if len(description) > 200:
                quality_score += 2.0
            elif len(description) > 100:
                quality_score += 1.5
            elif len(description) > 50:
                quality_score += 1.0
            
            # Quality indicators in description
            quality_matches = sum(1 for indicator in self.quality_indicators if indicator in description.lower())
            quality_score += min(2.0, quality_matches * 0.5)
        
        # Consistency factor (episode count vs time)
        if podcast.episode_count and podcast.episode_count > 50:
            quality_score += 2.0  # Shows consistency
        
        # Professional presentation
        if podcast.podcast_name and not any(char in podcast.podcast_name.lower() for char in ['test', 'temp', 'draft']):
            quality_score += 1.0
        
        # Multiple platforms presence
        platform_count = 1  # Base for current platform
        if podcast.apple_podcasts_url:
            platform_count += 1
        if podcast.podcast_website:
            platform_count += 1
        if podcast.social_links:
            platform_count += len(podcast.social_links)
        
        quality_score += min(2.0, (platform_count - 1) * 0.3)
        
        return round(min(10.0, quality_score), 1)
    
    def _calculate_guest_potential(self, podcast: PodcastData, intelligence: Dict[str, Any]) -> float:
        """Calculate guest appearance potential score (0-10)."""
        guest_score = 0.0
        
        # Base score from other metrics
        guest_score += intelligence['popularity_score'] * 0.3
        guest_score += intelligence['authority_score'] * 0.25
        guest_score += intelligence['content_quality_score'] * 0.2
        guest_score += intelligence['relevance_score'] * 0.25
        
        # Contact availability bonus
        if podcast.host_email:
            guest_score += 1.5
        elif podcast.booking_email:
            guest_score += 1.0
        elif podcast.podcast_website:
            guest_score += 0.5
        
        # Interview format indicators
        description = (podcast.podcast_description or "").lower()
        interview_indicators = ['interview', 'guest', 'conversation', 'talk', 'discuss']
        if any(indicator in description for indicator in interview_indicators):
            guest_score += 1.0
        
        return round(min(10.0, guest_score), 1)
    
    def _calculate_overall_score(self, intelligence: Dict[str, Any]) -> float:
        """Calculate overall intelligence score (0-10)."""
        weights = {
            'relevance_score': 0.25,
            'popularity_score': 0.25,
            'authority_score': 0.20,
            'content_quality_score': 0.15,
            'guest_potential_score': 0.15
        }
        
        overall_score = sum(
            intelligence[metric] * weight 
            for metric, weight in weights.items()
        )
        
        return round(min(10.0, overall_score), 1)
    
    def _estimate_downloads(self, podcast: PodcastData) -> str:
        """Estimate download numbers based on available metrics."""
        if not podcast.episode_count:
            return "Unknown"
        
        # Base estimate calculation
        base_per_episode = 1000  # Conservative base
        
        # Adjust based on social influence
        social_multiplier = 1.0
        if hasattr(podcast, 'raw_data') and podcast.raw_data:
            social_influence = podcast.raw_data.get('social_influence_score', 0)
            social_multiplier = 1 + (social_influence / 10)
        
        # Adjust based on episode count (established shows get more)
        episode_multiplier = 1.0
        if podcast.episode_count >= 200:
            episode_multiplier = 3.0
        elif podcast.episode_count >= 100:
            episode_multiplier = 2.0
        elif podcast.episode_count >= 50:
            episode_multiplier = 1.5
        
        # Adjust based on rating
        rating_multiplier = 1.0
        if podcast.rating:
            rating_multiplier = max(0.5, podcast.rating / 5.0 * 2)
        
        estimated_per_episode = int(base_per_episode * social_multiplier * episode_multiplier * rating_multiplier)
        total_estimated = estimated_per_episode * podcast.episode_count
        
        return self._format_number(total_estimated)
    
    def _categorize_audience_size(self, podcast: PodcastData) -> str:
        """Categorize audience size based on metrics."""
        if not podcast.episode_count:
            return "Unknown"
        
        # Simple categorization based on episode count and other factors
        score = 0
        
        if podcast.episode_count >= 200:
            score += 3
        elif podcast.episode_count >= 100:
            score += 2
        elif podcast.episode_count >= 50:
            score += 1
        
        if podcast.social_links and len(podcast.social_links) >= 3:
            score += 1
        
        if podcast.rating and podcast.rating >= 4.0:
            score += 1
        
        if hasattr(podcast, 'raw_data') and podcast.raw_data:
            social_influence = podcast.raw_data.get('social_influence_score', 0)
            if social_influence >= 7:
                score += 2
            elif social_influence >= 5:
                score += 1
        
        if score >= 6:
            return "Large (100K+ downloads)"
        elif score >= 4:
            return "Medium (10K-100K downloads)"
        elif score >= 2:
            return "Small (1K-10K downloads)"
        else:
            return "Micro (<1K downloads)"
    
    def _categorize_authority_level(self, authority_score: float) -> str:
        """Categorize host authority level."""
        if authority_score >= 8.0:
            return "Industry Leader"
        elif authority_score >= 6.0:
            return "Expert"
        elif authority_score >= 4.0:
            return "Professional"
        elif authority_score >= 2.0:
            return "Enthusiast"
        else:
            return "Beginner"
    
    def _analyze_content(self, podcast: PodcastData) -> Dict[str, Any]:
        """Analyze content characteristics."""
        content_analysis = {
            'format_type': 'Unknown',
            'topic_focus': [],
            'interview_style': False,
            'educational_content': False,
            'entertainment_focus': False
        }
        
        description = (podcast.podcast_description or "").lower()
        title = (podcast.podcast_name or "").lower()
        
        # Determine format type
        if any(word in description + title for word in ['interview', 'conversation', 'talk']):
            content_analysis['format_type'] = 'Interview'
            content_analysis['interview_style'] = True
        elif any(word in description + title for word in ['news', 'update', 'daily', 'weekly']):
            content_analysis['format_type'] = 'News/Update'
        elif any(word in description + title for word in ['education', 'learn', 'tutorial', 'guide']):
            content_analysis['format_type'] = 'Educational'
            content_analysis['educational_content'] = True
        elif any(word in description + title for word in ['comedy', 'funny', 'humor', 'entertainment']):
            content_analysis['format_type'] = 'Entertainment'
            content_analysis['entertainment_focus'] = True
        
        # Identify topic focus
        all_text = description + " " + title
        focus_areas = []
        
        if any(keyword in all_text for keyword in self.ai_keywords[:10]):  # Top AI keywords
            focus_areas.append('Technology/AI')
        if any(keyword in all_text for keyword in self.business_keywords[:10]):  # Top business keywords
            focus_areas.append('Business')
        
        content_analysis['topic_focus'] = focus_areas
        
        return content_analysis
    
    def _generate_recommendations(self, podcast: PodcastData, intelligence: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        overall_score = intelligence['overall_score']
        
        if overall_score >= 8.0:
            recommendations.append("🎯 HIGH PRIORITY: Excellent guest opportunity with strong audience and authority")
        elif overall_score >= 6.0:
            recommendations.append("✅ GOOD PROSPECT: Solid podcast with good potential for collaboration")
        elif overall_score >= 4.0:
            recommendations.append("⚠️ MODERATE: May be worth considering depending on your specific goals")
        else:
            recommendations.append("❌ LOW PRIORITY: Limited potential based on current metrics")
        
        # Contact-specific recommendations
        if podcast.host_email:
            recommendations.append("📧 Direct email available - high response likelihood")
        elif podcast.booking_email:
            recommendations.append("📧 Booking email available - contact through business channels")
        elif podcast.podcast_website:
            recommendations.append("🌐 Website available - check for contact forms")
        elif podcast.social_links:
            recommendations.append("📱 Reach out via social media - may require relationship building")
        
        # Content relevance recommendations
        if intelligence['relevance_score'] >= 8.0:
            recommendations.append("🎯 Highly relevant content - perfect audience alignment")
        elif intelligence['relevance_score'] < 4.0:
            recommendations.append("⚠️ Low topic relevance - consider if audience alignment matches your goals")
        
        return recommendations
    
    def _identify_risk_factors(self, podcast: PodcastData, intelligence: Dict[str, Any]) -> List[str]:
        """Identify potential risk factors."""
        risks = []
        
        # Low contact availability
        if not any([podcast.host_email, podcast.booking_email, podcast.podcast_website]):
            risks.append("No direct contact methods available")
        
        # Low authority
        if intelligence['authority_score'] < 3.0:
            risks.append("Host authority level may be low")
        
        # Low audience
        if intelligence['popularity_score'] < 3.0:
            risks.append("Limited audience size/engagement")
        
        # Inconsistent content
        if podcast.episode_count and podcast.episode_count < 10:
            risks.append("Limited content history - new or inconsistent podcast")
        
        # Low relevance
        if intelligence['relevance_score'] < 3.0:
            risks.append("Topic relevance may not align with your target audience")
        
        return risks
    
    def _format_number(self, number: int) -> str:
        """Format large numbers with K/M/B suffixes."""
        if number >= 1_000_000_000:
            return f"{number / 1_000_000_000:.1f}B"
        elif number >= 1_000_000:
            return f"{number / 1_000_000:.1f}M"
        elif number >= 1_000:
            return f"{number / 1_000:.1f}K"
        else:
            return str(number)


class TopicRelevanceAnalyzer:
    """Analyzes podcast relevance to specific topics using AI."""
    
    def __init__(self):
        """Initialize topic relevance analyzer."""
        self.logger = logging.getLogger(__name__)
        self.openai_available = config.has_openai_key()
        
        if self.openai_available:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            except ImportError:
                self.logger.warning("OpenAI library not available")
                self.openai_available = False
    
    def analyze_ai_relevance(self, podcast: PodcastData, topic: str) -> Dict[str, Any]:
        """Use AI to analyze podcast relevance to topic."""
        if not self.openai_available:
            return {"score": 0.0, "reasoning": "AI analysis not available", "keywords": []}
        
        try:
            # Prepare content for analysis
            content = f"""
            Podcast: {podcast.podcast_name}
            Host: {podcast.host_name or 'Unknown'}
            Description: {podcast.podcast_description or 'No description'}
            """
            
            prompt = f"""
            Analyze how relevant this podcast is to the topic "{topic}" on a scale of 0-10.
            
            Podcast Information:
            {content}
            
            Provide:
            1. Relevance score (0-10)
            2. Brief reasoning (2-3 sentences)
            3. Key relevant keywords found
            
            Format your response as:
            Score: X.X
            Reasoning: [your reasoning]
            Keywords: [comma-separated keywords]
            """
            
            response = self.openai_client.chat.completions.create(
                model=config.AI_SETTINGS['openai_model'],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.AI_SETTINGS['max_tokens'],
                temperature=config.AI_SETTINGS['temperature']
            )
            
            result_text = response.choices[0].message.content
            
            # Parse the response
            score_match = re.search(r'Score:\s*(\d+\.?\d*)', result_text)
            score = float(score_match.group(1)) if score_match else 0.0
            
            reasoning_match = re.search(r'Reasoning:\s*([^\n]+)', result_text)
            reasoning = reasoning_match.group(1) if reasoning_match else "No reasoning provided"
            
            keywords_match = re.search(r'Keywords:\s*([^\n]+)', result_text)
            keywords = keywords_match.group(1).split(',') if keywords_match else []
            keywords = [k.strip() for k in keywords]
            
            return {
                "score": score,
                "reasoning": reasoning,
                "keywords": keywords
            }
            
        except Exception as e:
            self.logger.error(f"Error in AI relevance analysis: {e}")
            return {"score": 0.0, "reasoning": f"Analysis failed: {str(e)}", "keywords": []}
"""
Website Navigation and Contact Page Discovery System
TASK-D001: Intelligent website navigation for business contact discovery

This module implements a sophisticated website navigation system using Botasaurus
with advanced anti-detection capabilities and human-like behavior simulation.

Features:
- Smart contact page discovery with 15+ patterns
- Human-like navigation with realistic delays and movements
- Sitemap.xml parsing for efficient discovery
- Multi-page exploration with breadcrumb navigation
- Contact form detection and analysis
- Session management with proper cleanup
- Concurrent navigation for multiple sites
- Comprehensive error recovery and fallbacks
"""

import os
import re
import json
import time
import random
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs
from pathlib import Path
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue, Empty

# Botasaurus imports
from botasaurus import *
from botasaurus.browser import Driver, Wait
from botasaurus.request import AntiDetectDriver
from bs4 import BeautifulSoup

# Local imports
from .engine import BotasaurusEngine, SessionConfig
from .anti_detection import AntiDetectionManager, HumanBehaviorSimulator
from .models import BusinessLead, ContactInfo, Address


@dataclass
class NavigationTarget:
    """Target page for navigation with priority scoring"""
    url: str
    page_type: str  # 'contact', 'about', 'team', 'form', 'sitemap'
    priority_score: float
    discovery_method: str  # 'link_analysis', 'sitemap', 'pattern_match'
    link_text: str = ""
    parent_context: str = ""
    estimated_relevance: float = 0.0
    
    def __post_init__(self):
        """Calculate overall relevance score"""
        self.estimated_relevance = (self.priority_score * 0.7) + (len(self.link_text) > 0) * 0.3


@dataclass
class ContactPageAnalysis:
    """Analysis result for a contact page"""
    url: str
    page_type: str
    confidence_score: float
    contact_indicators: List[str]
    forms_found: List[Dict[str, Any]]
    email_addresses: List[str]
    phone_numbers: List[str]
    social_links: Dict[str, str]
    navigation_time: float
    errors: List[str] = field(default_factory=list)
    
    def has_contact_info(self) -> bool:
        """Check if page has any contact information"""
        return bool(self.email_addresses or self.phone_numbers or self.forms_found)


@dataclass
class NavigationSession:
    """Complete navigation session results"""
    base_url: str
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Navigation results
    pages_visited: List[str] = field(default_factory=list)
    contact_pages: List[ContactPageAnalysis] = field(default_factory=list)
    about_pages: List[ContactPageAnalysis] = field(default_factory=list)
    team_pages: List[ContactPageAnalysis] = field(default_factory=list)
    
    # Discovery statistics
    total_links_analyzed: int = 0
    sitemap_urls_found: int = 0
    forms_discovered: int = 0
    emails_extracted: int = 0
    phones_extracted: int = 0
    
    # Performance metrics
    navigation_efficiency: float = 0.0  # contacts found per page visited
    detection_attempts: int = 0
    errors_encountered: List[str] = field(default_factory=list)
    
    def calculate_efficiency(self):
        """Calculate navigation efficiency metrics"""
        if self.pages_visited:
            contacts_found = sum(len(page.email_addresses) + len(page.phone_numbers) 
                               for page in self.contact_pages)
            self.navigation_efficiency = contacts_found / len(self.pages_visited)


class WebsiteNavigator:
    """
    Advanced website navigator with Botasaurus integration and anti-detection
    
    Capabilities:
    - Intelligent contact page discovery using 15+ patterns
    - Human-like behavior simulation
    - Session isolation and management
    - Concurrent navigation support
    - Comprehensive error recovery
    """
    
    def __init__(self, config: Optional[SessionConfig] = None):
        """Initialize website navigator with configuration"""
        self.config = config
        self.engine = None
        self.anti_detection = AntiDetectionManager()
        self.behavior_simulator = HumanBehaviorSimulator()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Navigation patterns and scoring
        self._init_navigation_patterns()
        
        # Performance settings
        self.max_concurrent_sessions = 5
        self.max_pages_per_session = 10
        self.max_navigation_time = 300  # 5 minutes per session
        self.default_delay_range = (2.0, 5.0)  # Human-like delays
        
        # Active sessions tracking
        self.active_sessions = {}
        self.session_lock = threading.Lock()
        
    def _init_navigation_patterns(self):
        """Initialize contact page detection patterns with priority scoring"""
        
        # URL path patterns (highest priority)
        self.url_patterns = [
            (re.compile(r'^/?contact(?:-us|-info)?/?$', re.IGNORECASE), 100, 'contact'),
            (re.compile(r'^/?get-in-touch/?$', re.IGNORECASE), 95, 'contact'),
            (re.compile(r'^/?reach-out/?$', re.IGNORECASE), 90, 'contact'),
            (re.compile(r'^/?contact-us/?$', re.IGNORECASE), 95, 'contact'),
            (re.compile(r'^/?contact-info(?:rmation)?/?$', re.IGNORECASE), 85, 'contact'),
            (re.compile(r'^/?contact-form/?$', re.IGNORECASE), 80, 'contact'),
            (re.compile(r'^/?support/?$', re.IGNORECASE), 75, 'contact'),
            (re.compile(r'^/?help/?$', re.IGNORECASE), 70, 'contact'),
            
            # About page patterns
            (re.compile(r'^/?about(?:-us)?/?$', re.IGNORECASE), 85, 'about'),
            (re.compile(r'^/?who-we-are/?$', re.IGNORECASE), 80, 'about'),
            (re.compile(r'^/?our-story/?$', re.IGNORECASE), 75, 'about'),
            (re.compile(r'^/?company/?$', re.IGNORECASE), 70, 'about'),
            (re.compile(r'^/?mission/?$', re.IGNORECASE), 65, 'about'),
            
            # Team page patterns
            (re.compile(r'^/?team/?$', re.IGNORECASE), 80, 'team'),
            (re.compile(r'^/?our-team/?$', re.IGNORECASE), 85, 'team'),
            (re.compile(r'^/?staff/?$', re.IGNORECASE), 75, 'team'),
            (re.compile(r'^/?people/?$', re.IGNORECASE), 70, 'team'),
            (re.compile(r'^/?leadership/?$', re.IGNORECASE), 75, 'team'),
            (re.compile(r'^/?management/?$', re.IGNORECASE), 70, 'team'),
            (re.compile(r'^/?directors/?$', re.IGNORECASE), 65, 'team'),
            
            # Location and office patterns
            (re.compile(r'^/?location(?:s)?/?$', re.IGNORECASE), 60, 'contact'),
            (re.compile(r'^/?office(?:s)?/?$', re.IGNORECASE), 55, 'contact'),
            (re.compile(r'^/?find-us/?$', re.IGNORECASE), 50, 'contact'),
            (re.compile(r'^/?directions/?$', re.IGNORECASE), 45, 'contact'),
        ]
        
        # Link text patterns
        self.link_text_patterns = [
            (re.compile(r'^contact\s*us$', re.IGNORECASE), 100, 'contact'),
            (re.compile(r'^contact$', re.IGNORECASE), 95, 'contact'),
            (re.compile(r'^get\s*in\s*touch$', re.IGNORECASE), 90, 'contact'),
            (re.compile(r'^reach\s*out$', re.IGNORECASE), 85, 'contact'),
            (re.compile(r'^contact\s*info(?:rmation)?$', re.IGNORECASE), 80, 'contact'),
            (re.compile(r'^email\s*us$', re.IGNORECASE), 75, 'contact'),
            (re.compile(r'^call\s*us$', re.IGNORECASE), 70, 'contact'),
            
            (re.compile(r'^about\s*us$', re.IGNORECASE), 85, 'about'),
            (re.compile(r'^about$', re.IGNORECASE), 80, 'about'),
            (re.compile(r'^who\s*we\s*are$', re.IGNORECASE), 75, 'about'),
            (re.compile(r'^our\s*story$', re.IGNORECASE), 70, 'about'),
            
            (re.compile(r'^our\s*team$', re.IGNORECASE), 85, 'team'),
            (re.compile(r'^team$', re.IGNORECASE), 80, 'team'),
            (re.compile(r'^meet\s*the\s*team$', re.IGNORECASE), 75, 'team'),
            (re.compile(r'^staff$', re.IGNORECASE), 70, 'team'),
        ]
        
        # Content indicators for page analysis
        self.content_indicators = {
            'email': [
                re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
                re.compile(r'email\s*:?\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE),
            ],
            'phone': [
                re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
                re.compile(r'phone\s*:?\s*[\d\s\-\(\)\.]{10,}', re.IGNORECASE),
                re.compile(r'tel\s*:?\s*[\d\s\-\(\)\.]{10,}', re.IGNORECASE),
            ],
            'contact_keywords': [
                'contact information', 'get in touch', 'reach out', 'contact us',
                'email us', 'call us', 'send message', 'contact form',
                'office hours', 'business hours', 'location', 'address'
            ]
        }
        
        # Social media patterns
        self.social_patterns = {
            'facebook': re.compile(r'(?:https?://)?(?:www\.)?facebook\.com/[\w\.-]+', re.IGNORECASE),
            'twitter': re.compile(r'(?:https?://)?(?:www\.)?twitter\.com/[\w\.-]+', re.IGNORECASE),
            'linkedin': re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/[\w\.-]+', re.IGNORECASE),
            'instagram': re.compile(r'(?:https?://)?(?:www\.)?instagram\.com/[\w\.-]+', re.IGNORECASE),
        }
    
    @browser(
        profile=lambda self: self.config.profile_name if self.config else "navigator_profile",
        headless=False,
        block_images=True,
        block_media=True,
        window_size=(1920, 1080),
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        reuse_driver=True,
        max_retry=3,
        bypass_cloudflare=True,  # Anti-detection feature
        human_cursor=True        # Human-like cursor movements
    )
    def create_navigation_driver(self, driver: Driver) -> Driver:
        """Create and configure Botasaurus driver for website navigation"""
        self.engine = BotasaurusEngine(self.config)
        
        # Apply anti-detection measures
        self.engine._apply_stealth_config(driver)
        
        # Configure for optimal contact page discovery
        driver.set_window_size(1920, 1080)
        
        # Disable unnecessary resources for faster navigation
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        return driver
    
    def discover_contact_pages(self, base_url: str, max_pages: int = 10) -> NavigationSession:
        """
        Main entry point for contact page discovery
        
        Args:
            base_url: The website URL to analyze
            max_pages: Maximum pages to visit during discovery
            
        Returns:
            NavigationSession with complete results
        """
        session_id = f"nav_{int(time.time())}_{random.randint(1000, 9999)}"
        session = NavigationSession(
            base_url=base_url,
            session_id=session_id,
            start_time=datetime.now()
        )
        
        try:
            self.logger.info(f"Starting contact discovery for {base_url} (session: {session_id})")
            
            # Initialize navigation driver
            driver = self.create_navigation_driver()
            
            with self.session_lock:
                self.active_sessions[session_id] = session
            
            # Phase 1: Analyze main page and discover navigation targets
            main_targets = self._analyze_main_page(driver, base_url, session)
            
            # Phase 2: Check for sitemap.xml
            sitemap_targets = self._discover_sitemap_targets(base_url, session)
            
            # Phase 3: Combine and prioritize all targets
            all_targets = self._prioritize_targets(main_targets + sitemap_targets)
            
            # Phase 4: Navigate to high-priority targets
            self._navigate_to_targets(driver, all_targets[:max_pages], session)
            
            # Phase 5: Analyze discovered pages for contact information
            self._analyze_contact_pages(session)
            
            session.end_time = datetime.now()
            session.calculate_efficiency()
            
            self.logger.info(f"Discovery completed: {len(session.contact_pages)} contact pages found "
                           f"with efficiency {session.navigation_efficiency:.2f}")
            
        except Exception as e:
            error_msg = f"Navigation session failed: {str(e)}"
            self.logger.error(error_msg)
            session.errors_encountered.append(error_msg)
            session.end_time = datetime.now()
        
        finally:
            # Cleanup session
            with self.session_lock:
                self.active_sessions.pop(session_id, None)
            
            try:
                driver.quit()
            except:
                pass
        
        return session
    
    def _analyze_main_page(self, driver: Driver, url: str, session: NavigationSession) -> List[NavigationTarget]:
        """Analyze main page to discover navigation targets"""
        targets = []
        
        try:
            # Navigate with human-like behavior
            self._navigate_with_behavior(driver, url)
            session.pages_visited.append(url)
            
            # Extract page content
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find all navigation links
            links = soup.find_all('a', href=True)
            session.total_links_analyzed = len(links)
            
            for link in links:
                href = link.get('href', '').strip()
                if not href or href.startswith('#'):
                    continue
                
                # Convert to absolute URL
                full_url = urljoin(url, href)
                
                # Skip external domains
                if urlparse(full_url).netloc != urlparse(url).netloc:
                    continue
                
                # Analyze link for contact relevance
                target = self._analyze_link_for_contact(link, full_url, url)
                if target and target.priority_score > 20:  # Minimum relevance threshold
                    targets.append(target)
            
            self.logger.info(f"Analyzed {len(links)} links, found {len(targets)} contact targets")
            
        except Exception as e:
            error_msg = f"Error analyzing main page {url}: {str(e)}"
            self.logger.error(error_msg)
            session.errors_encountered.append(error_msg)
        
        return targets
    
    def _discover_sitemap_targets(self, base_url: str, session: NavigationSession) -> List[NavigationTarget]:
        """Discover contact pages from sitemap.xml"""
        targets = []
        
        sitemap_urls = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemaps/sitemap.xml',
            '/sitemap.xml.gz'
        ]
        
        for sitemap_path in sitemap_urls:
            try:
                sitemap_url = urljoin(base_url, sitemap_path)
                
                # Use requests for sitemap (faster than browser)
                import requests
                response = requests.get(sitemap_url, timeout=10)
                
                if response.status_code == 200:
                    # Parse sitemap XML
                    try:
                        root = ET.fromstring(response.content)
                        
                        # Handle both regular and namespaced XML
                        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                            loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                            if loc_elem is not None:
                                url = loc_elem.text.strip()
                                target = self._analyze_url_for_contact(url)
                                if target:
                                    target.discovery_method = 'sitemap'
                                    targets.append(target)
                        
                        # Handle non-namespaced XML
                        if not targets:
                            for url_elem in root.findall('.//url'):
                                loc_elem = url_elem.find('loc')
                                if loc_elem is not None:
                                    url = loc_elem.text.strip()
                                    target = self._analyze_url_for_contact(url)
                                    if target:
                                        target.discovery_method = 'sitemap'
                                        targets.append(target)
                        
                        session.sitemap_urls_found = len(targets)
                        self.logger.info(f"Found {len(targets)} potential contact URLs in sitemap")
                        break  # Found valid sitemap
                        
                    except ET.ParseError:
                        continue
                        
            except Exception as e:
                self.logger.debug(f"Could not access sitemap {sitemap_path}: {e}")
                continue
        
        return targets
    
    def _analyze_link_for_contact(self, link, full_url: str, base_url: str) -> Optional[NavigationTarget]:
        """Analyze a link element for contact page relevance"""
        link_text = link.get_text(strip=True)
        link_title = link.get('title', '')
        href = link.get('href', '')
        
        # Get parent context
        parent_context = self._get_link_context(link)
        
        # Calculate priority score
        priority_score = 0.0
        page_type = 'unknown'
        
        # Score based on URL path
        url_score, url_type = self._score_url_path(full_url)
        priority_score += url_score
        if url_type != 'unknown':
            page_type = url_type
        
        # Score based on link text
        text_score, text_type = self._score_link_text(link_text)
        priority_score += text_score
        if text_type != 'unknown' and page_type == 'unknown':
            page_type = text_type
        
        # Additional scoring factors
        if 'nav' in parent_context.lower():
            priority_score += 15  # Navigation links are more relevant
        
        if link_title and any(keyword in link_title.lower() 
                            for keyword in ['contact', 'about', 'team']):
            priority_score += 10
        
        # Penalties
        if any(ext in href.lower() for ext in ['.pdf', '.jpg', '.png', '.zip', '.doc']):
            priority_score -= 30  # Avoid file downloads
        
        if priority_score > 20:  # Minimum threshold
            return NavigationTarget(
                url=full_url,
                page_type=page_type,
                priority_score=priority_score,
                discovery_method='link_analysis',
                link_text=link_text,
                parent_context=parent_context
            )
        
        return None
    
    def _analyze_url_for_contact(self, url: str) -> Optional[NavigationTarget]:
        """Analyze URL pattern for contact page relevance"""
        score, page_type = self._score_url_path(url)
        
        if score > 40:  # Higher threshold for sitemap URLs
            return NavigationTarget(
                url=url,
                page_type=page_type,
                priority_score=score,
                discovery_method='sitemap'
            )
        
        return None
    
    def _score_url_path(self, url: str) -> Tuple[float, str]:
        """Score URL path for contact relevance"""
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/').lower()
        
        for pattern, score, page_type in self.url_patterns:
            if pattern.match(path):
                return score, page_type
        
        return 0.0, 'unknown'
    
    def _score_link_text(self, text: str) -> Tuple[float, str]:
        """Score link text for contact relevance"""
        text = text.strip()
        if not text:
            return 0.0, 'unknown'
        
        for pattern, score, page_type in self.link_text_patterns:
            if pattern.match(text):
                return score, page_type
        
        return 0.0, 'unknown'
    
    def _get_link_context(self, link) -> str:
        """Get contextual information about a link's location"""
        context_parts = []
        
        # Check parent elements for navigation context
        parent = link.parent
        for _ in range(3):  # Check 3 levels up
            if parent and parent.name:
                classes = ' '.join(parent.get('class', []))
                id_attr = parent.get('id', '')
                context_parts.extend([classes, id_attr])
                parent = parent.parent
            else:
                break
        
        return ' '.join(filter(None, context_parts))
    
    def _prioritize_targets(self, targets: List[NavigationTarget]) -> List[NavigationTarget]:
        """Prioritize and deduplicate navigation targets"""
        # Remove duplicates by URL
        unique_targets = {}
        for target in targets:
            if target.url not in unique_targets or target.priority_score > unique_targets[target.url].priority_score:
                unique_targets[target.url] = target
        
        # Sort by priority score (highest first)
        sorted_targets = sorted(unique_targets.values(), 
                              key=lambda t: t.priority_score, 
                              reverse=True)
        
        return sorted_targets
    
    def _navigate_to_targets(self, driver: Driver, targets: List[NavigationTarget], session: NavigationSession):
        """Navigate to prioritized targets and collect page data"""
        for i, target in enumerate(targets):
            try:
                self.logger.info(f"Visiting target {i+1}/{len(targets)}: {target.url} "
                               f"(score: {target.priority_score:.1f})")
                
                # Navigate with human behavior
                if self._navigate_with_behavior(driver, target.url):
                    session.pages_visited.append(target.url)
                    
                    # Analyze page content
                    analysis = self._analyze_page_content(driver, target.url, target.page_type)
                    
                    # Categorize based on analysis results
                    if target.page_type == 'contact' or analysis.confidence_score > 0.7:
                        session.contact_pages.append(analysis)
                    elif target.page_type == 'about':
                        session.about_pages.append(analysis)
                    elif target.page_type == 'team':
                        session.team_pages.append(analysis)
                    else:
                        # Determine category based on content
                        if analysis.confidence_score > 0.5:
                            session.contact_pages.append(analysis)
                    
                    # Update session statistics
                    session.forms_discovered += len(analysis.forms_found)
                    session.emails_extracted += len(analysis.email_addresses)
                    session.phones_extracted += len(analysis.phone_numbers)
                
                # Human-like delay between navigations
                delay = random.uniform(*self.default_delay_range)
                time.sleep(delay)
                
            except Exception as e:
                error_msg = f"Error navigating to {target.url}: {str(e)}"
                self.logger.error(error_msg)
                session.errors_encountered.append(error_msg)
    
    def _navigate_with_behavior(self, driver: Driver, url: str) -> bool:
        """Navigate to URL with human-like behavior simulation"""
        try:
            start_time = time.time()
            
            # Pre-navigation delay
            time.sleep(random.uniform(0.5, 1.5))
            
            # Navigate to URL
            driver.get(url)
            
            # Wait for page load
            Wait.for_ready_state_complete(driver, timeout=10)
            
            # Simulate human reading behavior
            self._simulate_reading_behavior(driver)
            
            # Check for anti-bot detection
            if self._check_for_detection(driver):
                self.logger.warning(f"Possible detection on {url}")
                return False
            
            navigation_time = time.time() - start_time
            self.logger.debug(f"Navigation to {url} completed in {navigation_time:.2f}s")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Navigation failed for {url}: {e}")
            return False
    
    def _simulate_reading_behavior(self, driver: Driver):
        """Simulate human reading patterns"""
        try:
            # Random scroll patterns
            scroll_actions = self.behavior_simulator.get_scroll_pattern()
            
            for action in scroll_actions[:3]:  # Limit scrolling for efficiency
                if action['action'] == 'scroll':
                    driver.execute_script(f"window.scrollBy(0, {action['distance']})")
                elif action['action'] == 'wait':
                    time.sleep(min(action['duration'], 2.0))  # Cap wait times
                
                # Small delay between actions
                time.sleep(random.uniform(0.2, 0.5))
                
        except Exception as e:
            self.logger.debug(f"Behavior simulation error: {e}")
    
    def _check_for_detection(self, driver: Driver) -> bool:
        """Check if anti-bot measures detected our activity"""
        try:
            page_source = driver.page_source.lower()
            title = driver.title.lower()
            
            detection_indicators = [
                'captcha', 'recaptcha', 'hcaptcha', 'cloudflare',
                'bot detection', 'unusual activity', 'access denied',
                'security check', 'please verify', 'are you human'
            ]
            
            for indicator in detection_indicators:
                if indicator in page_source or indicator in title:
                    return True
            
            return False
            
        except:
            return False
    
    def _analyze_page_content(self, driver: Driver, url: str, expected_type: str) -> ContactPageAnalysis:
        """Analyze page content for contact information"""
        start_time = time.time()
        analysis = ContactPageAnalysis(
            url=url,
            page_type=expected_type,
            confidence_score=0.0,
            contact_indicators=[],
            forms_found=[],
            email_addresses=[],
            phone_numbers=[],
            social_links={},
            navigation_time=0.0
        )
        
        try:
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            text_content = soup.get_text()
            
            # Extract email addresses
            for pattern in self.content_indicators['email']:
                matches = pattern.findall(text_content)
                analysis.email_addresses.extend(matches)
            
            # Extract phone numbers
            for pattern in self.content_indicators['phone']:
                matches = pattern.findall(text_content)
                analysis.phone_numbers.extend(matches)
            
            # Find contact forms
            analysis.forms_found = self._analyze_forms(soup)
            
            # Extract social media links
            analysis.social_links = self._extract_social_links(soup)
            
            # Find contact indicators
            text_lower = text_content.lower()
            for keyword in self.content_indicators['contact_keywords']:
                if keyword in text_lower:
                    analysis.contact_indicators.append(keyword)
            
            # Calculate confidence score
            analysis.confidence_score = self._calculate_content_confidence(analysis)
            
            # Remove duplicates
            analysis.email_addresses = list(set(analysis.email_addresses))
            analysis.phone_numbers = list(set(analysis.phone_numbers))
            analysis.contact_indicators = list(set(analysis.contact_indicators))
            
            analysis.navigation_time = time.time() - start_time
            
            self.logger.debug(f"Content analysis for {url}: "
                            f"{len(analysis.email_addresses)} emails, "
                            f"{len(analysis.phone_numbers)} phones, "
                            f"{len(analysis.forms_found)} forms, "
                            f"confidence: {analysis.confidence_score:.2f}")
            
        except Exception as e:
            error_msg = f"Content analysis failed for {url}: {str(e)}"
            self.logger.error(error_msg)
            analysis.errors.append(error_msg)
        
        return analysis
    
    def _analyze_forms(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Analyze forms on the page for contact relevance"""
        forms = []
        
        for i, form in enumerate(soup.find_all('form')):
            form_data = {
                'index': i,
                'action': form.get('action', ''),
                'method': form.get('method', 'GET').upper(),
                'fields': [],
                'has_email': False,
                'has_message': False,
                'is_contact_form': False
            }
            
            # Analyze form fields
            for field in form.find_all(['input', 'textarea', 'select']):
                field_type = field.get('type', '').lower()
                field_name = field.get('name', '').lower()
                field_placeholder = field.get('placeholder', '').lower()
                
                field_data = {
                    'type': field_type,
                    'name': field_name,
                    'placeholder': field_placeholder,
                    'required': field.get('required') is not None
                }
                
                form_data['fields'].append(field_data)
                
                # Check for email field
                if (field_type == 'email' or 
                    'email' in field_name or 
                    'email' in field_placeholder):
                    form_data['has_email'] = True
                
                # Check for message field
                if (field.name == 'textarea' or
                    'message' in field_name or
                    'comment' in field_name):
                    form_data['has_message'] = True
            
            # Determine if this is a contact form
            form_data['is_contact_form'] = (
                form_data['has_email'] and 
                len(form_data['fields']) >= 2
            )
            
            forms.append(form_data)
        
        return [form for form in forms if form['is_contact_form']]
    
    def _extract_social_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract social media links from page"""
        social_links = {}
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            for platform, pattern in self.social_patterns.items():
                if pattern.match(href):
                    social_links[platform] = href
                    break
        
        return social_links
    
    def _calculate_content_confidence(self, analysis: ContactPageAnalysis) -> float:
        """Calculate confidence score based on found content"""
        score = 0.0
        
        # Email addresses (high value)
        if analysis.email_addresses:
            score += min(len(analysis.email_addresses) * 0.3, 0.5)
        
        # Phone numbers (high value)
        if analysis.phone_numbers:
            score += min(len(analysis.phone_numbers) * 0.25, 0.4)
        
        # Contact forms (very high value)
        if analysis.forms_found:
            score += min(len(analysis.forms_found) * 0.2, 0.3)
        
        # Contact indicators (moderate value)
        if analysis.contact_indicators:
            score += min(len(analysis.contact_indicators) * 0.05, 0.2)
        
        # Social links (low value)
        if analysis.social_links:
            score += min(len(analysis.social_links) * 0.02, 0.1)
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _analyze_contact_pages(self, session: NavigationSession):
        """Final analysis and categorization of discovered pages"""
        # Re-categorize pages based on final confidence scores
        all_pages = session.contact_pages + session.about_pages + session.team_pages
        
        # Clear existing categorization
        session.contact_pages.clear()
        session.about_pages.clear()
        session.team_pages.clear()
        
        for page in all_pages:
            if page.confidence_score > 0.7 or page.has_contact_info():
                session.contact_pages.append(page)
            elif 'about' in page.page_type.lower():
                session.about_pages.append(page)
            elif 'team' in page.page_type.lower():
                session.team_pages.append(page)
            else:
                # Default to contact pages if they have some contact info
                if page.confidence_score > 0.3:
                    session.contact_pages.append(page)
        
        # Sort by confidence score
        session.contact_pages.sort(key=lambda p: p.confidence_score, reverse=True)
        session.about_pages.sort(key=lambda p: p.confidence_score, reverse=True)
        session.team_pages.sort(key=lambda p: p.confidence_score, reverse=True)
    
    def navigate_multiple_sites(self, urls: List[str], max_concurrent: int = 5) -> Dict[str, NavigationSession]:
        """
        Navigate multiple websites concurrently
        
        Args:
            urls: List of website URLs to navigate
            max_concurrent: Maximum concurrent navigation sessions
            
        Returns:
            Dictionary mapping URLs to navigation sessions
        """
        results = {}
        max_workers = min(max_concurrent, self.max_concurrent_sessions, len(urls))
        
        self.logger.info(f"Starting concurrent navigation for {len(urls)} sites "
                        f"with {max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit navigation tasks
            future_to_url = {
                executor.submit(self.discover_contact_pages, url): url 
                for url in urls
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    session = future.result()
                    results[url] = session
                    self.logger.info(f"Completed navigation for {url}: "
                                   f"{len(session.contact_pages)} contact pages found")
                except Exception as e:
                    self.logger.error(f"Navigation failed for {url}: {e}")
                    # Create error session
                    results[url] = NavigationSession(
                        base_url=url,
                        session_id=f"error_{int(time.time())}",
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        errors_encountered=[str(e)]
                    )
        
        return results
    
    def export_session_data(self, session: NavigationSession, format: str = 'json') -> str:
        """Export navigation session data to specified format"""
        if format.lower() == 'json':
            return json.dumps({
                'session_id': session.session_id,
                'base_url': session.base_url,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat() if session.end_time else None,
                'pages_visited': session.pages_visited,
                'contact_pages': [
                    {
                        'url': page.url,
                        'confidence_score': page.confidence_score,
                        'email_addresses': page.email_addresses,
                        'phone_numbers': page.phone_numbers,
                        'forms_found': page.forms_found,
                        'social_links': page.social_links
                    }
                    for page in session.contact_pages
                ],
                'statistics': {
                    'total_links_analyzed': session.total_links_analyzed,
                    'sitemap_urls_found': session.sitemap_urls_found,
                    'forms_discovered': session.forms_discovered,
                    'emails_extracted': session.emails_extracted,
                    'phones_extracted': session.phones_extracted,
                    'navigation_efficiency': session.navigation_efficiency,
                    'detection_attempts': session.detection_attempts
                },
                'errors': session.errors_encountered
            }, indent=2)
        
        raise ValueError(f"Unsupported export format: {format}")


def create_website_navigator(config: Optional[SessionConfig] = None) -> WebsiteNavigator:
    """Factory function to create a configured website navigator"""
    if not config:
        config = SessionConfig(
            session_id=f"nav_{int(time.time())}",
            profile_name="navigator_default",
            stealth_level=3,
            block_images=True,
            block_media=True
        )
    
    return WebsiteNavigator(config)


if __name__ == "__main__":
    # Test the website navigator
    print("Botasaurus Website Navigator v1.0")
    print("="*50)
    
    # Create navigator
    navigator = create_website_navigator()
    
    # Test single site navigation
    test_url = "https://example.com"
    print(f"\nTesting navigation for: {test_url}")
    
    session = navigator.discover_contact_pages(test_url, max_pages=5)
    
    print(f"\nNavigation Results:")
    print(f"Pages visited: {len(session.pages_visited)}")
    print(f"Contact pages: {len(session.contact_pages)}")
    print(f"Emails found: {session.emails_extracted}")
    print(f"Phones found: {session.phones_extracted}")
    print(f"Forms found: {session.forms_discovered}")
    print(f"Navigation efficiency: {session.navigation_efficiency:.2f}")
    
    if session.errors_encountered:
        print(f"Errors: {len(session.errors_encountered)}")
    
    # Export results
    json_data = navigator.export_session_data(session)
    print(f"\nExported {len(json_data)} characters of session data")
    
    print("\nWebsite Navigator test completed!")
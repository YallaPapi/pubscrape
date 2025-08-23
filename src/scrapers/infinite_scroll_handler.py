#!/usr/bin/env python3
"""
Infinite Scroll Handler for Map Results using Botasaurus
Handles dynamic loading of Bing Maps and Google Maps results with sophisticated scrolling strategies
"""

from botasaurus import browser
from bs4 import BeautifulSoup
import time
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
try:
    from .scroll_strategies import (
        SmoothScrollStrategy, 
        ChunkScrollStrategy, 
        AdaptiveScrollStrategy,
        ScrollResult
    )
    from .map_extractors import BingMapsExtractor, GoogleMapsExtractor
except ImportError:
    # Handle relative imports when running as script
    from scroll_strategies import (
        SmoothScrollStrategy, 
        ChunkScrollStrategy, 
        AdaptiveScrollStrategy,
        ScrollResult
    )
    from map_extractors import BingMapsExtractor, GoogleMapsExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ScrollConfig:
    """Configuration for infinite scroll behavior"""
    max_scroll_iterations: int = 20
    scroll_pause_time: float = 2.0
    stable_height_count: int = 3
    element_batch_size: int = 10
    timeout_seconds: int = 300
    strategy_type: str = 'adaptive'  # 'smooth', 'chunk', 'adaptive'

@dataclass
class MapScrollSession:
    """Represents a map scrolling session"""
    platform: str  # 'bing' or 'google'
    query: str
    location: str
    config: ScrollConfig
    start_time: datetime
    extracted_businesses: List[Dict] = None
    scroll_metrics: Dict = None

class InfiniteScrollHandler:
    """
    Handles infinite scrolling for map search results with multiple strategies
    and platform-specific optimization
    """
    
    def __init__(self, config: ScrollConfig = None):
        self.config = config or ScrollConfig()
        self.extractors = {
            'bing': BingMapsExtractor(),
            'google': GoogleMapsExtractor()
        }
        self.scroll_strategies = {
            'smooth': SmoothScrollStrategy(),
            'chunk': ChunkScrollStrategy(), 
            'adaptive': AdaptiveScrollStrategy()
        }
        
    @browser(
        headless=False,
        block_images=True,
        reuse_driver=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        stealth=True
    )
    def scroll_and_extract_bing_maps(self, driver, query: str, location: str = None) -> MapScrollSession:
        """
        Main handler for Bing Maps infinite scroll and extraction
        
        Args:
            driver: Botasaurus browser driver
            query: Search query (e.g., "restaurants", "doctors")
            location: Location filter (e.g., "Miami, FL")
            
        Returns:
            MapScrollSession with extracted business data
        """
        session = MapScrollSession(
            platform='bing',
            query=query,
            location=location or '',
            config=self.config,
            start_time=datetime.now(),
            extracted_businesses=[],
            scroll_metrics={}
        )
        
        try:
            # Build Bing Maps search URL
            search_url = self._build_bing_maps_url(query, location)
            logger.info(f"Starting Bing Maps scroll session: {search_url}")
            
            # Navigate to Bing Maps
            driver.get(search_url)
            driver.sleep(3)
            
            # Handle any popups or overlays
            self._handle_bing_popups(driver)
            
            # Get scroll strategy
            strategy = self.scroll_strategies[self.config.strategy_type]
            
            # Perform infinite scroll with extraction
            scroll_result = self._execute_scroll_extraction(
                driver, session, strategy, 'bing'
            )
            
            # Final extraction of all visible elements
            final_businesses = self._extract_all_visible_businesses(driver, 'bing')
            
            # Update session results
            session.extracted_businesses = final_businesses
            session.scroll_metrics = scroll_result.metrics
            
            logger.info(f"Bing Maps extraction complete: {len(final_businesses)} businesses found")
            
        except Exception as e:
            logger.error(f"Error in Bing Maps scroll handler: {e}")
            session.scroll_metrics['error'] = str(e)
            
        return session
    
    @browser(
        headless=False,
        block_images=True,
        reuse_driver=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        stealth=True
    )
    def scroll_and_extract_google_maps(self, driver, query: str, location: str = None) -> MapScrollSession:
        """
        Main handler for Google Maps infinite scroll and extraction
        
        Args:
            driver: Botasaurus browser driver
            query: Search query (e.g., "restaurants", "doctors")
            location: Location filter (e.g., "Miami, FL")
            
        Returns:
            MapScrollSession with extracted business data
        """
        session = MapScrollSession(
            platform='google',
            query=query,
            location=location or '',
            config=self.config,
            start_time=datetime.now(),
            extracted_businesses=[],
            scroll_metrics={}
        )
        
        try:
            # Build Google Maps search URL
            search_url = self._build_google_maps_url(query, location)
            logger.info(f"Starting Google Maps scroll session: {search_url}")
            
            # Navigate to Google Maps
            driver.get(search_url)
            driver.sleep(4)
            
            # Handle any popups or overlays
            self._handle_google_popups(driver)
            
            # Get scroll strategy
            strategy = self.scroll_strategies[self.config.strategy_type]
            
            # Perform infinite scroll with extraction
            scroll_result = self._execute_scroll_extraction(
                driver, session, strategy, 'google'
            )
            
            # Final extraction of all visible elements
            final_businesses = self._extract_all_visible_businesses(driver, 'google')
            
            # Update session results
            session.extracted_businesses = final_businesses
            session.scroll_metrics = scroll_result.metrics
            
            logger.info(f"Google Maps extraction complete: {len(final_businesses)} businesses found")
            
        except Exception as e:
            logger.error(f"Error in Google Maps scroll handler: {e}")
            session.scroll_metrics['error'] = str(e)
            
        return session
    
    def _execute_scroll_extraction(self, driver, session: MapScrollSession, 
                                 strategy, platform: str) -> ScrollResult:
        """
        Execute scrolling with business extraction using selected strategy
        
        Args:
            driver: Browser driver
            session: Current scroll session
            strategy: Scroll strategy instance
            platform: 'bing' or 'google'
            
        Returns:
            ScrollResult with metrics and status
        """
        extractor = self.extractors[platform]
        start_time = time.time()
        
        # Initialize tracking variables
        previous_height = 0
        stable_height_count = 0
        iteration = 0
        total_businesses_found = 0
        last_business_count = 0
        
        logger.info(f"Starting {strategy.__class__.__name__} scroll extraction")
        
        while iteration < self.config.max_scroll_iterations:
            iteration += 1
            
            # Get current scroll position and height
            current_height = driver.run_js("return document.body.scrollHeight")
            scroll_position = driver.run_js("return window.pageYOffset")
            
            logger.debug(f"Iteration {iteration}: height={current_height}, position={scroll_position}")
            
            # Execute scroll strategy
            scroll_performed = strategy.scroll(driver, iteration)
            
            if not scroll_performed:
                logger.info("Scroll strategy indicates scrolling complete")
                break
            
            # Wait for content to load
            driver.sleep(self.config.scroll_pause_time)
            
            # Extract businesses from current view
            current_businesses = extractor.extract_business_cards(driver)
            current_count = len(current_businesses)
            
            # Update session with new businesses (deduplication handled by extractor)
            if hasattr(session, 'extracted_businesses'):
                session.extracted_businesses.extend(current_businesses)
                total_businesses_found = len(session.extracted_businesses)
            
            # Check for scroll completion conditions
            new_height = driver.run_js("return document.body.scrollHeight")
            
            # Track stable height (no new content loading)
            if new_height == previous_height:
                stable_height_count += 1
                logger.debug(f"Stable height count: {stable_height_count}")
            else:
                stable_height_count = 0
                previous_height = new_height
            
            # Check if we've found new businesses
            new_businesses_found = current_count > last_business_count
            last_business_count = current_count
            
            # Log progress
            if iteration % 5 == 0:
                logger.info(f"Iteration {iteration}: {total_businesses_found} total businesses found")
            
            # Exit conditions
            if stable_height_count >= self.config.stable_height_count:
                logger.info("Reached stable height - no more content loading")
                break
                
            if not new_businesses_found and iteration > 5:
                logger.info("No new businesses found in recent iterations")
                break
                
            # Timeout check
            if time.time() - start_time > self.config.timeout_seconds:
                logger.warning("Scroll timeout reached")
                break
        
        # Compile scroll metrics
        end_time = time.time()
        metrics = {
            'total_iterations': iteration,
            'duration_seconds': end_time - start_time,
            'final_height': driver.run_js("return document.body.scrollHeight"),
            'total_businesses_found': total_businesses_found,
            'strategy_used': strategy.__class__.__name__,
            'completed_reason': self._determine_completion_reason(
                iteration, stable_height_count, new_businesses_found, end_time - start_time
            )
        }
        
        return ScrollResult(
            success=True,
            total_scrolled=metrics['final_height'],
            iterations=iteration,
            businesses_found=total_businesses_found,
            metrics=metrics
        )
    
    def _extract_all_visible_businesses(self, driver, platform: str) -> List[Dict]:
        """
        Perform final extraction of all visible business cards
        
        Args:
            driver: Browser driver
            platform: 'bing' or 'google'
            
        Returns:
            List of extracted business dictionaries
        """
        extractor = self.extractors[platform]
        
        # Scroll to top to ensure we capture everything
        driver.run_js("window.scrollTo(0, 0)")
        driver.sleep(1)
        
        # Perform comprehensive extraction
        all_businesses = extractor.extract_all_businesses(driver)
        
        logger.info(f"Final extraction found {len(all_businesses)} businesses")
        return all_businesses
    
    def _build_bing_maps_url(self, query: str, location: str = None) -> str:
        """Build Bing Maps search URL"""
        base_url = "https://www.bing.com/maps"
        
        # Combine query with location if provided
        if location:
            search_term = f"{query} in {location}"
        else:
            search_term = query
        
        # Encode search term
        from urllib.parse import quote_plus
        encoded_query = quote_plus(search_term)
        
        return f"{base_url}?q={encoded_query}&FORM=LMLTCC"
    
    def _build_google_maps_url(self, query: str, location: str = None) -> str:
        """Build Google Maps search URL"""
        base_url = "https://www.google.com/maps/search"
        
        # Combine query with location if provided
        if location:
            search_term = f"{query} {location}"
        else:
            search_term = query
        
        # Encode search term
        from urllib.parse import quote_plus
        encoded_query = quote_plus(search_term)
        
        return f"{base_url}/{encoded_query}"
    
    def _handle_bing_popups(self, driver) -> None:
        """Handle Bing Maps popups and overlays"""
        try:
            # Close cookie banner
            cookie_banner = driver.select('button[aria-label*="Accept"]')
            if cookie_banner:
                cookie_banner.click()
                driver.sleep(1)
            
            # Close location permission popup
            location_popup = driver.select('button[aria-label*="Close"]')
            if location_popup:
                location_popup.click()
                driver.sleep(1)
                
        except Exception as e:
            logger.debug(f"No popups found or error handling: {e}")
    
    def _handle_google_popups(self, driver) -> None:
        """Handle Google Maps popups and overlays"""
        try:
            # Close cookie consent
            consent_button = driver.select('button[aria-label*="Accept all"]')
            if consent_button:
                consent_button.click()
                driver.sleep(1)
            
            # Decline location sharing
            location_decline = driver.select('button[data-value="2"]')
            if location_decline:
                location_decline.click()
                driver.sleep(1)
                
        except Exception as e:
            logger.debug(f"No popups found or error handling: {e}")
    
    def _determine_completion_reason(self, iteration: int, stable_height: int, 
                                   new_businesses: bool, duration: float) -> str:
        """Determine why scrolling completed"""
        if iteration >= self.config.max_scroll_iterations:
            return "max_iterations_reached"
        elif stable_height >= self.config.stable_height_count:
            return "stable_height_detected"
        elif not new_businesses:
            return "no_new_businesses"
        elif duration > self.config.timeout_seconds:
            return "timeout_reached"
        else:
            return "manual_completion"
    
    def create_session_report(self, session: MapScrollSession) -> Dict[str, Any]:
        """
        Create comprehensive session report
        
        Args:
            session: Completed scroll session
            
        Returns:
            Dictionary with session statistics and results
        """
        end_time = datetime.now()
        duration = (end_time - session.start_time).total_seconds()
        
        # Calculate business statistics
        businesses = session.extracted_businesses or []
        with_email = sum(1 for b in businesses if b.get('email'))
        with_phone = sum(1 for b in businesses if b.get('phone'))
        with_website = sum(1 for b in businesses if b.get('website'))
        
        report = {
            'session_info': {
                'platform': session.platform,
                'query': session.query,
                'location': session.location,
                'start_time': session.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration
            },
            'extraction_results': {
                'total_businesses': len(businesses),
                'businesses_with_email': with_email,
                'businesses_with_phone': with_phone, 
                'businesses_with_website': with_website,
                'email_rate': with_email / max(len(businesses), 1) * 100,
                'phone_rate': with_phone / max(len(businesses), 1) * 100,
                'website_rate': with_website / max(len(businesses), 1) * 100
            },
            'scroll_metrics': session.scroll_metrics or {},
            'configuration': {
                'max_iterations': session.config.max_scroll_iterations,
                'strategy': session.config.strategy_type,
                'pause_time': session.config.scroll_pause_time,
                'timeout': session.config.timeout_seconds
            }
        }
        
        return report


def create_scroll_handler(strategy_type: str = 'adaptive', 
                         max_iterations: int = 20) -> InfiniteScrollHandler:
    """
    Factory function to create configured scroll handler
    
    Args:
        strategy_type: 'smooth', 'chunk', or 'adaptive'
        max_iterations: Maximum scroll iterations
        
    Returns:
        Configured InfiniteScrollHandler instance
    """
    config = ScrollConfig(
        strategy_type=strategy_type,
        max_scroll_iterations=max_iterations
    )
    
    return InfiniteScrollHandler(config)
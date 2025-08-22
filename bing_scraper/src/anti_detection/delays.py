"""
Human-like Delays for Anti-Detection
Implements natural timing patterns to avoid bot detection.
"""

import time
import random
import logging
from typing import Tuple, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DelayConfig:
    """Configuration for delay timing."""
    min_delay: float = 1.0
    max_delay: float = 3.0
    base_multiplier: float = 1.0
    variance: float = 0.3

class HumanLikeDelays:
    """Generates human-like delay patterns for web scraping."""
    
    def __init__(self, settings):
        """Initialize with settings."""
        self.settings = settings
        self.base_delay = settings.base_delay_seconds
        self.request_count = 0
        self.session_start = time.time()
        
        # Delay configurations for different actions
        self.configs = {
            'page_load': DelayConfig(2.0, 5.0, 1.0, 0.4),
            'search': DelayConfig(1.5, 4.0, 1.2, 0.3),
            'navigation': DelayConfig(0.8, 2.5, 1.0, 0.2),
            'extraction': DelayConfig(0.5, 1.5, 0.8, 0.2),
            'typing': DelayConfig(0.1, 0.3, 0.5, 0.1),
            'mouse_move': DelayConfig(0.1, 0.3, 0.5, 0.1),
            'scroll': DelayConfig(0.5, 1.5, 1.0, 0.2),
            'reading': DelayConfig(1.0, 3.0, 1.0, 0.3),
            'click': DelayConfig(0.2, 0.8, 1.0, 0.1),
        }
        
        logger.info("HumanLikeDelays initialized")
    
    def random_delay(self, action: str = 'navigation') -> float:
        """
        Generate random delay based on action type.
        
        Args:
            action: Type of action ('page_load', 'search', 'navigation', 'extraction', 'typing')
            
        Returns:
            Delay duration in seconds
        """
        config = self.configs.get(action, self.configs['navigation'])
        
        # Base delay with human variance
        base = random.uniform(config.min_delay, config.max_delay)
        
        # Apply base multiplier from settings
        base *= (self.base_delay / 3.0)  # Normalize to base_delay_seconds
        
        # Add random variance
        variance = random.uniform(-config.variance, config.variance)
        delay = base * (1 + variance)
        
        # Ensure minimum delay
        delay = max(delay, 0.1)
        
        # Apply fatigue factor (slower as session progresses)
        fatigue_factor = self._get_fatigue_factor()
        delay *= fatigue_factor
        
        logger.debug(f"Generated {action} delay: {delay:.2f}s")
        time.sleep(delay)
        
        self.request_count += 1
        return delay
    
    def _get_fatigue_factor(self) -> float:
        """Calculate fatigue factor based on session duration and request count."""
        # Increase delays as session progresses (simulates human fatigue)
        session_duration = time.time() - self.session_start
        
        # Base fatigue from session duration (max 50% increase)
        duration_fatigue = min(1.5, 1.0 + (session_duration / 3600) * 0.5)
        
        # Request count fatigue (max 30% increase)
        request_fatigue = min(1.3, 1.0 + (self.request_count / 100) * 0.3)
        
        return duration_fatigue * request_fatigue
    
    def typing_delay(self, text: str) -> float:
        """
        Generate realistic typing delays for text input.
        
        Args:
            text: Text being typed
            
        Returns:
            Total typing duration
        """
        if not text:
            return 0
        
        total_delay = 0
        
        for i, char in enumerate(text):
            # Base typing speed: 60-120 WPM (250-500ms per character)
            base_speed = random.uniform(0.08, 0.16)  # seconds per character
            
            # Adjust for character complexity
            if char.isupper():
                base_speed *= 1.2  # Slower for uppercase
            elif char in '!@#$%^&*()_+-={}[]|\\:";\'<>?,./':
                base_speed *= 1.4  # Slower for special characters
            elif char == ' ':
                base_speed *= 0.8  # Faster for spaces
            
            # Add human variance
            char_delay = base_speed * random.uniform(0.7, 1.5)
            
            # Occasional longer pauses (thinking)
            if random.random() < 0.1:  # 10% chance
                char_delay += random.uniform(0.5, 2.0)
            
            time.sleep(char_delay)
            total_delay += char_delay
        
        logger.debug(f"Typing delay for '{text[:20]}...': {total_delay:.2f}s")
        return total_delay
    
    def page_load_delay(self) -> float:
        """Delay after page load, simulating reading time."""
        return self.random_delay('page_load')
    
    def search_delay(self) -> float:
        """Delay before performing search."""
        return self.random_delay('search')
    
    def extraction_delay(self) -> float:
        """Delay during data extraction."""
        return self.random_delay('extraction')
    
    def retry_delay(self, attempt: int) -> float:
        """
        Exponential backoff delay for retries.
        
        Args:
            attempt: Current retry attempt (1-based)
            
        Returns:
            Delay duration in seconds
        """
        # Exponential backoff with jitter
        base_delay = min(60, 2 ** attempt)  # Cap at 60 seconds
        jitter = random.uniform(0.8, 1.2)
        delay = base_delay * jitter
        
        logger.info(f"Retry delay (attempt {attempt}): {delay:.2f}s")
        time.sleep(delay)
        return delay
    
    def rate_limit_delay(self) -> float:
        """Delay when rate limit is detected."""
        # Longer delay to respect rate limits
        delay = random.uniform(30, 90)  # 30-90 seconds
        logger.warning(f"Rate limit delay: {delay:.2f}s")
        time.sleep(delay)
        return delay
    
    def session_break_delay(self) -> float:
        """Longer delay simulating session break."""
        delay = random.uniform(300, 900)  # 5-15 minutes
        logger.info(f"Session break delay: {delay:.2f}s")
        time.sleep(delay)
        return delay
    
    def smart_delay(self, response_time: Optional[float] = None, 
                   status_code: Optional[int] = None) -> float:
        """
        Smart delay based on server response characteristics.
        
        Args:
            response_time: Server response time in seconds
            status_code: HTTP status code
            
        Returns:
            Calculated delay duration
        """
        base_delay = self.base_delay
        
        # Adjust based on response time
        if response_time:
            if response_time > 5.0:
                # Server is slow, be more gentle
                base_delay *= 1.5
            elif response_time < 0.5:
                # Server is fast, can be more aggressive
                base_delay *= 0.8
        
        # Adjust based on status code
        if status_code:
            if status_code == 429:  # Rate limited
                return self.rate_limit_delay()
            elif status_code >= 500:  # Server error
                base_delay *= 2.0
            elif status_code == 403:  # Forbidden
                base_delay *= 1.8
        
        # Apply variance
        delay = base_delay * random.uniform(0.7, 1.4)
        
        logger.debug(f"Smart delay: {delay:.2f}s (response: {response_time}, status: {status_code})")
        time.sleep(delay)
        return delay
    
    def get_burst_pattern(self, count: int) -> List[float]:
        """
        Generate burst pattern delays for multiple requests.
        
        Args:
            count: Number of requests in burst
            
        Returns:
            List of delay durations
        """
        delays = []
        
        for i in range(count):
            if i == 0:
                # First request: normal delay
                delay = self.random_delay('navigation')
            elif i < count // 2:
                # Ramp up: shorter delays
                delay = self.random_delay('extraction') * 0.7
            else:
                # Cool down: longer delays
                delay = self.random_delay('navigation') * 1.3
            
            delays.append(delay)
        
        return delays
    
    def simulate_mouse_movements(self, driver, num_movements: int = None) -> float:
        """
        Simulate natural mouse movements on the page.
        
        Args:
            driver: Botasaurus driver instance
            num_movements: Number of mouse movements (random if None)
            
        Returns:
            Total time spent on mouse movements
        """
        if num_movements is None:
            num_movements = random.randint(2, 6)
        
        total_time = 0
        
        try:
            # Get page dimensions
            page_width = driver.run_js("return window.innerWidth;") or 1920
            page_height = driver.run_js("return window.innerHeight;") or 1080
            
            for i in range(num_movements):
                # Generate natural mouse movement patterns
                if i == 0:
                    # Start from a natural position
                    x = random.randint(page_width // 4, 3 * page_width // 4)
                    y = random.randint(page_height // 4, 3 * page_height // 4)
                else:
                    # Move in a natural curve from previous position
                    x_delta = random.randint(-200, 200)
                    y_delta = random.randint(-150, 150)
                    x = max(10, min(page_width - 10, x + x_delta))
                    y = max(10, min(page_height - 10, y + y_delta))
                
                # Execute mouse movement with JavaScript
                driver.run_js(f"""
                    var event = new MouseEvent('mousemove', {{
                        clientX: {x},
                        clientY: {y},
                        bubbles: true,
                        cancelable: true
                    }});
                    document.dispatchEvent(event);
                """)
                
                # Human-like pause between movements
                delay = self.random_delay('mouse_move')
                total_time += delay
                
                # Occasionally hover over elements
                if random.random() < 0.3:
                    try:
                        hover_js = f"""
                            var element = document.elementFromPoint({x}, {y});
                            if (element) {{
                                var hoverEvent = new MouseEvent('mouseover', {{
                                    clientX: {x},
                                    clientY: {y},
                                    bubbles: true
                                }});
                                element.dispatchEvent(hoverEvent);
                            }}
                        """
                        driver.run_js(hover_js)
                        time.sleep(random.uniform(0.2, 0.8))
                        total_time += 0.5
                    except:
                        pass
            
            logger.debug(f"Simulated {num_movements} mouse movements in {total_time:.2f}s")
            
        except Exception as e:
            logger.debug(f"Mouse movement simulation error: {e}")
        
        return total_time
    
    def simulate_scrolling(self, driver, scroll_type: str = 'reading') -> float:
        """
        Simulate natural scrolling behavior.
        
        Args:
            driver: Botasaurus driver instance
            scroll_type: Type of scrolling ('reading', 'scanning', 'searching')
            
        Returns:
            Total time spent scrolling
        """
        total_time = 0
        
        try:
            # Get page height
            page_height = driver.run_js("return document.body.scrollHeight;") or 2000
            viewport_height = driver.run_js("return window.innerHeight;") or 1080
            
            if page_height <= viewport_height:
                return 0  # No need to scroll
            
            if scroll_type == 'reading':
                # Slow, deliberate scrolling (reading content)
                scroll_steps = random.randint(3, 8)
                step_size = random.randint(100, 300)
            elif scroll_type == 'scanning':
                # Medium speed scrolling (looking for specific content)
                scroll_steps = random.randint(5, 12)
                step_size = random.randint(200, 500)
            else:  # searching
                # Faster scrolling (searching for something specific)
                scroll_steps = random.randint(2, 5)
                step_size = random.randint(300, 800)
            
            current_position = 0
            
            for i in range(scroll_steps):
                # Determine scroll direction and amount
                if random.random() < 0.1 and current_position > 0:
                    # Occasionally scroll up (user reconsidering)
                    scroll_amount = -random.randint(50, 200)
                else:
                    # Normal downward scroll
                    scroll_amount = random.randint(step_size // 2, step_size)
                
                # Execute scroll
                driver.run_js(f"window.scrollBy(0, {scroll_amount});")
                current_position += scroll_amount
                
                # Natural pause between scrolls
                if scroll_type == 'reading':
                    pause = random.uniform(1.0, 3.0)  # Reading time
                elif scroll_type == 'scanning':
                    pause = random.uniform(0.5, 1.5)  # Quick scanning
                else:
                    pause = random.uniform(0.2, 0.8)  # Fast searching
                
                time.sleep(pause)
                total_time += pause
                
                # Stop if we've reached the bottom
                current_scroll = driver.run_js("return window.pageYOffset;") or 0
                if current_scroll + viewport_height >= page_height * 0.95:
                    break
            
            # Occasionally scroll back to top or specific position
            if random.random() < 0.2:
                if random.random() < 0.5:
                    # Scroll to top
                    driver.run_js("window.scrollTo(0, 0);")
                else:
                    # Scroll to random position
                    random_position = random.randint(0, max(0, page_height - viewport_height))
                    driver.run_js(f"window.scrollTo(0, {random_position});")
                
                time.sleep(random.uniform(0.5, 1.5))
                total_time += 1.0
            
            logger.debug(f"Simulated {scroll_type} scrolling in {total_time:.2f}s")
            
        except Exception as e:
            logger.debug(f"Scrolling simulation error: {e}")
        
        return total_time
    
    def simulate_reading_behavior(self, driver, content_type: str = 'search_results') -> float:
        """
        Simulate realistic reading behavior patterns.
        
        Args:
            driver: Botasaurus driver instance
            content_type: Type of content being read
            
        Returns:
            Total time spent reading
        """
        total_time = 0
        
        try:
            if content_type == 'search_results':
                # Reading search results - quick scanning then focused reading
                
                # Quick initial scan
                total_time += self.simulate_scrolling(driver, 'scanning')
                
                # Focus on specific results (simulate clicking/hovering)
                num_results_viewed = random.randint(2, 5)
                
                for i in range(num_results_viewed):
                    # Simulate looking at a result
                    reading_time = random.uniform(2.0, 8.0)
                    time.sleep(reading_time)
                    total_time += reading_time
                    
                    # Small scroll or mouse movement
                    if random.random() < 0.7:
                        total_time += self.simulate_mouse_movements(driver, 2)
                    
                    if random.random() < 0.4:
                        scroll_time = self.simulate_scrolling(driver, 'reading')
                        total_time += scroll_time
            
            elif content_type == 'webpage':
                # Reading full webpage content
                reading_time = random.uniform(10.0, 30.0)
                
                # Break reading into chunks with scrolling
                chunks = random.randint(3, 6)
                time_per_chunk = reading_time / chunks
                
                for i in range(chunks):
                    time.sleep(time_per_chunk)
                    total_time += time_per_chunk
                    
                    if i < chunks - 1:  # Don't scroll after last chunk
                        scroll_time = self.simulate_scrolling(driver, 'reading')
                        total_time += scroll_time
            
            else:  # general content
                reading_time = random.uniform(3.0, 12.0)
                time.sleep(reading_time)
                total_time += reading_time
            
            logger.debug(f"Simulated reading {content_type} in {total_time:.2f}s")
            
        except Exception as e:
            logger.debug(f"Reading simulation error: {e}")
        
        return total_time
    
    def simulate_human_session_start(self, driver) -> float:
        """
        Simulate behavior when starting a new browsing session.
        
        Args:
            driver: Botasaurus driver instance
            
        Returns:
            Total time spent on session start behavior
        """
        total_time = 0
        
        try:
            # Initial page load wait (user orienting)
            initial_wait = random.uniform(2.0, 5.0)
            time.sleep(initial_wait)
            total_time += initial_wait
            
            # Quick page scan
            total_time += self.simulate_mouse_movements(driver, random.randint(3, 5))
            
            # Brief reading of page content
            total_time += self.simulate_reading_behavior(driver, 'general')
            
            logger.debug(f"Simulated session start behavior in {total_time:.2f}s")
            
        except Exception as e:
            logger.debug(f"Session start simulation error: {e}")
        
        return total_time
    
    def simulate_search_behavior(self, driver, query: str) -> float:
        """
        Simulate realistic search behavior patterns.
        
        Args:
            driver: Botasaurus driver instance
            query: Search query being entered
            
        Returns:
            Total time spent on search behavior
        """
        total_time = 0
        
        try:
            # Pre-search hesitation (thinking about query)
            thinking_time = random.uniform(0.5, 2.0)
            time.sleep(thinking_time)
            total_time += thinking_time
            
            # Mouse movement to search box (already done by main logic)
            total_time += self.simulate_mouse_movements(driver, 2)
            
            # Typing delay handled by typing_delay method
            
            # Post-typing pause (reviewing query)
            review_time = random.uniform(0.3, 1.5)
            time.sleep(review_time)
            total_time += review_time
            
            # Occasional query modification (backspace and retype)
            if random.random() < 0.15:  # 15% chance
                # Simulate small correction
                correction_time = random.uniform(1.0, 3.0)
                time.sleep(correction_time)
                total_time += correction_time
            
            logger.debug(f"Simulated search behavior for '{query}' in {total_time:.2f}s")
            
        except Exception as e:
            logger.debug(f"Search behavior simulation error: {e}")
        
        return total_time
    
    def get_session_stats(self) -> dict:
        """Get session delay statistics."""
        session_duration = time.time() - self.session_start
        avg_delay = session_duration / max(1, self.request_count)
        
        return {
            'session_duration': session_duration,
            'total_requests': self.request_count,
            'average_delay': avg_delay,
            'fatigue_factor': self._get_fatigue_factor(),
            'base_delay_setting': self.base_delay
        }
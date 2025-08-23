#!/usr/bin/env python3
"""
Scrolling Strategies for Infinite Scroll
Different approaches to handle dynamic content loading on map search results
"""

import time
import logging
import random
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ScrollResult:
    """Result of a scrolling operation"""
    success: bool
    total_scrolled: int
    iterations: int
    businesses_found: int
    metrics: Dict[str, Any]

class BaseScrollStrategy(ABC):
    """Base class for scrolling strategies"""
    
    def __init__(self):
        self.scroll_history = []
        self.performance_metrics = {}
    
    @abstractmethod
    def scroll(self, driver, iteration: int) -> bool:
        """
        Perform scrolling operation
        
        Args:
            driver: Browser driver instance
            iteration: Current iteration number
            
        Returns:
            True if scrolling should continue, False if complete
        """
        pass
    
    def reset(self):
        """Reset strategy state"""
        self.scroll_history.clear()
        self.performance_metrics.clear()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this strategy"""
        return self.performance_metrics.copy()

class SmoothScrollStrategy(BaseScrollStrategy):
    """
    Smooth continuous scrolling strategy
    Gradually scrolls down in small increments to simulate natural user behavior
    """
    
    def __init__(self, scroll_increment: int = 300, pause_time: float = 1.5):
        super().__init__()
        self.scroll_increment = scroll_increment
        self.pause_time = pause_time
        self.total_scrolled = 0
    
    def scroll(self, driver, iteration: int) -> bool:
        """Perform smooth scrolling"""
        try:
            # Get current scroll position and page height
            current_scroll = driver.run_js("return window.pageYOffset")
            page_height = driver.run_js("return document.body.scrollHeight")
            viewport_height = driver.run_js("return window.innerHeight")
            
            # Calculate scroll target
            scroll_target = current_scroll + self.scroll_increment
            
            # Check if we've reached the bottom
            if current_scroll + viewport_height >= page_height - 100:
                logger.debug("Smooth scroll: Reached bottom of page")
                return False
            
            # Perform smooth scroll with easing
            self._smooth_scroll_to(driver, scroll_target)
            
            # Add human-like pause with jitter
            jittered_pause = self.pause_time + random.uniform(-0.3, 0.5)
            time.sleep(jittered_pause)
            
            # Track metrics
            self.total_scrolled += self.scroll_increment
            self.scroll_history.append({
                'iteration': iteration,
                'scroll_position': scroll_target,
                'page_height': page_height,
                'timestamp': time.time()
            })
            
            logger.debug(f"Smooth scroll iteration {iteration}: scrolled to {scroll_target}")
            return True
            
        except Exception as e:
            logger.error(f"Error in smooth scroll iteration {iteration}: {e}")
            return False
    
    def _smooth_scroll_to(self, driver, target_position: int):
        """Perform smooth scrolling to target position"""
        current_position = driver.run_js("return window.pageYOffset")
        distance = target_position - current_position
        steps = max(1, abs(distance) // 50)  # Scroll in ~50px increments
        
        for i in range(steps):
            intermediate_position = current_position + (distance * (i + 1) / steps)
            driver.run_js(f"window.scrollTo(0, {intermediate_position})")
            time.sleep(0.05)  # Small delay between increments
        
        # Final scroll to exact target
        driver.run_js(f"window.scrollTo(0, {target_position})")

class ChunkScrollStrategy(BaseScrollStrategy):
    """
    Chunk-based scrolling strategy
    Scrolls in larger chunks and waits for content to load completely
    """
    
    def __init__(self, chunk_size: float = 0.8, wait_time: float = 3.0):
        super().__init__()
        self.chunk_size = chunk_size  # Fraction of viewport to scroll
        self.wait_time = wait_time
        self.chunks_scrolled = 0
    
    def scroll(self, driver, iteration: int) -> bool:
        """Perform chunk-based scrolling"""
        try:
            # Get current metrics
            viewport_height = driver.run_js("return window.innerHeight")
            current_scroll = driver.run_js("return window.pageYOffset")
            page_height = driver.run_js("return document.body.scrollHeight")
            
            # Calculate chunk scroll distance
            chunk_distance = int(viewport_height * self.chunk_size)
            scroll_target = current_scroll + chunk_distance
            
            # Check if we've reached the bottom
            if current_scroll + viewport_height >= page_height - 50:
                logger.debug("Chunk scroll: Reached bottom of page")
                return False
            
            # Record pre-scroll state
            pre_scroll_height = page_height
            
            # Perform chunk scroll
            driver.run_js(f"window.scrollTo(0, {scroll_target})")
            
            # Wait for content to load and stabilize
            self._wait_for_content_stabilization(driver)
            
            # Check if new content was loaded
            post_scroll_height = driver.run_js("return document.body.scrollHeight")
            new_content_loaded = post_scroll_height > pre_scroll_height
            
            # Track metrics
            self.chunks_scrolled += 1
            self.scroll_history.append({
                'iteration': iteration,
                'chunk_size': chunk_distance,
                'pre_height': pre_scroll_height,
                'post_height': post_scroll_height,
                'new_content': new_content_loaded,
                'timestamp': time.time()
            })
            
            logger.debug(f"Chunk scroll iteration {iteration}: chunk {chunk_distance}px, "
                        f"new content: {new_content_loaded}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in chunk scroll iteration {iteration}: {e}")
            return False
    
    def _wait_for_content_stabilization(self, driver):
        """Wait for content to stabilize after scrolling"""
        stable_checks = 0
        required_stable_checks = 3
        last_height = 0
        
        for _ in range(10):  # Max 10 checks
            time.sleep(0.5)
            current_height = driver.run_js("return document.body.scrollHeight")
            
            if current_height == last_height:
                stable_checks += 1
                if stable_checks >= required_stable_checks:
                    break
            else:
                stable_checks = 0
                last_height = current_height
        
        # Final stabilization wait
        time.sleep(self.wait_time)

class AdaptiveScrollStrategy(BaseScrollStrategy):
    """
    Adaptive scrolling strategy
    Dynamically adjusts scrolling based on content loading patterns and performance
    """
    
    def __init__(self, 
                 initial_increment: int = 400,
                 min_increment: int = 200,
                 max_increment: int = 800,
                 adaptation_threshold: int = 3):
        super().__init__()
        self.current_increment = initial_increment
        self.min_increment = min_increment
        self.max_increment = max_increment
        self.adaptation_threshold = adaptation_threshold
        
        # Adaptive parameters
        self.no_content_iterations = 0
        self.fast_loading_iterations = 0
        self.slow_loading_iterations = 0
        
    def scroll(self, driver, iteration: int) -> bool:
        """Perform adaptive scrolling"""
        try:
            # Get current page state
            current_scroll = driver.run_js("return window.pageYOffset")
            page_height = driver.run_js("return document.body.scrollHeight")
            viewport_height = driver.run_js("return window.innerHeight")
            
            # Check if we've reached the bottom
            if current_scroll + viewport_height >= page_height - 50:
                logger.debug("Adaptive scroll: Reached bottom of page")
                return False
            
            # Record pre-scroll state
            pre_scroll_height = page_height
            pre_scroll_time = time.time()
            
            # Adapt scroll increment based on recent performance
            self._adapt_scroll_increment()
            
            # Perform adaptive scroll
            scroll_target = current_scroll + self.current_increment
            self._perform_adaptive_scroll(driver, scroll_target)
            
            # Wait and measure content loading
            loading_metrics = self._measure_content_loading(driver, pre_scroll_height, pre_scroll_time)
            
            # Update adaptation metrics
            self._update_adaptation_metrics(loading_metrics)
            
            # Track detailed metrics
            self.scroll_history.append({
                'iteration': iteration,
                'scroll_increment': self.current_increment,
                'loading_time': loading_metrics['loading_time'],
                'new_content_height': loading_metrics['new_content_height'],
                'adaptation_reason': loading_metrics.get('adaptation_reason', 'normal'),
                'timestamp': time.time()
            })
            
            logger.debug(f"Adaptive scroll iteration {iteration}: increment={self.current_increment}px, "
                        f"loading_time={loading_metrics['loading_time']:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in adaptive scroll iteration {iteration}: {e}")
            return False
    
    def _adapt_scroll_increment(self):
        """Adapt scroll increment based on recent performance"""
        # Increase increment if content loads quickly
        if self.fast_loading_iterations >= self.adaptation_threshold:
            self.current_increment = min(self.current_increment + 100, self.max_increment)
            self.fast_loading_iterations = 0
            logger.debug(f"Adapted: Increased scroll increment to {self.current_increment}px")
        
        # Decrease increment if content loads slowly or not at all
        elif (self.slow_loading_iterations >= self.adaptation_threshold or 
              self.no_content_iterations >= self.adaptation_threshold):
            self.current_increment = max(self.current_increment - 50, self.min_increment)
            self.slow_loading_iterations = 0
            self.no_content_iterations = 0
            logger.debug(f"Adapted: Decreased scroll increment to {self.current_increment}px")
    
    def _perform_adaptive_scroll(self, driver, target_position: int):
        """Perform scrolling with adaptive smoothness"""
        current_position = driver.run_js("return window.pageYOffset")
        distance = target_position - current_position
        
        # Use smooth scrolling for smaller increments, immediate for larger
        if distance < 300:
            # Smooth scroll for small distances
            steps = 5
            for i in range(steps):
                intermediate = current_position + (distance * (i + 1) / steps)
                driver.run_js(f"window.scrollTo(0, {intermediate})")
                time.sleep(0.1)
        else:
            # Immediate scroll for large distances
            driver.run_js(f"window.scrollTo(0, {target_position})")
    
    def _measure_content_loading(self, driver, pre_height: int, pre_time: float) -> Dict[str, Any]:
        """Measure content loading performance"""
        # Wait with progressive checking
        max_wait_time = 5.0
        check_interval = 0.5
        checks = 0
        max_checks = int(max_wait_time / check_interval)
        
        stable_height = pre_height
        
        while checks < max_checks:
            time.sleep(check_interval)
            current_height = driver.run_js("return document.body.scrollHeight")
            
            if current_height > stable_height:
                stable_height = current_height
                # Reset wait if new content appears
                checks = max(0, checks - 2)
            
            checks += 1
        
        loading_time = time.time() - pre_time
        new_content_height = stable_height - pre_height
        
        return {
            'loading_time': loading_time,
            'new_content_height': new_content_height,
            'final_height': stable_height
        }
    
    def _update_adaptation_metrics(self, loading_metrics: Dict[str, Any]):
        """Update metrics for adaptation logic"""
        loading_time = loading_metrics['loading_time']
        new_content = loading_metrics['new_content_height']
        
        # Classify loading performance
        if new_content == 0:
            self.no_content_iterations += 1
            self.fast_loading_iterations = 0
            self.slow_loading_iterations = 0
        elif loading_time < 1.5:
            self.fast_loading_iterations += 1
            self.no_content_iterations = 0
            self.slow_loading_iterations = 0
        elif loading_time > 3.0:
            self.slow_loading_iterations += 1
            self.no_content_iterations = 0
            self.fast_loading_iterations = 0
        else:
            # Normal loading - reset counters
            self.no_content_iterations = 0
            self.fast_loading_iterations = 0
            self.slow_loading_iterations = 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get detailed adaptive metrics"""
        base_metrics = super().get_metrics()
        
        adaptive_metrics = {
            'current_increment': self.current_increment,
            'no_content_iterations': self.no_content_iterations,
            'fast_loading_iterations': self.fast_loading_iterations,
            'slow_loading_iterations': self.slow_loading_iterations,
            'total_adaptations': len([h for h in self.scroll_history 
                                    if h.get('adaptation_reason', 'normal') != 'normal'])
        }
        
        base_metrics.update(adaptive_metrics)
        return base_metrics

class IntelligentScrollStrategy(BaseScrollStrategy):
    """
    Intelligent scrolling strategy
    Uses machine learning-like heuristics to optimize scrolling patterns
    """
    
    def __init__(self):
        super().__init__()
        self.content_patterns = []
        self.optimal_increments = []
        self.learning_phase = True
        self.learning_iterations = 5
    
    def scroll(self, driver, iteration: int) -> bool:
        """Perform intelligent scrolling with pattern learning"""
        try:
            # Learning phase: try different strategies
            if self.learning_phase and iteration <= self.learning_iterations:
                return self._learning_scroll(driver, iteration)
            else:
                # Exploitation phase: use learned optimal strategy
                return self._optimized_scroll(driver, iteration)
                
        except Exception as e:
            logger.error(f"Error in intelligent scroll iteration {iteration}: {e}")
            return False
    
    def _learning_scroll(self, driver, iteration: int) -> bool:
        """Learning phase to determine optimal scroll patterns"""
        # Try different scroll increments and measure effectiveness
        test_increments = [200, 350, 500, 700, 900]
        increment = test_increments[iteration % len(test_increments)]
        
        # Measure content loading efficiency
        start_time = time.time()
        pre_height = driver.run_js("return document.body.scrollHeight")
        current_scroll = driver.run_js("return window.pageYOffset")
        
        # Perform test scroll
        driver.run_js(f"window.scrollTo(0, {current_scroll + increment})")
        time.sleep(2)
        
        # Measure results
        post_height = driver.run_js("return document.body.scrollHeight")
        loading_time = time.time() - start_time
        content_efficiency = (post_height - pre_height) / loading_time if loading_time > 0 else 0
        
        # Store learning data
        self.content_patterns.append({
            'increment': increment,
            'content_efficiency': content_efficiency,
            'loading_time': loading_time,
            'iteration': iteration
        })
        
        logger.debug(f"Learning scroll {iteration}: increment={increment}, efficiency={content_efficiency:.2f}")
        
        # End learning phase
        if iteration >= self.learning_iterations:
            self._analyze_learning_results()
            self.learning_phase = False
        
        return True
    
    def _optimized_scroll(self, driver, iteration: int) -> bool:
        """Optimized scrolling based on learned patterns"""
        # Use the most efficient increment discovered
        optimal_increment = self._get_optimal_increment()
        
        current_scroll = driver.run_js("return window.pageYOffset")
        page_height = driver.run_js("return document.body.scrollHeight")
        viewport_height = driver.run_js("return window.innerHeight")
        
        # Check if reached bottom
        if current_scroll + viewport_height >= page_height - 50:
            return False
        
        # Perform optimized scroll
        driver.run_js(f"window.scrollTo(0, {current_scroll + optimal_increment})")
        
        # Adaptive wait based on learned timing
        optimal_wait = self._get_optimal_wait_time()
        time.sleep(optimal_wait)
        
        logger.debug(f"Optimized scroll {iteration}: increment={optimal_increment}, wait={optimal_wait:.2f}s")
        return True
    
    def _analyze_learning_results(self):
        """Analyze learning phase results to determine optimal strategy"""
        if not self.content_patterns:
            return
        
        # Find the increment with highest content efficiency
        best_pattern = max(self.content_patterns, key=lambda x: x['content_efficiency'])
        self.optimal_increments.append(best_pattern['increment'])
        
        logger.info(f"Learning complete: optimal increment = {best_pattern['increment']}px, "
                   f"efficiency = {best_pattern['content_efficiency']:.2f}")
    
    def _get_optimal_increment(self) -> int:
        """Get the optimal scroll increment based on learning"""
        if self.optimal_increments:
            return self.optimal_increments[-1]
        return 400  # Default fallback
    
    def _get_optimal_wait_time(self) -> float:
        """Get optimal wait time based on learned patterns"""
        if self.content_patterns:
            avg_loading_time = sum(p['loading_time'] for p in self.content_patterns) / len(self.content_patterns)
            return min(max(avg_loading_time * 0.8, 1.0), 4.0)  # 80% of avg, clamped between 1-4s
        return 2.0  # Default fallback
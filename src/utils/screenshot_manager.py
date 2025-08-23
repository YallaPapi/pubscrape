"""
Screenshot Manager for Real-Time Browser Monitoring
Captures and manages browser screenshots during scraping
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import base64
import io
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class ScreenshotManager:
    """Manages browser screenshot capture and storage"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("data/screenshots")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_dir = None
        self.screenshot_count = 0
        self.callbacks = []
        
    def start_session(self, session_id: str):
        """Start a new screenshot session"""
        self.session_dir = self.output_dir / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_count = 0
        
        logger.info(f"Started screenshot session: {session_id}")
    
    def add_callback(self, callback: Callable[[bytes, str], None]):
        """Add callback for screenshot events"""
        self.callbacks.append(callback)
    
    def capture_browser_screenshot(self, browser_page, context: str = "", save_file: bool = True) -> Optional[bytes]:
        """Capture screenshot from browser page"""
        try:
            # Take screenshot
            screenshot_bytes = browser_page.screenshot(full_page=True)
            
            if save_file and self.session_dir:
                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"screenshot_{self.screenshot_count:04d}_{timestamp}.png"
                filepath = self.session_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(screenshot_bytes)
                
                logger.info(f"Screenshot saved: {filepath}")
            
            self.screenshot_count += 1
            
            # Call callbacks
            for callback in self.callbacks:
                try:
                    callback(screenshot_bytes, context)
                except Exception as e:
                    logger.error(f"Screenshot callback error: {e}")
            
            return screenshot_bytes
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return None
    
    def capture_element_screenshot(self, element, context: str = "", save_file: bool = True) -> Optional[bytes]:
        """Capture screenshot of specific element"""
        try:
            screenshot_bytes = element.screenshot()
            
            if save_file and self.session_dir:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"element_{self.screenshot_count:04d}_{timestamp}.png"
                filepath = self.session_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(screenshot_bytes)
                
                logger.info(f"Element screenshot saved: {filepath}")
            
            self.screenshot_count += 1
            
            # Call callbacks
            for callback in self.callbacks:
                try:
                    callback(screenshot_bytes, f"element: {context}")
                except Exception as e:
                    logger.error(f"Element screenshot callback error: {e}")
            
            return screenshot_bytes
            
        except Exception as e:
            logger.error(f"Error capturing element screenshot: {e}")
            return None
    
    def create_comparison_image(self, before_bytes: bytes, after_bytes: bytes, 
                               context: str = "") -> Optional[bytes]:
        """Create side-by-side comparison image"""
        try:
            # Load images
            before_img = Image.open(io.BytesIO(before_bytes))
            after_img = Image.open(io.BytesIO(after_bytes))
            
            # Resize to same height
            height = min(before_img.height, after_img.height)
            before_ratio = before_img.width / before_img.height
            after_ratio = after_img.width / after_img.height
            
            before_width = int(height * before_ratio)
            after_width = int(height * after_ratio)
            
            before_resized = before_img.resize((before_width, height))
            after_resized = after_img.resize((after_width, height))
            
            # Create combined image
            total_width = before_width + after_width + 20  # 20px separator
            combined_img = Image.new('RGB', (total_width, height), color='white')
            
            combined_img.paste(before_resized, (0, 0))
            combined_img.paste(after_resized, (before_width + 20, 0))
            
            # Save combined image
            output = io.BytesIO()
            combined_img.save(output, format='PNG')
            combined_bytes = output.getvalue()
            
            if self.session_dir:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"comparison_{self.screenshot_count:04d}_{timestamp}.png"
                filepath = self.session_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(combined_bytes)
                
                logger.info(f"Comparison screenshot saved: {filepath}")
            
            self.screenshot_count += 1
            
            # Call callbacks
            for callback in self.callbacks:
                try:
                    callback(combined_bytes, f"comparison: {context}")
                except Exception as e:
                    logger.error(f"Comparison screenshot callback error: {e}")
            
            return combined_bytes
            
        except Exception as e:
            logger.error(f"Error creating comparison image: {e}")
            return None
    
    def get_session_screenshots(self) -> list:
        """Get list of all screenshots in current session"""
        if not self.session_dir or not self.session_dir.exists():
            return []
        
        screenshots = []
        for file_path in sorted(self.session_dir.glob("*.png")):
            screenshots.append({
                "filename": file_path.name,
                "filepath": str(file_path),
                "timestamp": datetime.fromtimestamp(file_path.stat().st_mtime),
                "size": file_path.stat().st_size
            })
        
        return screenshots
    
    def cleanup_session(self):
        """Clean up current session"""
        self.session_dir = None
        self.screenshot_count = 0
        logger.info("Screenshot session cleaned up")

class LiveScreenshotStream:
    """Stream screenshots in real-time to dashboard"""
    
    def __init__(self, dashboard_callback: Optional[Callable] = None):
        self.dashboard_callback = dashboard_callback
        self.is_streaming = False
        self.stream_interval = 2.0  # seconds
        
    def start_streaming(self, browser_page):
        """Start streaming screenshots"""
        self.is_streaming = True
        
        def stream_worker():
            while self.is_streaming:
                try:
                    # Capture screenshot
                    screenshot_bytes = browser_page.screenshot()
                    
                    if self.dashboard_callback:
                        self.dashboard_callback(screenshot_bytes, "live_stream")
                    
                    time.sleep(self.stream_interval)
                    
                except Exception as e:
                    logger.error(f"Error in screenshot stream: {e}")
                    break
        
        import threading
        stream_thread = threading.Thread(target=stream_worker, daemon=True)
        stream_thread.start()
        
        logger.info("Started live screenshot streaming")
    
    def stop_streaming(self):
        """Stop streaming screenshots"""
        self.is_streaming = False
        logger.info("Stopped live screenshot streaming")
    
    def set_interval(self, interval: float):
        """Set streaming interval in seconds"""
        self.stream_interval = max(0.5, interval)  # Minimum 0.5 seconds

class ScreenshotAnnotator:
    """Add annotations to screenshots for better context"""
    
    def __init__(self):
        self.font_size = 20
        self.font_color = (255, 0, 0)  # Red
    
    def annotate_screenshot(self, screenshot_bytes: bytes, annotations: list) -> bytes:
        """Add text annotations to screenshot"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Load image
            img = Image.open(io.BytesIO(screenshot_bytes))
            draw = ImageDraw.Draw(img)
            
            # Try to load a font
            try:
                font = ImageFont.truetype("arial.ttf", self.font_size)
            except:
                font = ImageFont.load_default()
            
            # Add annotations
            y_offset = 10
            for annotation in annotations:
                text = annotation.get('text', '')
                x = annotation.get('x', 10)
                y = annotation.get('y', y_offset)
                color = annotation.get('color', self.font_color)
                
                # Add background rectangle for better readability
                bbox = draw.textbbox((x, y), text, font=font)
                draw.rectangle(bbox, fill=(255, 255, 255, 128))
                
                # Add text
                draw.text((x, y), text, fill=color, font=font)
                y_offset += self.font_size + 5
            
            # Save annotated image
            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error annotating screenshot: {e}")
            return screenshot_bytes
    
    def highlight_elements(self, screenshot_bytes: bytes, elements: list) -> bytes:
        """Highlight specific elements in screenshot"""
        try:
            from PIL import Image, ImageDraw
            
            img = Image.open(io.BytesIO(screenshot_bytes))
            draw = ImageDraw.Draw(img)
            
            for element in elements:
                x = element.get('x', 0)
                y = element.get('y', 0)
                width = element.get('width', 50)
                height = element.get('height', 20)
                color = element.get('color', (255, 0, 0))  # Red
                
                # Draw rectangle around element
                draw.rectangle([x, y, x + width, y + height], 
                             outline=color, width=3)
                
                # Add label if provided
                if 'label' in element:
                    draw.text((x, y - 20), element['label'], fill=color)
            
            # Save highlighted image
            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error highlighting elements: {e}")
            return screenshot_bytes
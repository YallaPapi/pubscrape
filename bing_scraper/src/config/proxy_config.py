"""Proxy configuration for Bing Scraper."""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass

@dataclass
class ProxyConfig:
    """Proxy configuration settings."""
    
    enabled: bool = False
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: str = "http"
    
    # Residential proxy pool settings
    residential_endpoint: Optional[str] = None
    residential_username: Optional[str] = None
    residential_password: Optional[str] = None
    
    def __post_init__(self):
        """Validate proxy configuration."""
        if self.enabled and not self.host:
            raise ValueError("Proxy host must be provided when proxy is enabled")
        
        if self.enabled and not self.port:
            raise ValueError("Proxy port must be provided when proxy is enabled")
    
    def get_proxy_dict(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration as dictionary for requests."""
        if not self.enabled:
            return None
        
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        else:
            auth = ""
        
        proxy_url = f"{self.proxy_type}://{auth}{self.host}:{self.port}"
        
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    
    def get_selenium_proxy_args(self) -> List[str]:
        """Get proxy arguments for Selenium/Chrome."""
        if not self.enabled:
            return []
        
        args = [f"--proxy-server={self.proxy_type}://{self.host}:{self.port}"]
        
        if self.username and self.password:
            args.append(f"--proxy-auth={self.username}:{self.password}")
        
        return args
    
    @classmethod
    def from_settings(cls, settings) -> 'ProxyConfig':
        """Create ProxyConfig from Settings object."""
        return cls(
            enabled=settings.proxy_enabled,
            host=settings.proxy_host,
            port=settings.proxy_port,
            username=settings.proxy_username,
            password=settings.proxy_password,
            proxy_type=settings.proxy_type,
            residential_endpoint=settings.residential_proxy_endpoint,
            residential_username=settings.residential_proxy_username,
            residential_password=settings.residential_proxy_password
        )
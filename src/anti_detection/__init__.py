"""
Anti-Detection System

Comprehensive anti-detection and stealth web scraping framework with:
- Advanced user agent rotation
- Proxy management and rotation
- Human behavior simulation
- Adaptive rate limiting with exponential backoff
- Session management and cookie persistence
- Detection evasion for Cloudflare, reCAPTCHA, and other systems
"""

from .stealth_manager import (
    StealthManager,
    StealthConfig,
    StealthLevel,
    DetectionRisk,
    SessionMetrics,
    create_stealth_manager
)

from .proxy_rotator import (
    ProxyRotator,
    ProxyInfo,
    ProxyType,
    ProxyStatus,
    ProxyProvider,
    RotationConfig,
    create_proxy_rotator
)

from .behavior_simulator import (
    BehaviorSimulator,
    BehaviorConfig,
    BehaviorProfile,
    BehaviorType,
    IntensityLevel,
    create_behavior_simulator
)

from .rate_limiter import (
    AdaptiveRateLimiter,
    RateLimitConfig,
    RequestStatus,
    CircuitState,
    RateLimitPolicy,
    create_adaptive_rate_limiter
)

# Version info
__version__ = "1.0.0"
__author__ = "Anti-Detection System"
__email__ = "contact@anti-detection.dev"

# Main exports
__all__ = [
    # Stealth Manager
    "StealthManager",
    "StealthConfig", 
    "StealthLevel",
    "DetectionRisk",
    "SessionMetrics",
    "create_stealth_manager",
    
    # Proxy System
    "ProxyRotator",
    "ProxyInfo",
    "ProxyType",
    "ProxyStatus", 
    "ProxyProvider",
    "RotationConfig",
    "create_proxy_rotator",
    
    # Behavior Simulation
    "BehaviorSimulator",
    "BehaviorConfig",
    "BehaviorProfile",
    "BehaviorType",
    "IntensityLevel", 
    "create_behavior_simulator",
    
    # Rate Limiting
    "AdaptiveRateLimiter",
    "RateLimitConfig",
    "RequestStatus",
    "CircuitState",
    "RateLimitPolicy",
    "create_adaptive_rate_limiter",
]


def create_anti_detection_system(config_file: str = None, **kwargs):
    """
    Create a complete anti-detection system with all components
    
    Args:
        config_file: Path to YAML configuration file
        **kwargs: Override configuration options
        
    Returns:
        Configured StealthManager instance
    """
    import yaml
    from pathlib import Path
    
    # Load configuration
    config = {}
    if config_file:
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
    
    # Apply overrides
    config.update(kwargs)
    
    # Create stealth configuration
    stealth_config = StealthConfig()
    
    if 'global' in config:
        global_config = config['global']
        if 'stealth_level' in global_config:
            stealth_config.stealth_level = StealthLevel(global_config['stealth_level'])
    
    if 'proxies' in config and config['proxies'].get('enabled', False):
        stealth_config.use_proxies = True
    
    if 'behavior_simulation' in config:
        behavior_config = config['behavior_simulation']
        stealth_config.simulate_human_behavior = behavior_config.get('enabled', True)
        if 'intensity' in behavior_config:
            intensity_map = {
                'minimal': IntensityLevel.MINIMAL,
                'low': IntensityLevel.LOW, 
                'medium': IntensityLevel.MEDIUM,
                'high': IntensityLevel.HIGH,
                'maximum': IntensityLevel.MAXIMUM
            }
            stealth_config.intensity = intensity_map.get(
                behavior_config['intensity'], 
                IntensityLevel.MEDIUM
            )
    
    return create_stealth_manager(
        stealth_level=stealth_config.stealth_level,
        use_proxies=stealth_config.use_proxies,
        simulate_behavior=stealth_config.simulate_human_behavior
    )


# Convenience imports for backward compatibility
StealthSystem = StealthManager
AntiDetection = StealthManager
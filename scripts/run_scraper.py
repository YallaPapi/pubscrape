#!/usr/bin/env python3
"""
VRSEN PubScrape Runner Script

Intelligent wrapper script with smart defaults, environment detection,
and automated setup for the VRSEN PubScrape platform.

Features:
- Automatic environment detection and configuration
- Intelligent defaults based on campaign type
- Pre-flight checks and validation
- Resource monitoring and optimization
- Automatic retry and recovery
- Progress tracking and reporting
"""

import os
import sys
import argparse
import asyncio
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import shutil
import psutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config_manager import config_manager
from src.utils.logger import setup_logging, get_logger
from src.utils.error_handler import ErrorHandler


class EnvironmentDetector:
    """Detect and configure environment settings"""
    
    def __init__(self):
        self.logger = get_logger("environment_detector")
    
    def detect_environment(self) -> str:
        """Detect current environment"""
        # Check environment variable
        env = os.getenv("VRSEN_ENV", "").lower()
        if env in ["development", "staging", "production"]:
            return env
        
        # Check if in Docker
        if os.path.exists("/.dockerenv"):
            return "production"
        
        # Check for development indicators
        dev_indicators = [
            Path("venv"),
            Path(".git"),
            Path("requirements-dev.txt"),
            Path("pytest.ini")
        ]
        
        if any(indicator.exists() for indicator in dev_indicators):
            return "development"
        
        return "production"
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system resource information"""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_free_gb": round(shutil.disk_usage(".").free / (1024**3), 2),
                "platform": sys.platform,
                "python_version": sys.version
            }
        except Exception as e:
            self.logger.warning(f"Could not get system info: {e}")
            return {}
    
    def optimize_config_for_system(self, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize configuration based on system resources"""
        optimizations = {}
        
        # CPU-based optimizations
        cpu_count = system_info.get("cpu_count", 4)
        optimizations["search.max_concurrent_searches"] = min(cpu_count, 8)
        optimizations["processing.max_workers"] = min(cpu_count * 2, 16)
        optimizations["crawling.concurrent_crawlers"] = min(cpu_count, 6)
        
        # Memory-based optimizations
        memory_gb = system_info.get("memory_gb", 8)
        if memory_gb < 4:
            optimizations["processing.batch_size"] = 50
            optimizations["performance.cache_size_mb"] = 256
            optimizations["search.max_pages_per_query"] = 3
        elif memory_gb < 8:
            optimizations["processing.batch_size"] = 100
            optimizations["performance.cache_size_mb"] = 512
        else:
            optimizations["processing.batch_size"] = 200
            optimizations["performance.cache_size_mb"] = 1024
        
        # Disk-based optimizations
        disk_free_gb = system_info.get("disk_free_gb", 10)
        if disk_free_gb < 5:
            optimizations["export.compress_output"] = True
            optimizations["export.auto_cleanup_days"] = 7
            optimizations["performance.disk_cache_enabled"] = False
        
        return optimizations


class CampaignIntelligence:
    """Intelligent campaign analysis and optimization"""
    
    def __init__(self):
        self.logger = get_logger("campaign_intelligence")
    
    def analyze_campaign(self, campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze campaign and suggest optimizations"""
        analysis = {
            "estimated_duration": "unknown",
            "resource_requirements": "medium",
            "suggested_settings": {},
            "warnings": [],
            "recommendations": []
        }
        
        # Analyze campaign type and size
        campaign_type = campaign_config.get("type", "general")
        target_count = campaign_config.get("target_leads", 100)
        
        # Estimate duration based on targets
        if target_count <= 50:
            analysis["estimated_duration"] = "5-15 minutes"
            analysis["resource_requirements"] = "low"
        elif target_count <= 200:
            analysis["estimated_duration"] = "15-45 minutes"
            analysis["resource_requirements"] = "medium"
        elif target_count <= 500:
            analysis["estimated_duration"] = "45-120 minutes"
            analysis["resource_requirements"] = "high"
        else:
            analysis["estimated_duration"] = "2+ hours"
            analysis["resource_requirements"] = "very high"
            analysis["warnings"].append("Large campaign detected - consider running in batches")
        
        # Campaign-specific optimizations
        if campaign_type == "doctor":
            analysis["suggested_settings"] = {
                "search.rate_limit_rpm": 8,  # Medical sites often have stricter limits
                "crawling.delay_between_requests": 2.0,
                "processing.validation_enabled": True
            }
            analysis["recommendations"].append("Medical lead generation requires careful rate limiting")
        
        elif campaign_type == "lawyer":
            analysis["suggested_settings"] = {
                "search.rate_limit_rpm": 10,
                "processing.email_validation_level": "strict",
                "crawling.respect_robots_txt": True
            }
            analysis["recommendations"].append("Legal professionals require high-quality validation")
        
        elif campaign_type == "restaurant":
            analysis["suggested_settings"] = {
                "search.max_pages_per_query": 3,  # Local businesses
                "crawling.max_pages_per_site": 5,
                "processing.phone_validation_enabled": True
            }
            analysis["recommendations"].append("Restaurant leads benefit from phone validation")
        
        # Check for potential issues
        if not campaign_config.get("queries"):
            analysis["warnings"].append("No search queries defined")
        
        if not campaign_config.get("regions"):
            analysis["warnings"].append("No target regions specified")
        
        return analysis


class PreflightChecker:
    """Comprehensive pre-flight checks"""
    
    def __init__(self):
        self.logger = get_logger("preflight_checker")
        self.error_handler = ErrorHandler()
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all pre-flight checks"""
        results = {
            "overall_status": "unknown",
            "checks": {},
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        checks = [
            ("api_keys", self._check_api_keys),
            ("dependencies", self._check_dependencies),
            ("directories", self._check_directories),
            ("permissions", self._check_permissions),
            ("network", self._check_network),
            ("disk_space", self._check_disk_space),
            ("memory", self._check_memory)
        ]
        
        passed_checks = 0
        total_checks = len(checks)
        
        for check_name, check_func in checks:
            try:
                check_result = await check_func()
                results["checks"][check_name] = check_result
                
                if check_result["status"] == "pass":
                    passed_checks += 1
                elif check_result["status"] == "warning":
                    results["warnings"].extend(check_result.get("messages", []))
                elif check_result["status"] == "fail":
                    results["errors"].extend(check_result.get("messages", []))
                
            except Exception as e:
                self.logger.error(f"Check {check_name} failed: {e}")
                results["checks"][check_name] = {
                    "status": "error",
                    "messages": [f"Check failed: {e}"]
                }
        
        # Determine overall status
        if results["errors"]:
            results["overall_status"] = "fail"
        elif results["warnings"]:
            results["overall_status"] = "warning"
        else:
            results["overall_status"] = "pass"
        
        results["score"] = f"{passed_checks}/{total_checks}"
        
        return results
    
    async def _check_api_keys(self) -> Dict[str, Any]:
        """Check API keys availability"""
        required_keys = ["OPENAI_API_KEY"]
        optional_keys = ["BING_API_KEY", "HUNTER_API_KEY", "MAILTESTER_API_KEY"]
        
        missing_required = []
        missing_optional = []
        
        for key in required_keys:
            if not os.getenv(key):
                missing_required.append(key)
        
        for key in optional_keys:
            if not os.getenv(key):
                missing_optional.append(key)
        
        if missing_required:
            return {
                "status": "fail",
                "messages": [f"Missing required API keys: {', '.join(missing_required)}"]
            }
        elif missing_optional:
            return {
                "status": "warning",
                "messages": [f"Missing optional API keys: {', '.join(missing_optional)}"]
            }
        else:
            return {"status": "pass", "messages": ["All API keys available"]}
    
    async def _check_dependencies(self) -> Dict[str, Any]:
        """Check Python dependencies"""
        try:
            import botasaurus
            import agency_swarm
            import selenium
            import requests
            import beautifulsoup4
            return {"status": "pass", "messages": ["All dependencies available"]}
        except ImportError as e:
            return {
                "status": "fail",
                "messages": [f"Missing dependency: {e}"]
            }
    
    async def _check_directories(self) -> Dict[str, Any]:
        """Check required directories"""
        directories = ["output", "logs", "cache", "data", "state"]
        issues = []
        
        for dir_name in directories:
            dir_path = Path(dir_name)
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot create {dir_name}: {e}")
        
        if issues:
            return {"status": "fail", "messages": issues}
        else:
            return {"status": "pass", "messages": ["All directories accessible"]}
    
    async def _check_permissions(self) -> Dict[str, Any]:
        """Check file permissions"""
        test_file = Path("output/.permission_test")
        try:
            test_file.write_text("test")
            test_file.unlink()
            return {"status": "pass", "messages": ["File permissions OK"]}
        except Exception as e:
            return {"status": "fail", "messages": [f"Permission error: {e}"]}
    
    async def _check_network(self) -> Dict[str, Any]:
        """Check network connectivity"""
        try:
            import requests
            response = requests.get("https://www.bing.com", timeout=10)
            if response.status_code == 200:
                return {"status": "pass", "messages": ["Network connectivity OK"]}
            else:
                return {"status": "warning", "messages": ["Network connectivity issues"]}
        except Exception as e:
            return {"status": "fail", "messages": [f"Network error: {e}"]}
    
    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space"""
        try:
            free_space_gb = shutil.disk_usage(".").free / (1024**3)
            if free_space_gb < 1:
                return {"status": "fail", "messages": ["Less than 1GB disk space available"]}
            elif free_space_gb < 5:
                return {"status": "warning", "messages": [f"Low disk space: {free_space_gb:.1f}GB"]}
            else:
                return {"status": "pass", "messages": [f"Disk space OK: {free_space_gb:.1f}GB"]}
        except Exception as e:
            return {"status": "warning", "messages": [f"Cannot check disk space: {e}"]}
    
    async def _check_memory(self) -> Dict[str, Any]:
        """Check available memory"""
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            if available_gb < 1:
                return {"status": "fail", "messages": ["Less than 1GB memory available"]}
            elif available_gb < 2:
                return {"status": "warning", "messages": [f"Low memory: {available_gb:.1f}GB"]}
            else:
                return {"status": "pass", "messages": [f"Memory OK: {available_gb:.1f}GB"]}
        except Exception as e:
            return {"status": "warning", "messages": [f"Cannot check memory: {e}"]}


class ScraperRunner:
    """Main scraper runner with intelligence and automation"""
    
    def __init__(self):
        self.logger = None
        self.env_detector = EnvironmentDetector()
        self.campaign_intelligence = CampaignIntelligence()
        self.preflight_checker = PreflightChecker()
    
    async def run(self, args: argparse.Namespace) -> int:
        """Main runner entry point"""
        try:
            # Setup logging first
            self.logger = setup_logging(
                level=args.log_level,
                enable_console=not args.quiet,
                enable_file=True
            )
            
            self.logger.info("🚀 VRSEN PubScrape Runner starting...")
            
            # Environment detection
            environment = self.env_detector.detect_environment()
            self.logger.info(f"📊 Environment detected: {environment}")
            
            # System analysis
            system_info = self.env_detector.get_system_info()
            self.logger.info(f"💻 System: {system_info.get('cpu_count', 'unknown')} CPU, "
                           f"{system_info.get('memory_gb', 'unknown')}GB RAM")
            
            # Pre-flight checks
            if not args.skip_checks:
                self.logger.info("🔍 Running pre-flight checks...")
                check_results = await self.preflight_checker.run_checks()
                
                if check_results["overall_status"] == "fail":
                    self.logger.error("❌ Pre-flight checks failed:")
                    for error in check_results["errors"]:
                        self.logger.error(f"   • {error}")
                    return 1
                elif check_results["overall_status"] == "warning":
                    self.logger.warning("⚠️  Pre-flight checks passed with warnings:")
                    for warning in check_results["warnings"]:
                        self.logger.warning(f"   • {warning}")
                else:
                    self.logger.info("✅ All pre-flight checks passed")
            
            # Load and analyze campaign
            campaign_config = self._load_campaign_config(args.campaign)
            if not campaign_config:
                return 1
            
            # Campaign intelligence
            analysis = self.campaign_intelligence.analyze_campaign(campaign_config)
            self.logger.info(f"📋 Campaign analysis:")
            self.logger.info(f"   • Estimated duration: {analysis['estimated_duration']}")
            self.logger.info(f"   • Resource requirements: {analysis['resource_requirements']}")
            
            if analysis["warnings"]:
                for warning in analysis["warnings"]:
                    self.logger.warning(f"   ⚠️  {warning}")
            
            if analysis["recommendations"]:
                for rec in analysis["recommendations"]:
                    self.logger.info(f"   💡 {rec}")
            
            # Apply optimizations
            optimizations = self.env_detector.optimize_config_for_system(system_info)
            optimizations.update(analysis["suggested_settings"])
            
            self._apply_optimizations(optimizations)
            
            # Run the actual scraper
            self.logger.info("🎯 Starting scraping campaign...")
            
            # Import and run main application
            from main import CLIApplication
            
            app = CLIApplication()
            if not app.initialize(args):
                return 1
            
            result = await app.run_scrape_command(args)
            
            if result == 0:
                self.logger.info("✅ Campaign completed successfully!")
            else:
                self.logger.error("❌ Campaign failed")
            
            return result
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Runner failed: {e}", exc_info=True)
            else:
                print(f"❌ Runner failed: {e}")
            return 1
    
    def _load_campaign_config(self, campaign_path: str) -> Optional[Dict[str, Any]]:
        """Load campaign configuration with intelligent defaults"""
        if not campaign_path:
            # Generate default campaign
            return self._generate_default_campaign()
        
        try:
            path = Path(campaign_path)
            if not path.exists():
                self.logger.error(f"Campaign file not found: {campaign_path}")
                return None
            
            with open(path, 'r') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    config = json.load(f)
                else:
                    self.logger.error(f"Unsupported campaign format: {path.suffix}")
                    return None
            
            # Validate and enhance config
            return self._enhance_campaign_config(config)
            
        except Exception as e:
            self.logger.error(f"Failed to load campaign: {e}")
            return None
    
    def _generate_default_campaign(self) -> Dict[str, Any]:
        """Generate a sensible default campaign"""
        return {
            "name": "Default Campaign",
            "type": "general",
            "target_leads": 50,
            "queries": [
                "business email contact information",
                "company contact details"
            ],
            "regions": ["United States"],
            "filters": {
                "email_required": True,
                "phone_preferred": False
            }
        }
    
    def _enhance_campaign_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance campaign config with intelligent defaults"""
        # Set defaults
        config.setdefault("target_leads", 100)
        config.setdefault("type", "general")
        config.setdefault("regions", ["United States"])
        
        # Validate queries
        if not config.get("queries"):
            config["queries"] = ["business contact information"]
        
        return config
    
    def _apply_optimizations(self, optimizations: Dict[str, str]):
        """Apply configuration optimizations"""
        for key_path, value in optimizations.items():
            try:
                config_manager.set(key_path, value)
                self.logger.debug(f"Applied optimization: {key_path} = {value}")
            except Exception as e:
                self.logger.warning(f"Failed to apply optimization {key_path}: {e}")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with intelligent defaults"""
    parser = argparse.ArgumentParser(
        description="VRSEN PubScrape Runner - Intelligent Web Scraping Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Quick start with defaults
    python scripts/run_scraper.py
    
    # Run specific campaign
    python scripts/run_scraper.py --campaign campaigns/doctors.yaml
    
    # High-volume campaign
    python scripts/run_scraper.py --campaign campaigns/lawyers.yaml --targets 500
    
    # Debug mode
    python scripts/run_scraper.py --debug --verbose
    
    # Production mode with monitoring
    python scripts/run_scraper.py --campaign campaigns/production.yaml --monitor
        """
    )
    
    # Campaign settings
    parser.add_argument(
        "--campaign", "-c",
        help="Campaign configuration file (auto-generates if not specified)"
    )
    parser.add_argument(
        "--targets", "-t", type=int,
        help="Target number of leads (overrides campaign config)"
    )
    parser.add_argument(
        "--type", choices=["doctor", "lawyer", "restaurant", "general"],
        help="Campaign type for intelligent optimization"
    )
    
    # Execution settings
    parser.add_argument(
        "--resume", 
        help="Resume from session ID"
    )
    parser.add_argument(
        "--max-pages", type=int,
        help="Maximum pages per query"
    )
    parser.add_argument(
        "--rate-limit", type=int,
        help="Rate limit (requests per minute)"
    )
    
    # System settings
    parser.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO", help="Logging level"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Quiet mode (minimal output)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Debug mode with detailed logging"
    )
    
    # Control options
    parser.add_argument(
        "--skip-checks", action="store_true",
        help="Skip pre-flight checks"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulate execution without actual scraping"
    )
    parser.add_argument(
        "--monitor", action="store_true",
        help="Enable real-time monitoring"
    )
    
    # Output settings
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory for results"
    )
    parser.add_argument(
        "--format", choices=["csv", "json", "xlsx"],
        default="csv", help="Output format"
    )
    
    return parser


async def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Adjust log level based on flags
    if args.debug:
        args.log_level = "DEBUG"
    elif args.verbose:
        args.log_level = "INFO"
    elif args.quiet:
        args.log_level = "WARNING"
    
    # Create and run scraper
    runner = ScraperRunner()
    exit_code = await runner.run(args)
    
    return exit_code


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
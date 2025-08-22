#!/usr/bin/env python3
"""
Startup script for VRSEN Lead Generation Integrated Backend
Handles initialization, database setup, and server startup
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
import uvicorn
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our integrated backend
from database import db_manager, Base
from integrated_backend import app

def setup_logging():
    """Setup comprehensive logging"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f"integrated_backend_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def setup_database():
    """Initialize database and create tables"""
    logger = logging.getLogger(__name__)
    
    try:
        # Create database tables
        db_manager.create_tables()
        logger.info("Database tables created/verified successfully")
        
        # Test database connection
        session = db_manager.get_session()
        try:
            # Simple query to test connection
            from database.models import CampaignModel
            count = session.query(CampaignModel).count()
            logger.info(f"Database connection successful. Found {count} existing campaigns.")
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise

def check_dependencies():
    """Check if all required dependencies are installed"""
    logger = logging.getLogger(__name__)
    
    required_modules = [
        'fastapi',
        'uvicorn', 
        'sqlalchemy',
        'botasaurus',
        'aiohttp',
        'pydantic'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        logger.error(f"Missing required modules: {', '.join(missing_modules)}")
        logger.error("Install with: pip install -r integrated_requirements.txt")
        sys.exit(1)
    
    logger.info("All required dependencies are available")

def setup_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "campaign_output",
        "exports",
        "temp"
    ]
    
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)

def load_environment():
    """Load environment variables"""
    from dotenv import load_dotenv
    
    # Load from .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
        logging.getLogger(__name__).info("Environment variables loaded from .env file")
    
    # Check for required environment variables
    optional_vars = {
        'MAILTESTER_API_KEY': 'Email validation will use fallback method',
        'OPENAI_API_KEY': 'AI features may be limited',
        'DATABASE_URL': 'Will use default SQLite database'
    }
    
    logger = logging.getLogger(__name__)
    for var, fallback_message in optional_vars.items():
        if not os.getenv(var):
            logger.warning(f"{var} not set - {fallback_message}")

def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                    VRSEN LEAD GENERATION SYSTEM                  ║
    ║                      Integrated Backend v2.0                    ║
    ║                                                                  ║
    ║  Features:                                                       ║
    ║  • Real-time campaign execution with WebSocket updates          ║
    ║  • SQLite database with full lead management                    ║
    ║  • Mailtester Ninja email validation integration               ║
    ║  • CSV export and file download functionality                  ║
    ║  • Production-ready FastAPI backend                            ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Main startup function"""
    print_banner()
    
    # Setup logging first
    logger = setup_logging()
    logger.info("Starting VRSEN Lead Generation Integrated Backend")
    
    try:
        # Check dependencies
        check_dependencies()
        
        # Load environment
        load_environment()
        
        # Setup directories
        setup_directories()
        logger.info("Directory structure created")
        
        # Setup database
        setup_database()
        
        # Get server configuration
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 8000))
        reload = os.getenv('RELOAD', 'true').lower() == 'true'
        log_level = os.getenv('LOG_LEVEL', 'info').lower()
        
        logger.info(f"Starting server on http://{host}:{port}")
        logger.info(f"Reload: {reload}, Log Level: {log_level}")
        
        # Print helpful information
        print(f"""
Server Configuration:
  • Host: {host}
  • Port: {port}
  • Reload: {reload}
  • Log Level: {log_level}
  
API Endpoints:
  • Health Check: http://{host}:{port}/api/health
  • API Documentation: http://{host}:{port}/docs
  • WebSocket: ws://{host}:{port}/ws
  
Frontend Integration:
  • Set VITE_API_BASE_URL=http://{host}:{port}/api
  • Start your React frontend on port 5173
        """)
        
        # Start the server
        uvicorn.run(
            "integrated_backend:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=True,
            reload_dirs=[str(project_root)] if reload else None
        )
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Setup script for VRSEN Lead Generation Frontend
This script sets up both the React frontend and FastAPI backend for development
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, cwd=None, check=True):
    """Run a shell command and handle errors"""
    print(f"Running: {command}")
    try:
        if platform.system() == "Windows":
            result = subprocess.run(command, shell=True, cwd=cwd, check=check, capture_output=True, text=True)
        else:
            result = subprocess.run(command.split(), cwd=cwd, check=check, capture_output=True, text=True)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr and check:
            print(f"Warning: {result.stderr}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False

def check_prerequisites():
    """Check if required tools are installed"""
    print("🔍 Checking prerequisites...")
    
    # Check Node.js
    if not run_command("node --version", check=False):
        print("❌ Node.js is not installed. Please install Node.js 18+ from https://nodejs.org/")
        return False
    
    # Check npm
    if not run_command("npm --version", check=False):
        print("❌ npm is not installed. Please install npm.")
        return False
    
    # Check Python
    if not run_command("python --version", check=False):
        if not run_command("python3 --version", check=False):
            print("❌ Python is not installed. Please install Python 3.8+")
            return False
    
    print("✅ All prerequisites are installed")
    return True

def setup_backend():
    """Set up the FastAPI backend"""
    print("\n🐍 Setting up FastAPI backend...")
    
    # Check if virtual environment exists
    venv_dir = Path("venv")
    if not venv_dir.exists():
        print("Creating Python virtual environment...")
        if not run_command("python -m venv venv"):
            if not run_command("python3 -m venv venv"):
                print("❌ Failed to create virtual environment")
                return False
    
    # Activate virtual environment and install requirements
    if platform.system() == "Windows":
        activate_cmd = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
    else:
        activate_cmd = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
    
    print("Installing backend dependencies...")
    if not run_command(f"{pip_cmd} install -r backend_requirements.txt"):
        print("❌ Failed to install backend dependencies")
        return False
    
    print("✅ Backend setup complete")
    return True

def setup_frontend():
    """Set up the React frontend"""
    print("\n⚛️  Setting up React frontend...")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False
    
    # Install npm dependencies
    print("Installing frontend dependencies...")
    if not run_command("npm install", cwd=frontend_dir):
        print("❌ Failed to install frontend dependencies")
        return False
    
    # Create .env file if it doesn't exist
    env_file = frontend_dir / ".env"
    if not env_file.exists():
        env_example = frontend_dir / ".env.example"
        if env_example.exists():
            print("Creating .env file from .env.example...")
            with open(env_example, 'r') as src, open(env_file, 'w') as dst:
                dst.write(src.read())
        else:
            print("Creating default .env file...")
            with open(env_file, 'w') as f:
                f.write("VITE_API_BASE_URL=http://localhost:8000/api\n")
                f.write("VITE_WS_URL=ws://localhost:8000/ws\n")
                f.write("VITE_APP_ENV=development\n")
    
    print("✅ Frontend setup complete")
    return True

def create_start_scripts():
    """Create convenient start scripts"""
    print("\n📝 Creating start scripts...")
    
    # Windows batch files
    with open("start_backend.bat", "w") as f:
        f.write("@echo off\n")
        f.write("echo Starting VRSEN Backend API...\n")
        f.write("venv\\Scripts\\activate\n")
        f.write("python backend_api.py\n")
        f.write("pause\n")
    
    with open("start_frontend.bat", "w") as f:
        f.write("@echo off\n")
        f.write("echo Starting VRSEN Frontend...\n")
        f.write("cd frontend\n")
        f.write("npm run dev\n")
        f.write("pause\n")
    
    with open("start_all.bat", "w") as f:
        f.write("@echo off\n")
        f.write("echo Starting VRSEN Lead Generation System...\n")
        f.write("start \"Backend API\" start_backend.bat\n")
        f.write("timeout /t 3\n")
        f.write("start \"Frontend\" start_frontend.bat\n")
        f.write("echo Both services starting...\n")
        f.write("echo Backend: http://localhost:8000\n")
        f.write("echo Frontend: http://localhost:5173\n")
        f.write("pause\n")
    
    # Unix shell scripts
    with open("start_backend.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write("echo 'Starting VRSEN Backend API...'\n")
        f.write("source venv/bin/activate\n")
        f.write("python backend_api.py\n")
    
    with open("start_frontend.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write("echo 'Starting VRSEN Frontend...'\n")
        f.write("cd frontend\n")
        f.write("npm run dev\n")
    
    with open("start_all.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write("echo 'Starting VRSEN Lead Generation System...'\n")
        f.write("./start_backend.sh &\n")
        f.write("sleep 3\n")
        f.write("./start_frontend.sh &\n")
        f.write("echo 'Both services starting...'\n")
        f.write("echo 'Backend: http://localhost:8000'\n")
        f.write("echo 'Frontend: http://localhost:5173'\n")
        f.write("wait\n")
    
    # Make shell scripts executable on Unix
    if platform.system() != "Windows":
        run_command("chmod +x start_backend.sh", check=False)
        run_command("chmod +x start_frontend.sh", check=False)
        run_command("chmod +x start_all.sh", check=False)
    
    print("✅ Start scripts created")

def main():
    """Main setup function"""
    print("🚀 VRSEN Lead Generation Frontend Setup")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Setup failed due to missing prerequisites")
        sys.exit(1)
    
    # Setup backend
    if not setup_backend():
        print("\n❌ Backend setup failed")
        sys.exit(1)
    
    # Setup frontend
    if not setup_frontend():
        print("\n❌ Frontend setup failed")
        sys.exit(1)
    
    # Create start scripts
    create_start_scripts()
    
    print("\n🎉 Setup complete!")
    print("=" * 50)
    print("📋 Next steps:")
    print("1. Start the backend API:")
    if platform.system() == "Windows":
        print("   start_backend.bat")
    else:
        print("   ./start_backend.sh")
    
    print("2. Start the frontend (in another terminal):")
    if platform.system() == "Windows":
        print("   start_frontend.bat")
    else:
        print("   ./start_frontend.sh")
    
    print("3. Or start both at once:")
    if platform.system() == "Windows":
        print("   start_all.bat")
    else:
        print("   ./start_all.sh")
    
    print("\n🌐 URLs:")
    print("   Backend API: http://localhost:8000")
    print("   API Docs: http://localhost:8000/docs")
    print("   Frontend: http://localhost:5173")
    
    print("\n📚 Documentation:")
    print("   Frontend README: frontend/README.md")
    print("   API Documentation: http://localhost:8000/docs (after starting backend)")

if __name__ == "__main__":
    main()
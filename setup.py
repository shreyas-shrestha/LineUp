#!/usr/bin/env python3
"""
setup.py - Setup and Migration Script for LineUp AI v2.0

This script helps you:
1. Install all dependencies
2. Initialize the database
3. Validate configuration
4. Run tests
5. Migrate from old version
"""

import sys
import os
import subprocess
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")


def run_command(cmd, description):
    """Run a shell command"""
    print(f"▶ {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        print(f"Error: {e.stderr}")
        return False


def check_python_version():
    """Check Python version"""
    print_header("Checking Python Version")
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print("✅ Python version is compatible")
    return True


def install_dependencies():
    """Install required dependencies"""
    print_header("Installing Dependencies")
    
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found")
        return False
    
    return run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing packages from requirements.txt"
    )


def create_env_file():
    """Create .env file from template"""
    print_header("Environment Configuration")
    
    if Path(".env").exists():
        print("ℹ️  .env file already exists")
        response = input("Do you want to recreate it? (y/N): ")
        if response.lower() != 'y':
            print("✅ Keeping existing .env file")
            return True
    
    if not Path("env.example.txt").exists():
        print("⚠️  env.example.txt not found")
        print("Creating minimal .env file...")
        
        with open(".env", "w") as f:
            f.write("# LineUp AI Configuration\n")
            f.write("PORT=5000\n")
            f.write("DEBUG=True\n")
            f.write("DATABASE_URL=sqlite:///lineup.db\n")
            f.write("SECRET_KEY=dev-secret-change-in-production\n")
            f.write("\n# Add your API keys below:\n")
            f.write("GEMINI_API_KEY=\n")
            f.write("GOOGLE_PLACES_API_KEY=\n")
        
        print("✅ Created basic .env file")
        print("ℹ️  Please edit .env and add your API keys")
        return True
    
    # Copy template
    try:
        with open("env.example.txt", "r") as src:
            with open(".env", "w") as dst:
                dst.write(src.read())
        print("✅ Created .env from template")
        print("ℹ️  Please edit .env and add your API keys")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env: {e}")
        return False


def initialize_database():
    """Initialize database"""
    print_header("Initializing Database")
    
    try:
        from models import init_db
        from config import Config
        
        print(f"Database URL: {Config.DATABASE_URL}")
        init_db()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False


def validate_config():
    """Validate configuration"""
    print_header("Validating Configuration")
    
    try:
        from config import Config
        
        status = Config.validate()
        
        print("\n📊 Configuration Status:")
        print(f"  Database: {Config.DATABASE_URL}")
        print(f"  Cache: {'Redis' if Config.REDIS_URL else 'Memory'}")
        
        if status['warnings']:
            print("\n⚠️  Warnings:")
            for warning in status['warnings']:
                print(f"  - {warning}")
        
        if status['info']:
            print("\n✅ Configured:")
            for info in status['info']:
                print(f"  {info}")
        
        print("\n✅ Configuration validated")
        return True
    except Exception as e:
        print(f"❌ Failed to validate config: {e}")
        return False


def run_tests():
    """Run test suite"""
    print_header("Running Tests")
    
    if not Path("tests").exists():
        print("⚠️  tests/ directory not found, skipping tests")
        return True
    
    response = input("Run tests now? (Y/n): ")
    if response.lower() == 'n':
        print("⏭️  Skipping tests")
        return True
    
    return run_command(
        f"{sys.executable} -m pytest tests/ -v",
        "Running test suite"
    )


def show_next_steps():
    """Show next steps"""
    print_header("Setup Complete! 🎉")
    
    print("Next steps:")
    print("\n1️⃣  Edit your .env file and add API keys:")
    print("   - Get Gemini API key: https://makersuite.google.com/app/apikey")
    print("   - Get Places API key: https://console.cloud.google.com/apis")
    print("\n2️⃣  Start the server:")
    print("   python app_refactored.py")
    print("\n3️⃣  Open in browser:")
    print("   http://localhost:5000")
    print("\n4️⃣  Optional - Run tests:")
    print("   pytest -v")
    print("\n5️⃣  Optional - Deploy to Render.com:")
    print("   - Connect your GitHub repo")
    print("   - Set environment variables in dashboard")
    print("   - Deploy!")
    
    print("\n📚 Documentation:")
    print("   - README_IMPROVEMENTS.md - Full feature guide")
    print("   - HAIRFAST_SETUP.md - Virtual try-on setup")
    print("   - env.example.txt - All configuration options")
    
    print("\n💡 Pro Tips:")
    print("   - SQLite works great for development (no setup!)")
    print("   - Redis is optional (uses memory cache if not available)")
    print("   - All services have free tiers - $0 monthly cost!")
    
    print("\n🎯 Minimum to get started:")
    print("   GEMINI_API_KEY - Everything else works with mock data!")
    
    print("\n")


def main():
    """Main setup function"""
    print_header("LineUp AI v2.0 - Setup Script")
    
    print("This script will:")
    print("  ✓ Check Python version")
    print("  ✓ Install dependencies")
    print("  ✓ Create .env configuration file")
    print("  ✓ Initialize database")
    print("  ✓ Validate configuration")
    print("  ✓ Run tests (optional)")
    print("")
    
    response = input("Continue with setup? (Y/n): ")
    if response.lower() == 'n':
        print("Setup cancelled")
        return
    
    # Run setup steps
    steps = [
        ("Checking Python version", check_python_version),
        ("Installing dependencies", install_dependencies),
        ("Creating .env file", create_env_file),
        ("Initializing database", initialize_database),
        ("Validating configuration", validate_config),
        ("Running tests", run_tests),
    ]
    
    failed_steps = []
    
    for description, func in steps:
        if not func():
            failed_steps.append(description)
            response = input(f"\n⚠️  '{description}' failed. Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("\n❌ Setup aborted")
                print(f"Failed at: {description}")
                return
    
    if failed_steps:
        print_header("Setup Completed with Warnings")
        print("⚠️  The following steps had issues:")
        for step in failed_steps:
            print(f"  - {step}")
        print("\nPlease review the errors above and fix them manually.")
    else:
        show_next_steps()


if __name__ == "__main__":
    main()


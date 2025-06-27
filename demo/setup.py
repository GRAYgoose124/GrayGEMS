#!/usr/bin/env python3
"""
Setup script for GrayGEMS Demo
Installs required dependencies for the demo
"""

import subprocess
import sys
from pathlib import Path

def install_requirements():
    """Install required packages"""
    requirements = [
        "fastapi",
        "uvicorn[standard]",
        "requests",
        "pydantic"
    ]
    
    print("📦 Installing demo dependencies...")
    for package in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ Installed {package}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            return False
    return True

def main():
    """Main setup function"""
    print("🚀 GrayGEMS Demo Setup")
    print("=" * 30)
    
    if install_requirements():
        print("\n✅ Setup completed successfully!")
        print("\nTo start the demo:")
        print("  python start_demo.py")
        print("\nTo test the demo:")
        print("  python test_demo.py")
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 
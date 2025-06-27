#!/usr/bin/env python3
"""
GrayGEMS Demo Starter
A simple script to start the GrayGEMS demo server
"""

import uvicorn
import sys
from pathlib import Path

# Add the demo directory to the Python path
demo_dir = Path(__file__).parent
sys.path.insert(0, str(demo_dir))

if __name__ == "__main__":
    print("🚀 Starting GrayGEMS Demo Server...")
    print("📁 Demo directory:", demo_dir)
    print("🌐 Server will be available at: http://localhost:8000")
    print("📚 API docs will be available at: http://localhost:8000/docs")
    print("🏥 Health check at: http://localhost:8000/health")
    print()
    print("Press Ctrl+C to stop the server")
    print()
    
    uvicorn.run(
        "demo.__main__:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 
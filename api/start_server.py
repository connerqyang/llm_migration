#!/usr/bin/env python3
"""
Start the FastAPI server for LLM Migration Tool
"""

import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Start the FastAPI server"""
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"
    
    print("🚀 Starting LLM Migration Tool API Server")
    print(f"📍 Server will be available at: http://{host}:{port}")
    print(f"📖 API Documentation: http://{host}:{port}/docs")
    print(f"🔄 Auto-reload: {reload}")
    print("="*50)
    
    # Start the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()
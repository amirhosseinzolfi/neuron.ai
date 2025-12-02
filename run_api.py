#!/usr/bin/env python3
"""
Unified API Runner for Blue Psychology Services
Runs TTS and Image Generation APIs
"""

import uvicorn
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Run the FastAPI application with all services"""
    
    print("=" * 60)
    print("🚀 Starting Blue Psychology API Server")
    print("=" * 60)
    print("\n📋 Available Services:")
    print("  • Text-to-Speech (TTS)")
    print("  • Image Generation")
    print("\n🌐 API Documentation:")
    print("  • Swagger UI: http://localhost:15800/docs")
    print("  • ReDoc: http://localhost:15800/redoc")
    print("\n📡 Endpoints:")
    print("  • POST /tts/generate - Generate speech from text")
    print("  • POST /image/generate - Generate single image from text")
    print("  • POST /image/generate-multiple - Generate multiple images")
    print("  • GET  /image/file/{filename} - Retrieve generated image")
    print("  • GET  /health - Health check")
    print("\n" + "=" * 60)
    
    uvicorn.run(
        "api.api:app",
        host=args.host,
        port=args.port,
        reload=True,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()

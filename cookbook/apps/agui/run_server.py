#!/usr/bin/env python3
"""Run the AG-UI multi-agent demo server.

Usage:
    python run_server.py [--port PORT]
    
This starts the server with all available agents:
- toolBasedGenerativeUIAgent: Haiku generator with tool-based UI
- sharedStateAgent: Recipe creator with bidirectional state sync
- agentiveGenerativeUIAgent: Step-based task execution with progress updates
- agenticChatAgent: General chat with UI interaction capabilities
- humanInTheLoopAgent: Task planning with approval workflow
- predictiveStateUpdatesAgent: Real-time collaborative editing
"""

import argparse
import uvicorn
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from cookbook.apps.agui.multi_agent_demo import app


def main():
    parser = argparse.ArgumentParser(description="Run the AG-UI multi-agent demo server")
    parser.add_argument(
        "--port",
        type=int,
        default=7777,
        help="Port to run the server on (default: 7777)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes"
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Starting AG-UI Multi-Agent Demo Server")
    print(f"📍 Server: http://localhost:{args.port}")
    print(f"📡 API Base: http://localhost:{args.port}/api/copilotkit")
    print(f"\nAvailable agents:")
    print("  - toolBasedGenerativeUIAgent")
    print("  - sharedStateAgent")
    print("  - agentiveGenerativeUIAgent")
    print("  - agenticChatAgent")
    print("  - humanInTheLoopAgent")
    print("  - predictiveStateUpdatesAgent")
    print("\nPress Ctrl+C to stop the server\n")
    
    uvicorn.run(
        "cookbook.apps.agui.multi_agent_demo:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Deployment entrypoint for Replit Autoscale.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

port = int(os.environ.get("PORT", "8000"))

import uvicorn
from backend.app import app

print(f"Starting uvicorn on 0.0.0.0:{port}", flush=True)
uvicorn.run(
    app,
    host="0.0.0.0",
    port=port,
    log_level="info",
    access_log=True,
    loop="asyncio",       # Force pure Python asyncio (not uvloop)
    http="h11",           # Force pure Python HTTP parser (not httptools)
)

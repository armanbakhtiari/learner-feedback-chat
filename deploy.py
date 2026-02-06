#!/usr/bin/env python3
"""
Deployment entrypoint for Replit Autoscale (Cloud Run).
Reads PORT from environment variable (set by Cloud Run) and starts the app.
"""
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Get port from environment (Cloud Run sets this)
port = int(os.environ.get("PORT", "8000"))
print(f"Starting server on port {port}", flush=True)

import uvicorn
from backend.app import app

uvicorn.run(app, host="0.0.0.0", port=port)

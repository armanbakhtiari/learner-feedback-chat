#!/usr/bin/env python3
"""
ONE script to start both backend and frontend servers
Run with: python run.py or python3 run.py
"""

import subprocess
import sys
import time
import webbrowser
import os
from pathlib import Path

# Use python3 explicitly
PYTHON_CMD = "python3" if sys.platform != "win32" else "python"

def print_banner():
    """Print welcome banner"""
    print("\n" + "="*70)
    print("🚀 LEARNER FEEDBACK CHAT APPLICATION")
    print("="*70 + "\n")

def check_port(port):
    """Check if a port is available"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result != 0  # Returns True if port is available

def start_backend():
    """Start the backend server"""
    print("📡 Starting backend server on port 8000...")

    if not check_port(8000):
        print("⚠️  Port 8000 is already in use!")
        response = input("Kill existing process and restart? (y/n): ")
        if response.lower() == 'y':
            os.system("lsof -ti:8000 | xargs kill -9 2>/dev/null")
            time.sleep(1)
        else:
            print("❌ Cannot start backend - port in use")
            return None

    backend_process = subprocess.Popen(
        [PYTHON_CMD, "backend/app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    # Wait for backend to start
    print("⏳ Waiting for backend to start...")
    for i in range(10):
        if not check_port(8000):
            print("✅ Backend is running on http://localhost:8000")
            return backend_process
        time.sleep(1)

    print("❌ Backend failed to start")
    return None

def start_frontend():
    """Start the frontend server"""
    print("\n📱 Starting frontend server on port 3000...")

    if not check_port(3000):
        print("⚠️  Port 3000 is already in use!")
        response = input("Kill existing process and restart? (y/n): ")
        if response.lower() == 'y':
            os.system("lsof -ti:3000 | xargs kill -9 2>/dev/null")
            time.sleep(1)
        else:
            print("❌ Cannot start frontend - port in use")
            return None

    frontend_process = subprocess.Popen(
        [PYTHON_CMD, "-m", "http.server", "3000"],
        cwd="frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    # Wait for frontend to start
    print("⏳ Waiting for frontend to start...")
    for i in range(5):
        if not check_port(3000):
            print("✅ Frontend is running on http://localhost:3000")
            return frontend_process
        time.sleep(1)

    print("❌ Frontend failed to start")
    return None

def main():
    """Main function"""
    print_banner()

    # Check if we're in the right directory
    if not Path("backend/app.py").exists():
        print("❌ Error: backend/app.py not found")
        print("Please run this script from the Implementation directory")
        sys.exit(1)

    # Start backend
    backend = start_backend()
    if not backend:
        sys.exit(1)

    # Start frontend
    frontend = start_frontend()
    if not frontend:
        backend.terminate()
        sys.exit(1)

    # Open browser
    print("\n" + "="*70)
    print("✨ APPLICATION IS READY!")
    print("="*70)
    print("\n📍 URLs:")
    print("   • Main App:     http://localhost:3000")
    print("   • Test Page:    http://localhost:3000/test.html")
    print("   • Backend API:  http://localhost:8000")
    print("\n💡 Tips:")
    print("   • First visit: http://localhost:3000/test.html to verify setup")
    print("   • Then visit:  http://localhost:3000 for the main app")
    print("   • Press Ctrl+C to stop both servers")
    print("\n🔍 LangSmith Tracing:")
    print("   • Project: Feedback_Chat_Agent")
    print("   • View at: https://smith.langchain.com/")
    print("\n" + "="*70 + "\n")

    # Open browser
    time.sleep(2)
    print("🌐 Opening browser...")
    try:
        webbrowser.open("http://localhost:3000/test.html")
    except:
        pass

    print("\n⌨️  Press Ctrl+C to stop the servers...\n")

    # Keep running until interrupted
    try:
        while True:
            time.sleep(1)
            # Check if processes are still running
            if backend.poll() is not None:
                print("\n❌ Backend stopped unexpectedly")
                break
            if frontend.poll() is not None:
                print("\n❌ Frontend stopped unexpectedly")
                break
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping servers...")
        backend.terminate()
        frontend.terminate()
        print("✅ Servers stopped")
        print("👋 Goodbye!\n")

if __name__ == "__main__":
    main()

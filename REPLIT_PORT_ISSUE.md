# Replit Port Access Issue - Solution

## 🐛 Problem

"Failed to fetch" error on chat page means the frontend can't reach the backend on port 8000.

## 🔍 Diagnosis Steps

### 1. Check Browser Console

Press **F12** in your browser and look at the Console tab. You should see:
```
API_BASE_URL: https://your-repl.replit.app:8000
Session ID: session_1
```

### 2. Check if Backend is Running

In Replit Console, you should see:
```
✅ Backend is running on http://localhost:8000
✅ Frontend is running on http://localhost:3000
```

### 3. Test Backend Directly

Try opening in a new browser tab:
```
https://your-repl-name.your-username.replit.app:8000/
```

If this fails, Replit isn't exposing port 8000 publicly.

## ✅ Solutions

### Solution 1: Use Replit's Port Forwarding

Replit might require a different URL format. Try accessing:
```
https://8000-your-repl-name.your-username.replit.dev
```

### Solution 2: Configure .replit File

Your `.replit` file should have:
```toml
[[ports]]
localPort = 8000
externalPort = 8000
exposeLocalhost = true
```

Make sure `exposeLocalhost = true` is set!

### Solution 3: Use Replit's Environment Variable

Check if Replit provides an environment variable for the backend URL.

## 🚀 Quick Fix

### Option A: Update .replit Configuration

1. In Replit, open `.replit` file
2. Find the ports section
3. Make sure it looks like this:

```toml
[[ports]]
localPort = 3000
externalPort = 80
exposeLocalhost = true

[[ports]]
localPort = 8000
externalPort = 8000
exposeLocalhost = true
```

4. Click "Run" to restart

### Option B: Check Replit Webview Settings

1. In Replit, click the "Webview" tab
2. Look for port settings
3. Make sure port 8000 is listed and accessible
4. Try clicking the "Open in new tab" button for port 8000

## 🔧 Alternative: Run Everything on Port 8000

If Replit only exposes one port reliably, we can serve frontend from backend:

1. Update `run.py` to skip port 3000
2. Serve frontend static files from FastAPI
3. Everything runs on port 8000

Would you like me to implement this solution?

## 📝 Debug Information Needed

Please provide:
1. What do you see in browser console (F12)?
2. Can you access `https://your-repl:8000/` in a new tab?
3. What does Replit's port panel show?
4. Any errors in Replit's Console tab?

This will help me provide the exact fix!

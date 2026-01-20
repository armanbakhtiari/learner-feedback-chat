# Deploy to Replit - Complete Guide

This guide will help you deploy your AI-powered Learner Feedback Chat System to Replit and make it publicly accessible.

## 🚀 Quick Deploy (Recommended Method)

### Method 1: Import from GitHub (Recommended)

1. **First, push to GitHub** (if not done):
   ```bash
   # See PUSH_TO_GITHUB.md for detailed instructions
   git remote add origin https://github.com/armanbakhtiari/learner-feedback-chat.git
   git push -u origin main
   ```

2. **Import to Replit:**
   - Go to https://replit.com/
   - Click **"+ Create Repl"**
   - Choose **"Import from GitHub"**
   - Enter: `armanbakhtiari/learner-feedback-chat`
   - Click **"Import from GitHub"**
   - Replit will automatically detect it's a Python project

### Method 2: Upload Directly

1. Go to https://replit.com/
2. Click **"+ Create Repl"**
3. Choose **"Python"** template
4. Name it: `learner-feedback-chat`
5. Click **"Create Repl"**
6. Upload files:
   - Delete default `main.py`
   - Drag and drop all your project folders/files
   - Or use the upload button in the Files pane

## ⚙️ Configure Replit

### 1. Set Environment Variables (Secrets)

In Replit, go to **Tools** → **Secrets** (🔒 icon in sidebar):

Add these secrets:

```
ANTHROPIC_API_KEY = sk-ant-your_key_here
LANGCHAIN_API_KEY = lsv2_pt_your_key_here
TAVILY_API_KEY = tvly-your_key_here
```

**Important:** Don't create a `.env` file in Replit - use Secrets instead!

### 2. Verify Configuration Files

Replit will auto-detect these files (already in your repo):
- `.replit` - Run configuration
- `replit.nix` - System packages
- `requirements.txt` - Python dependencies

### 3. Install Dependencies

Replit should auto-install, but if needed:

```bash
pip install -r requirements.txt
```

## ▶️ Run Your Application

### In Replit IDE:

1. Click the **"Run"** button (▶️) at the top
2. The console will show:
   ```
   🚀 LEARNER FEEDBACK CHAT APPLICATION
   ✨ APPLICATION IS READY!
   📍 Your Replit App:
      • URL: https://learner-feedback-chat.username.repl.co
   ```
3. The webview will open automatically

### Test Your Deployment:

- Main app: Click the webview or copy the URL
- Backend API: `https://your-repl-url.repl.co:8000`
- Visit `/docs` for API documentation

## 🌍 Make It Public

### Option 1: Share the Repl

1. In Replit, click **"Share"** button (top right)
2. Toggle **"Public"** on
3. Copy the share link
4. Anyone with the link can view and fork your Repl

### Option 2: Deploy as a Web App

1. Click **"Deploy"** button (🚀) in Replit
2. Choose **"Reserved VM"** or **"Autoscale"**
3. Configure:
   - Name: `learner-feedback-chat`
   - Choose plan (Free tier available)
4. Click **"Deploy"**
5. Get a permanent URL: `https://learner-feedback-chat.your-username.repl.app`

**Differences:**
- **Share Repl:** Free, but sleeps when inactive
- **Deploy:** Persistent, always-on (may require paid plan)

## 📊 Monitor Your Deployment

### Check Logs

In Replit console, you'll see:
```
📡 Starting backend server on port 8000...
✅ Backend is running
📱 Starting frontend server on port 3000...
✅ Frontend is running
```

### LangSmith Tracing

Your LangSmith traces will still work:
- Project: **Feedback_Chat_Agent**
- View at: https://smith.langchain.com/

## 🔧 Troubleshooting

### App Won't Start

**Check Python version:**
```bash
python3 --version
# Should be 3.8+
```

**Reinstall dependencies:**
```bash
pip install --force-reinstall -r requirements.txt
```

### Secrets Not Working

- Verify secrets are set in Tools → Secrets
- Restart the Repl after adding secrets
- Check spelling matches exactly: `ANTHROPIC_API_KEY`

### Port Issues

Replit automatically handles ports 3000 and 8000. If you see port errors:
- Stop the Repl
- Clear any running processes
- Restart

### Memory Issues

If you run out of memory:
- Upgrade to a paid plan for more resources
- Or optimize by removing unused dependencies

## 🎯 Post-Deployment Checklist

After deploying:

- [ ] Test the main app loads correctly
- [ ] Click "Lancer l'évaluation" - verify it runs
- [ ] Send a test message to the chat
- [ ] Request a visualization: "Créez un tableau"
- [ ] Check LangSmith for traces
- [ ] Share the public URL with collaborators
- [ ] (Optional) Deploy for always-on hosting

## 🔗 Useful Links

- **Your Repl Dashboard:** https://replit.com/~
- **Replit Docs:** https://docs.replit.com/
- **LangSmith Dashboard:** https://smith.langchain.com/
- **GitHub Repo:** https://github.com/armanbakhtiari/learner-feedback-chat

## 💰 Cost Considerations

### Free Tier (Share Repl)
- ✅ Perfect for development and demos
- ✅ Can share with unlimited viewers
- ⚠️ Sleeps after 1 hour of inactivity
- ⚠️ May be slower with limited resources

### Paid Tier (Deploy)
- ✅ Always-on (no sleeping)
- ✅ Better performance
- ✅ Custom domain support
- ✅ More memory/CPU
- 💰 ~$7-20/month depending on plan

## 🎉 Success!

Once deployed, your app will be accessible at:
```
https://learner-feedback-chat.your-username.repl.co
```

Share this URL with:
- Students for feedback
- Colleagues for collaboration
- Research participants for evaluation

## 🔄 Updating Your Deployment

When you make changes:

### If using GitHub sync:
1. Commit and push to GitHub
2. In Replit, click **"Pull"** from Git panel
3. Repl will auto-restart with new code

### If uploading directly:
1. Make changes in Replit editor
2. Click **"Run"** to restart
3. Changes are live immediately

---

**Need help?** Check Replit's documentation or Discord community.

**Ready to deploy?** Follow the steps above and your app will be live in minutes! 🚀

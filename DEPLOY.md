# Atlas v3 - Trading Dashboard Deployment Guide

## Quick Deploy to Render (5 minutes)

### Option 1: Deploy from GitHub (RECOMMENDED)

1. **Create GitHub Repo**
   - Go to github.com
   - Create new repo: `squeezeseeker-dashboard`
   - Make it private

2. **Push Code**
   ```bash
   cd /Users/mikeclawd/.openclaw/workspace
   git remote add origin https://github.com/YOUR_USERNAME/squeezeseeker-dashboard.git
   git push -u origin main
   ```

3. **Deploy on Render**
   - Go to render.com
   - Sign up (free)
   - Click "New Web Service"
   - Connect your GitHub repo
   - Render will auto-detect `render.yaml`
   - Add environment variables:
     - `ALPACA_API_KEY`: PKZ6EG2MCPTTD6S4EVXNCDET6H
     - `ALPACA_API_SECRET`: 4dSYTkBZVgqh3myNQEGYV51fdvwv4NZx9C92zsqEqrxi
   - Deploy!

4. **Get Your URL**
   - Render gives you: `https://squeezeseeker-trading.onrender.com`
   - Open on your phone ✅

### Option 2: Test Locally First

```bash
cd /Users/mikeclawd/.openclaw/workspace
pip install -r requirements.txt
python app.py
```

Open: http://localhost:3456

## Features

- **Portfolio View**: Real-time Alpaca positions, P&L, allocation
- **Recommendations**: 10-factor scored stocks with thesis
- **Stock Search**: Analyze any ticker instantly
- **Mobile-Responsive**: Works on phone, tablet, desktop
- **Auto-Refresh**: Data updates every 60 seconds

## Environment Variables (for Render)

```
ALPACA_API_KEY=PKZ6EG2MCPTTD6S4EVXNCDET6H
ALPACA_API_SECRET=4dSYTkBZVgqh3myNQEGYV51fdvwv4NZx9C92zsqEqrxi
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

# AMC-TRADER Installation Guide

Welcome to AMC-TRADER! This guide will help you install and set up the complete trading intelligence system on your computer.

## 📋 Quick Start

**Choose your installation method:**

### 🚀 One-Click Installation (Recommended)

**Mac Users:**
```bash
# Download and run the Mac installer
curl -fsSL https://raw.githubusercontent.com/yourusername/AMC-TRADER/main/setup-mac.command -o setup-mac.command
chmod +x setup-mac.command && ./setup-mac.command
```

**Windows Users:**
```cmd
# Download and run the Windows installer
curl -fsSL https://raw.githubusercontent.com/yourusername/AMC-TRADER/main/setup-windows.bat -o setup-windows.bat
setup-windows.bat
```

**Linux Users:**
```bash
# Download and run the Linux installer
curl -fsSL https://raw.githubusercontent.com/yourusername/AMC-TRADER/main/setup.sh -o setup.sh
chmod +x setup.sh && ./setup.sh
```

### 🐳 Docker Installation (Alternative)

If you prefer Docker or have installation issues:

```bash
# Clone repository
git clone https://github.com/yourusername/AMC-TRADER.git
cd AMC-TRADER

# Copy environment template
cp .env.template .env

# Edit .env with your API keys (see API Keys section below)
nano .env  # or use your preferred editor

# Start with Docker
docker-compose up -d

# Open browser to http://localhost:3000
```

---

## 🔑 API Keys Setup (REQUIRED)

After installation, you **must** configure your API keys:

### 1. Alpaca Trading API (Required)
- Sign up at [Alpaca Markets](https://alpaca.markets/)
- Go to your dashboard and generate API keys
- For testing, use **Paper Trading** (free virtual money)
- For real trading, use **Live Trading** (real money)

### 2. Polygon Market Data API (Required)  
- Sign up at [Polygon.io](https://polygon.io/)
- Go to dashboard and get your API key
- Free tier available with rate limits

### 3. Claude AI API (Optional)
- Sign up at [Anthropic Console](https://console.anthropic.com/)
- Generate API key for advanced AI analysis features

### 4. Twilio SMS API (Optional)
- Sign up at [Twilio](https://www.twilio.com/)
- Get Account SID, Auth Token, and phone number
- For SMS trading alerts

---

## ⚙️ Configuration

Edit your `.env` file with real values:

```bash
# Required API Keys
ALPACA_API_KEY=PKXXXXXXXXXXXXXXXX
ALPACA_SECRET_KEY=your_alpaca_secret_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets

POLYGON_API_KEY=your_polygon_key_here

# Optional API Keys  
CLAUDE_API_KEY=your_claude_key_here
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here
```

**Important Notes:**
- Start with `https://paper-api.alpaca.markets` for testing
- Change to `https://api.alpaca.markets` only when ready for live trading
- Keep your `.env` file secure and never share it

---

## 🚀 Running AMC-TRADER

### Automatic Startup (Recommended)

**Mac:** Double-click `start-amc-trader.command`  
**Windows:** Double-click `start-amc-trader.bat`  
**Linux:** Run `./start-amc-trader.sh`

This will:
- Start the backend API server (http://localhost:8000)
- Start the frontend web interface (http://localhost:3000)  
- Open your browser automatically
- Display all logs in the terminal

### Manual Startup

**Start Backend:**
```bash
cd AMC-TRADER
source venv/bin/activate  # On Windows: venv\Scripts\activate.bat
cd backend
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

**Start Frontend (new terminal):**
```bash
cd AMC-TRADER/frontend
npm run dev
```

### Docker Startup
```bash
cd AMC-TRADER
docker-compose up -d
```

---

## 🌐 Access Points

Once running, access these URLs:

- **Main Application**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs  
- **API Health Check**: http://localhost:8000/health
- **Database Admin** (if installed): http://localhost:5050

---

## 📱 Features Overview

### Discovery Engine
- Real-time stock opportunity detection
- Volume and price momentum analysis  
- Pattern recognition (VIGL, squeeze patterns)
- Risk scoring with WOLF pattern detection

### Portfolio Management
- Position tracking and analysis
- Automated thesis generation
- Buy/Hold/Sell recommendations
- Unrealized P&L monitoring

### Trading Interface
- Paper and live trading support
- Risk management controls
- Position sizing automation
- Stop-loss and take-profit management

### Analytics Dashboard
- Performance tracking
- Pattern success rates
- Risk analysis
- Historical backtesting

---

## 🔧 System Requirements

### Minimum Requirements
- **OS**: macOS 10.15+, Windows 10+, Ubuntu 18.04+
- **RAM**: 4GB (8GB recommended)
- **Storage**: 2GB free space
- **Internet**: Broadband connection for real-time data

### Software Dependencies
- **Python**: 3.9 or higher
- **Node.js**: 18.0 or higher
- **Git**: For cloning and updates
- **PostgreSQL**: 12+ (auto-installed)
- **Redis**: 6+ (auto-installed)

---

## 🐳 Docker Setup (Alternative Installation)

If you prefer containerized deployment:

### Quick Docker Start
```bash
# Clone repository
git clone https://github.com/yourusername/AMC-TRADER.git
cd AMC-TRADER

# Create environment file
cp .env.template .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services  
docker-compose down
```

### Docker Services
- `postgres`: Database server
- `redis`: Cache and job queue
- `backend`: FastAPI server
- `frontend`: React development server
- `nginx`: Reverse proxy (production profile)

### Production Docker Deployment
```bash
# Use production profile
docker-compose --profile production up -d

# Includes Nginx, monitoring, and optimized builds
```

---

## 🔍 Troubleshooting

### Installation Issues

**Python not found:**
```bash
# Mac: Install via Homebrew
brew install python@3.11

# Windows: Download from python.org
# Linux: apt-get install python3.11
```

**Node.js not found:**
```bash
# Mac: Install via Homebrew  
brew install node

# Windows: Download from nodejs.org
# Linux: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
```

**Database connection failed:**
```bash
# Check PostgreSQL is running
brew services list | grep postgresql

# Restart if needed
brew services restart postgresql
```

**Redis connection failed:**
```bash
# Check Redis is running
brew services list | grep redis

# Restart if needed  
brew services restart redis
```

### Runtime Issues

**API Key Errors:**
- Verify keys are correctly entered in `.env`
- Check Alpaca dashboard for key permissions
- Ensure Polygon key has sufficient quota

**Port Already in Use:**
```bash
# Find process using port 3000 or 8000
lsof -i :3000
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

**Permission Errors:**
```bash
# Fix .env file permissions
chmod 600 .env

# Fix script permissions
chmod +x setup.sh start-*.sh
```

### Getting Help

1. **Check the logs**: Backend logs show detailed error information
2. **Verify configuration**: Ensure all required API keys are set
3. **Test APIs**: Use the built-in health check endpoints  
4. **GitHub Issues**: Check for known issues and solutions
5. **Documentation**: Full system documentation in `/docs` folder

---

## 🔒 Security Best Practices

### API Key Security
- Never commit `.env` files to version control
- Use separate keys for development/production
- Rotate keys regularly
- Enable IP restrictions where supported

### Trading Safety
- **Always start with paper trading**
- Set position size limits  
- Use stop-loss orders
- Monitor positions actively
- Test strategies thoroughly before live trading

### System Security
- Keep software updated
- Use strong passwords
- Consider VPN for additional protection
- Monitor system logs for unusual activity

---

## 🔄 Updates and Maintenance

### Updating AMC-TRADER
```bash
cd AMC-TRADER
git pull origin main

# Update Python dependencies
source venv/bin/activate
pip install -r backend/requirements.txt

# Update Node.js dependencies
cd frontend
npm install

# Restart application
```

### Database Maintenance
```bash
# Backup database
pg_dump amc_trader > backup.sql

# Run database migrations (if any)
cd backend
alembic upgrade head
```

### Log Maintenance
```bash
# Clear old logs (optional)
find backend/logs -name "*.log" -mtime +30 -delete
```

---

## 💡 Tips for Success

### For Beginners
1. Start with paper trading to learn the system
2. Read all documentation before live trading
3. Understand each feature before relying on it
4. Set conservative risk limits initially
5. Monitor positions frequently at first

### For Advanced Users
1. Customize the discovery algorithms in `/backend/src/`
2. Add custom indicators and patterns
3. Integrate with additional data sources
4. Set up automated monitoring and alerts
5. Backtest strategies thoroughly

### Performance Optimization
1. Ensure adequate RAM (8GB+ recommended)
2. Use SSD storage for database
3. Monitor system resources during market hours
4. Consider dedicated server for production use
5. Optimize database queries for large datasets

---

## 📊 System Architecture

```
AMC-TRADER/
├── frontend/           # React TypeScript web interface
├── backend/           # Python FastAPI server
│   ├── src/
│   │   ├── app.py     # Main application
│   │   ├── routes/    # API endpoints
│   │   ├── services/  # Business logic
│   │   └── jobs/      # Background tasks
├── data/              # Stock universe and configs
├── docker-compose.yml # Container orchestration
├── .env.template     # Environment variables template
└── setup scripts     # Installation automation
```

---

## 🤝 Contributing

If you'd like to contribute to AMC-TRADER:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📞 Support

- **Documentation**: Check `/docs` folder for detailed guides
- **GitHub Issues**: Report bugs and request features
- **API Docs**: http://localhost:8000/docs when running
- **System Health**: http://localhost:8000/health for diagnostics

---

## ⚠️ Important Disclaimers

- **Trading Risk**: All trading involves risk of loss
- **Educational Purpose**: This software is for educational use
- **No Guarantees**: Past performance doesn't guarantee future results
- **Your Responsibility**: You are responsible for your trading decisions
- **Test First**: Always test with paper trading before using real money

---

## 🎉 Ready to Trade!

Once installed and configured:

1. ✅ All services are running
2. ✅ API keys are configured  
3. ✅ Database is connected
4. ✅ Frontend loads at http://localhost:3000
5. ✅ Paper trading is enabled

**You're ready to start discovering profitable trading opportunities!**

Happy Trading! 🚀📈

---

*For technical support or questions about this installation guide, please check the GitHub repository issues or create a new issue.*
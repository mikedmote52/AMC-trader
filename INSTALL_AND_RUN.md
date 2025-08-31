# 🚀 AMC-TRADER: Install & Run in 3 Steps

## For Complete Beginners (No Technical Experience Required)

### Step 1: Copy and Paste this Command

**Mac/Linux Users:**
```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/AMC-TRADER/main/quick-install.sh | bash
```

**Windows Users:**
1. Press `Windows + R`
2. Type `cmd` and press Enter
3. Copy and paste this command:
```cmd
curl -fsSL https://raw.githubusercontent.com/yourusername/AMC-TRADER/main/setup-windows.bat -o setup.bat && setup.bat
```

### Step 2: Get Your FREE API Keys

While the installer runs, sign up for these free accounts:

1. **Alpaca (Trading)**: https://alpaca.markets/
   - Click "Get Started" 
   - Choose "Paper Trading" (fake money for testing)
   - Copy your API Key and Secret

2. **Polygon (Market Data)**: https://polygon.io/
   - Sign up for free account
   - Go to dashboard and copy your API key

### Step 3: Configure and Run

1. The installer will create a file called `.env`
2. Open it with any text editor (Notepad, TextEdit, etc.)
3. Replace `your_alpaca_api_key_here` with your real Alpaca API key
4. Replace `your_polygon_api_key_here` with your real Polygon API key
5. Save the file

**Then run AMC-TRADER:**
- **Mac**: Double-click `start-amc-trader.command`
- **Windows**: Double-click `start-amc-trader.bat`
- **Linux**: Run `./start-amc-trader.sh`

## That's It! 🎉

Your browser will open to http://localhost:3000 and you'll see the AMC-TRADER interface.

---

## ❓ Need Help?

### Can't Run the Command?
- **Mac**: Open Terminal (Cmd+Space, type "terminal")
- **Windows**: Press Windows+R, type "cmd", press Enter
- **Linux**: Open your terminal application

### Installation Failed?
- Make sure you have internet connection
- Try running the command again
- Check that you have Python 3.9+ and Node.js 18+ installed

### API Keys Not Working?
- Double-check you copied them correctly (no extra spaces)
- Make sure you're using the Paper Trading URL for Alpaca
- Verify your Polygon account is activated

### Still Stuck?
1. Check the full installation guide: `README_INSTALL.md`
2. Look at common issues: `requirements-setup.txt`
3. Check GitHub issues for your problem
4. Try the Docker installation instead

---

## 🔒 Is This Safe?

- ✅ All code is open source and inspectable
- ✅ Uses paper trading by default (fake money)
- ✅ Your API keys stay on your computer
- ✅ No data is sent to third parties
- ✅ All trading is through official Alpaca API

**Never use real money until you understand how the system works!**

---

## 🎯 What You Get

- **Discovery Engine**: Finds profitable stock opportunities
- **Paper Trading**: Test strategies with fake money
- **Real-time Data**: Live market information
- **AI Analysis**: Smart trading recommendations
- **Risk Management**: Automatic stop-losses and position sizing
- **Performance tracking**: See how your strategies perform

---

## 💡 Pro Tips

1. **Start with Paper Trading**: Learn the system with fake money first
2. **Read the Documentation**: Check `README_INSTALL.md` for full details
3. **Understand the Features**: Don't rely on AI recommendations blindly
4. **Set Conservative Limits**: Start with small position sizes
5. **Monitor Your Trades**: Always watch your positions actively

---

## 🚀 Ready to Start Trading?

Once installed:
1. Go to http://localhost:3000
2. Explore the discovery engine
3. Set up some paper trades
4. Watch the AI analyze your positions
5. Learn how the system works
6. Graduate to live trading when ready

**Happy Trading!** 📈
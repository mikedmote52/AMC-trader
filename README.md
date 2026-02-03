# SqueezeSeeker Trading Dashboard

A modern, interactive web-based trading dashboard for paper trading with real-time portfolio tracking, stock analysis, and the 10-factor scoring system.

## Features

✨ **Modern UI** - Clean, Robinhood-style interface that works on desktop and mobile  
📊 **Real Portfolio Data** - Connected to Alpaca paper trading API  
📈 **Live Charts** - Portfolio allocation and historical price charts  
🎯 **10-Factor Analysis** - Score any stock using the SqueezeSeeker strategy  
🔍 **Stock Search** - Search any ticker and get instant analysis  
💰 **One-Click Trading** - Buy stocks directly from the dashboard  
⚡ **Real-Time Updates** - Data refreshes automatically every 30 seconds  

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Verify Alpaca Credentials

Make sure your Alpaca API credentials are in `~/.openclaw/secrets/alpaca.json`:

```json
{
  "apiKey": "YOUR_API_KEY",
  "apiSecret": "YOUR_API_SECRET",
  "baseUrl": "https://paper-api.alpaca.markets/v2",
  "paperTrading": true
}
```

### 3. Run the Dashboard

```bash
python app.py
```

### 4. Open in Browser

Navigate to: **http://localhost:5000**

## Dashboard Sections

### 📊 Portfolio
- Real-time portfolio value and P&L
- Buying power and cash balance
- Visual allocation chart
- Detailed positions table with individual P&L

### 🔥 Top Opportunities
- Recommended stocks scoring 7+ on the 10-factor system
- Buy buttons for instant paper trading
- Detailed thesis and price targets
- Catalyst dates and risk/reward ratios

### 📝 Pending Orders
- View all open orders
- Real-time status updates

### 🔍 Stock Search
- Search any ticker (e.g., AAPL, TSLA)
- Get instant 10-factor analysis
- View 3-month price chart
- See detailed scoring breakdown
- Buy directly from analysis modal

## 10-Factor Scoring System

Each stock is scored on 10 factors from STRATEGY.md:

1. **Strong Fundamental Story** - Revenue growth, partnerships, product momentum
2. **Technical Setup** - Price above 50-day MA, volume building
3. **Upcoming Catalyst** (2x weight) - Earnings, FDA, launches in 2-4 weeks
4. **Theme Alignment** - Hot sectors (AI, quantum, biotech)
5. **Social Confirmation** - Quality discussion building
6. **Insider Buying** - Recent Form 4 filings
7. **Low Float/High Short** - Squeeze potential
8. **Under $100** - Accessible pricing
9. **Liquidity** - 1M+ average volume
10. **No Recent Blow-off** - Not up 100%+ in past week

**Scoring:**
- **7-8**: BUY signal
- **9**: HIGH CONVICTION
- **10**: MAXIMUM CONVICTION (rare)

## API Endpoints

The Flask backend provides these endpoints:

- `GET /api/account` - Account info (cash, buying power, portfolio value)
- `GET /api/positions` - Current positions with P&L
- `GET /api/orders` - Pending orders
- `GET /api/recommendations` - Pre-screened stock recommendations
- `GET /api/search?symbol=AAPL` - Analyze any stock
- `GET /api/historical/AAPL` - 3-month historical data
- `POST /api/buy` - Place buy order (paper trading)

## Technology Stack

**Frontend:**
- HTML/CSS/JavaScript (vanilla, no frameworks)
- Chart.js for visualizations
- Responsive design with CSS Grid/Flexbox

**Backend:**
- Python Flask (lightweight, fast)
- Alpaca API for portfolio data
- Yahoo Finance (yfinance) for stock research

**Data Sources:**
- Alpaca Markets API (portfolio, orders, trading)
- Yahoo Finance API (prices, fundamentals, charts)

## Customization

### Adding Your Own Recommendations

Edit the `RECOMMENDED_STOCKS` array in `app.py` to add stocks you're tracking:

```python
{
    'symbol': 'AAPL',
    'name': 'Apple Inc',
    'price': 185.00,
    'thesis': 'Your investment thesis here...',
    'catalyst_date': '2025-02-15',
    'catalyst_type': 'Earnings',
    'price_target_low': 200.00,
    'price_target_high': 220.00,
    'risk_reward': '2.5:1',
    'sector': 'Technology',
    'scores': {...},
    'total_score': 8
}
```

### Styling

All styles are in `static/css/style.css`. Customize colors by editing CSS variables at the top:

```css
:root {
    --primary: #00c805;      /* Main green color */
    --danger: #ff5000;       /* Red for losses */
    --bg: #ffffff;           /* Background */
    /* ... */
}
```

## Security Notes

⚠️ **This is for paper trading only!** Do not use with real money without additional security measures.

- Keep your `alpaca.json` credentials secure
- Never commit credentials to version control
- Consider adding authentication for production use
- The dashboard runs locally by default (localhost)

## Troubleshooting

**"Failed to fetch account"**
- Verify Alpaca credentials in `~/.openclaw/secrets/alpaca.json`
- Check that `baseUrl` points to paper trading API
- Ensure API keys are valid and active

**"Error loading stock data"**
- Yahoo Finance may have rate limits
- Try waiting a few seconds and searching again
- Some tickers may not be available

**Charts not displaying**
- Ensure Chart.js CDN is accessible
- Check browser console for JavaScript errors
- Clear browser cache and reload

**Port 5000 already in use**
- Change port in `app.py`: `app.run(port=5001)`
- Or kill the process using port 5000

## Future Enhancements

Ideas for expansion:
- [ ] Add stop-loss and limit order support
- [ ] Integrate Reddit/Twitter sentiment analysis
- [ ] Add insider trading data (SEC Form 4)
- [ ] Email/SMS alerts for catalyst dates
- [ ] Backtesting engine
- [ ] Performance analytics and win rate tracking
- [ ] Multi-account support
- [ ] Dark mode toggle

## License

Personal use only. Built for the SqueezeSeeker trading strategy.

---

**Happy Trading! 🚀📈**

Remember: This is paper trading for learning and strategy development. Always do your own research before investing real money.

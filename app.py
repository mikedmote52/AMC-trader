#!/usr/bin/env python3
"""
SqueezeSeeker Trading Dashboard - Flask Backend
Connects to Alpaca API for portfolio data and Yahoo Finance for research
"""

import json
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template
import requests
import yfinance as yf
from functools import lru_cache

app = Flask(__name__, static_folder='static', template_folder='static')

# Load Alpaca credentials (from env vars for production, file for local)
if os.environ.get('ALPACA_API_KEY'):
    # Production (Render)
    ALPACA_API_KEY = os.environ['ALPACA_API_KEY']
    ALPACA_API_SECRET = os.environ['ALPACA_API_SECRET']
    ALPACA_BASE_URL = os.environ.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
else:
    # Local development
    ALPACA_CREDS_PATH = os.path.expanduser('~/.openclaw/secrets/alpaca.json')
    with open(ALPACA_CREDS_PATH, 'r') as f:
        alpaca_creds = json.load(f)
    ALPACA_API_KEY = alpaca_creds['apiKey']
    ALPACA_API_SECRET = alpaca_creds['apiSecret']
    ALPACA_BASE_URL = alpaca_creds['baseUrl']

# Alpaca headers
ALPACA_HEADERS = {
    'APCA-API-KEY-ID': ALPACA_API_KEY,
    'APCA-API-SECRET-KEY': ALPACA_API_SECRET,
    'Content-Type': 'application/json'
}

# 10-Factor Scoring System from STRATEGY.md
SCORING_FACTORS = {
    'fundamental_story': {'name': 'Strong Fundamental Story', 'weight': 1, 'description': 'Revenue growth, partnerships, or product momentum'},
    'technical_setup': {'name': 'Technical Setup', 'weight': 1, 'description': 'Consolidation breaking, volume building, above key MAs'},
    'catalyst': {'name': 'Upcoming Catalyst', 'weight': 2, 'description': 'Earnings, FDA, launch within 2-4 weeks (DOUBLE WEIGHT)'},
    'theme_alignment': {'name': 'Theme Alignment', 'weight': 1, 'description': 'Part of hot sector (AI, quantum, biotech, etc.)'},
    'social_confirmation': {'name': 'Social Confirmation', 'weight': 1, 'description': 'Quality discussion building (not just hype)'},
    'insider_buying': {'name': 'Insider Buying', 'weight': 1, 'description': 'Recent Form 4 filings showing accumulation'},
    'float_short': {'name': 'Low Float/High Short', 'weight': 1, 'description': 'Squeeze potential if momentum hits'},
    'under_100': {'name': 'Under $100', 'weight': 1, 'description': 'Accessible price for retail'},
    'liquidity': {'name': 'Liquidity', 'weight': 1, 'description': 'Can enter/exit cleanly'},
    'no_blowoff': {'name': 'No Recent Blow-off Top', 'weight': 1, 'description': 'Not already up 100%+ in past week'}
}

# Sample recommended stocks with analysis
RECOMMENDED_STOCKS = [
    {
        'symbol': 'RGTI',
        'name': 'Rigetti Computing',
        'price': 15.84,
        'thesis': 'Quantum computing pure-play with upcoming catalysts. IBM partnership announced, government contracts pipeline. Low float creates squeeze potential.',
        'catalyst_date': '2025-02-15',
        'catalyst_type': 'Product Demo',
        'price_target_low': 22.00,
        'price_target_high': 35.00,
        'risk_reward': '3.2:1',
        'sector': 'Quantum Computing',
        'scores': {
            'fundamental_story': 1,
            'technical_setup': 1,
            'catalyst': 2,
            'theme_alignment': 1,
            'social_confirmation': 1,
            'insider_buying': 0,
            'float_short': 1,
            'under_100': 1,
            'liquidity': 1,
            'no_blowoff': 0
        },
        'total_score': 9
    },
    {
        'symbol': 'AI',
        'name': 'C3.ai Inc',
        'price': 38.45,
        'thesis': 'Enterprise AI leader with accelerating revenue growth. Q3 earnings catalyst in 2 weeks. Strong partnership pipeline with Fortune 500.',
        'catalyst_date': '2025-02-12',
        'catalyst_type': 'Earnings',
        'price_target_low': 52.00,
        'price_target_high': 68.00,
        'risk_reward': '2.8:1',
        'sector': 'Artificial Intelligence',
        'scores': {
            'fundamental_story': 1,
            'technical_setup': 1,
            'catalyst': 2,
            'theme_alignment': 1,
            'social_confirmation': 1,
            'insider_buying': 0,
            'float_short': 0,
            'under_100': 1,
            'liquidity': 1,
            'no_blowoff': 1
        },
        'total_score': 9
    },
    {
        'symbol': 'SOUN',
        'name': 'SoundHound AI',
        'price': 12.67,
        'thesis': 'Voice AI leader benefiting from Apple/Siri concerns. Multiple analyst upgrades recently. Strong recurring revenue model.',
        'catalyst_date': '2025-02-20',
        'catalyst_type': 'Conference Presentation',
        'price_target_low': 18.00,
        'price_target_high': 28.00,
        'risk_reward': '3.5:1',
        'sector': 'Artificial Intelligence',
        'scores': {
            'fundamental_story': 1,
            'technical_setup': 1,
            'catalyst': 2,
            'theme_alignment': 1,
            'social_confirmation': 1,
            'insider_buying': 1,
            'float_short': 1,
            'under_100': 1,
            'liquidity': 1,
            'no_blowoff': 0
        },
        'total_score': 10
    }
]


def get_alpaca_account():
    """Get account information from Alpaca"""
    url = f"{ALPACA_BASE_URL}/account"
    response = requests.get(url, headers=ALPACA_HEADERS)
    if response.status_code == 200:
        return response.json()
    return None


def get_alpaca_positions():
    """Get current positions from Alpaca"""
    url = f"{ALPACA_BASE_URL}/positions"
    response = requests.get(url, headers=ALPACA_HEADERS)
    if response.status_code == 200:
        positions = response.json()
        # Enrich with current prices and calculate P&L
        for pos in positions:
            try:
                ticker = yf.Ticker(pos['symbol'])
                current_price = ticker.info.get('currentPrice', float(pos['current_price']))
                pos['current_price'] = current_price
                pos['market_value'] = float(pos['qty']) * current_price
                pos['unrealized_pl'] = pos['market_value'] - float(pos['cost_basis'])
                pos['unrealized_plpc'] = (pos['unrealized_pl'] / float(pos['cost_basis'])) * 100 if float(pos['cost_basis']) > 0 else 0
            except:
                pass
        return positions
    return []


def get_alpaca_orders():
    """Get pending orders from Alpaca"""
    url = f"{ALPACA_BASE_URL}/orders?status=open"
    response = requests.get(url, headers=ALPACA_HEADERS)
    if response.status_code == 200:
        return response.json()
    return []


def place_alpaca_order(symbol, qty, side='buy', order_type='market'):
    """Place an order with Alpaca"""
    url = f"{ALPACA_BASE_URL}/orders"
    data = {
        'symbol': symbol,
        'qty': qty,
        'side': side,
        'type': order_type,
        'time_in_force': 'day'
    }
    response = requests.post(url, headers=ALPACA_HEADERS, json=data)
    return response.json() if response.status_code == 200 else {'error': response.text}


@lru_cache(maxsize=100)
def get_stock_data(symbol):
    """Get comprehensive stock data from Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Get historical data for charts
        hist = ticker.history(period='6mo')
        
        # Calculate technical indicators
        if len(hist) > 0:
            current_price = hist['Close'].iloc[-1]
            ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) >= 50 else None
            ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1] if len(hist) >= 200 else None
            
            # Calculate RSI
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not rsi.empty else None
        else:
            current_price = info.get('currentPrice', 0)
            ma_50 = None
            ma_200 = None
            current_rsi = None
        
        return {
            'symbol': symbol,
            'name': info.get('longName', symbol),
            'price': current_price,
            'previous_close': info.get('previousClose', current_price),
            'change': current_price - info.get('previousClose', current_price),
            'change_percent': ((current_price - info.get('previousClose', current_price)) / info.get('previousClose', current_price) * 100) if info.get('previousClose') else 0,
            'market_cap': info.get('marketCap', 0),
            'volume': info.get('volume', 0),
            'avg_volume': info.get('averageVolume', 0),
            'pe_ratio': info.get('trailingPE', None),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'ma_50': ma_50,
            'ma_200': ma_200,
            'rsi': current_rsi,
            'float': info.get('floatShares', 0),
            'short_ratio': info.get('shortRatio', 0),
            '52w_high': info.get('fiftyTwoWeekHigh', 0),
            '52w_low': info.get('fiftyTwoWeekLow', 0),
            'historical_data': hist.reset_index().to_dict('records') if len(hist) > 0 else []
        }
    except Exception as e:
        return {'error': str(e), 'symbol': symbol}


def analyze_stock(symbol):
    """Perform 10-factor analysis on a stock"""
    data = get_stock_data(symbol)
    
    if 'error' in data:
        return data
    
    scores = {
        'fundamental_story': 0,
        'technical_setup': 0,
        'catalyst': 0,
        'theme_alignment': 0,
        'social_confirmation': 0,
        'insider_buying': 0,
        'float_short': 0,
        'under_100': 0,
        'liquidity': 0,
        'no_blowoff': 0
    }
    
    analysis_notes = []
    
    # 1. Strong fundamental story
    if data.get('pe_ratio') and data['pe_ratio'] < 50:
        scores['fundamental_story'] = 1
        analysis_notes.append('Reasonable valuation (P/E < 50)')
    elif data.get('market_cap', 0) > 1e9:
        scores['fundamental_story'] = 1
        analysis_notes.append('Established company with $1B+ market cap')
    
    # 2. Technical setup
    if data.get('ma_50') and data.get('price'):
        if data['price'] > data['ma_50']:
            scores['technical_setup'] = 1
            analysis_notes.append(f"Price (${data['price']:.2f}) above 50-day MA (${data['ma_50']:.2f})")
    
    # 3. Catalyst - need to check earnings calendar (simplified)
    # For now, assume no known catalyst
    scores['catalyst'] = 0
    analysis_notes.append('No known catalyst in 2-4 week window (manual research needed)')
    
    # 4. Theme alignment
    hot_sectors = ['Technology', 'Healthcare', 'Communication Services', 'Artificial Intelligence', 'Biotechnology']
    if data.get('sector') in hot_sectors or any(sector in data.get('industry', '') for sector in ['AI', 'Biotech', 'Quantum', 'Semiconductor']):
        scores['theme_alignment'] = 1
        analysis_notes.append(f"In hot sector: {data.get('sector', 'Unknown')}")
    
    # 5. Social confirmation - placeholder
    scores['social_confirmation'] = 0
    analysis_notes.append('Social sentiment requires manual research')
    
    # 6. Insider buying - placeholder
    scores['insider_buying'] = 0
    analysis_notes.append('Insider activity requires manual research')
    
    # 7. Low float/high short
    if data.get('float', 0) < 50e6:  # Under 50M float
        scores['float_short'] = 1
        analysis_notes.append(f'Low float ({data["float"]/1e6:.1f}M shares) - squeeze potential')
    elif data.get('short_ratio', 0) > 5:
        scores['float_short'] = 1
        analysis_notes.append(f'High short ratio ({data["short_ratio"]:.1f}x)')
    
    # 8. Under $100
    if data.get('price', 0) < 100:
        scores['under_100'] = 1
        analysis_notes.append(f'Accessible price at ${data["price"]:.2f}')
    
    # 9. Liquidity
    if data.get('avg_volume', 0) > 1e6:  # 1M+ average volume
        scores['liquidity'] = 1
        analysis_notes.append(f'Good liquidity ({data["avg_volume"]/1e6:.1f}M avg volume)')
    
    # 10. No recent blow-off
    if data.get('52w_high') and data.get('price'):
        pct_from_high = (data['52w_high'] - data['price']) / data['52w_high'] * 100
        if pct_from_high > 20:  # At least 20% off highs
            scores['no_blowoff'] = 1
            analysis_notes.append(f'{pct_from_high:.1f}% off 52-week high - not blown out')
    
    total_score = sum(scores.values())
    
    return {
        'symbol': symbol,
        'data': data,
        'scores': scores,
        'total_score': total_score,
        'analysis_notes': analysis_notes,
        'recommendation': 'STRONG BUY' if total_score >= 9 else 'BUY' if total_score >= 7 else 'HOLD' if total_score >= 5 else 'AVOID',
        'scoring_factors': SCORING_FACTORS
    }


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/account')
def api_account():
    account = get_alpaca_account()
    if account:
        return jsonify({
            'cash': float(account.get('cash', 0)),
            'portfolio_value': float(account.get('portfolio_value', 0)),
            'buying_power': float(account.get('buying_power', 0)),
            'equity': float(account.get('equity', 0)),
            'status': account.get('status', 'UNKNOWN')
        })
    return jsonify({'error': 'Failed to fetch account'}), 500


@app.route('/api/positions')
def api_positions():
    positions = get_alpaca_positions()
    return jsonify(positions)


@app.route('/api/orders')
def api_orders():
    orders = get_alpaca_orders()
    return jsonify(orders)


@app.route('/api/recommendations')
def api_recommendations():
    # Update prices for recommendations
    updated_recommendations = []
    for stock in RECOMMENDED_STOCKS:
        try:
            ticker = yf.Ticker(stock['symbol'])
            info = ticker.info
            current_price = info.get('currentPrice', stock['price'])
            stock['current_price'] = current_price
            stock['change_percent'] = ((current_price - stock['price']) / stock['price']) * 100
            stock['scores_detail'] = SCORING_FACTORS
            updated_recommendations.append(stock)
        except:
            updated_recommendations.append(stock)
    return jsonify(updated_recommendations)


@app.route('/api/search')
def api_search():
    symbol = request.args.get('symbol', '').upper()
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    
    analysis = analyze_stock(symbol)
    return jsonify(analysis)


@app.route('/api/buy', methods=['POST'])
def api_buy():
    data = request.json
    symbol = data.get('symbol', '').upper()
    qty = data.get('qty', 1)
    
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    
    result = place_alpaca_order(symbol, qty, 'buy')
    return jsonify(result)


@app.route('/api/historical/<symbol>')
def api_historical(symbol):
    try:
        ticker = yf.Ticker(symbol.upper())
        hist = ticker.history(period='3mo')
        data = []
        for index, row in hist.iterrows():
            data.append({
                'date': index.strftime('%Y-%m-%d'),
                'open': round(row['Open'], 2),
                'high': round(row['High'], 2),
                'low': round(row['Low'], 2),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume'])
            })
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

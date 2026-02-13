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

app = Flask(__name__, static_folder='static', template_folder='static')

def load_alpaca_config():
    """Load Alpaca configuration from env vars or local OpenClaw secret file."""
    env_key = os.environ.get('ALPACA_API_KEY')
    env_secret = os.environ.get('ALPACA_API_SECRET')
    env_base = os.environ.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

    def normalize_base_url(base_url):
        cleaned = (base_url or 'https://paper-api.alpaca.markets').rstrip('/')
        return cleaned[:-3] if cleaned.endswith('/v2') else cleaned

    if env_key and env_secret:
        return {
            'enabled': True,
            'source': 'env',
            'api_key': env_key,
            'api_secret': env_secret,
            'base_url': normalize_base_url(env_base)
        }

    creds_path = os.path.expanduser('~/.openclaw/secrets/alpaca.json')
    try:
        with open(creds_path, 'r', encoding='utf-8') as file_handle:
            alpaca_creds = json.load(file_handle)
        return {
            'enabled': True,
            'source': creds_path,
            'api_key': alpaca_creds['apiKey'],
            'api_secret': alpaca_creds['apiSecret'],
            'base_url': normalize_base_url(alpaca_creds.get('baseUrl', 'https://paper-api.alpaca.markets'))
        }
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        return {
            'enabled': False,
            'source': creds_path,
            'error': str(exc),
            'api_key': '',
            'api_secret': '',
            'base_url': 'https://paper-api.alpaca.markets'
        }


ALPACA_CONFIG = load_alpaca_config()

# Alpaca headers (empty when disabled)
ALPACA_HEADERS = {
    'APCA-API-KEY-ID': ALPACA_CONFIG['api_key'],
    'APCA-API-SECRET-KEY': ALPACA_CONFIG['api_secret'],
    'Content-Type': 'application/json'
} if ALPACA_CONFIG['enabled'] else {}

STOCK_DATA_CACHE = {}
STOCK_DATA_CACHE_TTL_SECONDS = int(os.environ.get('STOCK_DATA_CACHE_TTL_SECONDS', '300'))

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
    if not ALPACA_CONFIG['enabled']:
        return {
            'cash': 100000,
            'portfolio_value': 100000,
            'buying_power': 100000,
            'equity': 100000,
            'status': 'SIMULATION',
            'data_mode': 'offline'
        }

    url = f"{ALPACA_CONFIG['base_url']}/v2/account"
    response = requests.get(url, headers=ALPACA_HEADERS, timeout=10)
    if response.status_code == 200:
        return response.json()
    return None


def get_alpaca_positions():
    """Get current positions from Alpaca"""
    if not ALPACA_CONFIG['enabled']:
        return []

    url = f"{ALPACA_CONFIG['base_url']}/v2/positions"
    response = requests.get(url, headers=ALPACA_HEADERS, timeout=10)
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
            except Exception as exc:
                app.logger.warning('Failed to enrich position for %s: %s', pos.get('symbol', 'UNKNOWN'), exc)
        return positions
    return []


def get_alpaca_orders():
    """Get pending orders from Alpaca"""
    if not ALPACA_CONFIG['enabled']:
        return []

    url = f"{ALPACA_CONFIG['base_url']}/v2/orders?status=open"
    response = requests.get(url, headers=ALPACA_HEADERS, timeout=10)
    if response.status_code == 200:
        return response.json()
    return []


def place_alpaca_order(symbol, qty, side='buy', order_type='market'):
    """Place an order with Alpaca"""
    if not ALPACA_CONFIG['enabled']:
        return {
            'error': 'Trading unavailable: missing Alpaca credentials at ~/.openclaw/secrets/alpaca.json or ALPACA_API_KEY/ALPACA_API_SECRET env vars.'
        }

    url = f"{ALPACA_CONFIG['base_url']}/v2/orders"
    data = {
        'symbol': symbol,
        'qty': qty,
        'side': side,
        'type': order_type,
        'time_in_force': 'day'
    }
    response = requests.post(url, headers=ALPACA_HEADERS, json=data, timeout=10)
    return response.json() if response.status_code in (200, 201) else {'error': response.text}


def _build_offline_stock_data(symbol, error_message):
    """Return deterministic fallback stock data when market data providers are unavailable."""
    return {
        'symbol': symbol,
        'name': symbol,
        'price': 0.0,
        'previous_close': 0.0,
        'change': 0.0,
        'change_percent': 0.0,
        'market_cap': 0,
        'volume': 0,
        'avg_volume': 0,
        'pe_ratio': None,
        'sector': 'Unknown',
        'industry': 'Unknown',
        'ma_50': None,
        'ma_200': None,
        'rsi': None,
        'float': 0,
        'short_ratio': 0,
        '52w_high': 0,
        '52w_low': 0,
        'historical_data': [],
        'data_source': 'offline_fallback',
        'data_error': error_message,
    }


def get_stock_data(symbol):
    """Get comprehensive stock data from Yahoo Finance with success-only caching."""
    symbol = symbol.upper().strip()
    cached = STOCK_DATA_CACHE.get(symbol)
    if cached:
        cache_age = (datetime.utcnow() - cached['cached_at']).total_seconds()
        if cache_age < STOCK_DATA_CACHE_TTL_SECONDS:
            return cached['data']

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='6mo', auto_adjust=False)
        if hist.empty:
            raise ValueError('No historical data returned for symbol')

        fast_info = getattr(ticker, 'fast_info', {}) or {}
        try:
            info = ticker.info or {}
        except Exception as exc:
            app.logger.warning('ticker.info unavailable for %s: %s', symbol, exc)
            info = {}

        current_price = float(hist['Close'].iloc[-1])
        previous_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else float(fast_info.get('previousClose', current_price) or current_price)
        ma_50 = float(hist['Close'].rolling(window=50).mean().iloc[-1]) if len(hist) >= 50 else None
        ma_200 = float(hist['Close'].rolling(window=200).mean().iloc[-1]) if len(hist) >= 200 else None

        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = float(rsi.iloc[-1]) if not rsi.empty else None

        avg_volume = float(hist['Volume'].tail(20).mean()) if len(hist) >= 20 else float(hist['Volume'].mean())
        year_window = hist.tail(252) if len(hist) >= 252 else hist

        historical_rows = []
        for idx, row in hist.tail(120).iterrows():
            historical_rows.append({
                'date': idx.strftime('%Y-%m-%d'),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume'])
            })

        stock_data = {
            'symbol': symbol,
            'name': info.get('longName', symbol),
            'price': current_price,
            'previous_close': previous_close,
            'change': current_price - previous_close,
            'change_percent': ((current_price - previous_close) / previous_close * 100) if previous_close else 0,
            'market_cap': int(info.get('marketCap') or fast_info.get('marketCap') or 0),
            'volume': int(hist['Volume'].iloc[-1]) if len(hist) else 0,
            'avg_volume': avg_volume,
            'pe_ratio': info.get('trailingPE'),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'ma_50': ma_50,
            'ma_200': ma_200,
            'rsi': current_rsi,
            'float': int(info.get('floatShares') or 0),
            'short_ratio': float(info.get('shortRatio') or 0),
            '52w_high': float(info.get('fiftyTwoWeekHigh') or year_window['High'].max() or 0),
            '52w_low': float(info.get('fiftyTwoWeekLow') or year_window['Low'].min() or 0),
            'historical_data': historical_rows,
            'data_source': 'yfinance',
        }

        STOCK_DATA_CACHE[symbol] = {
            'cached_at': datetime.utcnow(),
            'data': stock_data,
        }
        return stock_data
    except Exception as exc:
        app.logger.warning('Stock data fetch failed for %s: %s', symbol, exc)
        return _build_offline_stock_data(symbol, str(exc))


def analyze_stock(symbol):
    """Perform 10-factor analysis on a stock"""
    data = get_stock_data(symbol)

    if data.get('data_source') == 'offline_fallback':
        return {
            'symbol': symbol,
            'data': data,
            'scores': {key: 0 for key in SCORING_FACTORS.keys()},
            'total_score': 0,
            'analysis_notes': [
                'Live market data unavailable right now. Please retry in a moment.',
                f"Provider error: {data.get('data_error', 'Unknown error')}"
            ],
            'recommendation': 'DATA UNAVAILABLE',
            'scoring_factors': SCORING_FACTORS
        }
    
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
            'status': account.get('status', 'UNKNOWN'),
            'alpaca_connected': ALPACA_CONFIG['enabled'],
            'alpaca_source': ALPACA_CONFIG['source']
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
        except Exception as exc:
            app.logger.warning('Failed to refresh recommendation for %s: %s', stock.get('symbol', 'UNKNOWN'), exc)
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
    flask_debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    app.run(debug=flask_debug, host='0.0.0.0', port=5000)

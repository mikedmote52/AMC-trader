#!/usr/bin/env python3
"""
SqueezeSeeker Trading Dashboard - Flask Backend
Connects to Open Claw V4 Scanner API for live data,
Alpaca API for portfolio, and Yahoo Finance for research.
"""

import json
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template
import requests
import yfinance as yf
from functools import lru_cache

app = Flask(__name__, static_folder='static', template_folder='static')

# Open Claw API URL (FastAPI server on VM or Render)
OPENCLAW_API_URL = os.environ.get('OPENCLAW_API_URL', 'http://localhost:8000')

# Load Alpaca credentials (from env vars for production, file for local)
if os.environ.get('ALPACA_API_KEY'):
    ALPACA_API_KEY = os.environ['ALPACA_API_KEY']
    ALPACA_API_SECRET = os.environ['ALPACA_API_SECRET']
    ALPACA_BASE_URL = os.environ.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
else:
    ALPACA_CREDS_PATH = os.path.expanduser('~/.openclaw/secrets/alpaca.json')
    try:
        with open(ALPACA_CREDS_PATH, 'r') as f:
            alpaca_creds = json.load(f)
        ALPACA_API_KEY = alpaca_creds['apiKey']
        ALPACA_API_SECRET = alpaca_creds['apiSecret']
        ALPACA_BASE_URL = alpaca_creds['baseUrl']
    except FileNotFoundError:
        ALPACA_API_KEY = ''
        ALPACA_API_SECRET = ''
        ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'

# Normalize base URL to include /v2
if ALPACA_BASE_URL and not ALPACA_BASE_URL.rstrip('/').endswith('/v2'):
    ALPACA_BASE_URL = ALPACA_BASE_URL.rstrip('/') + '/v2'

# Alpaca headers
ALPACA_HEADERS = {
    'APCA-API-KEY-ID': ALPACA_API_KEY,
    'APCA-API-SECRET-KEY': ALPACA_API_SECRET,
    'Content-Type': 'application/json'
}


def fetch_openclaw(endpoint, timeout=10):
    """Fetch data from Open Claw API with error handling"""
    try:
        url = f"{OPENCLAW_API_URL}{endpoint}"
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {'error': 'Open Claw API unavailable', 'offline': True}
    except requests.exceptions.Timeout:
        return {'error': 'Open Claw API timeout', 'offline': True}
    except Exception as e:
        return {'error': str(e)}


def post_openclaw(endpoint, payload, timeout=10):
    """POST data to Open Claw API with error handling"""
    try:
        url = f"{OPENCLAW_API_URL}{endpoint}"
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {'error': 'Open Claw API unavailable', 'offline': True}
    except requests.exceptions.Timeout:
        return {'error': 'Open Claw API timeout', 'offline': True}
    except Exception as e:
        return {'error': str(e)}


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
        for pos in positions:
            try:
                ticker = yf.Ticker(pos['symbol'])
                current_price = ticker.info.get('currentPrice', float(pos['current_price']))
                pos['current_price'] = current_price
                pos['market_value'] = float(pos['qty']) * current_price
                pos['unrealized_pl'] = pos['market_value'] - float(pos['cost_basis'])
                pos['unrealized_plpc'] = (pos['unrealized_pl'] / float(pos['cost_basis'])) * 100 if float(pos['cost_basis']) > 0 else 0
            except Exception:
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
        hist = ticker.history(period='6mo')

        if len(hist) > 0:
            current_price = hist['Close'].iloc[-1]
            ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) >= 50 else None
            ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1] if len(hist) >= 200 else None
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
            'last_equity': float(account.get('last_equity', 0)),
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


@app.route('/api/scanner/results')
def api_scanner_results():
    """Get latest V4 scanner candidates from Open Claw API"""
    data = fetch_openclaw('/api/scanner/latest')
    if data.get('offline'):
        return jsonify({
            'scanner_version': 'OFFLINE',
            'candidates': [],
            'message': 'Open Claw scanner is offline. Start the API server.'
        })
    return jsonify(data)


@app.route('/api/scanner/status')
def api_scanner_status():
    """Get scanner health and gate funnel stats from Open Claw"""
    data = fetch_openclaw('/api/scanner/status')
    return jsonify(data)


@app.route('/api/scanner/history')
def api_scanner_history():
    """Get 7-day scanner history from Open Claw"""
    data = fetch_openclaw('/api/scanner/history')
    return jsonify(data)


@app.route('/api/learning/performance')
def api_learning_performance():
    """Get learning system performance from Open Claw"""
    data = fetch_openclaw('/api/learning/performance')
    return jsonify(data)


@app.route('/api/learning/weights')
def api_learning_weights():
    """Get current V4 scoring weights from Open Claw"""
    data = fetch_openclaw('/api/learning/weights')
    return jsonify(data)


@app.route('/api/thesis')
def api_thesis():
    """Get active thesis for positions from Open Claw"""
    data = fetch_openclaw('/api/portfolio/thesis')
    return jsonify(data)


@app.route('/api/search')
def api_search():
    """Search and analyze a stock using Yahoo Finance + Open Claw scanner data"""
    symbol = request.args.get('symbol', '').upper()
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400

    stock_data = get_stock_data(symbol)
    if 'error' in stock_data:
        return jsonify(stock_data)

    # Check if this symbol is in the latest scanner results
    scanner_match = None
    scanner_data = fetch_openclaw('/api/scanner/latest')
    if not scanner_data.get('error'):
        for candidate in scanner_data.get('candidates', []):
            if candidate.get('symbol') == symbol:
                scanner_match = candidate
                break

    result = {
        'symbol': symbol,
        'data': stock_data,
        'scanner_match': scanner_match,
    }

    if scanner_match:
        result['v4_score'] = scanner_match.get('total_score', 0)
        result['explosion_probability'] = scanner_match.get('explosion_probability', 0)
        result['vigl_bonus'] = scanner_match.get('vigl_bonus', 0)
        result['tier'] = scanner_match.get('tier', 'N/A')
        result['rvol'] = scanner_match.get('rvol', 0)
    else:
        result['v4_score'] = None
        result['note'] = 'Not in current V4 scanner results'

    return jsonify(result)


@app.route('/api/trade', methods=['POST'])
def api_trade():
    """Place buy or sell order. Supports shares (qty) or dollars (notional)."""
    data = request.json
    symbol = data.get('symbol', '').upper()
    side = data.get('side', 'buy').lower()
    order_type = data.get('order_type', 'market')

    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    if side not in ('buy', 'sell'):
        return jsonify({'error': 'Side must be buy or sell'}), 400

    url = f"{ALPACA_BASE_URL}/orders"
    order_data = {
        'symbol': symbol,
        'side': side,
        'type': order_type,
        'time_in_force': 'day'
    }

    # Support either qty (shares) or notional (dollars)
    if data.get('notional'):
        order_data['notional'] = str(data['notional'])
    elif data.get('qty'):
        order_data['qty'] = str(data['qty'])
    else:
        return jsonify({'error': 'Must provide qty (shares) or notional (dollars)'}), 400

    response = requests.post(url, headers=ALPACA_HEADERS, json=order_data)
    if response.status_code in (200, 201):
        return jsonify(response.json())
    return jsonify({'error': response.text}), response.status_code


@app.route('/api/buy', methods=['POST'])
def api_buy():
    """Legacy buy endpoint - redirects to /api/trade"""
    data = request.json
    data['side'] = 'buy'
    with app.test_request_context(json=data):
        return api_trade()


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


@app.route('/api/approval/queue')
def api_approval_queue():
    """Get pending approval queue from Open Claw"""
    data = fetch_openclaw('/api/approval/queue')
    return jsonify(data)


@app.route('/api/approval/decide', methods=['POST'])
def api_approval_decide():
    """Submit approval/rejection decision to Open Claw"""
    payload = request.json
    data = post_openclaw('/api/approval/decide', payload)
    if data.get('offline'):
        return jsonify(data), 503
    return jsonify(data)


@app.route('/api/approval/history')
def api_approval_history():
    """Get approval history (optionally filtered by status) from Open Claw"""
    status = request.args.get('status', '')
    endpoint = f'/api/approval/history?status={status}' if status else '/api/approval/history'
    data = fetch_openclaw(endpoint)
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

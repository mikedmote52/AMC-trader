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

app = Flask(__name__, static_folder='static', template_folder='static')

# Open Claw API URL (FastAPI server on VM or Render)
OPENCLAW_API_URL = os.environ.get('OPENCLAW_API_URL', 'http://localhost:8000')


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
    if not ALPACA_CONFIG['enabled']:
        return {
            'cash': 100000,
            'portfolio_value': 100000,
            'buying_power': 100000,
            'equity': 100000,
            'last_equity': 100000,
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

    # If data provider failed, return structured fallback
    if stock_data.get('data_source') == 'offline_fallback':
        return jsonify({
            'symbol': symbol,
            'data': stock_data,
            'scanner_match': None,
            'v4_score': None,
            'note': f"Market data unavailable: {stock_data.get('data_error', 'Unknown error')}"
        })

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
    if not ALPACA_CONFIG['enabled']:
        return jsonify({'error': 'Trading unavailable: missing Alpaca credentials'}), 503

    data = request.json
    symbol = data.get('symbol', '').upper()
    side = data.get('side', 'buy').lower()
    order_type = data.get('order_type', 'market')

    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    if side not in ('buy', 'sell'):
        return jsonify({'error': 'Side must be buy or sell'}), 400

    url = f"{ALPACA_CONFIG['base_url']}/v2/orders"
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

    response = requests.post(url, headers=ALPACA_HEADERS, json=order_data, timeout=10)
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


@app.route('/api/performance')
def api_performance():
    """Return performance projections based on current portfolio"""
    try:
        if not ALPACA_CONFIG['enabled']:
            return jsonify({'error': 'Alpaca not configured'}), 503
            
        # Get account info
        account_url = f"{ALPACA_CONFIG['base_url']}/v2/account"
        account_resp = requests.get(account_url, headers=ALPACA_HEADERS, timeout=10)
        
        if account_resp.status_code != 200:
            return jsonify({'error': f'Alpaca API error: {account_resp.status_code}'}), 500
            
        account = account_resp.json()
        account_value = float(account['portfolio_value'])
        starting_value = 101000.0  # TODO: Make this configurable
        days_active = 10  # TODO: Calculate from actual trading history
        
        current_return = account_value - starting_value
        current_return_pct = (current_return / starting_value) * 100
        daily_avg = current_return_pct / days_active if days_active > 0 else 0
        
        # Annual projection (252 trading days)
        annual_multiplier = (1 + daily_avg/100) ** 252
        annual_ending = starting_value * annual_multiplier
        annual_gain = annual_ending - starting_value
        annual_return_pct = (annual_gain / starting_value) * 100
        
        # Monthly projection (21 trading days)
        monthly_multiplier = (1 + daily_avg/100) ** 21
        monthly_gain = starting_value * (monthly_multiplier - 1)
        
        return jsonify({
            'performance': {
                'account_value': round(account_value, 2),
                'starting_value': round(starting_value, 2),
                'total_return': round(current_return, 2),
                'total_return_pct': round(current_return_pct, 2),
                'days_active': days_active,
                'daily_avg_pct': round(daily_avg, 4),
                'annual_projection': round(annual_gain, 2),
                'annual_projection_pct': round(annual_return_pct, 1),
                'monthly_projection': round(monthly_gain, 2)
            }
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


if __name__ == '__main__':
    flask_debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    app.run(debug=flask_debug, host='0.0.0.0', port=5000)

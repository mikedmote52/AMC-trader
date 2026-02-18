# ============================================================================
# GHOST PORTFOLIO - Add this code to app.py after place_alpaca_order()
# ============================================================================

def get_closed_positions():
    """Load closed positions from JSON file"""
    closed_positions_file = os.path.expanduser('~/.openclaw/workspace/data/closed_positions.json')

    try:
        if os.path.exists(closed_positions_file):
            with open(closed_positions_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        app.logger.error(f'Error loading closed positions: {e}')

    return []


def save_closed_position(symbol, entry_date, entry_price, exit_date, exit_price, qty):
    """Save a closed position to the tracking file"""
    closed_positions_file = os.path.expanduser('~/.openclaw/workspace/data/closed_positions.json')

    try:
        # Load existing positions
        positions = get_closed_positions()

        # Calculate actual gain
        actual_gain = (exit_price - entry_price) * qty
        actual_gain_percent = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

        # Add new closed position
        positions.append({
            'symbol': symbol,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'exit_date': exit_date,
            'exit_price': exit_price,
            'qty': qty,
            'actual_gain': actual_gain,
            'actual_gain_percent': actual_gain_percent
        })

        # Save back to file
        os.makedirs(os.path.dirname(closed_positions_file), exist_ok=True)
        with open(closed_positions_file, 'w') as f:
            json.dump(positions, f, indent=2)

        app.logger.info(f'Saved closed position: {symbol} @ ${exit_price}')
    except Exception as e:
        app.logger.error(f'Error saving closed position: {e}')


def get_current_price_for_symbol(symbol):
    """Get current price for a symbol using yfinance"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='1d')
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        app.logger.warning(f'Could not fetch price for {symbol}: {e}')
    return None


# ============================================================================
# API ENDPOINT - Add this with the other @app.route definitions (around line 320)
# ============================================================================

@app.route('/api/ghost/portfolio')
def api_ghost_portfolio():
    """Get ghost portfolio - closed positions with current theoretical value"""
    try:
        closed_positions = get_closed_positions()

        if not closed_positions:
            return jsonify({
                'summary': {
                    'total_realized_gains': 0,
                    'theoretical_current_value': 0,
                    'total_closed_positions': 0,
                    'avg_hold_days': 0
                },
                'closed_positions': []
            })

        total_realized = 0
        total_theoretical = 0
        enriched_positions = []

        for pos in closed_positions:
            # Get current price
            current_price = get_current_price_for_symbol(pos['symbol'])

            if current_price is None:
                # Skip if we can't get current price
                continue

            # Calculate theoretical gain if still holding
            entry_price = pos['entry_price']
            qty = pos['qty']
            theoretical_gain = (current_price - entry_price) * qty
            theoretical_gain_percent = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

            # Calculate hold days
            try:
                entry_date = datetime.fromisoformat(pos['entry_date'].replace('Z', '+00:00'))
                exit_date = datetime.fromisoformat(pos['exit_date'].replace('Z', '+00:00'))
                hold_days = (exit_date - entry_date).days
            except:
                hold_days = 0

            total_realized += pos['actual_gain']
            total_theoretical += theoretical_gain

            enriched_positions.append({
                'symbol': pos['symbol'],
                'entry_date': pos['entry_date'],
                'entry_price': entry_price,
                'exit_date': pos['exit_date'],
                'exit_price': pos['exit_price'],
                'qty': qty,
                'actual_gain': pos['actual_gain'],
                'actual_gain_percent': pos['actual_gain_percent'],
                'current_price': current_price,
                'theoretical_gain': theoretical_gain,
                'theoretical_gain_percent': theoretical_gain_percent,
                'hold_days': hold_days
            })

        # Calculate summary
        avg_hold_days = sum(p['hold_days'] for p in enriched_positions) / len(enriched_positions) if enriched_positions else 0

        return jsonify({
            'summary': {
                'total_realized_gains': round(total_realized, 2),
                'theoretical_current_value': round(total_theoretical, 2),
                'total_closed_positions': len(enriched_positions),
                'avg_hold_days': round(avg_hold_days, 1)
            },
            'closed_positions': enriched_positions
        })

    except Exception as e:
        app.logger.error(f'Error in ghost portfolio: {e}')
        return jsonify({'error': str(e)}), 500

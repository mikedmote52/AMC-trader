#!/usr/bin/env python3
"""
DYNAMIC EXIT MANAGER V1.0 - Adaptive Stop-Loss & Profit-Taking

Replaces the static -15% stop / +30% profit-take with trade-type-aware
dynamic exits that let squeeze plays run while protecting gains.

The core insight from the reference portfolio:
- VIGL went +324%, CRWV +171%, AEVA +162%
- A static +30% sell would have cut these winners short
- Squeeze plays need wide initial stops and trailing exits
- Momentum plays need tighter management

Exit Profiles:
1. SQUEEZE: Wide initial stop (-25%), trailing stop kicks in at +50%
   - At +50%: trail at 40% of peak (so if peak is +100%, stop at +60%)
   - At +100%: tighten trail to 50% of peak
   - At +200%: tighten trail to 60% of peak
   - Let the squeeze run, protect the bulk of gains

2. MOMENTUM: Tighter management for predictable moves
   - Initial stop: -15%
   - At +20%: trail at 50% of peak
   - At +40%: take 30% off, trail rest at 60% of peak

3. DEFAULT: For positions without a tagged trade type
   - Uses the old rules: -15% stop, +30% half-sell
   - Applies to legacy positions entered before this system

Usage:
  python3 dynamic_exit_manager.py              # Check all positions, execute exits
  python3 dynamic_exit_manager.py --dry-run    # Show what would happen, no execution
  python3 dynamic_exit_manager.py --status     # Show current position status with exit levels

Runs on cron: every 30 minutes during market hours
"""

import json
import os
import sys
from datetime import datetime, date
import requests as http_requests

WORKSPACE = '/Users/mikeclawd/.openclaw/workspace'
SECRETS_DIR = '/Users/mikeclawd/.openclaw/secrets'
EXIT_STATE_FILE = os.path.join(WORKSPACE, 'data', 'exit_state.json')
ALLOCATION_LOG = os.path.join(WORKSPACE, 'data', 'allocation_history.json')

sys.path.insert(0, os.path.join(WORKSPACE, 'scripts'))

try:
    from telegram_alert import send_alert
except:
    def send_alert(msg): print(f"[TELEGRAM] {msg}")

try:
    from scanner_performance_tracker import update_trade_outcome
except:
    def update_trade_outcome(symbol, exit_price): pass  # Graceful if tracker unavailable


def get_alpaca_client():
    """Get Alpaca API credentials and headers"""
    with open(os.path.join(SECRETS_DIR, 'alpaca.json'), 'r') as f:
        creds = json.load(f)
    headers = {
        'APCA-API-KEY-ID': creds['apiKey'],
        'APCA-API-SECRET-KEY': creds['apiSecret']
    }
    base = creds.get('baseUrl', 'https://paper-api.alpaca.markets')
    return headers, base


def load_exit_state():
    """
    Load per-position exit configuration.
    Stores: trade_type, peak_gain, entry_date, exit_profile
    """
    try:
        if os.path.exists(EXIT_STATE_FILE):
            with open(EXIT_STATE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}


def save_exit_state(state):
    """Save exit state"""
    try:
        os.makedirs(os.path.dirname(EXIT_STATE_FILE), exist_ok=True)
        with open(EXIT_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except:
        pass


def get_trade_type(symbol):
    """
    Look up the trade type for a position from allocation history.
    Returns: 'squeeze', 'momentum', or 'default'
    """
    try:
        if os.path.exists(ALLOCATION_LOG):
            with open(ALLOCATION_LOG, 'r') as f:
                history = json.load(f)

            # Search backwards for most recent allocation of this symbol
            for decision in reversed(history):
                for alloc in decision.get('allocations', []):
                    if alloc.get('symbol') == symbol:
                        return decision.get('trade_type', 'default')
    except:
        pass
    return 'default'


def calculate_exit_action(symbol, current_gain_pct, exit_state_entry, qty):
    """
    Determine what exit action to take for a position.

    Returns: {
        'action': 'HOLD' | 'STOP_LOSS' | 'TRAILING_STOP' | 'PARTIAL_PROFIT' | 'FULL_EXIT',
        'sell_qty': int,
        'reason': str,
        'new_peak': float
    }
    """
    trade_type = exit_state_entry.get('trade_type', 'default')
    peak_gain = exit_state_entry.get('peak_gain', current_gain_pct)
    partial_taken = exit_state_entry.get('partial_taken', False)

    # Update peak
    new_peak = max(peak_gain, current_gain_pct)

    if trade_type == 'squeeze':
        return _squeeze_exit(symbol, current_gain_pct, new_peak, qty, partial_taken)
    elif trade_type == 'momentum':
        return _momentum_exit(symbol, current_gain_pct, new_peak, qty, partial_taken)
    else:
        return _default_exit(symbol, current_gain_pct, new_peak, qty, partial_taken)


def _squeeze_exit(symbol, gain, peak, qty, partial_taken):
    """
    Squeeze play exit logic — let it run.

    Stages:
    - Below -25%: hard stop, full exit
    - 0% to +50%: hold, no trailing stop yet (squeezes need room)
    - +50% to +100%: trail at 40% of peak (peak +80% → stop at +48%)
    - +100% to +200%: trail at 50% of peak (peak +150% → stop at +75%)
    - +200%+: trail at 60% of peak (peak +300% → stop at +180%)
    """
    # Hard stop
    if gain <= -25:
        return {
            'action': 'STOP_LOSS',
            'sell_qty': int(qty),
            'reason': f"Squeeze stop-loss at {gain:.1f}% (limit: -25%)",
            'new_peak': peak
        }

    # Below +50%: just hold, squeeze hasn't confirmed yet
    if peak < 50:
        return {
            'action': 'HOLD',
            'sell_qty': 0,
            'reason': f"Squeeze building: {gain:+.1f}% (peak: {peak:+.1f}%, waiting for +50%)",
            'new_peak': peak
        }

    # Determine trailing stop level based on peak tier
    if peak >= 200:
        trail_pct = 0.60  # Protect 60% of peak
    elif peak >= 100:
        trail_pct = 0.50  # Protect 50% of peak
    else:  # 50-99%
        trail_pct = 0.40  # Protect 40% of peak

    trail_stop = peak * trail_pct

    if gain <= trail_stop:
        return {
            'action': 'TRAILING_STOP',
            'sell_qty': int(qty),
            'reason': f"Squeeze trailing stop: {gain:.1f}% fell below {trail_stop:.1f}% (peak: {peak:.1f}%, trail: {trail_pct*100:.0f}%)",
            'new_peak': peak
        }

    return {
        'action': 'HOLD',
        'sell_qty': 0,
        'reason': f"Squeeze running: {gain:+.1f}% (peak: {peak:+.1f}%, trail stop: {trail_stop:+.1f}%)",
        'new_peak': peak
    }


def _momentum_exit(symbol, gain, peak, qty, partial_taken):
    """
    Momentum play exit logic — tighter management.

    Stages:
    - Below -15%: hard stop, full exit
    - +20% to +40%: trail at 50% of peak
    - +40%+: take 30% partial if not already taken, trail rest at 60% of peak
    """
    # Hard stop
    if gain <= -15:
        return {
            'action': 'STOP_LOSS',
            'sell_qty': int(qty),
            'reason': f"Momentum stop-loss at {gain:.1f}% (limit: -15%)",
            'new_peak': peak
        }

    # Below +20%: hold
    if peak < 20:
        return {
            'action': 'HOLD',
            'sell_qty': 0,
            'reason': f"Momentum developing: {gain:+.1f}% (waiting for +20%)",
            'new_peak': peak
        }

    # +40%+ partial profit taking
    if peak >= 40 and not partial_taken:
        sell_qty = max(1, int(qty * 0.3))  # Sell 30%
        return {
            'action': 'PARTIAL_PROFIT',
            'sell_qty': sell_qty,
            'reason': f"Momentum +{peak:.0f}%: taking 30% profit ({sell_qty} shares)",
            'new_peak': peak
        }

    # Trailing stop
    if peak >= 40:
        trail_pct = 0.60
    else:
        trail_pct = 0.50

    trail_stop = peak * trail_pct

    if gain <= trail_stop:
        return {
            'action': 'TRAILING_STOP',
            'sell_qty': int(qty),
            'reason': f"Momentum trailing stop: {gain:.1f}% below {trail_stop:.1f}% (peak: {peak:.1f}%)",
            'new_peak': peak
        }

    return {
        'action': 'HOLD',
        'sell_qty': 0,
        'reason': f"Momentum riding: {gain:+.1f}% (peak: {peak:+.1f}%, trail: {trail_stop:+.1f}%)",
        'new_peak': peak
    }


def _default_exit(symbol, gain, peak, qty, partial_taken):
    """
    Default exit logic for legacy positions — close to original V3.2 rules
    but slightly improved with trailing instead of fixed targets.

    - Stop: -15% full exit
    - +30%: sell 50% (once), then trail remaining at 50% of peak
    """
    if gain <= -15:
        return {
            'action': 'STOP_LOSS',
            'sell_qty': int(qty),
            'reason': f"Default stop-loss at {gain:.1f}%",
            'new_peak': peak
        }

    if peak >= 30 and not partial_taken:
        sell_qty = max(1, int(qty * 0.5))
        return {
            'action': 'PARTIAL_PROFIT',
            'sell_qty': sell_qty,
            'reason': f"Default +{peak:.0f}% profit: selling 50% ({sell_qty} shares)",
            'new_peak': peak
        }

    if peak >= 30 and partial_taken:
        trail_stop = peak * 0.50
        if gain <= trail_stop:
            return {
                'action': 'TRAILING_STOP',
                'sell_qty': int(qty),
                'reason': f"Default trail stop: {gain:.1f}% below {trail_stop:.1f}%",
                'new_peak': peak
            }

    return {
        'action': 'HOLD',
        'sell_qty': 0,
        'reason': f"Default hold: {gain:+.1f}% (peak: {peak:+.1f}%)",
        'new_peak': peak
    }


def execute_sell(headers, base, symbol, qty, reason):
    """Execute a sell order via Alpaca"""
    try:
        order = http_requests.post(
            f"{base}/v2/orders",
            headers=headers,
            json={
                'symbol': symbol,
                'qty': str(int(qty)),
                'side': 'sell',
                'type': 'market',
                'time_in_force': 'day'
            }
        )

        if order.status_code in [200, 201]:
            order_data = order.json()
            print(f"   ✅ SELL {qty} {symbol} — {reason}")
            return True
        else:
            print(f"   ❌ SELL FAILED {symbol}: {order.status_code} {order.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ SELL ERROR {symbol}: {e}")
        return False


def run_exit_check(dry_run=False, status_only=False):
    """Main exit check loop"""
    print("=" * 70)
    print(f"🛡️  DYNAMIC EXIT MANAGER V1.0")
    print(f"{datetime.now().strftime('%I:%M %p PT')}")
    print("=" * 70)

    headers, base = get_alpaca_client()

    # Get all positions
    positions = http_requests.get(f"{base}/v2/positions", headers=headers).json()

    if not positions:
        print("\n📭 No open positions")
        return

    # Load exit state
    exit_state = load_exit_state()

    actions_taken = []

    print(f"\n📊 Checking {len(positions)} positions...\n")

    for pos in positions:
        symbol = pos['symbol']
        qty = float(pos['qty'])
        gain_pct = float(pos['unrealized_plpc']) * 100
        current_price = float(pos['current_price'])
        avg_entry = float(pos['avg_entry_price'])
        market_value = float(pos['market_value'])

        # Get or initialize exit state for this position
        if symbol not in exit_state:
            trade_type = get_trade_type(symbol)
            exit_state[symbol] = {
                'trade_type': trade_type,
                'peak_gain': gain_pct,
                'entry_date': date.today().isoformat(),
                'partial_taken': False
            }

        state_entry = exit_state[symbol]

        # Calculate exit action
        action = calculate_exit_action(symbol, gain_pct, state_entry, qty)

        # Update peak in state
        exit_state[symbol]['peak_gain'] = action['new_peak']

        # Display
        trade_type_icon = {'squeeze': '🔥', 'momentum': '⚡', 'default': '📌'}.get(state_entry['trade_type'], '❓')
        print(f"{trade_type_icon} {symbol}: {gain_pct:+.1f}% (${market_value:.0f}) | {action['reason']}")

        if status_only:
            continue

        # Execute if needed
        if action['action'] in ['STOP_LOSS', 'TRAILING_STOP', 'PARTIAL_PROFIT', 'FULL_EXIT']:
            sell_qty = action['sell_qty']

            if sell_qty <= 0:
                continue

            if dry_run:
                print(f"   🔒 DRY RUN: Would sell {sell_qty} shares — {action['reason']}")
            else:
                success = execute_sell(headers, base, symbol, sell_qty, action['reason'])
                if success:
                    actions_taken.append({
                        'symbol': symbol,
                        'action': action['action'],
                        'qty': sell_qty,
                        'gain_pct': gain_pct,
                        'reason': action['reason']
                    })

                    # LEARNING LOOP: Record exit outcome in performance tracker
                    try:
                        update_trade_outcome(symbol, current_price)
                        print(f"   📊 Outcome recorded for {symbol} at ${current_price:.2f}")
                    except Exception as e:
                        print(f"   ⚠️  Could not record outcome: {e}")

                    # Update state
                    if action['action'] == 'PARTIAL_PROFIT':
                        exit_state[symbol]['partial_taken'] = True
                    elif action['action'] in ['STOP_LOSS', 'TRAILING_STOP', 'FULL_EXIT']:
                        # Position closed, clean up state
                        if sell_qty >= qty:
                            del exit_state[symbol]

    # Save updated state
    save_exit_state(exit_state)

    # Summary
    print(f"\n{'=' * 70}")
    if status_only:
        print("Status check complete (no actions taken)")
    elif dry_run:
        print("Dry run complete (no orders placed)")
    elif actions_taken:
        print(f"📤 Executed {len(actions_taken)} exit orders:")
        for a in actions_taken:
            print(f"   {a['action']}: {a['symbol']} x{a['qty']} at {a['gain_pct']:+.1f}%")

        # Telegram alert
        try:
            msg = "🛡️ *EXIT MANAGER ALERT*\n\n"
            for a in actions_taken:
                emoji = '🔴' if 'STOP' in a['action'] else '🟢'
                msg += f"{emoji} {a['action']}: *{a['symbol']}* x{a['qty']} ({a['gain_pct']:+.1f}%)\n"
                msg += f"   {a['reason']}\n\n"
            send_alert(msg)
        except:
            pass
    else:
        print("All positions holding. No exits triggered.")
    print("=" * 70)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Dynamic Exit Manager V1.0')
    parser.add_argument('--dry-run', action='store_true', help='Show actions without executing')
    parser.add_argument('--status', action='store_true', help='Show position status only')
    args = parser.parse_args()

    run_exit_check(dry_run=args.dry_run, status_only=args.status)

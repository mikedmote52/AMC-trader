#!/usr/bin/env python3
"""
OpenClaw API Server
Exposes scanner data, portfolio, learning system, and thesis tracking via HTTP API
Used by Codex dashboard for live data integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import os
import csv
from collections import defaultdict
import uvicorn
from typing import Optional

# Alpaca integration
import alpaca_trade_api as tradeapi

# Pydantic models for request bodies
class ApprovalDecision(BaseModel):
    symbol: str
    decision: str  # "approve" or "reject"
    price_at_decision: float
    notes: Optional[str] = ""
    scanner_score: int

app = FastAPI(title="OpenClaw API", version="1.0.0")

# Enable CORS for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to dashboard domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
WORKSPACE = "/Users/mikeclawd/.openclaw/workspace"
DATA_DIR = os.path.join(WORKSPACE, "data")
SECRETS_DIR = "/Users/mikeclawd/.openclaw/secrets"

# Alpaca client
def get_alpaca_client():
    """Initialize Alpaca API client"""
    with open(os.path.join(SECRETS_DIR, 'alpaca.json'), 'r') as f:
        creds = json.load(f)
    return tradeapi.REST(
        creds['apiKey'],
        creds['secretKey'],
        base_url=creds.get('baseUrl', 'https://paper-api.alpaca.markets')
    )


@app.get("/")
async def root():
    """API health check"""
    return {
        "service": "OpenClaw API",
        "version": "1.1.0",
        "status": "operational",
        "endpoints": [
            "/api/scanner/latest",
            "/api/scanner/status",
            "/api/portfolio/positions",
            "/api/portfolio/thesis",
            "/api/learning/performance",
            "/api/learning/weights",
            "/api/scanner/history",
            "/api/approval/queue",
            "/api/approval/decide",
            "/api/approval/history"
        ]
    }


@app.get("/api/scanner/latest")
async def get_latest_scanner_results():
    """
    Returns latest V4 scanner results
    """
    try:
        # Try V4 first, fall back to V3 if V4 doesn't exist yet
        v4_file = os.path.join(DATA_DIR, "diamonds_v4.json")
        v3_file = os.path.join(DATA_DIR, "diamonds.json")

        if os.path.exists(v4_file):
            with open(v4_file, 'r') as f:
                data = json.load(f)
                data['scanner_version'] = 'V4_SWING'
                return data
        elif os.path.exists(v3_file):
            with open(v3_file, 'r') as f:
                candidates = json.load(f)
                return {
                    'scanner_version': 'V3.1',
                    'candidates': candidates,
                    'scan_date': datetime.now().strftime('%Y-%m-%d'),
                    'note': 'V4 not yet available, showing V3.1 results'
                }
        else:
            raise HTTPException(status_code=404, detail="No scanner results found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading scanner results: {str(e)}")


@app.get("/api/scanner/status")
async def get_scanner_status():
    """
    Returns scanner health and gate funnel statistics
    """
    try:
        v4_file = os.path.join(DATA_DIR, "diamonds_v4.json")

        if os.path.exists(v4_file):
            with open(v4_file, 'r') as f:
                data = json.load(f)

            mod_time = os.path.getmtime(v4_file)
            last_scan = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')

            return {
                "scanner_version": "V4_SWING",
                "status": "operational",
                "last_scan_time": last_scan,
                "gates": data.get('gates', {}),
                "tiers": data.get('tiers', {}),
                "total_candidates": len(data.get('candidates', [])),
                "philosophy": data.get('philosophy', 'Wide net + Strict filter')
            }
        else:
            return {
                "scanner_version": "V4_SWING",
                "status": "no_results_yet",
                "last_scan_time": None,
                "message": "V4 scanner built but not yet run"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading scanner status: {str(e)}")


@app.get("/api/portfolio/positions")
async def get_portfolio_positions():
    """
    Returns current Alpaca positions with P&L
    """
    try:
        api = get_alpaca_client()

        # Get account info
        account = api.get_account()

        # Get positions
        positions = api.list_positions()

        positions_data = []
        for pos in positions:
            positions_data.append({
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'avg_entry_price': float(pos.avg_entry_price),
                'current_price': float(pos.current_price),
                'market_value': float(pos.market_value),
                'cost_basis': float(pos.cost_basis),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc),
                'side': pos.side,
                'change_today': float(pos.change_today) if pos.change_today else 0.0
            })

        return {
            'account': {
                'equity': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'last_equity': float(account.last_equity),
                'day_return': float(account.equity) - float(account.last_equity),
                'day_return_pct': ((float(account.equity) - float(account.last_equity)) / float(account.last_equity) * 100) if float(account.last_equity) > 0 else 0
            },
            'positions': positions_data,
            'total_positions': len(positions_data),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching portfolio: {str(e)}")


@app.get("/api/portfolio/thesis")
async def get_portfolio_thesis():
    """
    Returns active thesis for each position from portfolio tracking CSV
    """
    try:
        csv_file = os.path.join(DATA_DIR, "portfolio_tracking.csv")

        if not os.path.exists(csv_file):
            return {"positions": [], "note": "Portfolio tracking CSV not found"}

        # Get current positions from Alpaca
        api = get_alpaca_client()
        current_positions = {pos.symbol for pos in api.list_positions()}

        # Read portfolio tracking CSV
        thesis_data = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row.get('symbol')
                # Only include if position is still open (no exit date and currently held)
                if not row.get('exit_date') and symbol in current_positions:
                    thesis_data.append({
                        'symbol': symbol,
                        'entry_date': row.get('entry_date'),
                        'entry_price': float(row.get('entry_price', 0)),
                        'entry_thesis': row.get('entry_thesis', ''),
                        'scanner_score': int(row.get('scanner_score', 0)),
                        'vigl_match': row.get('vigl_match', 'unknown'),
                        'rvol': float(row.get('rvol', 0)),
                        # Validation fields (new)
                        'validation_status': row.get('validation_status', 'watch'),
                        'validation_reason': row.get('validation_reason', ''),
                        'critique': row.get('critique', ''),
                        'price_target': float(row.get('price_target', 0)) if row.get('price_target') else None,
                        'stop_loss': float(row.get('stop_loss', 0)) if row.get('stop_loss') else None
                    })

        return {
            'active_positions': thesis_data,
            'total_active': len(thesis_data),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading thesis data: {str(e)}")


@app.get("/api/learning/performance")
async def get_learning_performance():
    """
    Returns learning system performance data from scanner_performance.csv
    Win rate by score range, factor correlations
    """
    try:
        csv_file = os.path.join(DATA_DIR, "scanner_performance.csv")

        if not os.path.exists(csv_file):
            return {"note": "Learning performance CSV not found"}

        # Read scanner performance CSV
        trades = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('outcome') in ['WIN', 'LOSS']:
                    trades.append({
                        'symbol': row.get('symbol'),
                        'scanner_score': int(row.get('scanner_score', 0)),
                        'vigl_match': row.get('vigl_match', 'none'),
                        'rvol': float(row.get('rvol', 0)) if row.get('rvol') else 0,
                        'return_pct': float(row.get('return_pct', 0)) if row.get('return_pct') else 0,
                        'hold_days': int(row.get('hold_days', 0)) if row.get('hold_days') else 0,
                        'outcome': row.get('outcome'),
                        'entry_date': row.get('entry_date')
                    })

        # Calculate win rate by score range
        score_ranges = {
            '150+': {'wins': 0, 'losses': 0, 'total_return': 0},
            '110-149': {'wins': 0, 'losses': 0, 'total_return': 0},
            '60-109': {'wins': 0, 'losses': 0, 'total_return': 0}
        }

        vigl_stats = {
            'perfect': {'wins': 0, 'losses': 0, 'total_return': 0},
            'near': {'wins': 0, 'losses': 0, 'total_return': 0},
            'partial': {'wins': 0, 'losses': 0, 'total_return': 0},
            'none': {'wins': 0, 'losses': 0, 'total_return': 0}
        }

        for trade in trades:
            score = trade['scanner_score']
            outcome = trade['outcome']
            ret = trade['return_pct']
            vigl = trade['vigl_match']

            # Score range stats
            if score >= 150:
                range_key = '150+'
            elif score >= 110:
                range_key = '110-149'
            else:
                range_key = '60-109'

            if outcome == 'WIN':
                score_ranges[range_key]['wins'] += 1
            else:
                score_ranges[range_key]['losses'] += 1
            score_ranges[range_key]['total_return'] += ret

            # VIGL pattern stats
            if vigl in vigl_stats:
                if outcome == 'WIN':
                    vigl_stats[vigl]['wins'] += 1
                else:
                    vigl_stats[vigl]['losses'] += 1
                vigl_stats[vigl]['total_return'] += ret

        # Calculate win rates
        for range_key in score_ranges:
            total = score_ranges[range_key]['wins'] + score_ranges[range_key]['losses']
            score_ranges[range_key]['win_rate'] = (score_ranges[range_key]['wins'] / total * 100) if total > 0 else 0
            score_ranges[range_key]['total_trades'] = total

        for vigl_key in vigl_stats:
            total = vigl_stats[vigl_key]['wins'] + vigl_stats[vigl_key]['losses']
            vigl_stats[vigl_key]['win_rate'] = (vigl_stats[vigl_key]['wins'] / total * 100) if total > 0 else 0
            vigl_stats[vigl_key]['total_trades'] = total

        return {
            'total_trades': len(trades),
            'total_wins': sum(1 for t in trades if t['outcome'] == 'WIN'),
            'total_losses': sum(1 for t in trades if t['outcome'] == 'LOSS'),
            'overall_win_rate': (sum(1 for t in trades if t['outcome'] == 'WIN') / len(trades) * 100) if trades else 0,
            'by_score_range': score_ranges,
            'by_vigl_pattern': vigl_stats,
            'avg_return': sum(t['return_pct'] for t in trades) / len(trades) if trades else 0,
            'avg_hold_days': sum(t['hold_days'] for t in trades) / len(trades) if trades else 0,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading learning performance: {str(e)}")


@app.get("/api/learning/weights")
async def get_learning_weights():
    """
    Returns current scoring weights and any learning system adjustments
    """
    try:
        # V4 weights (hardcoded for now - learning system will adjust these later)
        v4_weights = {
            'scanner_version': 'V4_SWING',
            'base_components': {
                'stealth_accumulation': {
                    'weight': 40,
                    'max_points': 40,
                    'description': 'RVOL 1.5-2.5x + minimal price change (VIGL pattern)',
                    'formula': 'sigmoid((rvol-1.5)/1.0) * sigmoid((5.0-abs_change)/2.0) * 40'
                },
                'small_cap_potential': {
                    'weight': 25,
                    'max_points': 25,
                    'description': 'Low price = high explosive potential',
                    'formula': 'sigmoid((15.0-price)/8.0) * 25'
                },
                'coiling_pattern': {
                    'weight': 20,
                    'max_points': 20,
                    'description': 'Tight consolidation with volume',
                    'formula': 'sigmoid((rvol-1.3)/0.5) * sigmoid((3.0-abs_change)/1.5) * 20'
                },
                'volume_quality': {
                    'weight': 15,
                    'max_points': 15,
                    'description': 'RVOL strength',
                    'formula': 'sigmoid((rvol-1.5)/1.2) * 15'
                }
            },
            'bonuses': {
                'vigl_perfect': 15,
                'vigl_near': 10,
                'vigl_partial': 5,
                'pre_explosion_multiplier': 1.25
            },
            'gates': {
                'gate_a': {
                    'price_min': 0.50,
                    'price_max': 100.0,
                    'volume_min': 300000,
                    'rvol_min': 1.2
                },
                'gate_b': {
                    'rvol_min': 1.5,
                    'rvol_max': 2.5,
                    'change_max': 2.0,
                    'price_min': 5.0
                }
            },
            'learning_status': 'tracking_only',
            'adjustments': [],
            'last_updated': datetime.now().isoformat()
        }

        return v4_weights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching weights: {str(e)}")


@app.get("/api/scanner/history")
async def get_scanner_history():
    """
    Returns last 7 days of scanner results
    How many picks per day, tiers found
    """
    try:
        csv_file = os.path.join(DATA_DIR, "scanner_performance.csv")

        if not os.path.exists(csv_file):
            return {"note": "Scanner history CSV not found"}

        # Read scanner performance CSV
        scans_by_date = defaultdict(lambda: {
            'total_picks': 0,
            'high_conviction': 0,  # 150+
            'strong': 0,  # 110-149
            'watch': 0,  # 60-109
            'vigl_matches': 0,
            'symbols': []
        })

        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                scan_date = row.get('scan_date')
                if not scan_date:
                    continue

                # Only include last 7 days
                try:
                    date_obj = datetime.strptime(scan_date, '%Y-%m-%d')
                    if date_obj < datetime.now() - timedelta(days=7):
                        continue
                except:
                    continue

                score = int(row.get('scanner_score', 0))
                symbol = row.get('symbol')
                vigl = row.get('vigl_match', 'none')

                scans_by_date[scan_date]['total_picks'] += 1
                scans_by_date[scan_date]['symbols'].append(symbol)

                if score >= 150:
                    scans_by_date[scan_date]['high_conviction'] += 1
                elif score >= 110:
                    scans_by_date[scan_date]['strong'] += 1
                elif score >= 60:
                    scans_by_date[scan_date]['watch'] += 1

                if vigl in ['perfect', 'near', 'partial']:
                    scans_by_date[scan_date]['vigl_matches'] += 1

        # Convert to list and sort by date
        history = []
        for date, stats in sorted(scans_by_date.items()):
            history.append({
                'date': date,
                'total_picks': stats['total_picks'],
                'high_conviction': stats['high_conviction'],
                'strong': stats['strong'],
                'watch': stats['watch'],
                'vigl_matches': stats['vigl_matches'],
                'symbols': stats['symbols'][:10]  # Limit to first 10
            })

        return {
            'history': history,
            'days_tracked': len(history),
            'total_picks_7d': sum(day['total_picks'] for day in history),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading scanner history: {str(e)}")


@app.get("/api/approval/queue")
async def get_approval_queue():
    """
    Returns scanner picks awaiting approval decision
    Returns latest V4 candidates that haven't been approved/rejected yet
    """
    try:
        # Get latest scanner results
        v4_file = os.path.join(DATA_DIR, "diamonds_v4.json")
        decisions_file = os.path.join(DATA_DIR, "approval_decisions.csv")

        if not os.path.exists(v4_file):
            return {"queue": [], "note": "No V4 scanner results available"}

        # Read V4 candidates
        with open(v4_file, 'r') as f:
            scanner_data = json.load(f)

        candidates = scanner_data.get('candidates', [])

        # Get already-decided symbols (if decisions file exists)
        decided_symbols = set()
        if os.path.exists(decisions_file):
            with open(decisions_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Only exclude if decision was made today (allow re-evaluation on new scans)
                    decision_date = row.get('timestamp', '')
                    if decision_date:
                        try:
                            decision_dt = datetime.fromisoformat(decision_date.replace('Z', '+00:00'))
                            if decision_dt.date() == datetime.now().date():
                                decided_symbols.add(row.get('symbol'))
                        except:
                            pass

        # Filter out already-decided candidates
        queue = []
        for candidate in candidates:
            symbol = candidate.get('symbol')
            if symbol not in decided_symbols:
                queue.append({
                    'symbol': symbol,
                    'price': candidate.get('price'),
                    'total_score': candidate.get('total_score'),
                    'explosion_probability': candidate.get('explosion_probability'),
                    'tier': candidate.get('tier'),
                    'rvol': candidate.get('rvol'),
                    'change_pct': candidate.get('change_pct'),
                    'vigl_bonus': candidate.get('vigl_bonus', 0),
                    'gates_passed': candidate.get('gates_passed', []),
                    'components': candidate.get('components', {})
                })

        return {
            'queue': queue,
            'total_pending': len(queue),
            'scan_date': scanner_data.get('scan_date'),
            'scanner_version': scanner_data.get('scanner_version'),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching approval queue: {str(e)}")


@app.post("/api/approval/decide")
async def approval_decide(decision: ApprovalDecision):
    """
    Handle approve/reject decision for a scanner pick
    Logs decision to approval_decisions.csv
    """
    try:
        decisions_file = os.path.join(DATA_DIR, "approval_decisions.csv")

        # Ensure CSV exists with headers
        file_exists = os.path.exists(decisions_file)
        if not file_exists:
            with open(decisions_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'symbol', 'decision', 'price_at_decision', 'notes',
                    'timestamp', 'scanner_score'
                ])

        # Append decision
        with open(decisions_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                decision.symbol,
                decision.decision,
                decision.price_at_decision,
                decision.notes,
                datetime.now().isoformat(),
                decision.scanner_score
            ])

        return {
            'status': 'success',
            'message': f'{decision.symbol} {decision.decision}d successfully',
            'decision': decision.decision,
            'symbol': decision.symbol,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording decision: {str(e)}")


@app.get("/api/approval/history")
async def get_approval_history(status: str = "rejected", days: int = 30):
    """
    Returns history of approval decisions (default: rejected picks from last 30 days)
    Calculates would-be return for rejected picks
    """
    try:
        decisions_file = os.path.join(DATA_DIR, "approval_decisions.csv")

        if not os.path.exists(decisions_file):
            return {"history": [], "note": "No approval decisions recorded yet"}

        # Get current prices via Alpaca
        api = get_alpaca_client()

        history = []
        cutoff_date = datetime.now() - timedelta(days=days)

        with open(decisions_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('decision') != status:
                    continue

                # Check if within date range
                timestamp = row.get('timestamp', '')
                if timestamp:
                    try:
                        decision_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        if decision_dt < cutoff_date:
                            continue
                    except:
                        continue

                symbol = row.get('symbol')
                price_at_decision = float(row.get('price_at_decision', 0))

                # Get current price
                current_price = None
                would_be_return = None
                try:
                    bars = api.get_bars(symbol, '1Day', limit=1).df
                    if not bars.empty:
                        current_price = float(bars['close'].iloc[-1])
                        if price_at_decision > 0:
                            would_be_return = ((current_price - price_at_decision) / price_at_decision) * 100
                except:
                    pass

                history.append({
                    'symbol': symbol,
                    'rejected_date': timestamp,
                    'price_at_decision': price_at_decision,
                    'current_price': current_price,
                    'would_be_return': would_be_return,
                    'notes': row.get('notes', ''),
                    'scanner_score': int(row.get('scanner_score', 0))
                })

        # Sort by date (most recent first)
        history.sort(key=lambda x: x['rejected_date'], reverse=True)

        return {
            'history': history,
            'status_filter': status,
            'days': days,
            'total_records': len(history),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching approval history: {str(e)}")


if __name__ == "__main__":
    # Run on port 8000
    print("🚀 Starting OpenClaw API server on http://0.0.0.0:8000")
    print("📊 Dashboard can access scanner data, portfolio, learning system, approval workflow")
    uvicorn.run(app, host="0.0.0.0", port=8000)

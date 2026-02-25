#!/usr/bin/env python3
"""
DAILY ALLOCATOR V1.0 - Intelligent Capital Deployment Engine

Replaces the ad-hoc "agent picks from diamond list" approach with a
structured decision engine that thinks like a hedge fund PM.

Design principle: Replicate the pattern that produced +63.8% returns.
That pattern was: ONE high-conviction pick per day, concentrated bet,
let winners run. But the AI has full discretion to split, concentrate,
or pass entirely based on what the scanner found.

This script:
1. Reads scanner results (diamonds.json)
2. Reads current portfolio state from Alpaca
3. Calls the LLM (Gemini Flash) with full context to make an allocation decision
4. Outputs an allocation plan with reasoning
5. Optionally auto-executes via execute_trade.py

Cost: ~1 LLM call/day at ~$0.002 = negligible

Usage:
  python3 daily_allocator.py                    # Generate plan, prompt for execution
  python3 daily_allocator.py --auto             # Generate and auto-execute (for cron)
  python3 daily_allocator.py --plan-only        # Just show the plan, no execution
  python3 daily_allocator.py --budget 500       # Override daily budget
"""

import json
import os
import sys
import subprocess
from datetime import datetime, date
import requests as http_requests

# Paths
WORKSPACE = '/Users/mikeclawd/.openclaw/workspace'
DIAMONDS_FILE = os.path.join(WORKSPACE, 'data', 'diamonds.json')
ALLOCATION_LOG = os.path.join(WORKSPACE, 'data', 'allocation_history.json')
SECRETS_DIR = '/Users/mikeclawd/.openclaw/secrets'

sys.path.insert(0, os.path.join(WORKSPACE, 'scripts'))

try:
    from scanner_performance_tracker import link_trade_to_scan
except:
    def link_trade_to_scan(symbol, price, thesis): pass

# Default budget
DEFAULT_DAILY_BUDGET = 300

# Cost tracking (shared with scanner)
COST_TRACKER_FILE = os.path.join(WORKSPACE, 'data', 'daily_cost.json')
GEMINI_FLASH_INPUT_COST = 0.15 / 1_000_000
GEMINI_FLASH_OUTPUT_COST = 0.60 / 1_000_000


def log_cost(input_tokens, output_tokens):
    """Log LLM cost to shared daily tracker"""
    cost = (input_tokens * GEMINI_FLASH_INPUT_COST) + (output_tokens * GEMINI_FLASH_OUTPUT_COST)
    try:
        data = {'date': date.today().isoformat(), 'total_cost': 0.0, 'calls': 0}
        if os.path.exists(COST_TRACKER_FILE):
            with open(COST_TRACKER_FILE, 'r') as f:
                data = json.load(f)
            if data.get('date') != date.today().isoformat():
                data = {'date': date.today().isoformat(), 'total_cost': 0.0, 'calls': 0}
        data['total_cost'] = data.get('total_cost', 0.0) + cost
        data['calls'] = data.get('calls', 0) + 1
        with open(COST_TRACKER_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass
    return cost


def get_alpaca_client():
    """Get Alpaca API credentials"""
    with open(os.path.join(SECRETS_DIR, 'alpaca.json'), 'r') as f:
        creds = json.load(f)
    return creds


def get_portfolio_state():
    """Fetch current portfolio from Alpaca"""
    creds = get_alpaca_client()
    headers = {
        'APCA-API-KEY-ID': creds['apiKey'],
        'APCA-API-SECRET-KEY': creds['apiSecret']
    }
    base = creds.get('baseUrl', 'https://paper-api.alpaca.markets')

    # Get account
    account = http_requests.get(f"{base}/v2/account", headers=headers).json()

    # Get positions
    positions = http_requests.get(f"{base}/v2/positions", headers=headers).json()

    # Get today's orders to check remaining budget
    today = date.today().isoformat()
    orders = http_requests.get(
        f"{base}/v2/orders",
        headers=headers,
        params={'status': 'filled', 'after': f"{today}T00:00:00Z", 'direction': 'asc'}
    ).json()

    # Calculate today's buy spending
    today_spent = 0
    for order in orders:
        if order.get('side') == 'buy' and order.get('filled_avg_price'):
            today_spent += float(order['filled_avg_price']) * float(order.get('filled_qty', 0))

    # Format positions for LLM context
    position_summary = []
    for pos in positions:
        symbol = pos['symbol']
        qty = float(pos['qty'])
        avg_entry = float(pos['avg_entry_price'])
        current = float(pos['current_price'])
        market_value = float(pos['market_value'])
        unrealized_pl = float(pos['unrealized_pl'])
        unrealized_plpc = float(pos['unrealized_plpc']) * 100

        position_summary.append({
            'symbol': symbol,
            'qty': qty,
            'avg_entry': avg_entry,
            'current_price': current,
            'market_value': market_value,
            'unrealized_pl': unrealized_pl,
            'unrealized_pl_pct': unrealized_plpc
        })

    return {
        'portfolio_value': float(account.get('portfolio_value', 0)),
        'cash': float(account.get('cash', 0)),
        'buying_power': float(account.get('buying_power', 0)),
        'positions': position_summary,
        'num_positions': len(positions),
        'today_spent': today_spent
    }


def load_diamonds():
    """Load latest scanner results"""
    try:
        with open(DIAMONDS_FILE, 'r') as f:
            diamonds = json.load(f)
        return diamonds
    except Exception as e:
        print(f"Error loading diamonds: {e}")
        return []


def load_allocation_history():
    """Load past allocation decisions for pattern learning"""
    try:
        if os.path.exists(ALLOCATION_LOG):
            with open(ALLOCATION_LOG, 'r') as f:
                return json.load(f)
    except:
        pass
    return []


def save_allocation(decision):
    """Save allocation decision to history"""
    history = load_allocation_history()
    history.append(decision)
    # Keep last 90 days
    history = history[-90:]
    try:
        with open(ALLOCATION_LOG, 'w') as f:
            json.dump(history, f, indent=2, default=str)
    except:
        pass


def generate_allocation_plan(diamonds, portfolio, daily_budget):
    """
    The core intelligence: ask LLM to make an allocation decision
    with full context about scanner results, portfolio state, and
    the reference pattern we're trying to replicate.
    """
    remaining_budget = daily_budget - portfolio['today_spent']
    if remaining_budget <= 0:
        return {
            'action': 'PASS',
            'reason': f"Daily budget exhausted (${portfolio['today_spent']:.0f} spent today)",
            'allocations': [],
            'confidence': 0
        }

    if not diamonds:
        return {
            'action': 'PASS',
            'reason': 'No diamonds found by scanner',
            'allocations': [],
            'confidence': 0
        }

    # Format top diamonds for context
    top_diamonds = diamonds[:10]  # Top 10 by score
    diamond_block = ""
    for i, d in enumerate(top_diamonds, 1):
        flags = f" | FLAGS: {', '.join(d.get('red_flags', []))}" if d.get('red_flags') else ""
        diamond_block += f"""
{i}. {d['symbol']} — NET SCORE: {d.get('score', 0)}/305 (gross: {d.get('gross_score', d.get('score', 0))}, penalties: {d.get('penalties', 0)})
   Price: ${d.get('price', 0):.2f} | Float: {d.get('float', 'Unknown')} | Market Cap: {d.get('market_cap', 'Unknown')}
   Momentum: {d.get('momentum', 'N/A')} | Volume: {d.get('volume_pattern', 'N/A')}
   Catalyst: {d.get('catalyst', 'None')} | Squeeze: {d.get('squeeze', 'None')}
   VWAP: {d.get('vwap', 'N/A')} | Breakout: {d.get('breakout', 'N/A')}
   VIGL Pattern: {d.get('vigl', 'None')} | Chase Risk: {d.get('chase_risk', 'Low')}{flags}"""

    # Format current positions
    position_block = "NONE" if not portfolio['positions'] else ""
    for pos in sorted(portfolio['positions'], key=lambda x: x['unrealized_pl_pct'], reverse=True):
        position_block += f"\n   {pos['symbol']}: {pos['unrealized_pl_pct']:+.1f}% (${pos['market_value']:.0f}, entry ${pos['avg_entry']:.2f})"

    # Load recent allocation history
    history = load_allocation_history()
    recent_decisions = history[-5:] if history else []
    history_block = "No prior decisions"
    if recent_decisions:
        history_block = ""
        for h in recent_decisions:
            history_block += f"\n   {h.get('date', '?')}: {h.get('action', '?')} — {h.get('summary', '?')}"

    prompt = f"""You are a hedge fund portfolio manager specializing in micro-cap squeeze plays and momentum trades. Your mandate is to deploy capital for maximum short-term gains while managing downside risk.

REFERENCE BENCHMARK (the pattern you're trying to replicate):
ChatGPT's picks June 1 - July 4 produced +63.8% returns. Key characteristics:
- ONE high-conviction pick per day, $100 concentrated bets
- Top 3 winners: VIGL +324%, CRWV +171%, AEVA +162% (all micro-cap squeezes)
- Also included large-cap momentum: TSLA +21%, NVDA +16%, AMD +16%
- 93% win rate (14/15 profitable), only 1 loser (WOLF -25%)
- Winners were HELD through large runs, not sold at +30%

CURRENT PORTFOLIO:
Portfolio Value: ${portfolio['portfolio_value']:,.0f}
Cash: ${portfolio['cash']:,.0f} ({portfolio['cash']/max(portfolio['portfolio_value'],1)*100:.1f}%)
Open Positions: {portfolio['num_positions']}
Spent Today: ${portfolio['today_spent']:.0f}
Remaining Budget: ${remaining_budget:.0f}

Current Holdings:{position_block}

TODAY'S SCANNER RESULTS (ranked by net score after risk penalties):
{diamond_block}

RECENT ALLOCATION DECISIONS:{history_block}

DECISION REQUIRED:
You have ${remaining_budget:.0f} to deploy today. Based on the scanner results and portfolio state, make your allocation decision.

Rules:
- You can allocate ${remaining_budget:.0f} to one stock (concentrated), split across 2-3 stocks, or PASS entirely if nothing meets your bar
- Minimum position size: $50 (below this is not worth the transaction)
- You should PASS if no diamond scores above 150 net OR if all high-scorers have significant red flags
- CONCENTRATE when you see a setup matching the VIGL/CRWV pattern (stealth accumulation + low float + catalyst)
- SPLIT only when multiple genuinely independent catalysts exist (not just diversification for its own sake)
- Consider existing positions: don't double up on correlated trades, don't add to losers
- Factor in chase risk: if the stock already moved 10%+ today, the best entry may be tomorrow

Respond with ONLY valid JSON:
{{
  "action": "BUY" or "PASS",
  "confidence": 1-10,
  "allocations": [
    {{"symbol": "TICK", "amount": 150, "thesis": "Brief thesis explaining WHY this stock and this allocation size"}},
    {{"symbol": "TICK2", "amount": 150, "thesis": "..."}}
  ],
  "reasoning": "2-3 sentences explaining overall decision logic",
  "trade_type": "squeeze" or "momentum" or "mixed",
  "expected_hold_days": 5,
  "risk_notes": "Key risks to monitor"
}}

If PASS, set allocations to empty array and explain why in reasoning."""

    try:
        with open(os.path.join(SECRETS_DIR, 'openrouter.json'), 'r') as f:
            or_creds = json.load(f)

        response = http_requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f"Bearer {or_creds.get('apiKey', or_creds.get('api_key', ''))}",
                'Content-Type': 'application/json'
            },
            json={
                'model': 'google/gemini-2.5-flash',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 1000,
                'temperature': 0.3  # Slightly creative but mostly deterministic
            },
            timeout=30
        )

        if response.status_code == 200:
            resp_data = response.json()
            content = resp_data['choices'][0]['message']['content']

            # Track cost
            usage = resp_data.get('usage', {})
            cost = log_cost(usage.get('prompt_tokens', 3000), usage.get('completion_tokens', 500))
            print(f"💰 Allocator LLM cost: ${cost:.4f}")

            # Parse response
            content = content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1] if '\n' in content else content
                content = content.rsplit('```', 1)[0] if '```' in content else content
                content = content.strip()

            plan = json.loads(content)
            plan['date'] = date.today().isoformat()
            plan['remaining_budget'] = remaining_budget
            plan['scanner_top_score'] = diamonds[0].get('score', 0) if diamonds else 0
            plan['llm_cost'] = cost

            return plan
        else:
            print(f"⚠️  OpenRouter returned {response.status_code}")
            return fallback_allocation(diamonds, remaining_budget)

    except json.JSONDecodeError as e:
        print(f"⚠️  Failed to parse LLM response: {e}")
        return fallback_allocation(diamonds, remaining_budget)
    except Exception as e:
        print(f"⚠️  Allocator LLM failed: {e}")
        return fallback_allocation(diamonds, remaining_budget)


def fallback_allocation(diamonds, remaining_budget):
    """
    Deterministic fallback if LLM is unavailable.
    Simple rule: if top diamond scores 200+, concentrate full budget on it.
    If 150-199, use half budget. Below 150, pass.
    """
    if not diamonds:
        return {
            'action': 'PASS',
            'reason': 'No diamonds (fallback)',
            'allocations': [],
            'confidence': 0
        }

    top = diamonds[0]
    score = top.get('score', 0)
    has_flags = bool(top.get('red_flags'))

    if score >= 200 and not has_flags:
        return {
            'action': 'BUY',
            'confidence': 8,
            'allocations': [{
                'symbol': top['symbol'],
                'amount': remaining_budget,
                'thesis': f"Top diamond at {score}/305, no red flags. Full conviction. (FALLBACK)"
            }],
            'reasoning': f"LLM unavailable. Fallback rule: score {score} >= 200 with no flags = full budget.",
            'trade_type': 'unknown',
            'expected_hold_days': 5,
            'risk_notes': 'Fallback allocation — no LLM analysis'
        }
    elif score >= 200 and has_flags:
        return {
            'action': 'BUY',
            'confidence': 5,
            'allocations': [{
                'symbol': top['symbol'],
                'amount': int(remaining_budget * 0.5),
                'thesis': f"Score {score}/305 but has flags: {', '.join(top.get('red_flags', []))}. Half size. (FALLBACK)"
            }],
            'reasoning': f"LLM unavailable. Fallback: high score with flags = half position.",
            'trade_type': 'unknown',
            'expected_hold_days': 5,
            'risk_notes': f"Red flags: {', '.join(top.get('red_flags', []))}"
        }
    elif score >= 150:
        return {
            'action': 'BUY',
            'confidence': 4,
            'allocations': [{
                'symbol': top['symbol'],
                'amount': int(remaining_budget * 0.5),
                'thesis': f"Score {score}/305, moderate conviction. Half budget. (FALLBACK)"
            }],
            'reasoning': f"LLM unavailable. Fallback: score {score} = half budget.",
            'trade_type': 'unknown',
            'expected_hold_days': 3,
            'risk_notes': 'Moderate score — fallback conservative sizing'
        }
    else:
        return {
            'action': 'PASS',
            'confidence': 0,
            'allocations': [],
            'reasoning': f"LLM unavailable. Fallback: top score {score} < 150 = no trade.",
            'trade_type': 'none',
            'risk_notes': 'Below threshold'
        }


def execute_allocation(plan, auto=False):
    """Execute the allocation plan via execute_trade.py"""
    if plan['action'] == 'PASS':
        print(f"\n🚫 PASS — {plan.get('reasoning', 'No reason given')}")
        return

    print(f"\n📋 ALLOCATION PLAN (Confidence: {plan.get('confidence', '?')}/10)")
    print(f"   Type: {plan.get('trade_type', 'unknown')} | Hold: ~{plan.get('expected_hold_days', '?')} days")
    print(f"   {plan.get('reasoning', '')}")
    if plan.get('risk_notes'):
        print(f"   ⚠️  Risk: {plan['risk_notes']}")
    print()

    for alloc in plan.get('allocations', []):
        symbol = alloc['symbol']
        amount = alloc['amount']
        thesis = alloc['thesis']

        print(f"   → {symbol}: ${amount} — {thesis}")

    if not auto:
        print()
        confirm = input("Execute this plan? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Cancelled by user")
            return

    # Execute each allocation
    for alloc in plan.get('allocations', []):
        symbol = alloc['symbol']
        amount = alloc['amount']
        thesis = alloc['thesis']

        # Add allocation context to thesis
        full_thesis = f"[Allocator v1.0 | conf:{plan.get('confidence', '?')}/10 | type:{plan.get('trade_type', '?')}] {thesis}"

        print(f"\n🔄 Executing: {symbol} ${amount}...")

        try:
            result = subprocess.run(
                ['python3', os.path.join(WORKSPACE, 'scripts', 'execute_trade.py'),
                 symbol, str(amount), full_thesis],
                capture_output=True,
                text=True,
                timeout=30,
                input='yes\n' if auto else None  # Auto-confirm if --auto
            )

            if result.returncode == 0:
                print(f"   ✅ {symbol} executed")
                # LEARNING LOOP: Link buy to scanner performance tracker
                try:
                    link_trade_to_scan(symbol, amount, thesis)
                    print(f'   Trade linked to scanner performance tracker')
                except Exception as e:
                    print(f'   Could not link trade: {e}')
            else:
                print(f"   ❌ {symbol} failed: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print(f"   ❌ {symbol} timed out")
        except Exception as e:
            print(f"   ❌ {symbol} error: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Daily Allocator V1.0')
    parser.add_argument('--auto', action='store_true', help='Auto-execute without confirmation')
    parser.add_argument('--plan-only', action='store_true', help='Show plan only, no execution')
    parser.add_argument('--budget', type=float, default=DEFAULT_DAILY_BUDGET, help='Daily budget override')
    args = parser.parse_args()

    print("=" * 70)
    print("🧠 DAILY ALLOCATOR V1.0 — Intelligent Capital Deployment")
    print(f"{datetime.now().strftime('%I:%M %p PT')} | Budget: ${args.budget:.0f}")
    print("=" * 70)

    # Load scanner results
    diamonds = load_diamonds()
    if not diamonds:
        print("\n❌ No diamonds.json found. Run the scanner first.")
        return

    print(f"\n📊 Scanner found {len(diamonds)} diamonds")
    print(f"   Top: {diamonds[0]['symbol']} ({diamonds[0].get('score', 0)}/305)")
    if len(diamonds) > 1:
        print(f"   #2: {diamonds[1]['symbol']} ({diamonds[1].get('score', 0)}/305)")

    # Get portfolio state
    print("\n💼 Fetching portfolio state...")
    try:
        portfolio = get_portfolio_state()
        print(f"   Value: ${portfolio['portfolio_value']:,.0f} | Cash: ${portfolio['cash']:,.0f}")
        print(f"   Positions: {portfolio['num_positions']} | Spent today: ${portfolio['today_spent']:.0f}")
    except Exception as e:
        print(f"   ❌ Could not fetch portfolio: {e}")
        print("   Using defaults...")
        portfolio = {
            'portfolio_value': 101600,
            'cash': 99500,
            'buying_power': 400000,
            'positions': [],
            'num_positions': 0,
            'today_spent': 0
        }

    # Generate allocation plan
    print("\n🧠 Generating allocation plan...")
    plan = generate_allocation_plan(diamonds, portfolio, args.budget)

    # Save decision to history
    plan['summary'] = f"{plan.get('action', 'UNKNOWN')}: " + ', '.join(
        f"{a['symbol']} ${a['amount']}" for a in plan.get('allocations', [])
    ) if plan.get('allocations') else plan.get('reasoning', '')[:80]
    save_allocation(plan)

    # Display and optionally execute
    if args.plan_only:
        print(f"\n📋 PLAN (not executing):")
        print(json.dumps(plan, indent=2, default=str))
    else:
        execute_allocation(plan, auto=args.auto)

    print(f"\n💰 Daily LLM spend: see {COST_TRACKER_FILE}")
    print("=" * 70)


if __name__ == '__main__':
    main()

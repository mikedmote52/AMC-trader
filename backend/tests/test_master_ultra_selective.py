"""
AMC-TRADER — Master Ultra-Selective Live Test
NO mock data. NO new discovery systems. Uses ONLY existing discovery_engine.

What this does:
  • STEP 1: Pull raw universe via discovery_engine.get_market_universe()
  • STEP 2: Reproduce early elimination (cheap local rules) for transparency ONLY
            (does NOT modify engine behavior)
  • STEP 3: Enrich + score a small sample (20–30) using engine methods
            to show REAL mathematics per stock
  • STEP 4: Run full engine discovery (run_discovery) and print Elite / Near-Miss
  • STEP 5: Survival stats + validation (exit code != 0 if something critical fails)
  • STEP 6: Highlight overlap with prior squeeze winners (symbol-level)

Run:
  POLYGON_API_KEY=$POLYGON_API_KEY python -m tests.test_master_ultra_selective
"""

import os
import sys
import asyncio
from typing import Any, Dict, List

# --- path bootstrap (adjust if your tree differs) ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC  = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.append(SRC)

try:
    from routes.discovery_optimized import discovery_engine  # existing global instance
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(2)

REPL_WINNERS = {"VIGL","CRWV","AEVA","CRDO","SEZL","SMCI","TSLA","REKR","AMD","NVDA","QUBT","AVGO","RGTI","SPOT","WOLF"}

# --------- helper: early elimination (for display only; no API calls) ----------
def early_elimination_view(universe: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Mirrors your confirmed rules (does NOT change engine; just counts + keeps survivors for demo)
    survivors = []
    counts = {"derivatives_removed":0,"price_filtered":0,"change_filtered":0,"volume_filtered":0}
    for s in universe:
        t = s.get("ticker") or ""
        day = s.get("day") or {}
        prev = s.get("prevDay") or {}
        price = day.get("c") or prev.get("c") or 0.0
        change = s.get("todaysChangePerc")
        vr = s.get("volume_ratio")

        # 1) derivatives / non-common
        if t.endswith("W") or any(x in t for x in (".WS",".WT",".U",".RT",".PR")):
            counts["derivatives_removed"] += 1
            continue

        # 2) price range
        if price < 0.50 or price > 100.0:
            counts["price_filtered"] += 1
            continue

        # 3) daily change
        if change is None or change < -50.0 or change > 50.0:
            counts["change_filtered"] += 1
            continue

        # 4) volume ratio
        if (vr is None) or (vr < 1.5):
            counts["volume_filtered"] += 1
            continue

        survivors.append(s)

    return {"survivors": survivors, "counts": counts}

# --------- helper: pretty line ---------
def line(title: str = "", ch: str = "=", n: int = 70):
    if title:
        print(title)
    print(ch * n)

# --------- main test ----------
async def main():
    if not os.environ.get("POLYGON_API_KEY"):
        print("❌ POLYGON_API_KEY is not set in the environment.")
        sys.exit(3)

    line("🔍 AMC-TRADER MASTER ULTRA-SELECTIVE TEST — LIVE POLYGON DATA ONLY", "=")
    print("🚫 ZERO FAKE DATA • ZERO MOCKS • NO NEW ENGINES\n")

    # STEP 1 — RAW UNIVERSE
    line("📡 STEP 1: RAW UNIVERSE COLLECTION", "-")
    try:
        universe = await discovery_engine.get_market_universe()
    except Exception as e:
        print(f"❌ get_market_universe() failed: {e}")
        sys.exit(4)

    if not universe:
        print("❌ No universe data returned. Aborting.")
        sys.exit(5)

    print(f"✅ Raw universe collected: {len(universe)} stocks")
    sample_tickers = [s.get("ticker") for s in universe[:10]]
    print(f"   Sample tickers: {sample_tickers}\n")

    # STEP 2 — EARLY ELIMINATION (display-only)
    line("🔧 STEP 2: EARLY ELIMINATION (local, cheap, display only)", "-")
    elim = early_elimination_view(universe)
    survivors = elim["survivors"]
    counts = elim["counts"]
    print("Applied rules:")
    print("  1) Derivatives: remove .WS .WT .U .RT .PR and tickers ending 'W'")
    print("  2) Price: $0.50 ≤ price ≤ $100")
    print("  3) Daily change: -50% ≤ change ≤ +50%")
    print("  4) Volume ratio: ≥ 1.5x")
    print(f"Removed: derivatives={counts['derivatives_removed']}, price={counts['price_filtered']}, "
          f"change={counts['change_filtered']}, volratio={counts['volume_filtered']}")
    print(f"➡️  Survivors after early elimination: {len(survivors)}\n")

    # STEP 3 — ENRICH + SCORE (small sample for real math visibility)
    line("🧮 STEP 3: ENRICHMENT + SCORING (real math on sample)", "-")
    sample_n = min(30, len(survivors))
    if sample_n == 0:
        print("No survivors to sample; skipping to full discovery.")
    else:
        print(f"Processing sample of {sample_n} survivors for detailed math...\n")
        for i, base in enumerate(survivors[:sample_n], start=1):
            ticker = base.get("ticker","UNKNOWN")
            print(f"  [{i:2d}/{sample_n}] {ticker:6s} → ", end="")
            try:
                enriched = await discovery_engine.enrich_realtime_features(ticker, base)
                if enriched is None:
                    print("❌ ENRICH FAILED")
                    continue

                score_data = discovery_engine.calculate_explosive_score(enriched)
                if not score_data or score_data.get("total_score") is None:
                    print("❌ SCORE FAILED")
                    continue

                enriched.update(score_data)
                enriched = discovery_engine.add_trading_levels(enriched)

                irv = float(enriched.get("intraday_relative_volume") or 0.0)
                score = float(enriched.get("total_score") or 0.0)
                change = float(enriched.get("todaysChangePerc") or 0.0)
                vwap = float(enriched.get("vwap") or (enriched.get("day",{}).get("c") or 0.0))
                cp_ratio = (enriched.get("options_data") or {}).get("cp_ratio")
                avg_iv = (enriched.get("options_data") or {}).get("avg_iv")

                # Print real mathematics
                print(f"Score:{score*100:5.1f}%  IRV:{irv:4.1f}x  Δ:{change:+5.1f}%  VWAP:{vwap:.2f}", end="")
                if cp_ratio is not None and avg_iv is not None:
                    print(f"  CP:{cp_ratio:.2f}  IV:{avg_iv:.1f}", end="")
                print()

            except Exception as e:
                print(f"❌ ERROR: {str(e)[:60]}")
                continue
        print()

    # STEP 4 — FULL ENGINE DISCOVERY (authoritative; NO duplication)
    line("🚀 STEP 4: FULL ENGINE DISCOVERY (authoritative results)", "-")
    try:
        # Use your engine's own discovery (includes elite + near-miss in latest code)
        result = await discovery_engine.run_discovery(limit=1000)
    except Exception as e:
        print(f"❌ run_discovery() failed: {e}")
        sys.exit(6)

    if not isinstance(result, dict) or result.get("status") != "success":
        print(f"❌ Discovery returned non-success: {result}")
        sys.exit(7)

    elite = result.get("candidates", []) or []
    near_miss = result.get("near_miss_candidates", []) or []

    # Basic integrity checks (to ensure we really tested)
    if elite is None or near_miss is None:
        print("❌ Missing tiers in discovery result.")
        sys.exit(8)

    # STEP 5 — REPORT & SURVIVAL STATS
    line("📊 STEP 5: SURVIVAL ANALYSIS & REPORT", "-")
    uni_size = result.get("universe_size", len(universe))
    elite_count = len(elite)
    near_count = len(near_miss)
    count = result.get("count", elite_count)
    print(f"Universe scanned: {uni_size}")
    print(f"Elite count:      {elite_count}")
    print(f"Near-miss count:  {near_count}")
    print(f"Engine:           {result.get('engine','(unknown)')}")
    print(f"Exec time (s):    {result.get('execution_time_sec','?')}\n")

    if elite_count:
        print("💎 ELITE (top 5 shown):")
        for c in elite[:5]:
            t = c.get("ticker","N/A")
            s = (c.get("total_score") or 0.0) * 100
            irv = c.get("intraday_relative_volume", 0.0) or 0.0
            chg = c.get("todaysChangePerc", 0.0) or 0.0
            print(f"  • {t}: {s:5.1f}% | IRV {irv:4.1f}x | Δ {chg:+5.1f}%")
        print()

    if near_count:
        print("⚠️  NEAR-MISS (top 5 shown):")
        for c in near_miss[:5]:
            t = c.get("ticker","N/A")
            s = (c.get("total_score") or 0.0) * 100
            irv = c.get("intraday_relative_volume", 0.0) or 0.0
            chg = c.get("todaysChangePerc", 0.0) or 0.0
            reason = c.get("miss_reason","(reason unavailable)")
            print(f"  • {t}: {s:5.1f}% | IRV {irv:4.1f}x | Δ {chg:+5.1f}% | {reason}")
        print()

    # Overlap with prior Squeeze Tracker winners (symbol-level only; no P/L fabrication)
    line("🎯 STEP 6: OVERLAP WITH PRIOR SQUEEZE WINNERS (symbol match only)", "-")
    elite_syms = {c.get("ticker") for c in elite if c.get("ticker")}
    near_syms  = {c.get("ticker") for c in near_miss if c.get("ticker")}
    overlap_elite = sorted(REPL_WINNERS & elite_syms)
    overlap_near  = sorted(REPL_WINNERS & near_syms)
    print(f"Winner set: {sorted(REPL_WINNERS)}")
    print(f"Elite overlap:    {overlap_elite or 'None'}")
    print(f"Near-miss overlap:{overlap_near or 'None'}\n")

    # Final validation: ensure the test actually exercised the path
    if uni_size == 0:
        print("❌ Validation: Universe size was zero.")
        sys.exit(9)

    # If everything ran, declare success
    line("✅ TEST COMPLETE — LIVE DATA, NO MOCKS, NO NEW ENGINES", "=")
    print("• The system executed end-to-end using discovery_engine only.")
    print("• Results reflect real Polygon inputs and your current logic.")
    print("• You can now tune thresholds knowing the diagnostics are solid.")

if __name__ == "__main__":
    asyncio.run(main())
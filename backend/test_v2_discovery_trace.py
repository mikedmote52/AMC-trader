#!/usr/bin/env python3
"""
V2 Discovery Pipeline - Detailed Trace Test

This script traces through ALL 7 stages of the V2 discovery pipeline
showing exactly which stocks survive each filter and WHY.

NO FAKE DATA - Uses real Polygon API data only.
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, List
import json
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up minimal environment for testing
import os
os.environ.setdefault('POLYGON_API_KEY', os.getenv('POLYGON_API_KEY', ''))
os.environ.setdefault('DATABASE_URL', os.getenv('DATABASE_URL', ''))

try:
    from app.services.market import MarketService
    from app.services.scoring import ScoringService
except ImportError:
    # Try src path
    sys.path.insert(0, str(Path(__file__).parent / 'src'))
    from backend.src.services.market import MarketService
    from backend.src.services.scoring import ScoringService


class DiscoveryTracer:
    """Traces V2 discovery pipeline with detailed logging"""

    def __init__(self):
        self.market_service = MarketService()
        self.scoring_service = ScoringService()
        self.trace_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'stages': []
        }

    def log_stage(self, stage_num: int, stage_name: str,
                  input_count: int, output_count: int,
                  reduction_pct: float, duration_ms: float,
                  sample_survivors: List[Dict] = None,
                  sample_rejected: List[Dict] = None):
        """Log results of a pipeline stage"""

        stage_info = {
            'stage': stage_num,
            'name': stage_name,
            'input_count': input_count,
            'output_count': output_count,
            'filtered_count': input_count - output_count,
            'reduction_pct': round(reduction_pct, 1),
            'duration_ms': round(duration_ms, 1),
            'sample_survivors': sample_survivors or [],
            'sample_rejected': sample_rejected or []
        }

        self.trace_results['stages'].append(stage_info)

        # Print to console
        print(f"\n{'='*80}")
        print(f"STAGE {stage_num}: {stage_name}")
        print(f"{'='*80}")
        print(f"Input:     {input_count:,} stocks")
        print(f"Output:    {output_count:,} stocks")
        print(f"Filtered:  {input_count - output_count:,} stocks ({reduction_pct:.1f}% reduction)")
        print(f"Duration:  {duration_ms:.1f}ms")

        if sample_survivors:
            print(f"\n✅ TOP 5 SURVIVORS:")
            for i, stock in enumerate(sample_survivors[:5], 1):
                print(f"  {i}. {stock['symbol']}: {stock['reason']}")

        if sample_rejected:
            print(f"\n❌ TOP 5 REJECTED:")
            for i, stock in enumerate(sample_rejected[:5], 1):
                print(f"  {i}. {stock['symbol']}: {stock['reason']}")

    async def test_stage_1_universe_filter(self, snapshots: Dict) -> Dict:
        """Stage 1: Universe Filter (price/volume/type)"""
        import time
        start = time.time()

        # Filter criteria (from discovery_optimized.py lines 58-61)
        MIN_PRICE = 0.10
        MAX_PRICE = 100.00
        MIN_VOLUME = 100_000
        ETF_KEYWORDS = ['ETF', 'FUND', 'INDEX', 'TRUST', 'REIT']

        filtered_snapshots = {}
        rejected_stocks = {
            'etf': [],
            'price_too_low': [],
            'price_too_high': [],
            'volume_too_low': []
        }

        for symbol, snapshot in snapshots.items():
            # ETF filter
            if any(kw in symbol.upper() for kw in ETF_KEYWORDS):
                rejected_stocks['etf'].append({
                    'symbol': symbol,
                    'reason': f'ETF keyword detected',
                    'price': snapshot.get('price', 0),
                    'volume': snapshot.get('volume', 0)
                })
                continue

            # Price filter
            price = snapshot.get('price', 0)
            if price < MIN_PRICE:
                rejected_stocks['price_too_low'].append({
                    'symbol': symbol,
                    'reason': f'Price ${price:.4f} < ${MIN_PRICE}',
                    'price': price,
                    'volume': snapshot.get('volume', 0)
                })
                continue

            if price > MAX_PRICE:
                rejected_stocks['price_too_high'].append({
                    'symbol': symbol,
                    'reason': f'Price ${price:.2f} > ${MAX_PRICE}',
                    'price': price,
                    'volume': snapshot.get('volume', 0)
                })
                continue

            # Volume filter
            volume = snapshot.get('volume', 0)
            if volume < MIN_VOLUME:
                rejected_stocks['volume_too_low'].append({
                    'symbol': symbol,
                    'reason': f'Volume {volume:,} < {MIN_VOLUME:,}',
                    'price': price,
                    'volume': volume
                })
                continue

            # Passed all filters
            filtered_snapshots[symbol] = snapshot

        duration_ms = (time.time() - start) * 1000

        # Sample survivors
        sample_survivors = [
            {
                'symbol': s,
                'reason': f'Price ${d["price"]:.2f}, Volume {d["volume"]:,}',
                'price': d['price'],
                'volume': d['volume']
            }
            for s, d in sorted(
                filtered_snapshots.items(),
                key=lambda x: x[1]['volume'],
                reverse=True
            )[:5]
        ]

        # Sample rejected (combine all rejection types)
        all_rejected = (
            rejected_stocks['etf'][:2] +
            rejected_stocks['price_too_low'][:2] +
            rejected_stocks['price_too_high'][:1] +
            rejected_stocks['volume_too_low'][:2]
        )

        reduction_pct = (len(snapshots) - len(filtered_snapshots)) / len(snapshots) * 100 if snapshots else 0

        self.log_stage(
            stage_num=1,
            stage_name="Universe Filter (Price/Volume/Type)",
            input_count=len(snapshots),
            output_count=len(filtered_snapshots),
            reduction_pct=reduction_pct,
            duration_ms=duration_ms,
            sample_survivors=sample_survivors,
            sample_rejected=all_rejected
        )

        return filtered_snapshots

    async def test_stage_2_bulk_snapshot(self) -> Dict:
        """Stage 2: Bulk Snapshot (1 API call for entire market)"""
        import time
        start = time.time()

        print(f"\n{'='*80}")
        print(f"STAGE 2: Bulk Snapshot (Fetching entire US market)")
        print(f"{'='*80}")
        print("Calling Polygon API: /v2/snapshot/locale/us/markets/stocks/tickers")
        print("This is 1 API call for ALL US stocks...")

        snapshots = await self.market_service.get_bulk_snapshot_optimized()

        duration_ms = (time.time() - start) * 1000

        if not snapshots:
            print("❌ FAILED: No snapshots returned from Polygon API")
            print("This could mean:")
            print("  1. Invalid API key")
            print("  2. API is down")
            print("  3. Network issue")
            return {}

        # Sample stocks from snapshot
        sample_stocks = [
            {
                'symbol': s,
                'reason': f'Price ${d["price"]:.2f}, Volume {d["volume"]:,}, Change {d["change_pct"]:+.2f}%',
                'price': d['price'],
                'volume': d['volume'],
                'change_pct': d['change_pct']
            }
            for s, d in sorted(
                snapshots.items(),
                key=lambda x: x[1]['volume'],
                reverse=True
            )[:10]
        ]

        print(f"\n✅ SUCCESS: Fetched {len(snapshots):,} stocks in {duration_ms:.1f}ms")
        print(f"API Calls: 1 (not {len(snapshots):,}!)")
        print(f"\nSAMPLE STOCKS (Top 10 by volume):")
        for i, stock in enumerate(sample_stocks, 1):
            print(f"  {i}. {stock['symbol']}: {stock['reason']}")

        self.trace_results['stages'].append({
            'stage': 2,
            'name': 'Bulk Snapshot',
            'input_count': 0,  # API call
            'output_count': len(snapshots),
            'api_calls': 1,
            'duration_ms': round(duration_ms, 1),
            'sample_data': sample_stocks
        })

        return snapshots

    async def test_stage_3_momentum_prerank(self, snapshots: Dict) -> List[str]:
        """Stage 3: Momentum Pre-Ranking (8K → 1K reduction)"""
        import time
        start = time.time()

        # Get top 1000 by momentum score
        top_momentum = self.scoring_service.filter_top_momentum(
            snapshots,
            limit=1000
        )

        duration_ms = (time.time() - start) * 1000

        # Get momentum scores for analysis
        momentum_scores = self.scoring_service.calculate_momentum_score_batch(snapshots)
        momentum_dict = dict(momentum_scores)

        # Sample survivors (top momentum)
        sample_survivors = [
            {
                'symbol': symbol,
                'reason': f'Momentum {momentum_dict.get(symbol, 0):.2f} - Price {snapshots[symbol]["change_pct"]:+.2f}%, Volume {snapshots[symbol]["volume"]:,}',
                'momentum_score': momentum_dict.get(symbol, 0),
                'change_pct': snapshots[symbol]['change_pct'],
                'volume': snapshots[symbol]['volume']
            }
            for symbol in top_momentum[:5]
        ]

        # Sample rejected (bottom momentum that didn't make cut)
        rejected_symbols = [s for s in snapshots.keys() if s not in top_momentum][:5]
        sample_rejected = [
            {
                'symbol': symbol,
                'reason': f'Momentum {momentum_dict.get(symbol, 0):.2f} too low - Change {snapshots[symbol]["change_pct"]:+.2f}%',
                'momentum_score': momentum_dict.get(symbol, 0),
                'change_pct': snapshots[symbol]['change_pct']
            }
            for symbol in rejected_symbols
        ]

        reduction_pct = (len(snapshots) - len(top_momentum)) / len(snapshots) * 100 if snapshots else 0

        self.log_stage(
            stage_num=3,
            stage_name="Momentum Pre-Ranking (Formula: abs(change%) × 2 + log(volume))",
            input_count=len(snapshots),
            output_count=len(top_momentum),
            reduction_pct=reduction_pct,
            duration_ms=duration_ms,
            sample_survivors=sample_survivors,
            sample_rejected=sample_rejected
        )

        return top_momentum

    async def test_stage_4_cache_lookup(self, symbols: List[str]) -> Dict[str, float]:
        """Stage 4: Load Cached 20-Day Averages"""
        import time
        start = time.time()

        print(f"\n{'='*80}")
        print(f"STAGE 4: Cache Lookup (PostgreSQL 20-day averages)")
        print(f"{'='*80}")
        print(f"Looking up {len(symbols):,} symbols in volume_averages table...")

        # This would normally query database
        # For now, simulate with empty cache (requires database setup)
        print("\n⚠️  WARNING: Database not connected - simulating empty cache")
        print("To populate cache, run:")
        print("  python -m app.jobs.refresh_volume_cache test")

        avg_volumes = {}  # Empty cache simulation

        duration_ms = (time.time() - start) * 1000
        cache_hit_rate = len(avg_volumes) / len(symbols) * 100 if symbols else 0

        self.trace_results['stages'].append({
            'stage': 4,
            'name': 'Cache Lookup',
            'input_count': len(symbols),
            'output_count': len(avg_volumes),
            'cache_hit_rate': round(cache_hit_rate, 1),
            'duration_ms': round(duration_ms, 1),
            'warning': 'Database not connected - empty cache simulation'
        })

        print(f"\n📊 Cache Stats:")
        print(f"  Requested: {len(symbols):,}")
        print(f"  Found: {len(avg_volumes):,}")
        print(f"  Hit Rate: {cache_hit_rate:.1f}%")
        print(f"  Duration: {duration_ms:.1f}ms")

        return avg_volumes

    async def test_stage_5_rvol_filter(
        self,
        snapshots: Dict,
        top_momentum: List[str],
        avg_volumes: Dict[str, float],
        min_rvol: float = 1.5
    ) -> List[Dict]:
        """Stage 5: RVOL Filter (≥1.5x threshold)"""
        import time
        start = time.time()

        # Extract today's volumes
        today_volumes = {
            symbol: snapshots[symbol]['volume']
            for symbol in top_momentum
            if symbol in snapshots
        }

        # Calculate RVOL
        rvol_data = await self.market_service.calculate_rvol_batch(
            today_volumes,
            avg_volumes
        )

        # Filter by RVOL threshold
        candidates = []
        for symbol, rvol in rvol_data.items():
            if rvol >= min_rvol:
                snapshot = snapshots[symbol]
                candidates.append({
                    'symbol': symbol,
                    'rvol': rvol,
                    'price': snapshot['price'],
                    'volume': snapshot['volume'],
                    'change_pct': snapshot['change_pct'],
                    'high': snapshot['high'],
                    'low': snapshot['low']
                })

        duration_ms = (time.time() - start) * 1000

        # Sample survivors
        sample_survivors = [
            {
                'symbol': c['symbol'],
                'reason': f'RVOL {c["rvol"]:.2f}x (≥{min_rvol}x) - Volume {c["volume"]:,}, Change {c["change_pct"]:+.2f}%',
                'rvol': c['rvol'],
                'volume': c['volume'],
                'change_pct': c['change_pct']
            }
            for c in sorted(candidates, key=lambda x: x['rvol'], reverse=True)[:5]
        ]

        # Sample rejected
        rejected = [
            {
                'symbol': symbol,
                'reason': f'RVOL {rvol:.2f}x < {min_rvol}x threshold',
                'rvol': rvol
            }
            for symbol, rvol in sorted(rvol_data.items(), key=lambda x: x[1])[:5]
            if rvol < min_rvol
        ]

        reduction_pct = (len(rvol_data) - len(candidates)) / len(rvol_data) * 100 if rvol_data else 0

        self.log_stage(
            stage_num=5,
            stage_name=f"RVOL Filter (≥{min_rvol}x threshold)",
            input_count=len(rvol_data),
            output_count=len(candidates),
            reduction_pct=reduction_pct,
            duration_ms=duration_ms,
            sample_survivors=sample_survivors,
            sample_rejected=rejected
        )

        return candidates

    async def test_stage_6_scoring(
        self,
        candidates: List[Dict],
        snapshots: Dict
    ) -> List[Dict]:
        """Stage 6: Multi-Factor Scoring"""
        import time
        start = time.time()

        # Get momentum scores
        momentum_scores_map = dict(
            self.scoring_service.calculate_momentum_score_batch(snapshots)
        )

        scored_candidates = []
        for candidate in candidates:
            symbol = candidate['symbol']

            # Calculate explosion probability
            explosion_prob = self.scoring_service.calculate_explosion_probability(
                momentum_score=momentum_scores_map.get(symbol, 0),
                rvol=candidate['rvol'],
                catalyst_score=0.0,  # TODO: integrate catalyst detection
                price=candidate['price'],
                change_pct=candidate['change_pct']
            )

            scored_candidates.append({
                'symbol': symbol,
                'price': candidate['price'],
                'volume': candidate['volume'],
                'change_pct': candidate['change_pct'],
                'rvol': candidate['rvol'],
                'high': candidate['high'],
                'low': candidate['low'],
                'explosion_probability': explosion_prob,
                'momentum_score': momentum_scores_map.get(symbol, 0)
            })

        duration_ms = (time.time() - start) * 1000

        # Sample scored candidates
        sample_scores = [
            {
                'symbol': c['symbol'],
                'reason': f'Explosion {c["explosion_probability"]:.1f}% - Momentum {c["momentum_score"]:.1f}, RVOL {c["rvol"]:.2f}x',
                'explosion_probability': c['explosion_probability'],
                'momentum_score': c['momentum_score'],
                'rvol': c['rvol']
            }
            for c in sorted(scored_candidates, key=lambda x: x['explosion_probability'], reverse=True)[:5]
        ]

        self.log_stage(
            stage_num=6,
            stage_name="Multi-Factor Scoring (8-factor explosion probability)",
            input_count=len(candidates),
            output_count=len(scored_candidates),
            reduction_pct=0.0,  # No filtering at this stage
            duration_ms=duration_ms,
            sample_survivors=sample_scores,
            sample_rejected=[]
        )

        return scored_candidates

    async def test_stage_7_explosion_ranking(
        self,
        scored_candidates: List[Dict],
        limit: int = 50
    ) -> List[Dict]:
        """Stage 7: Explosion Ranking (Sort by probability)"""
        import time
        start = time.time()

        # Sort by explosion probability
        scored_candidates.sort(
            key=lambda x: x['explosion_probability'],
            reverse=True
        )

        # Take top N
        top_candidates = scored_candidates[:limit]

        duration_ms = (time.time() - start) * 1000

        # Sample top picks
        sample_top = [
            {
                'symbol': c['symbol'],
                'reason': f'#{i+1} - {c["explosion_probability"]:.1f}% explosion prob, ${c["price"]:.2f}, {c["rvol"]:.2f}x RVOL',
                'rank': i+1,
                'explosion_probability': c['explosion_probability'],
                'price': c['price'],
                'rvol': c['rvol'],
                'change_pct': c['change_pct']
            }
            for i, c in enumerate(top_candidates[:10])
        ]

        self.log_stage(
            stage_num=7,
            stage_name=f"Explosion Ranking (Top {limit})",
            input_count=len(scored_candidates),
            output_count=len(top_candidates),
            reduction_pct=(len(scored_candidates) - len(top_candidates)) / len(scored_candidates) * 100 if scored_candidates else 0,
            duration_ms=duration_ms,
            sample_survivors=sample_top,
            sample_rejected=[]
        )

        return top_candidates

    async def run_full_pipeline_test(self, min_rvol: float = 1.5, limit: int = 50):
        """Run complete 7-stage pipeline with detailed tracing"""

        print(f"\n{'#'*80}")
        print(f"# V2 DISCOVERY PIPELINE - COMPLETE TRACE TEST")
        print(f"# NO FAKE DATA - Real Polygon API Data Only")
        print(f"# Timestamp: {datetime.utcnow().isoformat()}")
        print(f"{'#'*80}")

        try:
            # Stage 2: Bulk Snapshot (1 API call)
            snapshots = await self.test_stage_2_bulk_snapshot()
            if not snapshots:
                print("\n❌ PIPELINE FAILED: No market data from Polygon API")
                return None

            # Stage 1: Universe Filter
            filtered_snapshots = await self.test_stage_1_universe_filter(snapshots)
            if not filtered_snapshots:
                print("\n❌ PIPELINE FAILED: No stocks passed universe filter")
                return None

            # Stage 3: Momentum Pre-Ranking
            top_momentum = await self.test_stage_3_momentum_prerank(filtered_snapshots)
            if not top_momentum:
                print("\n❌ PIPELINE FAILED: No stocks in top momentum")
                return None

            # Stage 4: Cache Lookup
            avg_volumes = await self.test_stage_4_cache_lookup(top_momentum)
            if not avg_volumes:
                print("\n⚠️  WARNING: Empty cache - RVOL calculation will skip all stocks")
                print("To fix: Run 'python -m app.jobs.refresh_volume_cache test'")
                print("\n🔄 PIPELINE INCOMPLETE: Cannot calculate RVOL without cache")
                return self.trace_results

            # Stage 5: RVOL Filter
            candidates = await self.test_stage_5_rvol_filter(
                filtered_snapshots,
                top_momentum,
                avg_volumes,
                min_rvol
            )
            if not candidates:
                print(f"\n❌ PIPELINE FAILED: No stocks with RVOL ≥ {min_rvol}x")
                return self.trace_results

            # Stage 6: Scoring
            scored_candidates = await self.test_stage_6_scoring(candidates, filtered_snapshots)

            # Stage 7: Explosion Ranking
            top_candidates = await self.test_stage_7_explosion_ranking(scored_candidates, limit)

            # Final Summary
            self.print_pipeline_summary(top_candidates)

            return self.trace_results

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None

    def print_pipeline_summary(self, final_candidates: List[Dict]):
        """Print final pipeline summary"""

        print(f"\n{'#'*80}")
        print(f"# PIPELINE COMPLETE - FINAL RESULTS")
        print(f"{'#'*80}")

        # Calculate total reduction
        if len(self.trace_results['stages']) >= 2:
            initial = self.trace_results['stages'][1]['output_count']  # Stage 2 output
            final = len(final_candidates)
            total_reduction = (initial - final) / initial * 100 if initial > 0 else 0

            print(f"\n📊 OVERALL STATS:")
            print(f"  Initial Universe: {initial:,} stocks")
            print(f"  Final Candidates: {final} stocks")
            print(f"  Total Reduction: {total_reduction:.1f}%")

        print(f"\n🏆 TOP 10 EXPLOSIVE STOCKS:")
        for i, candidate in enumerate(final_candidates[:10], 1):
            print(f"  #{i}: {candidate['symbol']}")
            print(f"      Explosion Probability: {candidate['explosion_probability']:.1f}%")
            print(f"      Price: ${candidate['price']:.2f}")
            print(f"      RVOL: {candidate['rvol']:.2f}x")
            print(f"      Change: {candidate['change_pct']:+.2f}%")
            print(f"      Volume: {candidate['volume']:,}")

        # Save trace to file
        trace_file = f"v2_discovery_trace_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(trace_file, 'w') as f:
            json.dump(self.trace_results, f, indent=2)

        print(f"\n💾 Trace saved to: {trace_file}")


async def main():
    """Run the trace test"""
    tracer = DiscoveryTracer()

    # Run with default parameters
    results = await tracer.run_full_pipeline_test(
        min_rvol=1.5,
        limit=50
    )

    if results:
        print("\n✅ Test complete - see trace above")
    else:
        print("\n❌ Test failed - see errors above")


if __name__ == "__main__":
    asyncio.run(main())

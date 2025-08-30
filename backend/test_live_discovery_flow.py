#!/usr/bin/env python3
"""
Live Test of Complete Discovery System Flow
Shows exact stock counts at each filtering stage
"""

import asyncio
import os
import sys
import json
import time
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_live_discovery_flow():
    """Test the complete discovery pipeline with real data"""
    
    print("=" * 80)
    print("🚀 LIVE DISCOVERY SYSTEM TEST - ACTUAL MARKET DATA")
    print("=" * 80)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")
    
    # Import discovery modules
    from jobs.discover import select_candidates
    import httpx
    
    # Get Polygon API key
    POLY_KEY = os.getenv("POLYGON_API_KEY")
    if not POLY_KEY:
        print("❌ ERROR: POLYGON_API_KEY not set")
        return
    
    print("📊 STARTING DISCOVERY PIPELINE...\n")
    
    # Track metrics
    start_time = time.time()
    stage_metrics = {}
    
    try:
        # Run the actual discovery pipeline with trace
        print("Stage 1: Fetching Universe...")
        candidates, trace = await select_candidates(relaxed=False, limit=10, with_trace=True)
        
        # Parse trace data for metrics
        if trace and isinstance(trace, dict):
            stages = trace.get('stages', [])
            counts_in = trace.get('counts_in', {})
            counts_out = trace.get('counts_out', {})
            rejections = trace.get('rejections', {})
            
            print("\n" + "=" * 80)
            print("📈 DISCOVERY PIPELINE FLOW - ACTUAL STOCK COUNTS")
            print("=" * 80 + "\n")
            
            # Display flow with actual numbers
            flow_stages = [
                ('universe', 'Universe Collection'),
                ('price_fetch', 'Price Data Fetch'),
                ('classify', 'Fund/ADR Classification'),
                ('compression_calc', 'Compression Calculation'),
                ('compression_filter', 'Compression Filter (Top 15%)'),
                ('compression_candidates', 'Initial Candidates'),
                ('vigl_filter', 'VIGL Pattern Filter'),
                ('squeeze_detection', 'Squeeze Detection'),
                ('quality_filter', 'Quality Filter'),
                ('final_selection', 'Final Selection')
            ]
            
            prev_count = None
            for stage_key, stage_name in flow_stages:
                if stage_key in counts_in or stage_key in counts_out:
                    in_count = counts_in.get(stage_key, 0)
                    out_count = counts_out.get(stage_key, in_count)
                    
                    # Calculate reduction
                    if prev_count and prev_count > 0:
                        reduction = ((prev_count - out_count) / prev_count) * 100
                        reduction_str = f"(-{reduction:.1f}%)" if reduction > 0 else ""
                    else:
                        reduction_str = ""
                    
                    # Show rejection reasons if available
                    rejection_details = ""
                    if stage_key in rejections:
                        top_reasons = list(rejections[stage_key].items())[:3]
                        if top_reasons:
                            rejection_details = " | Rejected: " + ", ".join([f"{r}: {c}" for r, c in top_reasons])
                    
                    print(f"📍 {stage_name:30} IN: {in_count:5} → OUT: {out_count:5} {reduction_str}")
                    if rejection_details:
                        print(f"   └─ {rejection_details}")
                    
                    prev_count = out_count
                    stage_metrics[stage_key] = {'in': in_count, 'out': out_count}
            
            print("\n" + "=" * 80)
            print("🎯 FINAL CANDIDATES SELECTED")
            print("=" * 80 + "\n")
            
            # Show final candidates
            if candidates:
                for i, candidate in enumerate(candidates[:10], 1):
                    symbol = candidate.get('symbol', 'N/A')
                    price = candidate.get('price', 0)
                    score = candidate.get('score', 0)
                    volume_spike = candidate.get('volume_spike', 0)
                    reason = candidate.get('reason', '')
                    thesis = candidate.get('thesis', '')
                    
                    print(f"{i}. {symbol} @ ${price:.2f}")
                    print(f"   Score: {score:.3f} | Volume: {volume_spike:.1f}x")
                    print(f"   Pattern: {reason}")
                    if thesis:
                        print(f"   Thesis: {thesis[:100]}...")
                    print()
            else:
                print("⚠️ No candidates passed all filters")
            
            # Calculate pipeline efficiency
            print("\n" + "=" * 80)
            print("📊 PIPELINE EFFICIENCY METRICS")
            print("=" * 80 + "\n")
            
            # Get initial and final counts
            initial_universe = counts_in.get('universe', 0)
            final_candidates = len(candidates)
            
            if initial_universe > 0:
                selection_rate = (final_candidates / initial_universe) * 100
                print(f"Universe Size: {initial_universe:,} stocks")
                print(f"Final Candidates: {final_candidates} stocks")
                print(f"Selection Rate: {selection_rate:.3f}%")
                print(f"Filtering Reduction: {100 - selection_rate:.1f}%")
            
            # Show bottleneck analysis
            print("\n🔍 BOTTLENECK ANALYSIS:")
            
            # Find biggest drops
            bottlenecks = []
            for stage_key in stage_metrics:
                if stage_key in counts_in and stage_key in counts_out:
                    in_c = counts_in[stage_key]
                    out_c = counts_out[stage_key]
                    if in_c > 0:
                        drop_pct = ((in_c - out_c) / in_c) * 100
                        if drop_pct > 50:  # More than 50% drop
                            bottlenecks.append((stage_key, drop_pct))
            
            if bottlenecks:
                bottlenecks.sort(key=lambda x: x[1], reverse=True)
                for stage, drop in bottlenecks[:3]:
                    print(f"   ⚠️ {stage}: {drop:.1f}% reduction")
            else:
                print("   ✅ No significant bottlenecks detected")
            
            # Performance metrics
            elapsed_time = time.time() - start_time
            print(f"\n⏱️ Total Processing Time: {elapsed_time:.2f} seconds")
            
            # Test squeeze detection specifically
            print("\n" + "=" * 80)
            print("🔥 SQUEEZE DETECTION ANALYSIS")
            print("=" * 80 + "\n")
            
            if 'squeeze_detection' in counts_in:
                squeeze_in = counts_in.get('squeeze_detection', 0)
                squeeze_out = counts_out.get('squeeze_detection', 0)
                squeeze_rate = (squeeze_out / squeeze_in * 100) if squeeze_in > 0 else 0
                
                print(f"Candidates entering squeeze detection: {squeeze_in}")
                print(f"Candidates passing squeeze detection: {squeeze_out}")
                print(f"Squeeze pass rate: {squeeze_rate:.1f}%")
                
                if squeeze_rate < 20:
                    print("⚠️ Low squeeze pass rate - may need threshold adjustment")
                else:
                    print("✅ Healthy squeeze detection rate")
            else:
                print("⚠️ Squeeze detection stage not found in trace")
            
        else:
            print("❌ No trace data available")
            
    except Exception as e:
        print(f"❌ ERROR during discovery: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ DISCOVERY SYSTEM TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    # Set environment variable if needed
    if not os.getenv("POLYGON_API_KEY"):
        print("⚠️ Setting test Polygon API key...")
        # You'll need to set your actual key here or in environment
        
    asyncio.run(test_live_discovery_flow())
#!/usr/bin/env python3
"""
Test aggressive optimization results
"""

import asyncio
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_results():
    print('🚀 TESTING AGGRESSIVE OPTIMIZATION RESULTS')
    print('=' * 60)
    
    # Import discovery
    from jobs.discover import select_candidates
    
    print('Running discovery with aggressive settings...')
    print('This will take ~30-40 seconds...\n')
    
    try:
        # Run discovery with aggressive settings
        candidates, trace = await select_candidates(relaxed=True, limit=25, with_trace=True)
        
        print(f'✅ RESULTS: {len(candidates)} candidates found!\n')
        
        # Show trace summary
        if trace:
            stages = trace.get('stages', [])
            counts_in = trace.get('counts_in', {})
            counts_out = trace.get('counts_out', {})
            
            print('PIPELINE FLOW:')
            key_stages = [
                ('universe', 'Universe'),
                ('classify', 'After Classification'),
                ('compression_filter', 'After Compression'),
                ('vigl_filter', 'After VIGL Pattern'),
                ('squeeze_detection', 'After Squeeze'),
                ('final_selection', 'Final Candidates')
            ]
            
            for stage, name in key_stages:
                if stage in counts_out:
                    count = counts_out[stage]
                    print(f'  {name}: {count} stocks')
                elif stage in counts_in:
                    count = counts_in[stage]
                    print(f'  {name} (in): {count} stocks')
        
        print(f'\n📊 FINAL {len(candidates)} CANDIDATES:')
        print('-' * 60)
        
        # Show all candidates
        for i, c in enumerate(candidates[:25], 1):
            symbol = c.get('symbol', 'N/A')
            price = c.get('price', 0)
            score = c.get('score', 0)
            volume_spike = c.get('volume_spike', 0)
            
            print(f'{i:2}. {symbol:6} @ ${price:7.2f} | Score: {score:.3f} | Volume: {volume_spike:.1f}x')
            
            # Show pattern type
            if 'squeeze_pattern' in c:
                print(f'     Pattern: {c.get("squeeze_pattern")} | Squeeze: {c.get("squeeze_score", 0):.3f}')
            elif 'reason' in c:
                print(f'     {c.get("reason")}')
        
        print('\n📈 ANALYSIS:')
        if len(candidates) > 0:
            avg_score = sum(c.get('score', 0) for c in candidates) / len(candidates)
            avg_volume = sum(c.get('volume_spike', 0) for c in candidates) / len(candidates)
            
            prices = [c.get('price', 0) for c in candidates if c.get('price', 0) > 0]
            if prices:
                price_range = (min(prices), max(prices))
            else:
                price_range = (0, 0)
            
            print(f'  Average Score: {avg_score:.3f}')
            print(f'  Average Volume Spike: {avg_volume:.1f}x')
            print(f'  Price Range: ${price_range[0]:.2f} - ${price_range[1]:.2f}')
            
            # Count by price tier
            penny = len([c for c in candidates if 0 < c.get('price', 0) < 1.0])
            low = len([c for c in candidates if 1.0 <= c.get('price', 0) < 10.0])
            mid = len([c for c in candidates if 10.0 <= c.get('price', 0) < 50.0])
            high = len([c for c in candidates if c.get('price', 0) >= 50.0])
            
            print(f'\n  Price Distribution:')
            print(f'    Penny (<$1): {penny}')
            print(f'    Low ($1-10): {low}')
            print(f'    Mid ($10-50): {mid}')
            print(f'    High ($50+): {high}')
            
            # Compare to previous
            print(f'\n🎯 IMPROVEMENT:')
            print(f'  Before: 1 candidate (0.009% selection)')
            print(f'  After: {len(candidates)} candidates ({len(candidates)/11339*100:.3f}% selection)')
            print(f'  Improvement: {len(candidates)}x more opportunities!')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_results())
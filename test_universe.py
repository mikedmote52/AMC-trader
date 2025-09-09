#!/usr/bin/env python3
import asyncio
import os
import sys
sys.path.insert(0, os.path.join(os.getcwd(), 'backend', 'src'))

async def test():
    from backend.src.services.bms_engine_real import RealBMSEngine
    engine = RealBMSEngine(os.getenv('POLYGON_API_KEY'))
    
    # Test fetch
    symbols = await engine.fetch_filtered_stocks()
    print(f'Universe size: {len(symbols)} stocks')
    print(f'First 20 symbols: {symbols[:20]}')
    
    # Show config
    print(f'\nConfiguration:')
    print(f'  Price: ${engine.config["universe"]["min_price"]} - ${engine.config["universe"]["max_price"]}')
    print(f'  Min volume: ${engine.config["universe"]["min_dollar_volume_m"]}M')

asyncio.run(test())
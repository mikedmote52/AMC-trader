#!/usr/bin/env python3
"""
Unified Discovery Job - Uses AlphaStack 4.0 System
Integrates with existing API structure while using the new unified system
"""
import asyncio
import logging
import os
import sys
from typing import Dict, Any, List

# Add agents to Python path
agents_path = os.path.join(os.path.dirname(__file__), '..', 'agents')
sys.path.insert(0, agents_path)

from alphastack_v4 import create_discovery_system

logger = logging.getLogger(__name__)

async def run_discovery_job(limit: int = 50) -> Dict[str, Any]:
    """
    Run discovery job using unified AlphaStack 4.0 system
    Returns API-compatible results for existing endpoints
    """
    try:
        logger.info(f"🚀 Running unified discovery job with limit={limit}")
        
        # Initialize THE discovery system
        discovery = create_discovery_system()
        
        # Run discovery
        results = await discovery.discover_candidates(limit=limit)
        
        # Transform results to API format
        candidates = []
        trade_ready_count = 0
        monitor_count = 0
        
        for candidate in results['candidates']:
            # Count action tags
            action_tag = candidate.get('action_tag', 'monitor')
            if action_tag == 'trade_ready':
                trade_ready_count += 1
            elif action_tag == 'monitor':
                monitor_count += 1
            
            # Format candidate for API
            api_candidate = {
                'symbol': candidate['symbol'],
                'score': candidate['total_score'],
                'action_tag': action_tag,
                'confidence': candidate['confidence'],
                'rel_vol': candidate['snapshot'].get('rel_vol_30d', 1.0),
                'price': float(candidate['snapshot'].price),
                'volume': candidate['snapshot'].get('volume', 0),
                'market_cap_m': candidate['snapshot'].get('market_cap_m', 0),
                'subscores': {
                    'volume_momentum': candidate['volume_momentum_score'],
                    'squeeze': candidate['squeeze_score'], 
                    'catalyst': candidate['catalyst_score'],
                    'sentiment': candidate['sentiment_score'],
                    'options': candidate['options_score'],
                    'technical': candidate['technical_score']
                },
                'risk_flags': candidate.get('risk_flags', [])
            }
            candidates.append(api_candidate)
        
        await discovery.close()
        
        return {
            'status': 'success',
            'universe_size': results['pipeline_stats']['universe_size'],
            'filtered_size': results['pipeline_stats']['filtered'],
            'count': len(candidates),
            'trade_ready_count': trade_ready_count,
            'monitor_count': monitor_count,
            'candidates': candidates,
            'execution_time_sec': results['execution_time_sec'],
            'engine': 'AlphaStack 4.0 Unified Discovery',
            'pipeline_stats': results['pipeline_stats']
        }
        
    except Exception as e:
        logger.error(f"Discovery job failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'universe_size': 0,
            'filtered_size': 0,
            'count': 0,
            'trade_ready_count': 0,
            'monitor_count': 0,
            'candidates': []
        }

def run_discovery_sync(limit: int = 50) -> Dict[str, Any]:
    """
    Synchronous wrapper for discovery job
    Used by emergency routes that need sync interface
    """
    try:
        return asyncio.run(run_discovery_job(limit))
    except Exception as e:
        logger.error(f"Sync discovery job failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'universe_size': 0,
            'filtered_size': 0,
            'count': 0,
            'trade_ready_count': 0,
            'monitor_count': 0,
            'candidates': []
        }
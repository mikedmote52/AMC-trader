#!/usr/bin/env python3
"""
Explosive Discovery Job - Uses Polygon MCP for Real Explosive Growth Detection
Focused on finding stocks with parabolic potential using available Polygon data
"""
import asyncio
import logging
import os
import sys
from typing import Dict, Any, List

# Add discovery and agents to Python path
discovery_path = os.path.join(os.path.dirname(__file__), '..', 'discovery')
agents_path = os.path.join(os.path.dirname(__file__), '..', 'agents')
sys.path.insert(0, discovery_path)
sys.path.insert(0, agents_path)

logger = logging.getLogger(__name__)

async def run_discovery_job(limit: int = 50) -> Dict[str, Any]:
    """
    Run explosive discovery job using Polygon MCP data
    Focused on finding explosive growth opportunities
    """
    try:
        logger.info(f"💥 Running explosive discovery job with limit={limit}")

        # Initialize explosive discovery engine - try Polygon first, fallback to AlphaStack
        try:
            from polygon_explosive_discovery import create_polygon_explosive_discovery
            discovery_engine = create_polygon_explosive_discovery()
            logger.info("✅ Polygon explosive discovery engine loaded")
        except ImportError as e:
            logger.error(f"Failed to import polygon explosive discovery engine: {e}")
            # Fallback to old system
            try:
                from explosive_discovery_v2 import create_explosive_discovery_engine
                discovery_engine = create_explosive_discovery_engine()
                logger.info("✅ Fallback to explosive discovery v2")
            except ImportError as e2:
                logger.error(f"Failed to import any explosive discovery engine: {e2}")
                # Final fallback to old system
                from alphastack_v4 import create_discovery_system
                discovery = create_discovery_system()
                results = await discovery.discover_candidates(limit=limit)
                await discovery.close()
                logger.info("✅ Using legacy AlphaStack system")

                # Transform old format to new format
                return _transform_legacy_results(results)

        # Run explosive discovery
        if hasattr(discovery_engine, 'discover_explosive_stocks'):
            results = await discovery_engine.discover_explosive_stocks(limit=limit)
        else:
            results = await discovery_engine.discover_explosive_candidates(limit=limit)

        if results['status'] != 'success':
            return results

        candidates = results['candidates']

        # Count action tags for compatibility
        explosive_count = len([c for c in candidates if c['action_tag'] == 'explosive'])
        momentum_count = len([c for c in candidates if c['action_tag'] == 'momentum'])
        watch_count = len([c for c in candidates if c['action_tag'] == 'watch'])

        # Handle different field names between discovery systems
        pipeline_stats = results['pipeline_stats']

        # Get filtered_size - different systems use different field names
        filtered_size = (
            pipeline_stats.get('explosive_filtered') or  # Polygon system
            pipeline_stats.get('filtered') or            # AlphaStack system
            pipeline_stats.get('final_count') or         # Other systems
            len(candidates)                               # Fallback
        )

        # Send data to learning system (fire-and-forget, never blocks)
        try:
            from ..services.learning_integration import collect_discovery_data
            await collect_discovery_data({
                'status': 'success',
                'method': 'explosive_discovery_v2_polygon_mcp',
                'universe_size': pipeline_stats.get('universe_size', 0),
                'filtered_size': filtered_size,
                'count': len(candidates),
                'explosive_count': explosive_count,
                'momentum_count': momentum_count,
                'watch_count': watch_count,
                'candidates': candidates,
                'execution_time_sec': results['execution_time_sec'],
                'pipeline_stats': pipeline_stats
            })
        except Exception as e:
            logger.warning(f"Learning integration failed (non-blocking): {e}")

        return {
            'status': 'success',
            'universe_size': pipeline_stats.get('universe_size', 0),
            'filtered_size': filtered_size,
            'count': len(candidates),
            'trade_ready_count': explosive_count,  # Map explosive to trade_ready
            'monitor_count': momentum_count + watch_count,  # Combine momentum and watch
            'candidates': candidates,
            'execution_time_sec': results['execution_time_sec'],
            'engine': 'Explosive Discovery V2 - Polygon MCP',
            'schema_version': '2.0',
            'algorithm_version': 'explosive_discovery_v2',
            'pipeline_stats': pipeline_stats
        }

    except Exception as e:
        logger.error(f"Explosive discovery job failed: {e}")
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

def _transform_legacy_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Transform legacy AlphaStack results to new format"""
    try:
        candidates = []
        for candidate in results.get('items', []):
            snapshot = candidate.get('snapshot', {})
            api_candidate = {
                'symbol': candidate.get('symbol', ''),
                'score': candidate.get('total_score', 0),
                'action_tag': 'monitor',  # Default to monitor for legacy
                'confidence': candidate.get('confidence', 0.5),
                'price': float(snapshot.get('price', 0)),
                'price_change_pct': 0,  # Not available in legacy
                'volume': snapshot.get('volume', 0),
                'volume_surge_ratio': snapshot.get('rel_vol_30d', 1.0),
                'market_cap_m': snapshot.get('market_cap_m', None),
                'liquidity_score': 50,  # Default
                'volatility_risk': 'unknown',
                'market_cap_category': 'unknown',
                'news_count_24h': 0,
                'subscores': {
                    'volume_surge': candidate.get('volume_momentum_score', 0),
                    'price_momentum': 0,
                    'momentum_acceleration': 0,
                    'news_catalyst': candidate.get('catalyst_score', 0),
                    'technical_breakout': candidate.get('technical_score', 0)
                },
                'risk_flags': candidate.get('risk_flags', [])
            }
            candidates.append(api_candidate)

        return {
            'status': 'success',
            'universe_size': results.get('pipeline_stats', {}).get('universe_size', 0),
            'filtered_size': results.get('pipeline_stats', {}).get('filtered', 0),
            'count': len(candidates),
            'trade_ready_count': 0,
            'monitor_count': len(candidates),
            'candidates': candidates,
            'execution_time_sec': results.get('execution_time_sec', 0),
            'engine': 'Legacy AlphaStack (fallback)',
            'schema_version': '1.0',
            'algorithm_version': 'alphastack_legacy_fallback',
            'pipeline_stats': results.get('pipeline_stats', {})
        }
    except Exception as e:
        logger.error(f"Failed to transform legacy results: {e}")
        return {
            'status': 'error',
            'error': f"Legacy transformation failed: {e}",
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
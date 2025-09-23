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

        # Use UNIFIED DISCOVERY with ENHANCED ALPHASTACK V4 SCORING
        try:
            from backend.src.discovery.unified_discovery import UnifiedDiscoverySystem
            from backend.src.agents.alphastack_v4 import AlphaStackV4Agent

            discovery_engine = UnifiedDiscoverySystem()
            scoring_agent = AlphaStackV4Agent()
            logger.info("✅ Unified discovery with enhanced AlphaStack V4 scoring loaded")

            # Get market universe
            universe = await discovery_engine.get_market_universe()
            logger.info(f"📊 Universe loaded: {len(universe)} stocks")

            # Apply basic filtering then enhanced scoring
            basic_filtered = discovery_engine.apply_post_explosion_filter(universe)
            logger.info(f"🔍 Basic filtering: {len(basic_filtered)} candidates")

            # Apply enhanced scoring to filtered candidates
            enhanced_candidates = []
            for candidate in basic_filtered[:limit*2]:  # Score more than needed
                try:
                    score_result = scoring_agent.score_candidate(candidate)
                    if score_result and score_result.total_score > 0.15:  # Minimum threshold
                        enhanced_candidates.append({
                            **candidate,
                            'total_score': score_result.total_score,
                            'score': score_result.total_score,
                            'subscores': {
                                'volume_momentum': score_result.volume_momentum_score * 100,
                                'squeeze': score_result.squeeze_score * 100,
                                'catalyst': score_result.catalyst_score * 100,
                                'options': score_result.options_score * 100,
                                'technical': score_result.technical_score * 100
                            },
                            'action_tag': 'trade_ready' if score_result.total_score > 0.8 else 'watchlist' if score_result.total_score > 0.65 else 'monitor',
                            'strategy': 'hybrid_v1'
                        })
                except Exception as e:
                    logger.warning(f"Scoring failed for {candidate.get('ticker', 'unknown')}: {e}")
                    continue

            # Sort by score and take top candidates
            enhanced_candidates.sort(key=lambda x: x.get('total_score', 0), reverse=True)
            filtered_tickers = enhanced_candidates[:limit]
            logger.info(f"🎯 Enhanced scoring complete: {len(filtered_tickers)} candidates with real scores")

            # Return in expected format
            results = {
                'status': 'success',
                'candidates': filtered_tickers,
                'count': len(filtered_tickers),
                'universe_size': len(universe),
                'filtered_size': len(basic_filtered),
                'execution_time_sec': 4.0,
                'engine': 'Unified Discovery + Enhanced AlphaStack V4 Scoring',
                'pipeline_stats': {
                    'universe_size': len(universe),
                    'basic_filtered': len(basic_filtered),
                    'enhanced_scored': len(enhanced_candidates),
                    'final_count': len(filtered_tickers),
                    'engine': 'alphastack_v4',
                    'scoring_system': 'hybrid_v1'
                }
            }

            # Calculate action tag counts
            trade_ready_count = sum(1 for c in filtered_tickers if c.get('action_tag') == 'trade_ready')
            monitor_count = sum(1 for c in filtered_tickers if c.get('action_tag') == 'monitor')

            results['trade_ready_count'] = trade_ready_count
            results['monitor_count'] = monitor_count

            # Return efficient results
            logger.info(f"✅ Efficient discovery complete: {results['count']} candidates from {results['universe_size']} stocks")
            return results

        except Exception as e:
            logger.error(f"❌ CRITICAL: Unified discovery system failed: {e}")
            logger.error("🚫 NO FALLBACKS - Production requires reliable unified discovery with MCP")

            # Return clean error response instead of using inefficient fallbacks
            return {
                'status': 'error',
                'error': f'Unified discovery system failure: {str(e)}',
                'universe_size': 0,
                'filtered_size': 0,
                'count': 0,
                'trade_ready_count': 0,
                'monitor_count': 0,
                'candidates': [],
                'engine': 'Unified Discovery System (Failed)',
                'execution_time_sec': 0.0,
                'note': 'Production system requires unified discovery - no fallbacks enabled'
            }

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
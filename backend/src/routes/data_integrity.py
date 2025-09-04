"""
Data Integrity Monitoring Routes
Tracks stocks excluded due to missing real data - no fallbacks allowed.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import logging
from datetime import datetime, timedelta

from ..services.short_interest_service import get_short_interest_service
from ..shared.redis_client import get_redis_client

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/data-integrity/exclusions")
async def get_exclusion_report():
    """
    Report on stocks excluded from analysis due to missing real data.
    This endpoint helps monitor the impact of eliminating fallback contamination.
    """
    try:
        redis_client = get_redis_client()
        si_service = await get_short_interest_service()
        
        # Get recent discovery attempts from Redis logs
        exclusion_keys = redis_client.keys("amc:exclusion:*")
        
        exclusions = {
            'short_interest': [],
            'price_data': [],
            'volume_data': [],
            'float_data': [],
            'summary': {
                'total_exclusions': 0,
                'by_reason': {},
                'last_updated': datetime.utcnow().isoformat()
            }
        }
        
        # Count exclusions by reason
        for key in exclusion_keys:
            try:
                key_str = key.decode() if isinstance(key, bytes) else key
                reason = key_str.split(':')[2] if len(key_str.split(':')) > 2 else 'unknown'
                symbol = key_str.split(':')[3] if len(key_str.split(':')) > 3 else 'unknown'
                
                exclusion_data = redis_client.get(key)
                if exclusion_data:
                    timestamp = redis_client.get(f"{key}:timestamp")
                    exclusions[reason].append({
                        'symbol': symbol,
                        'excluded_at': timestamp.decode() if timestamp else None,
                        'details': exclusion_data.decode() if exclusion_data else 'No details'
                    })
                    
                    # Update summary
                    exclusions['summary']['total_exclusions'] += 1
                    exclusions['summary']['by_reason'][reason] = exclusions['summary']['by_reason'].get(reason, 0) + 1
                    
            except Exception as e:
                logger.warning(f"Error processing exclusion key {key}: {e}")
                continue
        
        return exclusions
        
    except Exception as e:
        logger.error(f"Error generating exclusion report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate exclusion report: {str(e)}")

@router.get("/data-integrity/sources")
async def get_data_sources():
    """
    Report on data source health and coverage.
    Shows which symbols have real data vs those excluded.
    """
    try:
        si_service = await get_short_interest_service()
        
        # Test a sample of symbols to check source coverage
        test_symbols = ['AAPL', 'NVDA', 'TSLA', 'QUBT', 'PLTR', 'NAMM', 'LCFY', 'UAMY']
        
        source_report = {
            'sources': {
                'yahoo_finance': {'available': [], 'count': 0},
                'cache': {'available': [], 'count': 0},
                'excluded': {'symbols': [], 'count': 0}
            },
            'coverage_stats': {
                'real_data_percentage': 0,
                'exclusion_percentage': 0,
                'total_tested': len(test_symbols)
            },
            'last_updated': datetime.utcnow().isoformat()
        }
        
        for symbol in test_symbols:
            try:
                si_data = await si_service.get_short_interest(symbol)
                if si_data and si_data.source not in ['sector_fallback', 'default_fallback']:
                    source_report['sources'][si_data.source]['available'].append({
                        'symbol': symbol,
                        'confidence': si_data.confidence,
                        'last_updated': si_data.last_updated.isoformat(),
                        'short_percent': si_data.short_percent_float
                    })
                    source_report['sources'][si_data.source]['count'] += 1
                else:
                    source_report['sources']['excluded']['symbols'].append({
                        'symbol': symbol,
                        'reason': 'No real short interest data available'
                    })
                    source_report['sources']['excluded']['count'] += 1
                    
            except Exception as e:
                logger.warning(f"Error checking {symbol}: {e}")
                source_report['sources']['excluded']['symbols'].append({
                    'symbol': symbol,
                    'reason': f'Data fetch error: {str(e)}'
                })
                source_report['sources']['excluded']['count'] += 1
        
        # Calculate coverage percentages
        real_data_count = sum(source_report['sources'][source]['count'] for source in ['yahoo_finance', 'cache'])
        total_count = len(test_symbols)
        
        source_report['coverage_stats']['real_data_percentage'] = round((real_data_count / total_count) * 100, 2)
        source_report['coverage_stats']['exclusion_percentage'] = round((source_report['sources']['excluded']['count'] / total_count) * 100, 2)
        
        return source_report
        
    except Exception as e:
        logger.error(f"Error generating source report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate source report: {str(e)}")

@router.get("/data-integrity/contamination-check")
async def check_contamination():
    """
    Verify that no fallback data contamination exists in the system.
    This endpoint should show zero contaminated entries after the fix.
    """
    try:
        si_service = await get_short_interest_service()
        
        # Check common symbols for any remaining contamination
        test_symbols = ['QUBT', 'PLTR', 'NAMM', 'LCFY', 'UAMY', 'SERV', 'MSOS', 'ATAI']
        
        contamination_report = {
            'contaminated_entries': [],
            'clean_entries': [],
            'contamination_summary': {
                'total_contaminated': 0,
                'total_clean': 0,
                'contamination_percentage': 0,
                'validation_passed': True
            },
            'last_checked': datetime.utcnow().isoformat()
        }
        
        for symbol in test_symbols:
            try:
                si_data = await si_service.get_short_interest(symbol)
                
                if si_data:
                    # Check for contamination indicators
                    is_contaminated = (
                        si_data.source in ['sector_fallback', 'default_fallback'] or
                        (si_data.short_percent_float == 0.15 and si_data.confidence == 0.3) or
                        si_data.source == 'sector_fallback'
                    )
                    
                    entry = {
                        'symbol': symbol,
                        'source': si_data.source,
                        'short_percent': si_data.short_percent_float,
                        'confidence': si_data.confidence,
                        'last_updated': si_data.last_updated.isoformat()
                    }
                    
                    if is_contaminated:
                        contamination_report['contaminated_entries'].append(entry)
                        contamination_report['contamination_summary']['total_contaminated'] += 1
                        contamination_report['contamination_summary']['validation_passed'] = False
                    else:
                        contamination_report['clean_entries'].append(entry)
                        contamination_report['contamination_summary']['total_clean'] += 1
                else:
                    # Properly excluded - this is good
                    contamination_report['clean_entries'].append({
                        'symbol': symbol,
                        'status': 'properly_excluded',
                        'reason': 'No real data available - correctly excluded'
                    })
                    contamination_report['contamination_summary']['total_clean'] += 1
                    
            except Exception as e:
                logger.warning(f"Error checking contamination for {symbol}: {e}")
                continue
        
        total_entries = contamination_report['contamination_summary']['total_contaminated'] + contamination_report['contamination_summary']['total_clean']
        if total_entries > 0:
            contamination_report['contamination_summary']['contamination_percentage'] = round(
                (contamination_report['contamination_summary']['total_contaminated'] / total_entries) * 100, 2
            )
        
        return contamination_report
        
    except Exception as e:
        logger.error(f"Error checking contamination: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check contamination: {str(e)}")
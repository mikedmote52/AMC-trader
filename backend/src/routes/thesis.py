from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
from datetime import datetime
import json

from ..services.thesis_generator import ThesisGenerator, AIThesisGenerator

router = APIRouter()

@router.post("/generate-entry-thesis")
async def generate_entry_thesis(
    symbol: str,
    discovery_data: Dict,
    use_ai: bool = True
):
    """Generate entry thesis for a newly discovered stock opportunity"""
    try:
        thesis_gen = ThesisGenerator()
        thesis_result = await thesis_gen.generate_entry_thesis_for_discovery(symbol, discovery_data)
        
        # Log for learning system if decision is made
        if thesis_result.get('recommendation'):
            await thesis_gen.integrate_with_learning_system(
                symbol, thesis_result, thesis_result.get('recommendation')
            )
        
        return {
            "success": True,
            "data": thesis_result,
            "ai_powered": thesis_result.get('ai_generated', False)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating entry thesis: {str(e)}")

@router.post("/update-thesis-with-performance")
async def update_thesis_with_performance(
    symbol: str,
    position_data: Dict,
    use_ai: bool = True
):
    """Update thesis based on current position performance"""
    try:
        thesis_gen = ThesisGenerator()
        thesis_result = await thesis_gen.generate_thesis_for_position(symbol, position_data, use_ai)
        
        return {
            "success": True,
            "data": thesis_result,
            "ai_enhanced": thesis_result.get('enhanced', False)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating thesis: {str(e)}")

@router.post("/generate-exit-strategy")
async def generate_exit_strategy(
    symbol: str,
    position_data: Dict,
    market_conditions: Optional[Dict] = None
):
    """Generate comprehensive exit strategy for a position"""
    try:
        thesis_gen = ThesisGenerator()
        exit_result = await thesis_gen.generate_exit_strategy(symbol, position_data, market_conditions)
        
        # Log exit decision for learning
        if exit_result.get('exit_recommendation'):
            await thesis_gen.integrate_with_learning_system(
                symbol, exit_result, exit_result.get('exit_recommendation')
            )
        
        return {
            "success": True,
            "data": exit_result,
            "ai_powered": exit_result.get('ai_generated', False)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating exit strategy: {str(e)}")

@router.get("/thesis-for-position/{symbol}")
async def get_thesis_for_position(
    symbol: str,
    current_price: float,
    entry_price: Optional[float] = None,
    market_value: Optional[float] = None,
    use_ai: bool = True
):
    """Get comprehensive thesis analysis for an existing position"""
    try:
        # Build position data
        position_data = {
            'symbol': symbol,
            'last_price': current_price,
            'avg_entry_price': entry_price or current_price,
            'market_value': market_value or 1000,
            'unrealized_pl_pct': ((current_price - (entry_price or current_price)) / (entry_price or current_price)) * 100 if entry_price else 0
        }
        
        thesis_gen = ThesisGenerator()
        thesis_result = await thesis_gen.generate_thesis_for_position(symbol, position_data, use_ai)
        
        return {
            "success": True,
            "data": thesis_result,
            "enhanced": thesis_result.get('enhanced', False),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting thesis for position: {str(e)}")

@router.post("/analyze-portfolio-thesis")
async def analyze_portfolio_thesis(
    portfolio_positions: Dict,
    use_ai: bool = True
):
    """Generate thesis analysis for entire portfolio"""
    try:
        thesis_gen = ThesisGenerator()
        portfolio_analysis = {}
        
        for symbol, position_data in portfolio_positions.items():
            try:
                thesis_result = await thesis_gen.generate_thesis_for_position(
                    symbol, position_data, use_ai
                )
                portfolio_analysis[symbol] = thesis_result
                
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                portfolio_analysis[symbol] = {
                    "error": str(e),
                    "symbol": symbol,
                    "thesis": f"Analysis failed for {symbol}"
                }
        
        # Generate portfolio-level insights
        portfolio_insights = _generate_portfolio_insights(portfolio_analysis)
        
        return {
            "success": True,
            "data": {
                "individual_analysis": portfolio_analysis,
                "portfolio_insights": portfolio_insights,
                "analysis_timestamp": datetime.now().isoformat(),
                "ai_enhanced_count": sum(1 for analysis in portfolio_analysis.values() 
                                       if analysis.get('enhanced')),
                "total_positions": len(portfolio_analysis)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing portfolio thesis: {str(e)}")

@router.get("/learning-enhanced-recommendations")
async def get_learning_enhanced_recommendations():
    """Get thesis recommendations enhanced by learning system insights"""
    try:
        from ..routes.learning import LearningSystem
        
        # Get learning insights
        insights = await LearningSystem.get_learning_insights(30)
        
        # Generate learning-enhanced recommendations
        recommendations = {
            "market_timing_insights": [],
            "successful_patterns": [],
            "risk_management_lessons": [],
            "thesis_optimization": []
        }
        
        if insights.get("decision_stats"):
            for stat in insights["decision_stats"]:
                if stat.get("avg_return", 0) > 5:
                    recommendations["market_timing_insights"].append({
                        "insight": f"Strong performance in {stat['market_time']} timing",
                        "avg_return": stat["avg_return"],
                        "recommendation": f"Consider focusing thesis generation during {stat['market_time']} periods"
                    })
        
        if insights.get("best_patterns"):
            for pattern in insights["best_patterns"][:3]:
                recommendations["successful_patterns"].append({
                    "pattern": pattern["reasoning"],
                    "success_rate": pattern["avg_return"],
                    "frequency": pattern["occurrences"],
                    "application": "Apply similar reasoning in future thesis generation"
                })
        
        return {
            "success": True,
            "data": recommendations,
            "learning_period_days": insights.get("learning_period_days", 30),
            "total_decisions_analyzed": insights.get("total_decisions", 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting learning insights: {str(e)}")

def _generate_portfolio_insights(portfolio_analysis: Dict) -> Dict:
    """Generate portfolio-level insights from individual position analysis"""
    insights = {
        "overall_sentiment": "NEUTRAL",
        "high_confidence_positions": [],
        "risk_positions": [],
        "ai_vs_traditional_analysis": {},
        "sector_distribution": {},
        "recommendation_summary": {}
    }
    
    # Analyze confidence levels
    high_confidence = []
    risk_positions = []
    recommendations = {}
    sectors = {}
    ai_count = 0
    
    for symbol, analysis in portfolio_analysis.items():
        if isinstance(analysis, dict) and not analysis.get('error'):
            confidence = analysis.get('confidence', 0.5)
            risk_level = analysis.get('risk_level', 'MODERATE')
            recommendation = analysis.get('recommendation', 'HOLD')
            sector = analysis.get('sector', 'Unknown')
            
            # High confidence positions
            if confidence > 0.7:
                high_confidence.append({
                    "symbol": symbol,
                    "confidence": confidence,
                    "recommendation": recommendation
                })
            
            # Risk positions
            if risk_level in ['HIGH', 'CRITICAL']:
                risk_positions.append({
                    "symbol": symbol,
                    "risk_level": risk_level,
                    "recommendation": recommendation
                })
            
            # Recommendation summary
            recommendations[recommendation] = recommendations.get(recommendation, 0) + 1
            
            # Sector distribution
            sectors[sector] = sectors.get(sector, 0) + 1
            
            # AI enhancement tracking
            if analysis.get('enhanced'):
                ai_count += 1
    
    insights["high_confidence_positions"] = sorted(high_confidence, key=lambda x: x['confidence'], reverse=True)[:5]
    insights["risk_positions"] = risk_positions
    insights["recommendation_summary"] = recommendations
    insights["sector_distribution"] = sectors
    insights["ai_vs_traditional_analysis"] = {
        "ai_enhanced": ai_count,
        "traditional": len(portfolio_analysis) - ai_count,
        "enhancement_rate": (ai_count / len(portfolio_analysis)) * 100 if portfolio_analysis else 0
    }
    
    # Overall sentiment
    buy_signals = recommendations.get('BUY_MORE', 0)
    hold_signals = recommendations.get('HOLD', 0)
    sell_signals = recommendations.get('TRIM', 0) + recommendations.get('LIQUIDATE', 0)
    
    if buy_signals > sell_signals:
        insights["overall_sentiment"] = "BULLISH"
    elif sell_signals > buy_signals:
        insights["overall_sentiment"] = "BEARISH"
    else:
        insights["overall_sentiment"] = "NEUTRAL"
    
    return insights

@router.post("/generate-squeeze-thesis")
async def generate_squeeze_thesis(
    symbol: str,
    metrics: Dict
):
    """Generate squeeze-specific thesis with VIGL pattern recognition"""
    try:
        thesis_gen = ThesisGenerator()
        squeeze_result = await thesis_gen.generate_squeeze_thesis(symbol, metrics)
        
        # Log squeeze analysis for learning
        if squeeze_result.get('recommendation'):
            await thesis_gen.integrate_with_learning_system(
                symbol, squeeze_result, squeeze_result.get('recommendation')
            )
        
        return {
            "success": True,
            "data": squeeze_result,
            "squeeze_detected": squeeze_result.get('pattern_type') in ['VIGL_SQUEEZE', 'SQUEEZE_WATCH'],
            "pattern_similarity": squeeze_result.get('pattern_match', {}).get('similarity', 0.0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating squeeze thesis: {str(e)}")

@router.post("/pattern-specific-recommendation")
async def get_pattern_specific_recommendation(
    symbol: str,
    pattern_type: str,
    metrics: Dict
):
    """Get pattern-specific recommendations (VIGL/momentum fade/breakdown)"""
    try:
        thesis_gen = ThesisGenerator()
        pattern_result = await thesis_gen.generate_pattern_specific_recommendation(
            symbol, pattern_type, metrics
        )
        
        return {
            "success": True,
            "data": pattern_result,
            "pattern_type": pattern_type,
            "action_required": pattern_result.get('action') in ['IMMEDIATE_EXIT', 'TRIM_50', 'AGGRESSIVE_ACCUMULATION']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating pattern recommendation: {str(e)}")

@router.post("/track-thesis-accuracy")
async def track_thesis_accuracy(
    symbol: str,
    original_thesis: Dict,
    outcome_data: Dict
):
    """Track thesis accuracy and update learning system"""
    try:
        thesis_gen = ThesisGenerator()
        accuracy_result = await thesis_gen.track_thesis_accuracy(
            symbol, original_thesis, outcome_data
        )
        
        return {
            "success": True,
            "data": accuracy_result,
            "accuracy_score": accuracy_result.get('thesis_accuracy', 0.0),
            "recommendation_success": accuracy_result.get('recommendation_success', False)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking thesis accuracy: {str(e)}")

@router.get("/squeeze-scanner")
async def squeeze_scanner():
    """Scan for VIGL-like squeeze opportunities across watchlist"""
    try:
        # This would integrate with your existing discovery system
        # For now, return structure for potential squeeze opportunities
        
        watchlist_symbols = ['QUBT', 'SPHR', 'AMDL', 'CELC', 'TEM']  # Example watchlist
        squeeze_opportunities = []
        
        thesis_gen = ThesisGenerator()
        
        for symbol in watchlist_symbols:
            # Get real market data for the symbol
            try:
                from ..services.bms_engine_enhanced import EnhancedBMSEngine
                import os
                
                polygon_key = os.getenv('POLYGON_API_KEY', '1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC')
                bms_engine = EnhancedBMSEngine(polygon_key)
                
                market_data = await bms_engine.get_real_market_data(symbol)
                if not market_data:
                    continue
                
                real_metrics = {
                    'symbol': symbol,
                    'squeeze_score': market_data.get('rel_volume_30d', 1.0) / 10.0,  # Simplified scoring
                    'volume_spike': market_data.get('rel_volume_30d', 1.0),
                    'short_interest': market_data.get('short_ratio', 0.0) / 10.0,
                    'float': market_data.get('float_shares', 50_000_000),
                    'price': market_data.get('price', 0.0),
                    'momentum': 'bullish' if market_data.get('momentum_1d', 0) > 2 else 'neutral'
                }
                
                squeeze_thesis = await thesis_gen.generate_squeeze_thesis(symbol, real_metrics)
            except Exception as e:
                logger.error(f"Error getting real data for {symbol}: {e}")
                continue
            
            if squeeze_thesis.get('pattern_type') in ['VIGL_SQUEEZE', 'SQUEEZE_WATCH']:
                squeeze_opportunities.append({
                    'symbol': symbol,
                    'squeeze_score': real_metrics['squeeze_score'],
                    'thesis': squeeze_thesis.get('thesis', ''),
                    'confidence': squeeze_thesis.get('confidence', 0.5),
                    'pattern_similarity': squeeze_thesis.get('pattern_match', {}).get('similarity', 0.0),
                    'recommendation': squeeze_thesis.get('recommendation', 'RESEARCH'),
                    'targets': squeeze_thesis.get('targets', {}),
                    'risk_management': squeeze_thesis.get('risk_management', {})
                })
        
        # Sort by squeeze score
        squeeze_opportunities.sort(key=lambda x: x['squeeze_score'], reverse=True)
        
        return {
            "success": True,
            "data": {
                "squeeze_opportunities": squeeze_opportunities,
                "total_scanned": len(watchlist_symbols),
                "high_probability_squeezers": len([s for s in squeeze_opportunities if s['squeeze_score'] > 0.75]),
                "scan_timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running squeeze scanner: {str(e)}")

@router.get("/vigl-pattern-analysis")
async def vigl_pattern_analysis():
    """Get detailed VIGL pattern analysis and historical performance"""
    try:
        from ..services.thesis_generator import HISTORICAL_SQUEEZE_PATTERNS
        
        vigl_data = HISTORICAL_SQUEEZE_PATTERNS.get('VIGL', {})
        
        analysis = {
            "vigl_reference": vigl_data,
            "key_metrics": {
                "volume_spike_threshold": "20.9x average (minimum 15x for alerts)",
                "optimal_price_range": "$1.00 - $8.00",
                "float_size_max": "100M shares (smaller = better)",
                "short_interest_min": "10% (higher = more squeeze potential)",
                "momentum_requirement": "0.7+ momentum score"
            },
            "risk_management": {
                "stop_loss": "Strict -8% from entry",
                "position_sizing": "2-3% of portfolio maximum",
                "time_horizon": "2-4 weeks for initial move",
                "exit_strategy": "Trim on doubles, exit on breakdown"
            },
            "success_criteria": {
                "pattern_similarity": "70%+ similarity to historical patterns",
                "volume_confirmation": "Sustained above 15x average",
                "price_action": "Clean breakout above resistance",
                "catalyst": "Fundamental or technical catalyst identified"
            },
            "historical_winners": {
                "VIGL": f"+{vigl_data.get('max_gain', 0):.0f}% in {vigl_data.get('pattern_duration', 0)} days",
                "CRWV": "+515% in 18 days",
                "AEVA": "+345% in 21 days"
            }
        }
        
        return {
            "success": True,
            "data": analysis,
            "pattern_effectiveness": "324% average return when criteria met",
            "win_rate": "Historical data suggests 70%+ win rate for proper VIGL setups"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting VIGL analysis: {str(e)}")
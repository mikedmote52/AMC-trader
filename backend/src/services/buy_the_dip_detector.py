#!/usr/bin/env python3
"""
Buy-the-Dip Detection Engine - Zero Disruption Portfolio Enhancement
Monitors underperforming holdings for dip-buying opportunities
"""

import asyncio
import json
import logging
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from ..shared.database import get_db_pool
from ..shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)

@dataclass
class DipAnalysis:
    """Buy-the-dip analysis for a portfolio position"""
    symbol: str
    analysis_date: str
    current_price: float
    original_thesis: str
    thesis_strength: str  # STRONG, MODERATE, WEAK, FAILED
    
    # Price analysis
    price_drop_pct: float
    support_level: Optional[float]
    resistance_level: Optional[float]
    
    # Technical indicators
    rsi: Optional[float]
    volume_spike: float
    oversold_indicator: bool
    
    # Position analysis  
    current_position_size: float
    position_cost_basis: float
    unrealized_pl_pct: float
    
    # Buy recommendation
    dip_buy_recommendation: str  # STRONG_BUY, BUY, HOLD, WAIT, AVOID
    recommended_entry_price: Optional[float]
    recommended_position_size: Optional[float]
    risk_score: float
    
    # Reasoning
    reasoning: List[str]
    confidence: float

class BuyTheDipDetector:
    """
    Detects buy-the-dip opportunities in portfolio holdings
    ZERO DISRUPTION - Only monitors, doesn't make trades
    """
    
    def __init__(self):
        self.redis = get_redis_client()
        self.dip_prefix = "amc:dip:analysis:"
        
    async def analyze_portfolio_dips(self) -> List[DipAnalysis]:
        """
        Analyze all portfolio holdings for dip-buying opportunities
        Called by background job - non-interfering with trading
        """
        try:
            # Get current portfolio from existing API
            portfolio_data = await self._get_portfolio_data()
            if not portfolio_data:
                logger.warning("No portfolio data available for dip analysis")
                return []
            
            dip_analyses = []
            
            for position in portfolio_data.get('positions', []):
                try:
                    analysis = await self._analyze_position_dip(position)
                    if analysis:
                        dip_analyses.append(analysis)
                        
                        # Store analysis for tracking
                        await self._store_dip_analysis(analysis)
                        
                        # Generate alerts for strong buy opportunities
                        if analysis.dip_buy_recommendation in ['STRONG_BUY', 'BUY']:
                            await self._generate_dip_alert(analysis)
                            
                except Exception as e:
                    logger.error(f"Error analyzing {position.get('symbol', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Dip analysis complete: {len(dip_analyses)} positions analyzed")
            return dip_analyses
            
        except Exception as e:
            logger.error(f"Portfolio dip analysis failed: {e}")
            return []
    
    async def _get_portfolio_data(self) -> Optional[Dict]:
        """Get current portfolio data from existing API"""
        try:
            # Use existing portfolio API endpoint
            async with httpx.AsyncClient() as client:
                response = await client.get("https://amc-trader.onrender.com/portfolio/holdings")
                if response.status_code == 200:
                    data = response.json()
                    return data.get('data', {})
            return None
        except Exception as e:
            logger.error(f"Failed to get portfolio data: {e}")
            return None
    
    async def _analyze_position_dip(self, position: Dict) -> Optional[DipAnalysis]:
        """Analyze individual position for dip-buying opportunity"""
        try:
            symbol = position.get('symbol')
            if not symbol:
                return None
            
            current_price = position.get('last_price', 0.0)
            cost_basis = position.get('avg_entry_price', 0.0)
            position_size = position.get('qty', 0.0)
            unrealized_pl_pct = position.get('unrealized_pl_pct', 0.0)
            thesis = position.get('thesis', '')
            
            # Only analyze positions that are down
            if unrealized_pl_pct >= -2.0:  # Less than 2% down - not a dip
                return None
            
            # Get technical analysis data
            price_drop_pct = abs(unrealized_pl_pct)
            volume_spike = await self._get_volume_spike(symbol)
            rsi = await self._get_rsi(symbol)
            support_level, resistance_level = await self._get_support_resistance(symbol)
            
            # Analyze thesis strength
            thesis_strength = self._analyze_thesis_strength(thesis, position)
            
            # Generate buy recommendation
            recommendation, entry_price, recommended_size, risk_score, reasoning = self._generate_dip_recommendation(
                symbol, current_price, cost_basis, price_drop_pct, thesis_strength, volume_spike, rsi
            )
            
            # Calculate confidence based on multiple factors
            confidence = self._calculate_confidence(thesis_strength, volume_spike, rsi, price_drop_pct)
            
            return DipAnalysis(
                symbol=symbol,
                analysis_date=datetime.now().isoformat(),
                current_price=current_price,
                original_thesis=thesis,
                thesis_strength=thesis_strength,
                price_drop_pct=price_drop_pct,
                support_level=support_level,
                resistance_level=resistance_level,
                rsi=rsi,
                volume_spike=volume_spike,
                oversold_indicator=rsi < 30 if rsi else False,
                current_position_size=position_size,
                position_cost_basis=cost_basis,
                unrealized_pl_pct=unrealized_pl_pct,
                dip_buy_recommendation=recommendation,
                recommended_entry_price=entry_price,
                recommended_position_size=recommended_size,
                risk_score=risk_score,
                reasoning=reasoning,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze position {symbol}: {e}")
            return None
    
    def _analyze_thesis_strength(self, thesis: str, position: Dict) -> str:
        """Analyze if the original investment thesis is still strong"""
        
        # Extract key indicators from thesis
        thesis_lower = thesis.lower()
        confidence = position.get('confidence', 0.0)
        
        # Strong thesis indicators
        strong_indicators = [
            'strong' in thesis_lower,
            'explosive' in thesis_lower,
            'breakout' in thesis_lower,
            'momentum' in thesis_lower and 'building' in thesis_lower,
            confidence > 0.7
        ]
        
        # Weak thesis indicators  
        weak_indicators = [
            'review' in thesis_lower,
            'warning' in thesis_lower,
            'stress' in thesis_lower,
            'concerning' in thesis_lower,
            confidence < 0.4
        ]
        
        # Failed thesis indicators
        failed_indicators = [
            'failed' in thesis_lower,
            'broken' in thesis_lower,
            'avoid' in thesis_lower,
            confidence < 0.2
        ]
        
        if any(failed_indicators):
            return "FAILED"
        elif any(weak_indicators):
            return "WEAK"
        elif any(strong_indicators) or sum(strong_indicators) >= 2:
            return "STRONG"
        else:
            return "MODERATE"
    
    async def _get_volume_spike(self, symbol: str) -> float:
        """Get volume spike ratio for symbol"""
        try:
            # Try to get from existing discovery data first
            key = f"amc:discovery:v2:contenders.latest"
            contenders_data = self.redis.get(key)
            if contenders_data:
                contenders = json.loads(contenders_data)
                for item in contenders:
                    if item.get('symbol') == symbol:
                        return item.get('volume_spike', 1.0)
            
            # Fallback: calculate from market data
            return 1.0  # Default if no data available
            
        except Exception:
            return 1.0
    
    async def _get_rsi(self, symbol: str) -> Optional[float]:
        """Get RSI for symbol (simplified calculation)"""
        try:
            # This would typically require historical price data
            # For now, return None - can be enhanced with proper RSI calculation
            return None
        except Exception:
            return None
    
    async def _get_support_resistance(self, symbol: str) -> Tuple[Optional[float], Optional[float]]:
        """Get support and resistance levels"""
        try:
            # Simplified support/resistance calculation
            # In a full implementation, this would analyze price history
            return None, None
        except Exception:
            return None, None
    
    def _generate_dip_recommendation(
        self, 
        symbol: str, 
        current_price: float, 
        cost_basis: float, 
        price_drop_pct: float, 
        thesis_strength: str,
        volume_spike: float, 
        rsi: Optional[float]
    ) -> Tuple[str, Optional[float], Optional[float], float, List[str]]:
        """Generate buy-the-dip recommendation with reasoning"""
        
        reasoning = []
        risk_score = 0.5  # Default medium risk
        
        # Thesis strength is primary factor
        if thesis_strength == "FAILED":
            reasoning.append("❌ Thesis has failed - avoid adding to position")
            return "AVOID", None, None, 0.8, reasoning
        
        elif thesis_strength == "WEAK":
            reasoning.append("⚠️ Thesis showing weakness - wait for confirmation")
            return "WAIT", None, None, 0.7, reasoning
        
        # For MODERATE and STRONG thesis, analyze dip opportunity
        
        # Price drop analysis
        if price_drop_pct > 25:
            reasoning.append(f"🔻 Significant drop: -{price_drop_pct:.1f}%")
            if thesis_strength == "STRONG":
                reasoning.append("💎 Strong thesis + big drop = opportunity")
                recommendation = "STRONG_BUY"
                risk_score = 0.3  # Lower risk for strong thesis big dips
            else:
                recommendation = "BUY"
                risk_score = 0.5
        
        elif price_drop_pct > 15:
            reasoning.append(f"📉 Moderate drop: -{price_drop_pct:.1f}%")
            if thesis_strength == "STRONG":
                recommendation = "BUY"
                risk_score = 0.4
            else:
                recommendation = "HOLD"
                risk_score = 0.6
        
        elif price_drop_pct > 5:
            reasoning.append(f"📊 Minor drop: -{price_drop_pct:.1f}%")
            recommendation = "HOLD"
            risk_score = 0.6
        
        else:
            reasoning.append("📈 Not a significant dip")
            return "HOLD", None, None, 0.5, reasoning
        
        # Volume analysis
        if volume_spike > 2.0:
            reasoning.append(f"📊 High volume: {volume_spike:.1f}x - institutional interest")
            risk_score -= 0.1  # Volume reduces risk
        
        # RSI analysis
        if rsi and rsi < 30:
            reasoning.append(f"📉 Oversold RSI: {rsi:.1f} - bounce potential")
            risk_score -= 0.1
        elif rsi and rsi > 70:
            reasoning.append(f"📈 Overbought RSI: {rsi:.1f} - may continue down")
            risk_score += 0.1
        
        # Calculate entry price (slightly below current for better entry)
        if recommendation in ["STRONG_BUY", "BUY"]:
            entry_price = current_price * 0.98  # 2% below current
            
            # Position sizing based on risk and recommendation strength
            base_size_pct = 0.25 if recommendation == "STRONG_BUY" else 0.15
            recommended_size = base_size_pct * (1 - risk_score)  # Lower risk = larger size
            
            reasoning.append(f"💰 Entry: ${entry_price:.2f}, Size: {recommended_size:.1%}")
        else:
            entry_price = None
            recommended_size = None
        
        return recommendation, entry_price, recommended_size, risk_score, reasoning
    
    def _calculate_confidence(
        self, 
        thesis_strength: str, 
        volume_spike: float, 
        rsi: Optional[float], 
        price_drop_pct: float
    ) -> float:
        """Calculate confidence in the dip analysis"""
        
        confidence_factors = []
        
        # Thesis strength confidence
        thesis_confidence = {
            "STRONG": 0.9,
            "MODERATE": 0.6,
            "WEAK": 0.3,
            "FAILED": 0.1
        }
        confidence_factors.append(thesis_confidence.get(thesis_strength, 0.5))
        
        # Volume confidence (higher volume = more confident)
        volume_confidence = min(volume_spike / 5.0, 1.0)
        confidence_factors.append(volume_confidence)
        
        # RSI confidence (extreme readings = more confident)
        if rsi:
            if rsi < 20 or rsi > 80:
                rsi_confidence = 0.9
            elif rsi < 30 or rsi > 70:
                rsi_confidence = 0.7
            else:
                rsi_confidence = 0.5
            confidence_factors.append(rsi_confidence)
        
        # Drop magnitude confidence (bigger drops with strong thesis = more confident)
        if thesis_strength == "STRONG" and price_drop_pct > 20:
            drop_confidence = 0.9
        elif price_drop_pct > 10:
            drop_confidence = 0.7
        else:
            drop_confidence = 0.5
        confidence_factors.append(drop_confidence)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    async def _store_dip_analysis(self, analysis: DipAnalysis):
        """Store dip analysis in database and Redis"""
        try:
            # Store in Redis with 7-day expiration
            key = f"{self.dip_prefix}{analysis.symbol}:{datetime.now().strftime('%Y%m%d_%H%M')}"
            self.redis.setex(key, 7 * 86400, json.dumps(asdict(analysis)))
            
            # Keep latest analysis easily accessible
            latest_key = f"{self.dip_prefix}{analysis.symbol}:latest"
            self.redis.setex(latest_key, 24 * 3600, json.dumps(asdict(analysis)))
            
            # Store in database
            pool = await get_db_pool()
            if pool:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO monitoring.buy_the_dip_analysis 
                        (symbol, analysis_date, current_price, original_thesis, thesis_strength,
                         price_drop_pct, support_level, resistance_level, rsi, volume_spike,
                         oversold_indicator, current_position_size, position_cost_basis,
                         unrealized_pl_pct, dip_buy_recommendation, recommended_entry_price,
                         recommended_position_size, risk_score)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                    """,
                        analysis.symbol,
                        datetime.fromisoformat(analysis.analysis_date),
                        analysis.current_price,
                        analysis.original_thesis,
                        analysis.thesis_strength,
                        analysis.price_drop_pct,
                        analysis.support_level,
                        analysis.resistance_level,
                        analysis.rsi,
                        analysis.volume_spike,
                        analysis.oversold_indicator,
                        analysis.current_position_size,
                        analysis.position_cost_basis,
                        analysis.unrealized_pl_pct,
                        analysis.dip_buy_recommendation,
                        analysis.recommended_entry_price,
                        analysis.recommended_position_size,
                        analysis.risk_score
                    )
        except Exception as e:
            logger.error(f"Failed to store dip analysis (non-critical): {e}")
    
    async def _generate_dip_alert(self, analysis: DipAnalysis):
        """Generate alert for buy-the-dip opportunity"""
        try:
            alert_data = {
                'type': 'BUY_THE_DIP',
                'timestamp': datetime.now().isoformat(),
                'symbol': analysis.symbol,
                'recommendation': analysis.dip_buy_recommendation,
                'current_price': analysis.current_price,
                'drop_pct': analysis.price_drop_pct,
                'entry_price': analysis.recommended_entry_price,
                'position_size': analysis.recommended_position_size,
                'thesis_strength': analysis.thesis_strength,
                'confidence': analysis.confidence,
                'reasoning': analysis.reasoning,
                'message': f"BUY DIP: {analysis.symbol} down {analysis.price_drop_pct:.1f}%, strong thesis, entry ${analysis.recommended_entry_price:.2f}"
            }
            
            # Store alert
            alert_key = "amc:dip:alerts"
            self.redis.lpush(alert_key, json.dumps(alert_data))
            self.redis.ltrim(alert_key, 0, 49)  # Keep last 50 alerts
            self.redis.expire(alert_key, 604800)  # 7 days
            
            # Publish for real-time notifications
            self.redis.publish("amc:alerts:buy_the_dip", json.dumps(alert_data))
            
            logger.info(f"Buy-the-dip alert: {analysis.symbol} {analysis.dip_buy_recommendation}")
            
        except Exception as e:
            logger.error(f"Failed to generate dip alert: {e}")
    
    async def get_active_dip_opportunities(self) -> List[Dict]:
        """Get current buy-the-dip opportunities"""
        return await self.get_recent_opportunities()
    
    async def get_recent_opportunities(self, min_drop_pct: float = 10.0, days_back: int = 7) -> List[Dict]:
        """Get recent buy-the-dip opportunities from database"""
        try:
            pool = await get_db_pool()
            if not pool:
                return []
                
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM monitoring.buy_the_dip_analysis 
                    WHERE price_drop_pct >= $1 
                    AND analysis_date >= $2
                    AND dip_buy_recommendation IN ('STRONG_BUY', 'BUY')
                    ORDER BY analysis_date DESC, risk_score ASC
                    LIMIT 50
                """, min_drop_pct, datetime.now() - timedelta(days=days_back))
                
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get dip opportunities: {e}")
            return []

# Background job for dip analysis
async def run_dip_analysis():
    """Background job to analyze portfolio for dip opportunities"""
    detector = BuyTheDipDetector()
    
    while True:
        try:
            await detector.analyze_portfolio_dips()
            # Run analysis every 4 hours
            await asyncio.sleep(4 * 3600)
        except Exception as e:
            logger.error(f"Dip analysis job error: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour on error

# Background job for dip analysis
async def run_dip_analysis():
    """Background job to analyze portfolio for dip opportunities"""
    detector = BuyTheDipDetector()
    
    while True:
        try:
            await detector.analyze_portfolio_dips()
            # Run analysis every 4 hours
            await asyncio.sleep(4 * 3600)
        except Exception as e:
            logger.error(f"Dip analysis job error: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour on error

# Global detector instance
_dip_detector = None

def get_buy_the_dip_detector() -> BuyTheDipDetector:
    """Get singleton buy-the-dip detector instance"""
    global _dip_detector
    if _dip_detector is None:
        _dip_detector = BuyTheDipDetector()
    return _dip_detector
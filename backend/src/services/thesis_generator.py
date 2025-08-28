import os
import httpx
import asyncio
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

# Sector classification mapping
SECTOR_MAPPING = {
    'AMDL': 'Biotech',
    'CARS': 'Automotive', 
    'CELC': 'Energy',
    'GMAB': 'Biotech',
    'KSS': 'Retail',
    'QUBT': 'Technology',
    'SPHR': 'Healthcare',
    'SSRM': 'Mining',
    'TEM': 'Telecom',
    'TEVA': 'Pharma',
    'UP': 'Cannabis',
    'WULF': 'Bitcoin Mining'
}

# Risk tolerance thresholds
RISK_THRESHOLDS = {
    'high_gain': 50.0,      # >50% gain
    'good_gain': 10.0,      # 10-50% gain  
    'neutral': -5.0,        # -5% to 10% range
    'concerning': -15.0,    # -5% to -15% loss
    'critical': -25.0       # <-25% loss
}

class ThesisGenerator:
    """Enhanced thesis generation for all portfolio positions"""
    
    def __init__(self):
        self.polygon_api_key = POLYGON_API_KEY
        
    async def generate_thesis_for_position(self, symbol: str, position_data: Dict) -> Dict:
        """Generate comprehensive thesis for a single position"""
        try:
            # Extract position metrics
            unrealized_pl_pct = position_data.get('unrealized_pl_pct', 0.0)
            market_value = position_data.get('market_value', 0.0)
            current_price = position_data.get('last_price', 0.0)
            avg_entry_price = position_data.get('avg_entry_price', 0.0)
            
            # Get sector info
            sector = SECTOR_MAPPING.get(symbol, 'Unknown')
            
            # Fetch additional market data if available
            market_context = await self._fetch_market_context(symbol)
            
            # Generate thesis based on performance and context
            thesis = self._build_thesis(symbol, unrealized_pl_pct, sector, market_context, current_price)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(unrealized_pl_pct, market_context, market_value)
            
            # Generate intelligent recommendation
            recommendation = self._generate_recommendation(unrealized_pl_pct, confidence, market_context)
            
            # Create reasoning for learning system
            reasoning = self._build_reasoning(symbol, unrealized_pl_pct, sector, confidence, recommendation)
            
            return {
                'thesis': thesis,
                'confidence': confidence,
                'recommendation': recommendation,
                'reasoning': reasoning,
                'sector': sector,
                'risk_level': self._assess_risk_level(unrealized_pl_pct),
                'market_context': market_context
            }
            
        except Exception as e:
            print(f"Error generating thesis for {symbol}: {e}")
            return self._fallback_thesis(symbol, position_data)
    
    async def _fetch_market_context(self, symbol: str) -> Dict:
        """Fetch additional market context for thesis enhancement"""
        context = {
            'volume_trend': 'normal',
            'volatility': 'medium',
            'momentum': 'neutral',
            'data_available': False
        }
        
        if not self.polygon_api_key:
            return context
            
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Get recent price data for volatility/momentum analysis
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
                params = {"apikey": self.polygon_api_key}
                
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    if len(results) >= 2:
                        context = self._analyze_market_data(results)
                        context['data_available'] = True
                        
        except Exception as e:
            print(f"Failed to fetch market context for {symbol}: {e}")
            
        return context
    
    def _analyze_market_data(self, results: List[Dict]) -> Dict:
        """Analyze price/volume data for market context"""
        if len(results) < 2:
            return {'volume_trend': 'unknown', 'volatility': 'unknown', 'momentum': 'unknown'}
            
        # Calculate recent volatility (last 5 days vs previous period)
        recent_prices = [r['c'] for r in results[-5:]]
        older_prices = [r['c'] for r in results[-10:-5]] if len(results) >= 10 else recent_prices
        
        recent_volatility = self._calculate_volatility(recent_prices)
        older_volatility = self._calculate_volatility(older_prices)
        
        # Volume trend
        recent_volumes = [r['v'] for r in results[-3:]]
        avg_recent_volume = sum(recent_volumes) / len(recent_volumes)
        older_volumes = [r['v'] for r in results[-10:-3]] if len(results) >= 10 else recent_volumes
        avg_older_volume = sum(older_volumes) / len(older_volumes)
        
        volume_ratio = avg_recent_volume / avg_older_volume if avg_older_volume > 0 else 1.0
        
        # Price momentum (last price vs 5-day avg)
        recent_avg = sum(recent_prices) / len(recent_prices)
        current_price = results[-1]['c']
        momentum_pct = ((current_price - recent_avg) / recent_avg) * 100 if recent_avg > 0 else 0
        
        return {
            'volume_trend': 'high' if volume_ratio > 1.5 else 'low' if volume_ratio < 0.7 else 'normal',
            'volatility': 'high' if recent_volatility > older_volatility * 1.5 else 'low' if recent_volatility < older_volatility * 0.7 else 'medium',
            'momentum': 'bullish' if momentum_pct > 2 else 'bearish' if momentum_pct < -2 else 'neutral',
            'momentum_pct': round(momentum_pct, 2),
            'volume_ratio': round(volume_ratio, 2)
        }
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate simple volatility measure"""
        if len(prices) < 2:
            return 0.0
            
        # Calculate percentage changes
        changes = []
        for i in range(1, len(prices)):
            change_pct = abs((prices[i] - prices[i-1]) / prices[i-1]) * 100
            changes.append(change_pct)
            
        return sum(changes) / len(changes) if changes else 0.0
    
    def _build_thesis(self, symbol: str, pl_pct: float, sector: str, market_context: Dict, current_price: float) -> str:
        """Build comprehensive thesis based on position performance and context"""
        
        # Performance assessment
        if pl_pct > RISK_THRESHOLDS['high_gain']:
            performance_desc = f"Exceptional performer +{pl_pct:.1f}% gain"
            position_status = "strong momentum play"
        elif pl_pct > RISK_THRESHOLDS['good_gain']:
            performance_desc = f"Strong performer +{pl_pct:.1f}% gain"
            position_status = "positive momentum"
        elif pl_pct > RISK_THRESHOLDS['neutral']:
            performance_desc = f"Modest performer +{pl_pct:.1f}% gain"
            position_status = "early stage development"
        elif pl_pct > RISK_THRESHOLDS['concerning']:
            performance_desc = f"Underperformer {pl_pct:.1f}% loss"
            position_status = "requires thesis reevaluation"
        else:
            performance_desc = f"Significant underperformer {pl_pct:.1f}% loss"
            position_status = "thesis under review"
            
        # Market context integration
        momentum_desc = ""
        if market_context.get('data_available'):
            momentum = market_context.get('momentum', 'neutral')
            if momentum == 'bullish':
                momentum_desc = f", showing bullish momentum (+{market_context.get('momentum_pct', 0):.1f}%)"
            elif momentum == 'bearish':
                momentum_desc = f", showing bearish momentum ({market_context.get('momentum_pct', 0):.1f}%)"
            
            volume_trend = market_context.get('volume_trend', 'normal')
            if volume_trend == 'high':
                momentum_desc += f", elevated volume activity"
            elif volume_trend == 'low':
                momentum_desc += f", below-average volume"
                
        # Risk assessment
        if pl_pct < RISK_THRESHOLDS['critical']:
            risk_desc = "HIGH RISK - position requires immediate review"
        elif pl_pct < RISK_THRESHOLDS['concerning']:
            risk_desc = "elevated risk profile"
        elif pl_pct > RISK_THRESHOLDS['high_gain']:
            risk_desc = "elevated volatility risk due to large gains"
        else:
            risk_desc = "manageable risk profile"
            
        # Sector context
        sector_context = self._get_sector_context(sector)
        
        # Build final thesis
        thesis = f"{symbol}: {performance_desc} in {sector} sector. {position_status.capitalize()}{momentum_desc}. Current price ${current_price:.2f}. {sector_context} Risk assessment: {risk_desc}."
        
        return thesis
    
    def _get_sector_context(self, sector: str) -> str:
        """Provide sector-specific context"""
        sector_insights = {
            'Biotech': 'Biotech sector subject to regulatory and trial outcome volatility.',
            'Automotive': 'Auto sector facing EV transition and supply chain pressures.',
            'Energy': 'Energy sector influenced by oil prices and renewable transition.',
            'Retail': 'Retail sector impacted by consumer spending and e-commerce trends.',
            'Technology': 'Tech sector subject to innovation cycles and market sentiment.',
            'Healthcare': 'Healthcare sector with defensive characteristics and regulatory exposure.',
            'Mining': 'Mining sector tied to commodity prices and economic cycles.',
            'Telecom': 'Telecom sector with utility-like characteristics and 5G investment.',
            'Pharma': 'Pharma sector with patent cliffs and regulatory approval risks.',
            'Cannabis': 'Cannabis sector with regulatory and banking challenges.',
            'Bitcoin Mining': 'Bitcoin mining sector highly correlated with crypto prices.'
        }
        
        return sector_insights.get(sector, f'{sector} sector with unique market dynamics.')
    
    def _calculate_confidence(self, pl_pct: float, market_context: Dict, market_value: float) -> float:
        """Calculate confidence score based on multiple factors"""
        base_confidence = 0.5
        
        # Performance-based confidence adjustment
        if pl_pct > RISK_THRESHOLDS['high_gain']:
            performance_adj = 0.3  # High gains increase confidence
        elif pl_pct > RISK_THRESHOLDS['good_gain']:
            performance_adj = 0.2
        elif pl_pct > RISK_THRESHOLDS['neutral']:
            performance_adj = 0.1
        elif pl_pct > RISK_THRESHOLDS['concerning']:
            performance_adj = -0.1
        else:
            performance_adj = -0.3  # Large losses decrease confidence
            
        # Market context adjustments
        context_adj = 0.0
        if market_context.get('data_available'):
            if market_context.get('momentum') == 'bullish':
                context_adj += 0.1
            elif market_context.get('momentum') == 'bearish':
                context_adj -= 0.1
                
            if market_context.get('volume_trend') == 'high':
                context_adj += 0.05
                
        # Position size consideration (larger positions get slightly lower confidence due to concentration risk)
        size_adj = -0.05 if market_value > 5000 else 0.0
        
        final_confidence = max(0.0, min(1.0, base_confidence + performance_adj + context_adj + size_adj))
        return round(final_confidence, 3)
    
    def _generate_recommendation(self, pl_pct: float, confidence: float, market_context: Dict) -> str:
        """Generate intelligent recommendation based on performance and confidence"""
        
        # Critical situations first
        if pl_pct < RISK_THRESHOLDS['critical']:
            return "reduce"  # >25% loss
        
        # High performers with good confidence
        if pl_pct > RISK_THRESHOLDS['high_gain'] and confidence > 0.7:
            return "hold"  # Take profits on high gains, but don't necessarily increase
        elif pl_pct > RISK_THRESHOLDS['good_gain'] and confidence > 0.6:
            return "increase"  # Strong performance with good confidence
            
        # Concerning losses
        if pl_pct < RISK_THRESHOLDS['concerning'] and confidence < 0.4:
            return "reduce"  # Double negative: losses + low confidence
            
        # Market context considerations
        if market_context.get('momentum') == 'bearish' and pl_pct < 0:
            return "review"  # Bearish momentum with losses needs review
            
        # Default recommendations
        if confidence > 0.7:
            return "increase"
        elif confidence < 0.3:
            return "reduce"
        else:
            return "hold"
    
    def _build_reasoning(self, symbol: str, pl_pct: float, sector: str, confidence: float, recommendation: str) -> str:
        """Build detailed reasoning for learning system"""
        
        performance_reason = ""
        if pl_pct > RISK_THRESHOLDS['good_gain']:
            performance_reason = f"Strong +{pl_pct:.1f}% performance indicates successful thesis execution"
        elif pl_pct < RISK_THRESHOLDS['concerning']:
            performance_reason = f"Concerning {pl_pct:.1f}% loss suggests thesis needs reevaluation"
        else:
            performance_reason = f"Neutral {pl_pct:.1f}% performance suggests thesis developing as expected"
            
        confidence_reason = f"Confidence level {confidence:.1f} based on performance consistency and market factors"
        
        recommendation_reason = ""
        if recommendation == "increase":
            recommendation_reason = "Recommend increasing position due to strong performance and positive outlook"
        elif recommendation == "reduce":
            recommendation_reason = "Recommend reducing position due to underperformance or elevated risk"
        elif recommendation == "review":
            recommendation_reason = "Position requires manual review due to conflicting signals"
        else:
            recommendation_reason = "Recommend holding current position size pending further development"
            
        return f"{performance_reason}. {confidence_reason}. {recommendation_reason}. {sector} sector context considered."
    
    def _assess_risk_level(self, pl_pct: float) -> str:
        """Assess risk level based on current performance"""
        if pl_pct < RISK_THRESHOLDS['critical']:
            return "CRITICAL"
        elif pl_pct < RISK_THRESHOLDS['concerning']:
            return "HIGH"
        elif pl_pct > RISK_THRESHOLDS['high_gain']:
            return "ELEVATED"  # High gains can be risky too
        else:
            return "MODERATE"
    
    def _fallback_thesis(self, symbol: str, position_data: Dict) -> Dict:
        """Fallback thesis when analysis fails"""
        pl_pct = position_data.get('unrealized_pl_pct', 0.0)
        sector = SECTOR_MAPPING.get(symbol, 'Unknown')
        
        return {
            'thesis': f"{symbol}: Position in {sector} sector with {pl_pct:.1f}% current performance. Analysis pending additional data.",
            'confidence': 0.5,
            'recommendation': "hold",
            'reasoning': f"Limited data available for detailed analysis. Current performance {pl_pct:.1f}%.",
            'sector': sector,
            'risk_level': 'MODERATE',
            'market_context': {'data_available': False}
        }
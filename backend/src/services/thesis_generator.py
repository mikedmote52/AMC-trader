import os
import httpx
import asyncio
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: Anthropic not available. Install with: pip install anthropic")

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

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

# VIGL Pattern Historical Reference Data
HISTORICAL_SQUEEZE_PATTERNS = {
    'VIGL': {
        'entry_price': 2.94,
        'peak_price': 12.46,
        'max_gain': 324.0,
        'volume_spike': 20.9,
        'float_size': 15.2e6,  # 15.2M float
        'short_interest': 0.18,  # 18%
        'pattern_duration': 14,  # days to peak
        'characteristics': ['extreme_volume', 'small_float', 'high_short_interest', 'catalyst_driven']
    },
    'CRWV': {
        'entry_price': 1.45,
        'peak_price': 8.92,
        'max_gain': 515.0,
        'volume_spike': 35.2,
        'float_size': 8.5e6,
        'short_interest': 0.22,
        'pattern_duration': 18,
        'characteristics': ['parabolic_volume', 'micro_float', 'squeeze_momentum']
    },
    'AEVA': {
        'entry_price': 4.12,
        'peak_price': 18.35,
        'max_gain': 345.0,
        'volume_spike': 18.3,
        'float_size': 45.8e6,
        'short_interest': 0.15,
        'pattern_duration': 21,
        'characteristics': ['tech_catalyst', 'institutional_interest', 'sector_rotation']
    }
}

# Squeeze detection thresholds
SQUEEZE_THRESHOLDS = {
    'volume_spike_min': 15.0,    # Minimum volume spike vs 30-day avg
    'short_interest_min': 0.10,  # 10% minimum short interest
    'float_max': 100e6,          # Maximum float size (100M)
    'price_range': (1.0, 8.0),   # Optimal price range for squeezes
    'momentum_min': 0.7,         # Minimum momentum score
    'confidence_threshold': 0.75  # Minimum confidence for squeeze alert
}

class AIThesisGenerator:
    """AI-powered thesis generation using Claude for sophisticated analysis"""
    
    def __init__(self):
        self.claude_api_key = CLAUDE_API_KEY
        self.anthropic_client = None
        if ANTHROPIC_AVAILABLE and self.claude_api_key:
            self.anthropic_client = Anthropic(api_key=self.claude_api_key)
    
    async def generate_entry_thesis(self, symbol: str, discovery_data: Dict) -> Dict:
        """Generate entry thesis explaining why this stock was selected"""
        if not self.anthropic_client:
            return self._fallback_entry_thesis(symbol, discovery_data)
        
        try:
            prompt = f"""
Generate a comprehensive entry thesis for stock {symbol} based on this discovery data:

{json.dumps(discovery_data, indent=2)}

Provide:
1. **Investment Thesis**: Why this stock represents a good opportunity (2-3 sentences)
2. **Key Catalysts**: What specific events or trends could drive price appreciation
3. **Risk Factors**: Primary risks that could negatively impact the investment
4. **Price Targets**: Realistic upside potential based on fundamentals
5. **Timeline**: Expected timeframe for thesis to play out

Format as structured JSON with these keys: thesis, catalysts, risks, price_targets, timeline, confidence_score (0.0-1.0)
"""
            
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse Claude's response
            response_text = message.content[0].text
            try:
                thesis_data = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback to structured parsing if JSON fails
                thesis_data = self._parse_claude_response(response_text)
                
            return {
                'type': 'ENTRY',
                'symbol': symbol,
                'ai_generated': True,
                **thesis_data,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"AI thesis generation failed for {symbol}: {e}")
            return self._fallback_entry_thesis(symbol, discovery_data)
    
    async def update_thesis_with_performance(self, symbol: str, current_price: float, entry_price: float, 
                                           original_thesis: Dict, market_data: Dict = None) -> Dict:
        """Update thesis based on performance and new market data"""
        if not self.anthropic_client:
            return self._fallback_performance_update(symbol, current_price, entry_price, original_thesis)
        
        try:
            performance_pct = ((current_price - entry_price) / entry_price) * 100
            
            prompt = f"""
Update the investment thesis for {symbol} based on recent performance:

Original Thesis:
{json.dumps(original_thesis, indent=2)}

Performance Data:
- Entry Price: ${entry_price:.2f}
- Current Price: ${current_price:.2f}
- Performance: {performance_pct:.1f}%

Market Context:
{json.dumps(market_data or {}, indent=2)}

Provide updated analysis:
1. **Thesis Status**: Is the original thesis still valid? (CONFIRMED/EVOLVING/CHALLENGED)
2. **Performance Analysis**: What does the current performance tell us?
3. **Updated Reasoning**: How should we interpret recent price action?
4. **Risk Assessment**: Have risk factors changed?
5. **Action Recommendation**: HOLD/BUY_MORE/TRIM/LIQUIDATE with reasoning
6. **Confidence Update**: Updated confidence score (0.0-1.0)

Format as structured JSON.
"""
            
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            try:
                update_data = json.loads(response_text)
            except json.JSONDecodeError:
                update_data = self._parse_claude_response(response_text)
            
            return {
                'type': 'PERFORMANCE_UPDATE',
                'symbol': symbol,
                'ai_generated': True,
                'performance_pct': performance_pct,
                'original_thesis': original_thesis,
                **update_data,
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"AI performance update failed for {symbol}: {e}")
            return self._fallback_performance_update(symbol, current_price, entry_price, original_thesis)
    
    async def generate_exit_recommendation(self, symbol: str, performance_data: Dict, 
                                         market_conditions: Dict = None) -> Dict:
        """Generate intelligent exit recommendation based on performance and conditions"""
        if not self.anthropic_client:
            return self._fallback_exit_recommendation(symbol, performance_data)
        
        try:
            prompt = f"""
Generate an exit strategy recommendation for {symbol}:

Position Performance:
{json.dumps(performance_data, indent=2)}

Current Market Conditions:
{json.dumps(market_conditions or {}, indent=2)}

Provide comprehensive exit analysis:
1. **Exit Recommendation**: HOLD/TRIM_25/TRIM_50/TRIM_75/LIQUIDATE
2. **Rationale**: Detailed reasoning for the recommendation
3. **Optimal Timing**: Best timing for the exit (immediate/wait_for_bounce/wait_for_breakout/etc)
4. **Risk Management**: How this decision manages portfolio risk
5. **Alternative Scenarios**: What would change the recommendation
6. **Learning Points**: Key lessons from this position

Format as structured JSON with confidence_score (0.0-1.0).
"""
            
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            try:
                exit_data = json.loads(response_text)
            except json.JSONDecodeError:
                exit_data = self._parse_claude_response(response_text)
            
            return {
                'type': 'EXIT_STRATEGY',
                'symbol': symbol,
                'ai_generated': True,
                **exit_data,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"AI exit recommendation failed for {symbol}: {e}")
            return self._fallback_exit_recommendation(symbol, performance_data)
    
    def _parse_claude_response(self, response_text: str) -> Dict:
        """Parse Claude response when JSON parsing fails"""
        # Basic parsing for key information
        result = {
            'thesis': '',
            'confidence_score': 0.5,
            'recommendation': 'HOLD'
        }
        
        lines = response_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if 'thesis' in line.lower() and ':' in line:
                result['thesis'] = line.split(':', 1)[1].strip()
            elif 'confidence' in line.lower() and any(char.isdigit() for char in line):
                # Extract confidence score
                import re
                scores = re.findall(r'0?\.[0-9]+|[01]', line)
                if scores:
                    result['confidence_score'] = float(scores[0])
            elif any(rec in line.upper() for rec in ['HOLD', 'BUY', 'SELL', 'TRIM', 'LIQUIDATE']):
                for rec in ['LIQUIDATE', 'TRIM', 'BUY_MORE', 'HOLD']:
                    if rec in line.upper():
                        result['recommendation'] = rec
                        break
        
        return result
    
    def _fallback_entry_thesis(self, symbol: str, discovery_data: Dict) -> Dict:
        """Fallback entry thesis when AI is unavailable"""
        return {
            'type': 'ENTRY',
            'symbol': symbol,
            'ai_generated': False,
            'thesis': f"{symbol} selected based on discovery algorithm signals. Monitor for momentum confirmation.",
            'catalysts': ['Discovery algorithm signal', 'Market momentum', 'Volume patterns'],
            'risks': ['Market volatility', 'Sector rotation', 'Execution risk'],
            'confidence_score': 0.6,
            'generated_at': datetime.now().isoformat()
        }
    
    def _fallback_performance_update(self, symbol: str, current_price: float, entry_price: float, original_thesis: Dict) -> Dict:
        """Fallback performance update when AI is unavailable"""
        performance_pct = ((current_price - entry_price) / entry_price) * 100
        
        if performance_pct > 25:
            status = "CONFIRMED"
            recommendation = "TRIM"
        elif performance_pct > 10:
            status = "CONFIRMED" 
            recommendation = "HOLD"
        elif performance_pct > -10:
            status = "EVOLVING"
            recommendation = "HOLD"
        else:
            status = "CHALLENGED"
            recommendation = "TRIM"
        
        return {
            'type': 'PERFORMANCE_UPDATE',
            'symbol': symbol,
            'ai_generated': False,
            'performance_pct': performance_pct,
            'thesis_status': status,
            'recommendation': recommendation,
            'confidence_score': 0.5,
            'updated_at': datetime.now().isoformat()
        }
    
    def _fallback_exit_recommendation(self, symbol: str, performance_data: Dict) -> Dict:
        """Fallback exit recommendation when AI is unavailable"""
        pl_pct = performance_data.get('unrealized_pl_pct', 0)
        
        if pl_pct < -25:
            recommendation = "LIQUIDATE"
        elif pl_pct < -15:
            recommendation = "TRIM_50"
        elif pl_pct > 50:
            recommendation = "TRIM_25"
        else:
            recommendation = "HOLD"
        
        return {
            'type': 'EXIT_STRATEGY',
            'symbol': symbol,
            'ai_generated': False,
            'exit_recommendation': recommendation,
            'confidence_score': 0.5,
            'generated_at': datetime.now().isoformat()
        }


class ThesisGenerator:
    """Enhanced thesis generation for all portfolio positions - maintains backward compatibility"""
    
    def __init__(self):
        self.polygon_api_key = POLYGON_API_KEY
        self.ai_generator = AIThesisGenerator()
        self.historical_patterns = HISTORICAL_SQUEEZE_PATTERNS
        
    async def generate_thesis_for_position(self, symbol: str, position_data: Dict, use_ai: bool = True) -> Dict:
        """Generate comprehensive thesis for a single position with optional AI enhancement"""
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
            
            # Try AI-powered analysis first if enabled
            if use_ai and avg_entry_price > 0:
                ai_update = await self.ai_generator.update_thesis_with_performance(
                    symbol, current_price, avg_entry_price, 
                    {'sector': sector}, market_context
                )
                
                if ai_update.get('ai_generated'):
                    # Merge AI insights with traditional analysis
                    traditional_analysis = self._generate_traditional_analysis(
                        symbol, unrealized_pl_pct, sector, market_context, market_value
                    )
                    
                    return {
                        **traditional_analysis,
                        'ai_thesis': ai_update.get('thesis_status', 'AI analysis available'),
                        'ai_confidence': ai_update.get('confidence_score', traditional_analysis['confidence']),
                        'ai_recommendation': ai_update.get('recommendation', traditional_analysis['recommendation']),
                        'ai_reasoning': ai_update.get('rationale', 'AI-powered analysis integrated'),
                        'enhanced': True,
                        'ai_update_data': ai_update
                    }
            
            # Fallback to traditional analysis
            return self._generate_traditional_analysis(symbol, unrealized_pl_pct, sector, market_context, market_value)
            
        except Exception as e:
            print(f"Error generating thesis for {symbol}: {e}")
            return self._fallback_thesis(symbol, position_data)
    
    def _generate_traditional_analysis(self, symbol: str, unrealized_pl_pct: float, sector: str, market_context: Dict, market_value: float) -> Dict:
        """Generate traditional thesis analysis"""
        # Generate thesis based on performance and context
        thesis = self._build_thesis(symbol, unrealized_pl_pct, sector, market_context, 0.0)
        
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
            'market_context': market_context,
            'enhanced': False
        }
    
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
        """Build comprehensive, actionable thesis for investment decisions"""
        
        # Get detailed action reasoning
        action_thesis = self._build_action_thesis(symbol, pl_pct, sector, market_context)
        
        # Performance context with specific implications
        performance_insight = self._get_performance_insight(pl_pct)
        
        # Market technical analysis
        technical_analysis = self._get_technical_analysis(market_context, pl_pct)
        
        # Sector-specific catalysts and risks
        sector_analysis = self._get_detailed_sector_analysis(sector, symbol)
        
        # Risk management perspective
        risk_management = self._get_risk_management_view(pl_pct, current_price)
        
        # Build comprehensive thesis with clear action rationale
        thesis = f"{action_thesis} {performance_insight} {technical_analysis} {sector_analysis} {risk_management}"
        
        return thesis
    
    def _build_action_thesis(self, symbol: str, pl_pct: float, sector: str, market_context: Dict) -> str:
        """Build action-oriented thesis explaining why to buy/hold/sell/trim"""
        
        if pl_pct > 100:  # Exceptional gains like UP with 107%
            return f"🚀 {symbol}: TRIM POSITION - Lock in spectacular +{pl_pct:.0f}% gains. This exceptional performance warrants profit-taking to protect capital and reduce concentration risk."
            
        elif pl_pct > RISK_THRESHOLDS['high_gain']:  # >50% gains
            return f"💰 {symbol}: CONSIDER TRIMMING - Strong +{pl_pct:.1f}% gains justify taking some profits. Scale out gradually while letting winners run."
            
        elif pl_pct > 25:  # Good gains 25-50%
            return f"📈 {symbol}: HOLD STRONG - Solid +{pl_pct:.1f}% performance validates thesis. Let momentum continue while monitoring for signs of topping."
            
        elif pl_pct > RISK_THRESHOLDS['good_gain']:  # 10-25% gains
            return f"🎯 {symbol}: ADD ON STRENGTH - +{pl_pct:.1f}% gain shows thesis working. Consider adding to winning position on any pullbacks."
            
        elif pl_pct > RISK_THRESHOLDS['neutral']:  # Small gains 0-10%
            return f"⏳ {symbol}: HOLD & MONITOR - Early +{pl_pct:.1f}% gains suggest thesis developing. Watch for momentum acceleration or stalling."
            
        elif pl_pct > -2:  # Flat to small loss
            return f"⚖️ {symbol}: HOLD POSITION - Flat performance ({pl_pct:.1f}%) is normal during base-building. Thesis remains intact."
            
        elif pl_pct > RISK_THRESHOLDS['concerning']:  # -2% to -15%
            return f"⚠️ {symbol}: REVIEW THESIS - {pl_pct:.1f}% loss requires analysis. Has fundamental story changed or is this temporary weakness?"
            
        elif pl_pct > RISK_THRESHOLDS['critical']:  # -15% to -25%
            return f"🔄 {symbol}: REDUCE EXPOSURE - {pl_pct:.1f}% loss suggests thesis may be flawed. Consider cutting position size to manage risk."
            
        else:  # >25% loss
            return f"🚨 {symbol}: EXIT POSITION - Severe {pl_pct:.1f}% loss indicates broken thesis. Cut losses to preserve capital for better opportunities."
    
    def _get_performance_insight(self, pl_pct: float) -> str:
        """Get specific insight based on performance level"""
        
        if pl_pct > 100:
            return "Parabolic moves like this rarely last - smart money takes profits on such extreme gains."
        elif pl_pct > 50:
            return "Strong momentum suggests fundamental catalysts at work. Monitor for sustainability signals."
        elif pl_pct > 25:
            return "Solid gains indicate market validation of investment thesis. Momentum could accelerate."
        elif pl_pct > 10:
            return "Positive momentum building. This is often where institutional money starts taking notice."
        elif pl_pct > 0:
            return "Early positive signals. Base-building phase may be setting up for bigger move."
        elif pl_pct > -10:
            return "Modest weakness could be consolidation before next leg up, or early warning sign."
        elif pl_pct > -20:
            return "Concerning underperformance. Thesis stress-test required - what changed?"
        else:
            return "Severe underperformance suggests fundamental thesis breakdown. Capital preservation critical."
    
    def _get_technical_analysis(self, market_context: Dict, pl_pct: float) -> str:
        """Enhanced technical analysis with actionable insights"""
        
        if not market_context.get('data_available'):
            return "Limited technical data available for deeper analysis."
            
        momentum = market_context.get('momentum', 'neutral')
        volume_trend = market_context.get('volume_trend', 'normal')
        momentum_pct = market_context.get('momentum_pct', 0)
        
        technical_signals = []
        
        # Momentum analysis
        if momentum == 'bullish' and momentum_pct > 5:
            technical_signals.append(f"Strong bullish momentum (+{momentum_pct:.1f}%) indicates continued upward pressure")
        elif momentum == 'bullish':
            technical_signals.append(f"Modest bullish momentum (+{momentum_pct:.1f}%) shows steady accumulation")
        elif momentum == 'bearish' and momentum_pct < -5:
            technical_signals.append(f"Significant bearish momentum ({momentum_pct:.1f}%) warns of further selling")
        elif momentum == 'bearish':
            technical_signals.append(f"Mild bearish momentum ({momentum_pct:.1f}%) suggests profit-taking or consolidation")
        else:
            technical_signals.append("Neutral momentum indicates sideways consolidation")
        
        # Volume analysis
        if volume_trend == 'high':
            if pl_pct > 0:
                technical_signals.append("High volume confirms buying interest - bullish validation")
            else:
                technical_signals.append("High volume on weakness suggests institutional selling - bearish")
        elif volume_trend == 'low':
            technical_signals.append("Low volume suggests lack of conviction - wait for catalysts")
        
        return ". ".join(technical_signals) + "." if technical_signals else "Technical picture mixed."
    
    def _get_detailed_sector_analysis(self, sector: str, symbol: str) -> str:
        """Enhanced sector analysis with specific catalysts and risks"""
        
        sector_insights = {
            'Biotech': f"Biotech sector catalyst watch: FDA approvals, clinical trial results, partnership announcements. High volatility from binary events. Risk: regulatory setbacks, trial failures.",
            'Automotive': f"Auto sector facing EV transition pressures. Tesla's success driving sector transformation. Supply chain normalization could boost traditional players.",
            'Energy': f"Energy sector sensitive to oil prices, geopolitical events. Renewable transition creates both risk and opportunity. Dividend sustainability key concern.",
            'Retail': f"Retail sector dependent on consumer spending strength. E-commerce pressure on traditional retailers continues. Back-to-school, holiday seasons critical.",
            'Technology': f"Tech sector driven by AI adoption, cloud growth, digital transformation. Interest rate sensitivity high. Innovation cycles create winners and losers.",
            'Healthcare': f"Healthcare offers defensive characteristics during economic uncertainty. Aging demographics provide tailwinds. Regulatory pricing pressure ongoing.",
            'Mining': f"Mining sector highly cyclical, tied to global economic growth. Commodity price volatility creates both opportunity and risk. ESG concerns growing.",
            'Telecom': f"Telecom sector utility-like with 5G infrastructure investment cycle. Dividend yields attractive but growth limited. Competitive dynamics intense.",
            'Pharma': f"Pharma sector facing patent cliff pressures. Pipeline development and M&A activity key catalysts. Regulatory approval timing critical.",
            'Cannabis': f"Cannabis sector regulatory normalization still pending. Banking access improvements would be major catalyst. State-by-state growth continues.",
            'Bitcoin Mining': f"Bitcoin mining directly tied to crypto prices and energy costs. Hashrate difficulty adjustments impact profitability. Regulatory clarity improving."
        }
        
        base_analysis = sector_insights.get(sector, f'{sector} sector dynamics require individual assessment.')
        
        # Add symbol-specific insights for known positions
        symbol_specifics = {
            'UP': "Cannabis play with potential federal legalization catalysts. MSO with multi-state operations.",
            'KSS': "Department store turnaround story. Real estate value and omnichannel execution key.",
            'WULF': "Bitcoin mining with renewable energy focus. Lower cost structure vs peers.",
            'QUBT': "Quantum computing pure play. Early stage tech with massive potential but execution risk.",
            'SPHR': "Healthcare equipment/services. Demographic tailwinds but margin pressures.",
            'SSRM': "Silver mining with precious metals exposure. Inflation hedge characteristics."
        }
        
        if symbol in symbol_specifics:
            return f"{base_analysis} {symbol}-specific: {symbol_specifics[symbol]}"
        
        return base_analysis
    
    async def generate_entry_thesis_for_discovery(self, symbol: str, discovery_data: Dict) -> Dict:
        """Generate entry thesis for newly discovered opportunities"""
        try:
            # Try AI-powered entry thesis first
            ai_thesis = await self.ai_generator.generate_entry_thesis(symbol, discovery_data)
            
            if ai_thesis.get('ai_generated'):
                return {
                    'symbol': symbol,
                    'type': 'ENTRY_OPPORTUNITY',
                    'ai_generated': True,
                    'entry_thesis': ai_thesis.get('thesis', f'{symbol} discovery opportunity'),
                    'key_catalysts': ai_thesis.get('catalysts', []),
                    'risk_factors': ai_thesis.get('risks', []),
                    'price_targets': ai_thesis.get('price_targets', {}),
                    'timeline': ai_thesis.get('timeline', 'Medium-term'),
                    'confidence': ai_thesis.get('confidence_score', 0.6),
                    'recommendation': 'RESEARCH',  # Initial recommendation for discovered stocks
                    'discovery_data': discovery_data,
                    'generated_at': datetime.now().isoformat()
                }
            
            # Fallback to traditional entry analysis
            return self._generate_traditional_entry_thesis(symbol, discovery_data)
            
        except Exception as e:
            print(f"Error generating entry thesis for {symbol}: {e}")
            return self._generate_traditional_entry_thesis(symbol, discovery_data)
    
    def _generate_traditional_entry_thesis(self, symbol: str, discovery_data: Dict) -> Dict:
        """Generate traditional entry thesis for discoveries"""
        sector = SECTOR_MAPPING.get(symbol, 'Unknown')
        confidence = discovery_data.get('confidence', 0.6)
        
        # Build entry thesis based on discovery signals
        entry_signals = discovery_data.get('signals', [])
        volume_score = discovery_data.get('volume_score', 0)
        momentum_score = discovery_data.get('momentum_score', 0)
        
        thesis_components = []
        if volume_score > 0.7:
            thesis_components.append("Strong volume confirmation")
        if momentum_score > 0.7:
            thesis_components.append("Positive momentum building")
        if entry_signals:
            thesis_components.append(f"Discovery signals: {', '.join(entry_signals[:3])}")
        
        entry_thesis = f"{symbol} ({sector}) shows {', '.join(thesis_components)}. Discovery algorithm flagged for potential opportunity."
        
        return {
            'symbol': symbol,
            'type': 'ENTRY_OPPORTUNITY',
            'ai_generated': False,
            'entry_thesis': entry_thesis,
            'key_catalysts': ['Discovery algorithm signal', f'{sector} sector momentum', 'Technical breakout potential'],
            'risk_factors': ['Market volatility', 'Sector rotation risk', 'False breakout risk'],
            'confidence': confidence,
            'recommendation': 'RESEARCH',
            'sector': sector,
            'discovery_data': discovery_data,
            'generated_at': datetime.now().isoformat()
        }
    
    async def generate_exit_strategy(self, symbol: str, position_data: Dict, market_conditions: Dict = None) -> Dict:
        """Generate comprehensive exit strategy with AI insights"""
        try:
            # Try AI-powered exit recommendation
            ai_exit = await self.ai_generator.generate_exit_recommendation(symbol, position_data, market_conditions)
            
            if ai_exit.get('ai_generated'):
                return {
                    'symbol': symbol,
                    'type': 'EXIT_STRATEGY',
                    'ai_generated': True,
                    'exit_recommendation': ai_exit.get('exit_recommendation', 'HOLD'),
                    'rationale': ai_exit.get('rationale', 'AI-powered exit analysis'),
                    'optimal_timing': ai_exit.get('optimal_timing', 'Market dependent'),
                    'risk_management': ai_exit.get('risk_management', 'Standard risk protocols'),
                    'alternative_scenarios': ai_exit.get('alternative_scenarios', {}),
                    'learning_points': ai_exit.get('learning_points', []),
                    'confidence': ai_exit.get('confidence_score', 0.6),
                    'generated_at': datetime.now().isoformat()
                }
            
            # Fallback to traditional exit analysis
            return self._generate_traditional_exit_strategy(symbol, position_data, market_conditions)
            
        except Exception as e:
            print(f"Error generating exit strategy for {symbol}: {e}")
            return self._generate_traditional_exit_strategy(symbol, position_data, market_conditions)
    
    def _generate_traditional_exit_strategy(self, symbol: str, position_data: Dict, market_conditions: Dict = None) -> Dict:
        """Generate traditional exit strategy"""
        unrealized_pl_pct = position_data.get('unrealized_pl_pct', 0.0)
        market_value = position_data.get('market_value', 0.0)
        
        # Determine exit recommendation based on performance
        if unrealized_pl_pct < -25:
            exit_rec = "LIQUIDATE"
            rationale = f"Critical {unrealized_pl_pct:.1f}% loss requires capital preservation"
        elif unrealized_pl_pct < -15:
            exit_rec = "TRIM_50"
            rationale = f"Significant {unrealized_pl_pct:.1f}% loss warrants position size reduction"
        elif unrealized_pl_pct > 100:
            exit_rec = "TRIM_75"
            rationale = f"Exceptional {unrealized_pl_pct:.1f}% gain requires profit taking"
        elif unrealized_pl_pct > 50:
            exit_rec = "TRIM_25"
            rationale = f"Strong {unrealized_pl_pct:.1f}% gain warrants partial profit taking"
        else:
            exit_rec = "HOLD"
            rationale = f"Current {unrealized_pl_pct:.1f}% performance within acceptable range"
        
        return {
            'symbol': symbol,
            'type': 'EXIT_STRATEGY',
            'ai_generated': False,
            'exit_recommendation': exit_rec,
            'rationale': rationale,
            'optimal_timing': 'Monitor key levels and volume',
            'confidence': 0.6,
            'generated_at': datetime.now().isoformat()
        }
    
    async def integrate_with_learning_system(self, symbol: str, thesis_data: Dict, decision_made: str = None):
        """Integrate thesis generation with learning system for continuous improvement"""
        try:
            from ..routes.learning import LearningSystem
            
            if decision_made:
                # Log the decision for learning
                await LearningSystem.log_decision(
                    symbol=symbol,
                    decision_type=decision_made,
                    recommendation_source="ai_thesis_generator",
                    confidence_score=thesis_data.get('confidence', 0.5),
                    price_at_decision=thesis_data.get('current_price', 0.0),
                    market_time=self._get_market_time(),
                    reasoning=thesis_data.get('reasoning', 'AI thesis generation'),
                    metadata={
                        'thesis_type': thesis_data.get('type', 'UNKNOWN'),
                        'ai_generated': thesis_data.get('ai_generated', False),
                        'sector': thesis_data.get('sector', 'Unknown'),
                        'enhanced': thesis_data.get('enhanced', False)
                    }
                )
                
            return {"learning_integration": "success", "decision_logged": bool(decision_made)}
            
        except Exception as e:
            print(f"Learning system integration error: {e}")
            return {"learning_integration": "failed", "error": str(e)}
    
    async def track_thesis_accuracy(self, symbol: str, original_thesis: Dict, outcome_data: Dict) -> Dict:
        """Track thesis accuracy and update confidence scoring based on outcomes"""
        try:
            from ..routes.learning import LearningSystem
            
            # Calculate accuracy metrics
            original_recommendation = original_thesis.get('recommendation', 'HOLD')
            original_confidence = original_thesis.get('confidence', 0.5)
            pattern_type = original_thesis.get('pattern_type', 'STANDARD')
            
            actual_return = outcome_data.get('return_pct', 0.0)
            days_held = outcome_data.get('days_held', 0)
            
            # Determine outcome success
            if original_recommendation == 'BUY_MORE' or original_recommendation == 'RESEARCH':
                success = actual_return > 5.0  # Success if >5% gain
            elif original_recommendation == 'TRIM':
                success = actual_return < 0 or days_held > 14  # Success if avoided loss or held too long
            elif original_recommendation == 'LIQUIDATE':
                success = actual_return < -10.0  # Success if avoided major loss
            else:  # HOLD
                success = abs(actual_return) < 15.0  # Success if stayed within reasonable range
                
            # Calculate confidence accuracy
            confidence_accuracy = self._calculate_confidence_accuracy(original_confidence, success, abs(actual_return))
            
            # Update pattern success rates
            pattern_performance = await self._update_pattern_performance(pattern_type, success, actual_return)
            
            # Store learning data
            learning_entry = {
                'symbol': symbol,
                'original_thesis': original_thesis,
                'outcome': {
                    'return_pct': actual_return,
                    'days_held': days_held,
                    'success': success,
                    'confidence_accuracy': confidence_accuracy
                },
                'pattern_performance': pattern_performance,
                'timestamp': datetime.now().isoformat()
            }
            
            # Log the outcome for learning
            await LearningSystem.log_outcome(
                symbol=symbol,
                decision_id=original_thesis.get('decision_id', 0),  # Would need to track this
                outcome_type='gain' if actual_return > 0 else 'loss',
                price_at_outcome=outcome_data.get('exit_price', 0.0),
                return_pct=actual_return,
                days_held=days_held,
                market_conditions={
                    'thesis_accuracy': confidence_accuracy,
                    'pattern_type': pattern_type,
                    'recommendation_success': success
                }
            )
            
            return {
                'accuracy_tracking': 'success',
                'thesis_accuracy': confidence_accuracy,
                'recommendation_success': success,
                'pattern_performance_updated': True,
                'learning_data': learning_entry
            }
            
        except Exception as e:
            print(f"Error tracking thesis accuracy: {e}")
            return {'accuracy_tracking': 'failed', 'error': str(e)}
    
    def _calculate_confidence_accuracy(self, original_confidence: float, success: bool, actual_return: float) -> float:
        """Calculate how accurate the original confidence score was"""
        if success:
            # Higher confidence + success = good accuracy
            # Lower confidence + success = under-confident (moderate accuracy)
            if original_confidence > 0.8:
                return 0.9  # High confidence, successful - excellent accuracy
            elif original_confidence > 0.6:
                return 0.8  # Medium confidence, successful - good accuracy
            else:
                return 0.6  # Low confidence, successful - under-confident
        else:
            # Higher confidence + failure = poor accuracy
            # Lower confidence + failure = appropriately cautious (better accuracy)
            if original_confidence > 0.8:
                return 0.2  # High confidence, failed - poor accuracy
            elif original_confidence > 0.6:
                return 0.4  # Medium confidence, failed - moderate accuracy
            else:
                return 0.7  # Low confidence, failed - appropriately cautious
    
    async def _update_pattern_performance(self, pattern_type: str, success: bool, actual_return: float) -> Dict:
        """Update success rates for different pattern types"""
        try:
            # This could be stored in database or cache for persistence
            # For now, return performance update info
            performance_update = {
                'pattern_type': pattern_type,
                'success': success,
                'return': actual_return,
                'updated_at': datetime.now().isoformat()
            }
            
            # Pattern-specific learning
            if pattern_type == 'VIGL_SQUEEZE':
                if success and actual_return > 50:
                    performance_update['learning'] = 'VIGL pattern continues to be highly effective'
                elif not success:
                    performance_update['learning'] = 'VIGL pattern failed - analyze what was different'
            elif pattern_type == 'MOMENTUM_FADE':
                if success:
                    performance_update['learning'] = 'Momentum fade detection working well'
                else:
                    performance_update['learning'] = 'Momentum fade detection needs refinement'
            
            return performance_update
            
        except Exception as e:
            print(f"Error updating pattern performance: {e}")
            return {'pattern_type': pattern_type, 'error': str(e)}
    
    async def get_adaptive_confidence_scoring(self, symbol: str, metrics: Dict) -> float:
        """Get adaptive confidence scoring based on historical accuracy"""
        try:
            from ..routes.learning import LearningSystem
            
            # Get historical performance for similar patterns
            insights = await LearningSystem.get_learning_insights(90)  # 90 days of data
            
            base_confidence = 0.6  # Default confidence
            pattern_type = self._detect_pattern_type(metrics)
            
            # Adjust confidence based on historical pattern performance
            if insights.get('decision_stats'):
                for stat in insights['decision_stats']:
                    if stat.get('recommendation_source') == 'ai_thesis_generator':
                        avg_return = stat.get('avg_return', 0)
                        decision_count = stat.get('decision_count', 0)
                        
                        if decision_count >= 5:  # Enough data points
                            if avg_return > 10:
                                base_confidence += 0.2  # Increase confidence for good performance
                            elif avg_return < -5:
                                base_confidence -= 0.1  # Decrease confidence for poor performance
            
            # Pattern-specific confidence adjustments
            if pattern_type == 'VIGL_SQUEEZE':
                # VIGL patterns historically strong - boost confidence
                base_confidence += 0.15
            elif pattern_type == 'BREAKDOWN':
                # Breakdown patterns clear - high confidence in exits
                base_confidence += 0.1
                
            return min(max(base_confidence, 0.1), 0.95)  # Keep within bounds
            
        except Exception as e:
            print(f"Error in adaptive confidence scoring: {e}")
            return 0.6  # Default confidence
    
    def _detect_pattern_type(self, metrics: Dict) -> str:
        """Detect pattern type from metrics for confidence adjustment"""
        squeeze_score = metrics.get('squeeze_score', 0)
        volume_spike = metrics.get('volume_spike', 1)
        momentum = metrics.get('momentum', 'neutral')
        
        if squeeze_score > 0.75:
            return 'VIGL_SQUEEZE'
        elif volume_spike > 10 and momentum == 'bullish':
            return 'MOMENTUM_BREAKOUT'
        elif momentum == 'bearish' and volume_spike > 5:
            return 'BREAKDOWN'
        elif momentum == 'neutral':
            return 'CONSOLIDATION'
        else:
            return 'STANDARD'
    
    def _get_market_time(self) -> str:
        """Determine current market time period"""
        from datetime import datetime
        import pytz
        
        try:
            et = pytz.timezone('US/Eastern')
            now = datetime.now(et)
            hour = now.hour
            
            if hour < 9:
                return "premarket"
            elif 9 <= hour < 10:
                return "open"
            elif 10 <= hour < 14:
                return "midday"
            elif 14 <= hour < 16:
                return "close"
            else:
                return "afterhours"
        except:
            return "unknown"
    
    async def generate_squeeze_thesis(self, symbol: str, metrics: Dict) -> Dict:
        """Generate squeeze-specific thesis with VIGL pattern recognition"""
        try:
            squeeze_score = metrics.get('squeeze_score', 0)
            volume_spike = metrics.get('volume_spike', 1.0)
            short_interest = metrics.get('short_interest', 0.0)
            float_size = metrics.get('float', 50e6)  # Default 50M float
            price = metrics.get('price', 0.0)
            
            # High-confidence squeeze detection
            if squeeze_score > SQUEEZE_THRESHOLDS['confidence_threshold']:
                # Generate VIGL-style squeeze alert
                thesis = f"🚨 EXTREME SQUEEZE ALERT: {symbol} showing VIGL-like pattern with "
                thesis += f"{volume_spike:.1f}x volume spike. "
                thesis += f"Short interest {short_interest:.1%} with only {float_size/1e6:.1f}M float. "
                
                # Pattern similarity analysis
                best_match = self._find_best_pattern_match(metrics)
                if best_match['similarity'] > 0.70:
                    thesis += f"{best_match['similarity']:.0%} similar to {best_match['pattern']} "
                    thesis += f"before +{best_match['max_gain']:.0f}% move. "
                
                thesis += "CRITICAL: Set stops at -8% for risk management."
                
                # Dynamic recommendations based on price and metrics
                if price < 5.0 and volume_spike > 20.0:
                    recommendation = 'BUY_MORE'
                    confidence_boost = 0.15
                elif price < 5.0:
                    recommendation = 'BUY_MORE' 
                    confidence_boost = 0.10
                else:
                    recommendation = 'RESEARCH'
                    confidence_boost = 0.05
                
                # Calculate targets based on historical patterns
                targets = self._calculate_squeeze_targets(price, best_match)
                
                return {
                    'thesis': thesis,
                    'confidence': min(squeeze_score + confidence_boost, 0.95),
                    'recommendation': recommendation,
                    'pattern_type': 'VIGL_SQUEEZE',
                    'risk_level': 'HIGH_REWARD',
                    'pattern_match': best_match,
                    'squeeze_metrics': {
                        'volume_spike': volume_spike,
                        'short_interest': short_interest,
                        'float_size': float_size,
                        'squeeze_score': squeeze_score
                    },
                    'targets': targets,
                    'risk_management': {
                        'stop_loss': price * 0.92,  # -8% stop
                        'position_size': 'Conservative due to high volatility',
                        'time_horizon': '2-4 weeks for initial move'
                    },
                    'generated_at': datetime.now().isoformat()
                }
            
            # Medium confidence squeeze potential
            elif squeeze_score > 0.50:
                thesis = f"⚡ SQUEEZE POTENTIAL: {symbol} showing elevated squeeze metrics. "
                thesis += f"Volume spike {volume_spike:.1f}x with {short_interest:.1%} short interest. "
                thesis += "Monitor for momentum acceleration."
                
                return {
                    'thesis': thesis,
                    'confidence': squeeze_score + 0.05,
                    'recommendation': 'RESEARCH',
                    'pattern_type': 'SQUEEZE_WATCH',
                    'risk_level': 'MODERATE',
                    'targets': self._calculate_conservative_targets(price),
                    'generated_at': datetime.now().isoformat()
                }
            
            # Low squeeze probability
            else:
                return self._generate_non_squeeze_thesis(symbol, metrics)
                
        except Exception as e:
            print(f"Error generating squeeze thesis for {symbol}: {e}")
            return self._fallback_squeeze_thesis(symbol, metrics)
    
    def _find_best_pattern_match(self, metrics: Dict) -> Dict:
        """Find the best historical pattern match for current metrics"""
        current_volume = metrics.get('volume_spike', 1.0)
        current_short = metrics.get('short_interest', 0.0)
        current_float = metrics.get('float', 50e6)
        current_price = metrics.get('price', 5.0)
        
        best_match = {'pattern': 'VIGL', 'similarity': 0.0, 'max_gain': 324.0}
        
        for pattern_name, pattern_data in self.historical_patterns.items():
            # Calculate similarity score across multiple dimensions
            volume_similarity = min(current_volume / pattern_data['volume_spike'], 1.0) * 0.4
            short_similarity = min(current_short / pattern_data['short_interest'], 1.0) * 0.3
            float_similarity = min(pattern_data['float_size'] / current_float, 1.0) * 0.2
            price_similarity = (1.0 - abs(current_price - pattern_data['entry_price']) / 10.0) * 0.1
            
            total_similarity = max(0, volume_similarity + short_similarity + float_similarity + price_similarity)
            
            if total_similarity > best_match['similarity']:
                best_match = {
                    'pattern': pattern_name,
                    'similarity': total_similarity,
                    'max_gain': pattern_data['max_gain'],
                    'duration': pattern_data['pattern_duration'],
                    'characteristics': pattern_data['characteristics']
                }
        
        return best_match
    
    def _calculate_squeeze_targets(self, price: float, pattern_match: Dict) -> Dict:
        """Calculate dynamic price targets based on pattern similarity"""
        base_multiplier = pattern_match['max_gain'] / 100.0  # Convert % to multiplier
        similarity_factor = pattern_match['similarity']
        
        # Conservative scaling based on similarity
        conservative_multiplier = 1.5 * similarity_factor
        aggressive_multiplier = min(base_multiplier * similarity_factor, 4.0)  # Cap at 4x
        moonshot_multiplier = min(base_multiplier, 6.0)  # Cap at 6x
        
        return {
            'stop_loss': price * 0.92,  # -8% stop loss
            'target_1': price * conservative_multiplier,  # Conservative target
            'target_2': price * (conservative_multiplier + aggressive_multiplier) / 2,  # Mid target
            'target_3': price * aggressive_multiplier,  # Aggressive target  
            'moonshot': price * moonshot_multiplier,  # Maximum potential based on pattern
            'pattern_based': True,
            'similarity_factor': similarity_factor
        }
    
    def _calculate_conservative_targets(self, price: float) -> Dict:
        """Calculate conservative targets for lower-confidence setups"""
        return {
            'stop_loss': price * 0.90,  # -10% stop
            'target_1': price * 1.25,   # +25%
            'target_2': price * 1.50,   # +50%
            'conservative': True
        }
    
    def _generate_non_squeeze_thesis(self, symbol: str, metrics: Dict) -> Dict:
        """Generate thesis for non-squeeze patterns"""
        price = metrics.get('price', 0.0)
        volume_spike = metrics.get('volume_spike', 1.0)
        
        if volume_spike > 5.0:
            thesis = f"📊 MOMENTUM PLAY: {symbol} showing {volume_spike:.1f}x volume increase. "
            thesis += "Not squeeze-level metrics but worth monitoring for trend continuation."
            recommendation = 'RESEARCH'
        else:
            thesis = f"📈 STANDARD ANALYSIS: {symbol} showing normal trading patterns. "
            thesis += "Apply traditional technical analysis for entry/exit decisions."
            recommendation = 'HOLD'
        
        return {
            'thesis': thesis,
            'confidence': 0.5,
            'recommendation': recommendation,
            'pattern_type': 'STANDARD',
            'risk_level': 'MODERATE',
            'generated_at': datetime.now().isoformat()
        }
    
    def _fallback_squeeze_thesis(self, symbol: str, metrics: Dict) -> Dict:
        """Fallback thesis when squeeze analysis fails"""
        return {
            'thesis': f"{symbol}: Squeeze analysis pending. Using traditional thesis framework.",
            'confidence': 0.4,
            'recommendation': 'HOLD',
            'pattern_type': 'ANALYSIS_FAILED',
            'risk_level': 'MODERATE',
            'error': 'Squeeze analysis unavailable',
            'generated_at': datetime.now().isoformat()
        }
    
    async def generate_pattern_specific_recommendation(self, symbol: str, pattern_type: str, metrics: Dict) -> Dict:
        """Generate pattern-specific recommendations for different market conditions"""
        try:
            current_price = metrics.get('price', 0.0)
            volume_trend = metrics.get('volume_trend', 'normal')
            momentum = metrics.get('momentum', 'neutral')
            
            if pattern_type == 'VIGL_SQUEEZE':
                # VIGL pattern → Aggressive accumulation below $5
                if current_price < 5.0:
                    return {
                        'action': 'AGGRESSIVE_ACCUMULATION',
                        'reasoning': f'VIGL-pattern confirmed below $5 threshold at ${current_price:.2f}',
                        'position_sizing': '2-3% of portfolio maximum due to high risk/reward',
                        'entry_strategy': 'Scale in on volume spikes and dips',
                        'risk_management': 'Strict -8% stop loss, no exceptions'
                    }
                else:
                    return {
                        'action': 'RESEARCH_ONLY',
                        'reasoning': f'Price ${current_price:.2f} above optimal entry range for VIGL pattern',
                        'wait_for': 'Pullback to $4.50-5.00 range for better risk/reward'
                    }
            
            elif pattern_type == 'MOMENTUM_FADE':
                # Momentum fade → Trim 50% on first double
                if metrics.get('unrealized_pl_pct', 0) > 100:
                    return {
                        'action': 'TRIM_50',
                        'reasoning': 'Momentum fading after initial double - lock in gains',
                        'timing': 'Immediate execution recommended',
                        'keep_watching': 'Monitor remaining position for breakdown signals'
                    }
                elif metrics.get('unrealized_pl_pct', 0) > 50:
                    return {
                        'action': 'PREPARE_TO_TRIM',
                        'reasoning': 'Momentum showing early fade signs - prepare exit strategy',
                        'watch_for': 'Volume decline and price stagnation'
                    }
            
            elif pattern_type == 'BREAKDOWN':
                # Breakdown → Immediate exit
                return {
                    'action': 'IMMEDIATE_EXIT',
                    'reasoning': 'Pattern breakdown confirmed - capital preservation critical',
                    'urgency': 'Execute within 24 hours',
                    'no_hesitation': 'Do not wait for bounce - pattern integrity compromised'
                }
            
            elif pattern_type == 'CONSOLIDATION':
                return {
                    'action': 'HOLD_AND_MONITOR',
                    'reasoning': 'Healthy consolidation after move - maintain position',
                    'watch_for': 'Volume expansion for next leg confirmation'
                }
            
            else:
                return {
                    'action': 'STANDARD_ANALYSIS',
                    'reasoning': f'Pattern {pattern_type} requires individual assessment'
                }
                
        except Exception as e:
            print(f"Error generating pattern-specific recommendation: {e}")
            return {
                'action': 'HOLD',
                'reasoning': 'Pattern analysis unavailable - default to hold',
                'error': str(e)
            }
    
    def _get_risk_management_view(self, pl_pct: float, current_price: float) -> str:
        """Risk management perspective with specific guidance"""
        
        if pl_pct > 100:
            return f"Risk Management: Extreme gains require immediate profit-taking. Consider selling 50-75% to lock in gains while maintaining upside exposure."
            
        elif pl_pct > 50:
            return f"Risk Management: Large gains suggest trimming 25-50% of position. Use stop-losses to protect remaining gains."
            
        elif pl_pct > 25:
            return f"Risk Management: Solid gains warrant protective stops. Consider trailing stops to lock in profits while allowing for continued upside."
            
        elif pl_pct > 10:
            return f"Risk Management: Positive momentum developing. Set stop-loss below recent support levels to protect capital."
            
        elif pl_pct > -5:
            return f"Risk Management: Position within acceptable range. Monitor for breakdown below key support levels."
            
        elif pl_pct > -15:
            return f"Risk Management: Position showing stress. Reassess thesis and consider position sizing reduction if conviction waning."
            
        elif pl_pct > -25:
            return f"Risk Management: Significant loss requiring action. Cut position size by 50% or more to limit further damage."
            
        else:
            return f"Risk Management: Critical loss levels. Exit position to preserve remaining capital for better opportunities."
    
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
        """Generate intelligent recommendation mapping to frontend actions"""
        
        # Map to frontend action types: "BUY MORE", "HOLD", "TRIM", "LIQUIDATE"
        
        # Critical situations first - major losses require liquidation
        if pl_pct < RISK_THRESHOLDS['critical']:  # <-25% loss
            return "LIQUIDATE"
        
        # Extreme gains require trimming regardless of confidence
        if pl_pct > 100:  # UP-style gains
            return "TRIM"
            
        # Large gains should be trimmed to lock in profits
        if pl_pct > RISK_THRESHOLDS['high_gain']:  # >50% gains
            return "TRIM"
            
        # Concerning losses require position reduction
        if pl_pct < RISK_THRESHOLDS['concerning']:  # -5% to -25% loss
            if confidence < 0.4:
                return "TRIM"  # Low confidence + losses = reduce
            else:
                return "HOLD"  # Still have confidence despite losses
        
        # Strong performance with good confidence = add more
        if pl_pct > RISK_THRESHOLDS['good_gain'] and confidence > 0.6:  # >10% gains
            return "BUY MORE"
            
        # Market context considerations
        if market_context.get('momentum') == 'bearish' and pl_pct < 0:
            return "HOLD"  # Don't add to bearish momentum + losses
            
        # Positive momentum with modest gains
        if pl_pct > 5 and confidence > 0.7:
            return "BUY MORE"
            
        # High confidence regardless of performance
        if confidence > 0.8:
            return "BUY MORE"
            
        # Low confidence requires caution
        if confidence < 0.3:
            return "TRIM"
            
        # Default to hold for everything else
        return "HOLD"
    
    def _build_reasoning(self, symbol: str, pl_pct: float, sector: str, confidence: float, recommendation: str) -> str:
        """Build detailed reasoning explaining the recommendation"""
        
        # Performance assessment with specific reasoning
        if pl_pct > 100:
            performance_reason = f"Exceptional +{pl_pct:.0f}% gains are rare and unsustainable"
        elif pl_pct > RISK_THRESHOLDS['high_gain']:
            performance_reason = f"Strong +{pl_pct:.1f}% performance validates investment thesis"
        elif pl_pct > RISK_THRESHOLDS['good_gain']:
            performance_reason = f"Solid +{pl_pct:.1f}% gains show momentum building"
        elif pl_pct > RISK_THRESHOLDS['neutral']:
            performance_reason = f"Early +{pl_pct:.1f}% gains suggest thesis developing correctly"
        elif pl_pct > RISK_THRESHOLDS['concerning']:
            performance_reason = f"Modest {pl_pct:.1f}% loss is within normal volatility range"
        elif pl_pct > RISK_THRESHOLDS['critical']:
            performance_reason = f"Concerning {pl_pct:.1f}% loss requires thesis reassessment"
        else:
            performance_reason = f"Severe {pl_pct:.1f}% loss indicates thesis breakdown"
            
        # Confidence reasoning
        if confidence > 0.8:
            confidence_reason = f"High confidence ({confidence:.1f}) based on strong fundamentals and technicals"
        elif confidence > 0.6:
            confidence_reason = f"Good confidence ({confidence:.1f}) with positive outlook"
        elif confidence > 0.4:
            confidence_reason = f"Moderate confidence ({confidence:.1f}) with mixed signals"
        else:
            confidence_reason = f"Low confidence ({confidence:.1f}) due to concerning factors"
        
        # Action reasoning mapped to frontend
        action_explanations = {
            "BUY MORE": "Adding to position due to positive momentum and strong fundamentals",
            "HOLD": "Maintaining current position size while monitoring developments", 
            "TRIM": "Reducing position size to manage risk and lock in gains",
            "LIQUIDATE": "Exiting position to preserve capital for better opportunities"
        }
        
        recommendation_reason = action_explanations.get(recommendation, f"Recommend {recommendation.lower()}")
        
        # Sector-specific insight
        sector_factor = f"{sector} sector dynamics support this assessment"
        
        return f"{performance_reason}. {confidence_reason}. {recommendation_reason}. {sector_factor}."
    
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
import asyncio
import asyncpg
import httpx
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import statistics
import os

@dataclass
class TimingAnalysisPoint:
    """Individual timing analysis data point"""
    symbol: str
    analysis_date: datetime
    
    # Entry timing analysis
    discovery_date: datetime
    entry_date: datetime
    entry_delay_days: int
    entry_price: float
    discovery_price: float
    entry_timing_cost: float  # % lost due to delayed entry
    
    # Optimal entry analysis
    optimal_entry_date: Optional[datetime] = None
    optimal_entry_price: Optional[float] = None
    optimal_entry_improvement: Optional[float] = None  # % better if entered optimally
    
    # Exit timing analysis (if applicable)
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    optimal_exit_date: Optional[datetime] = None
    optimal_exit_price: Optional[float] = None
    exit_timing_cost: Optional[float] = None
    
    # Market conditions at entry/exit
    market_volatility: Optional[float] = None
    volume_ratio: Optional[float] = None  # vs average
    sector_momentum: Optional[str] = None
    
    # Classification
    entry_timing_grade: Optional[str] = None  # excellent, good, fair, poor, terrible
    exit_timing_grade: Optional[str] = None

@dataclass
class MarketTimingMetrics:
    """Aggregate market timing performance metrics"""
    period_start: datetime
    period_end: datetime
    total_positions: int
    
    # Entry timing performance
    avg_entry_delay_days: float = 0.0
    avg_entry_timing_cost: float = 0.0  # % cost of delayed entries
    optimal_entry_improvement: float = 0.0  # % improvement possible
    
    # Exit timing performance
    avg_exit_timing_cost: float = 0.0
    optimal_exit_improvement: float = 0.0
    
    # Timing grades distribution
    excellent_timing_rate: float = 0.0  # % with excellent timing
    poor_timing_rate: float = 0.0       # % with poor timing
    
    # Market condition analysis
    best_entry_conditions: Optional[Dict] = None
    worst_entry_conditions: Optional[Dict] = None
    timing_vs_volatility_correlation: Optional[float] = None
    
    # VIGL baseline comparison
    vigl_timing_benchmark: float = 0.0  # VIGL entry timing as benchmark
    timing_vs_vigl_gap: float = 0.0     # Performance gap vs VIGL timing
    
    # Improvement opportunities
    total_timing_cost: float = 0.0      # Total % lost to poor timing
    potential_improvement: float = 0.0   # Total % improvement possible

class MarketTimingAnalyzer:
    """Comprehensive market entry/exit timing analysis"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'postgresql://localhost/amc_trader')
        self.polygon_api_key = os.getenv('POLYGON_API_KEY')
        
        # VIGL baseline timing (perfect example)
        self.vigl_baseline = {
            'symbol': 'VIGL',
            'discovery_to_entry_days': 0,  # Entered immediately
            'entry_timing_cost': 0.0,      # Perfect entry
            'peak_return': 324.0,          # Peak performance
            'optimal_exit_timing': True    # Exited near peak
        }
    
    async def get_db_pool(self):
        """Get database connection pool"""
        try:
            return await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
        except Exception as e:
            print(f"Database connection failed: {e}")
            return None
    
    async def analyze_position_timing(self, symbol: str, position_date: datetime) -> TimingAnalysisPoint:
        """Analyze timing for a specific position"""
        pool = await self.get_db_pool()
        if not pool:
            return None
            
        try:
            async with pool.acquire() as conn:
                # Get position and discovery data
                position_data = await self._get_position_data(conn, symbol, position_date)
                discovery_data = await self._get_discovery_data(conn, symbol, position_date)
                
                if not position_data or not discovery_data:
                    return None
                
                # Get market data for timing analysis
                market_data = await self._get_market_data_for_timing(
                    symbol, discovery_data['created_at'], position_date
                )
                
                # Create timing analysis
                timing_point = TimingAnalysisPoint(
                    symbol=symbol,
                    analysis_date=datetime.utcnow(),
                    discovery_date=discovery_data['created_at'],
                    entry_date=position_date,
                    entry_delay_days=(position_date - discovery_data['created_at']).days,
                    entry_price=position_data['avg_entry_price'],
                    discovery_price=discovery_data['price']
                )
                
                # Calculate entry timing cost
                timing_point.entry_timing_cost = self._calculate_entry_timing_cost(
                    timing_point.discovery_price, 
                    timing_point.entry_price
                )
                
                # Analyze optimal entry timing
                if market_data:
                    optimal_analysis = self._analyze_optimal_entry_timing(market_data, discovery_data)
                    timing_point.optimal_entry_date = optimal_analysis.get('optimal_date')
                    timing_point.optimal_entry_price = optimal_analysis.get('optimal_price')
                    timing_point.optimal_entry_improvement = optimal_analysis.get('improvement_pct')
                    timing_point.market_volatility = optimal_analysis.get('volatility')
                    timing_point.volume_ratio = optimal_analysis.get('volume_ratio')
                
                # Grade entry timing
                timing_point.entry_timing_grade = self._grade_entry_timing(
                    timing_point.entry_timing_cost, 
                    timing_point.entry_delay_days
                )
                
                # Store timing analysis
                await self._store_timing_analysis(conn, timing_point)
                
                return timing_point
                
        except Exception as e:
            print(f"Error analyzing timing for {symbol}: {e}")
            return None
        finally:
            if pool:
                await pool.close()
    
    async def _get_position_data(self, conn, symbol: str, position_date: datetime) -> Optional[Dict]:
        """Get position data for timing analysis"""
        query = """
        SELECT symbol, avg_entry_price, quantity, created_at, market_value
        FROM positions
        WHERE symbol = $1 AND created_at <= $2
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        row = await conn.fetchrow(query, symbol, position_date + timedelta(days=1))
        return dict(row) if row else None
    
    async def _get_discovery_data(self, conn, symbol: str, position_date: datetime) -> Optional[Dict]:
        """Get original discovery data for timing analysis"""
        query = """
        SELECT symbol, price, composite_score, created_at, volume
        FROM recommendations
        WHERE symbol = $1 AND created_at <= $2
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        row = await conn.fetchrow(query, symbol, position_date)
        return dict(row) if row else None
    
    async def _get_market_data_for_timing(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[List[Dict]]:
        """Get market data between discovery and entry for timing analysis"""
        if not self.polygon_api_key:
            return None
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get daily data between discovery and entry
                start_str = start_date.strftime('%Y-%m-%d')
                end_str = end_date.strftime('%Y-%m-%d')
                
                url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_str}/{end_str}"
                params = {"apikey": self.polygon_api_key}
                
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return data.get('results', [])
        except Exception as e:
            print(f"Failed to get market data for timing analysis: {e}")
        
        return None
    
    def _calculate_entry_timing_cost(self, discovery_price: float, entry_price: float) -> float:
        """Calculate cost of delayed entry vs discovery price"""
        if discovery_price <= 0:
            return 0.0
        
        # Positive = cost (entered higher than discovery)
        # Negative = benefit (entered lower than discovery)
        return ((entry_price - discovery_price) / discovery_price) * 100
    
    def _analyze_optimal_entry_timing(self, market_data: List[Dict], discovery_data: Dict) -> Dict:
        """Analyze what would have been optimal entry timing"""
        if not market_data:
            return {}
        
        # Find lowest price point (best entry) after discovery
        best_price = min(market_data, key=lambda x: x['l'])  # lowest price
        optimal_price = best_price['l']
        
        # Calculate improvement vs discovery price
        discovery_price = discovery_data['price']
        improvement_pct = ((discovery_price - optimal_price) / discovery_price) * 100 if discovery_price > 0 else 0
        
        # Calculate volatility during period
        prices = [day['c'] for day in market_data]
        volatility = self._calculate_volatility(prices) if len(prices) > 1 else 0.0
        
        # Calculate average volume ratio
        volumes = [day['v'] for day in market_data]
        avg_volume = sum(volumes) / len(volumes)
        discovery_volume = discovery_data.get('volume', avg_volume)
        volume_ratio = avg_volume / discovery_volume if discovery_volume > 0 else 1.0
        
        return {
            'optimal_date': datetime.fromtimestamp(best_price['t'] / 1000),
            'optimal_price': optimal_price,
            'improvement_pct': improvement_pct,
            'volatility': volatility,
            'volume_ratio': volume_ratio
        }
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility"""
        if len(prices) < 2:
            return 0.0
            
        changes = []
        for i in range(1, len(prices)):
            change_pct = abs((prices[i] - prices[i-1]) / prices[i-1]) * 100
            changes.append(change_pct)
            
        return sum(changes) / len(changes) if changes else 0.0
    
    def _grade_entry_timing(self, timing_cost: float, delay_days: int) -> str:
        """Grade entry timing quality"""
        # Excellent: Immediate entry with minimal cost
        if delay_days == 0 and abs(timing_cost) < 2:
            return "excellent"
        
        # Good: Quick entry with low cost
        if delay_days <= 1 and abs(timing_cost) < 5:
            return "good"
        
        # Fair: Reasonable timing
        if delay_days <= 3 and abs(timing_cost) < 10:
            return "fair"
        
        # Poor: Delayed entry or high cost
        if delay_days > 3 or abs(timing_cost) > 10:
            return "poor"
        
        # Terrible: Very delayed with high cost
        if delay_days > 7 and abs(timing_cost) > 15:
            return "terrible"
        
        return "fair"  # Default
    
    async def _store_timing_analysis(self, conn, timing_point: TimingAnalysisPoint):
        """Store timing analysis in database"""
        try:
            query = """
            INSERT INTO market_timing_analysis 
            (symbol, analysis_date, discovery_date, entry_date, entry_delay_days,
             entry_price, discovery_price, entry_timing_cost, optimal_entry_date,
             optimal_entry_price, optimal_entry_improvement, market_volatility,
             volume_ratio, entry_timing_grade)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (symbol, analysis_date) DO UPDATE SET
            entry_timing_cost = EXCLUDED.entry_timing_cost,
            entry_timing_grade = EXCLUDED.entry_timing_grade,
            updated_at = NOW()
            """
            
            await conn.execute(query,
                             timing_point.symbol, timing_point.analysis_date,
                             timing_point.discovery_date, timing_point.entry_date,
                             timing_point.entry_delay_days, timing_point.entry_price,
                             timing_point.discovery_price, timing_point.entry_timing_cost,
                             timing_point.optimal_entry_date, timing_point.optimal_entry_price,
                             timing_point.optimal_entry_improvement, timing_point.market_volatility,
                             timing_point.volume_ratio, timing_point.entry_timing_grade)
                             
        except Exception as e:
            print(f"Error storing timing analysis: {e}")
    
    async def calculate_timing_metrics(self, period_days: int = 30) -> MarketTimingMetrics:
        """Calculate comprehensive timing metrics"""
        pool = await self.get_db_pool()
        if not pool:
            return self._empty_timing_metrics()
            
        try:
            async with pool.acquire() as conn:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=period_days)
                
                # Get all timing analyses for period
                query = """
                SELECT * FROM market_timing_analysis
                WHERE analysis_date >= $1 AND analysis_date <= $2
                ORDER BY analysis_date DESC
                """
                
                analyses = await conn.fetch(query, start_date, end_date)
                
                if not analyses:
                    return self._empty_timing_metrics(start_date, end_date)
                
                metrics = MarketTimingMetrics(
                    period_start=start_date,
                    period_end=end_date,
                    total_positions=len(analyses)
                )
                
                # Calculate entry timing metrics
                entry_delays = [a['entry_delay_days'] for a in analyses if a['entry_delay_days'] is not None]
                entry_costs = [a['entry_timing_cost'] for a in analyses if a['entry_timing_cost'] is not None]
                improvements = [a['optimal_entry_improvement'] for a in analyses if a['optimal_entry_improvement'] is not None]
                
                if entry_delays:
                    metrics.avg_entry_delay_days = statistics.mean(entry_delays)
                
                if entry_costs:
                    metrics.avg_entry_timing_cost = statistics.mean(entry_costs)
                    metrics.total_timing_cost = sum(max(0, cost) for cost in entry_costs)  # Only costs, not benefits
                
                if improvements:
                    metrics.optimal_entry_improvement = statistics.mean(improvements)
                    metrics.potential_improvement = sum(max(0, imp) for imp in improvements)
                
                # Calculate timing grades distribution
                grades = [a['entry_timing_grade'] for a in analyses if a['entry_timing_grade']]
                if grades:
                    total_grades = len(grades)
                    metrics.excellent_timing_rate = (grades.count('excellent') / total_grades) * 100
                    metrics.poor_timing_rate = (grades.count('poor') + grades.count('terrible')) / total_grades * 100
                
                # Analyze market conditions for best/worst timing
                metrics.best_entry_conditions = self._analyze_best_timing_conditions(analyses)
                metrics.worst_entry_conditions = self._analyze_worst_timing_conditions(analyses)
                
                # VIGL comparison
                metrics.vigl_timing_benchmark = self.vigl_baseline['entry_timing_cost']
                metrics.timing_vs_vigl_gap = metrics.avg_entry_timing_cost - metrics.vigl_timing_benchmark
                
                return metrics
                
        except Exception as e:
            print(f"Error calculating timing metrics: {e}")
            return self._empty_timing_metrics()
        finally:
            if pool:
                await pool.close()
    
    def _analyze_best_timing_conditions(self, analyses: List) -> Dict:
        """Analyze market conditions associated with best timing"""
        excellent_timings = [a for a in analyses if a['entry_timing_grade'] == 'excellent']
        
        if not excellent_timings:
            return {}
        
        volatilities = [a['market_volatility'] for a in excellent_timings if a['market_volatility'] is not None]
        volume_ratios = [a['volume_ratio'] for a in excellent_timings if a['volume_ratio'] is not None]
        
        return {
            'avg_volatility': statistics.mean(volatilities) if volatilities else None,
            'avg_volume_ratio': statistics.mean(volume_ratios) if volume_ratios else None,
            'sample_size': len(excellent_timings),
            'characteristics': 'Low volatility, moderate volume' if volatilities and statistics.mean(volatilities) < 5 else 'Variable conditions'
        }
    
    def _analyze_worst_timing_conditions(self, analyses: List) -> Dict:
        """Analyze market conditions associated with worst timing"""
        poor_timings = [a for a in analyses if a['entry_timing_grade'] in ['poor', 'terrible']]
        
        if not poor_timings:
            return {}
        
        volatilities = [a['market_volatility'] for a in poor_timings if a['market_volatility'] is not None]
        volume_ratios = [a['volume_ratio'] for a in poor_timings if a['volume_ratio'] is not None]
        
        return {
            'avg_volatility': statistics.mean(volatilities) if volatilities else None,
            'avg_volume_ratio': statistics.mean(volume_ratios) if volume_ratios else None,
            'sample_size': len(poor_timings),
            'characteristics': 'High volatility, extreme volume' if volatilities and statistics.mean(volatilities) > 10 else 'Variable conditions'
        }
    
    def _empty_timing_metrics(self, start_date: datetime = None, end_date: datetime = None) -> MarketTimingMetrics:
        """Return empty metrics for error cases"""
        end_date = end_date or datetime.utcnow()
        start_date = start_date or (end_date - timedelta(days=30))
        
        return MarketTimingMetrics(
            period_start=start_date,
            period_end=end_date,
            total_positions=0,
            timing_vs_vigl_gap=10.0  # Assume we're worse than VIGL timing
        )
    
    async def batch_analyze_timing(self, period_days: int = 30) -> int:
        """Analyze timing for all positions in period"""
        pool = await self.get_db_pool()
        if not pool:
            return 0
            
        analyzed_count = 0
        
        try:
            async with pool.acquire() as conn:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=period_days)
                
                # Get all positions that don't have timing analysis yet
                query = """
                SELECT DISTINCT p.symbol, p.created_at
                FROM positions p
                LEFT JOIN market_timing_analysis m ON p.symbol = m.symbol 
                WHERE p.created_at >= $1 AND p.created_at <= $2
                AND m.symbol IS NULL
                ORDER BY p.created_at DESC
                """
                
                positions = await conn.fetch(query, start_date, end_date)
                
                # Analyze each position
                for pos in positions:
                    timing_analysis = await self.analyze_position_timing(
                        pos['symbol'], pos['created_at']
                    )
                    if timing_analysis:
                        analyzed_count += 1
                        
                        # Small delay to avoid API rate limits
                        await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"Error in batch timing analysis: {e}")
        finally:
            if pool:
                await pool.close()
                
        return analyzed_count
    
    async def generate_timing_report(self, period_days: int = 30) -> Dict:
        """Generate comprehensive market timing report"""
        
        # Run batch analysis first to ensure current data
        analyzed_count = await self.batch_analyze_timing(period_days)
        
        # Calculate metrics
        metrics = await self.calculate_timing_metrics(period_days)
        
        # Analyze performance vs VIGL baseline
        vigl_gap_analysis = self._analyze_vigl_gap(metrics)
        
        # Generate insights and recommendations
        insights = []
        recommendations = []
        
        # Entry delay analysis
        if metrics.avg_entry_delay_days > 2:
            insights.append(f"Average entry delay of {metrics.avg_entry_delay_days:.1f} days reduces performance")
            recommendations.append("Implement same-day entry system like VIGL approach")
        
        # Entry timing cost analysis
        if metrics.avg_entry_timing_cost > 5:
            insights.append(f"Entry timing costs averaging {metrics.avg_entry_timing_cost:.1f}% per position")
            recommendations.append("Review entry triggers - may be missing optimal windows")
        
        # Timing vs VIGL analysis
        if metrics.timing_vs_vigl_gap > 5:
            insights.append(f"Entry timing {metrics.timing_vs_vigl_gap:.1f}% worse than VIGL baseline")
            recommendations.append("URGENT: Restore immediate entry capability demonstrated by VIGL")
        
        # Excellent timing rate
        if metrics.excellent_timing_rate < 20:
            insights.append(f"Only {metrics.excellent_timing_rate:.1f}% of entries have excellent timing")
            recommendations.append("Target 50%+ excellent timing rate - study VIGL entry patterns")
        
        # Market conditions insights
        if metrics.best_entry_conditions and metrics.worst_entry_conditions:
            best_vol = metrics.best_entry_conditions.get('avg_volatility', 0)
            worst_vol = metrics.worst_entry_conditions.get('avg_volatility', 0)
            
            if best_vol and worst_vol and worst_vol > best_vol * 2:
                insights.append("Best timing occurs in low volatility conditions")
                recommendations.append("Consider volatility filter for entry timing")
        
        return {
            'summary': {
                'period_days': period_days,
                'positions_analyzed': metrics.total_positions,
                'newly_analyzed': analyzed_count,
                'avg_entry_delay': metrics.avg_entry_delay_days,
                'avg_timing_cost': metrics.avg_entry_timing_cost,
                'total_timing_cost': metrics.total_timing_cost,
                'potential_improvement': metrics.potential_improvement,
                'vigl_gap': metrics.timing_vs_vigl_gap,
                'status': self._assess_timing_status(metrics)
            },
            'detailed_metrics': asdict(metrics),
            'vigl_comparison': vigl_gap_analysis,
            'performance_insights': insights,
            'recommendations': recommendations,
            'improvement_opportunities': self._identify_timing_improvements(metrics),
            'next_actions': self._generate_timing_actions(metrics)
        }
    
    def _analyze_vigl_gap(self, metrics: MarketTimingMetrics) -> Dict:
        """Analyze gap between current timing and VIGL baseline"""
        return {
            'vigl_entry_delay': self.vigl_baseline['discovery_to_entry_days'],
            'current_entry_delay': metrics.avg_entry_delay_days,
            'delay_gap_days': metrics.avg_entry_delay_days - self.vigl_baseline['discovery_to_entry_days'],
            'vigl_timing_cost': self.vigl_baseline['entry_timing_cost'],
            'current_timing_cost': metrics.avg_entry_timing_cost,
            'cost_gap_pct': metrics.timing_vs_vigl_gap,
            'vigl_success_factors': [
                'Immediate entry upon discovery',
                'No hesitation or delay',
                'Perfect price execution',
                'High conviction entry'
            ],
            'restoration_priority': 'CRITICAL' if metrics.timing_vs_vigl_gap > 10 else 'HIGH'
        }
    
    def _assess_timing_status(self, metrics: MarketTimingMetrics) -> str:
        """Assess overall timing performance status"""
        if metrics.timing_vs_vigl_gap > 15:
            return 'CRITICAL'
        elif metrics.timing_vs_vigl_gap > 8:
            return 'WARNING'
        elif metrics.excellent_timing_rate > 50:
            return 'EXCELLENT'
        elif metrics.excellent_timing_rate > 30:
            return 'GOOD'
        else:
            return 'FAIR'
    
    def _identify_timing_improvements(self, metrics: MarketTimingMetrics) -> List[Dict]:
        """Identify specific timing improvement opportunities"""
        improvements = []
        
        if metrics.avg_entry_delay_days > 1:
            improvements.append({
                'area': 'Entry Speed',
                'current': f"{metrics.avg_entry_delay_days:.1f} days delay",
                'target': "Same day entry (0 days)",
                'impact': f"{metrics.potential_improvement:.1f}% improvement potential",
                'priority': 'HIGH'
            })
        
        if metrics.poor_timing_rate > 30:
            improvements.append({
                'area': 'Timing Quality',
                'current': f"{metrics.poor_timing_rate:.1f}% poor timing",
                'target': "<20% poor timing rate",
                'impact': 'Reduce timing costs significantly',
                'priority': 'MEDIUM'
            })
        
        if metrics.total_timing_cost > 50:
            improvements.append({
                'area': 'Cost Reduction',
                'current': f"{metrics.total_timing_cost:.1f}% total costs",
                'target': "<20% total timing costs",
                'impact': 'Direct profit improvement',
                'priority': 'HIGH'
            })
        
        return improvements
    
    def _generate_timing_actions(self, metrics: MarketTimingMetrics) -> List[str]:
        """Generate specific next actions for timing improvement"""
        actions = []
        
        if metrics.timing_vs_vigl_gap > 10:
            actions.append("IMMEDIATE: Implement same-day entry system like VIGL")
        
        if metrics.avg_entry_delay_days > 2:
            actions.append("THIS WEEK: Setup automated entry triggers to reduce delays")
        
        if metrics.poor_timing_rate > 40:
            actions.append("URGENT: Review entry decision process - too many poor timing decisions")
        
        actions.append("DAILY: Monitor entry timing vs discovery for new positions")
        actions.append("WEEKLY: Track timing improvement vs VIGL baseline")
        
        return actions

# Database table for market timing analysis
CREATE_MARKET_TIMING_TABLE = """
CREATE TABLE IF NOT EXISTS market_timing_analysis (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    analysis_date TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Entry timing data
    discovery_date TIMESTAMP WITH TIME ZONE NOT NULL,
    entry_date TIMESTAMP WITH TIME ZONE NOT NULL,
    entry_delay_days INTEGER NOT NULL,
    entry_price FLOAT NOT NULL,
    discovery_price FLOAT NOT NULL,
    entry_timing_cost FLOAT NOT NULL,
    
    -- Optimal timing analysis
    optimal_entry_date TIMESTAMP WITH TIME ZONE,
    optimal_entry_price FLOAT,
    optimal_entry_improvement FLOAT,
    
    -- Exit timing data (optional)
    exit_date TIMESTAMP WITH TIME ZONE,
    exit_price FLOAT,
    optimal_exit_date TIMESTAMP WITH TIME ZONE,
    optimal_exit_price FLOAT,
    exit_timing_cost FLOAT,
    
    -- Market context
    market_volatility FLOAT,
    volume_ratio FLOAT,
    sector_momentum VARCHAR(20),
    
    -- Grading
    entry_timing_grade VARCHAR(20),
    exit_timing_grade VARCHAR(20),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(symbol, analysis_date)
);

CREATE INDEX IF NOT EXISTS idx_timing_symbol ON market_timing_analysis(symbol);
CREATE INDEX IF NOT EXISTS idx_timing_analysis_date ON market_timing_analysis(analysis_date);
CREATE INDEX IF NOT EXISTS idx_timing_entry_grade ON market_timing_analysis(entry_timing_grade);
CREATE INDEX IF NOT EXISTS idx_timing_entry_delay ON market_timing_analysis(entry_delay_days);
CREATE INDEX IF NOT EXISTS idx_timing_cost ON market_timing_analysis(entry_timing_cost);
"""
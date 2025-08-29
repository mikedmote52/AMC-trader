import os
import asyncio
import asyncpg
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import json

class PerformanceCategory(Enum):
    EXPLOSIVE_GROWTH = "explosive_growth"  # >50% returns
    STRONG_PERFORMER = "strong_performer"  # 10-50% returns
    MODERATE_PERFORMER = "moderate_performer"  # 0-10% returns
    UNDERPERFORMER = "underperformer"  # -5-0% returns
    POOR_PERFORMER = "poor_performer"  # <-5% returns

@dataclass
class BaselineMetrics:
    """June-July 2024 baseline performance metrics to restore"""
    win_rate: float = 73.0  # 11 of 15 picks profitable
    average_return: float = 63.8  # Average return percentage
    explosive_growth_rate: float = 46.7  # % of picks with >50% returns (7/15)
    total_profit: float = 957.50  # Total profit on $1,500 invested
    max_individual_return: float = 324.0  # VIGL's peak performance
    benchmark_period: str = "June-July 2024"
    
    # Individual star performers
    star_performers: Dict[str, float] = None
    
    def __post_init__(self):
        if self.star_performers is None:
            self.star_performers = {
                "VIGL": 324.0,
                "CRWV": 171.0,
                "AEVA": 162.0
            }

@dataclass
class PerformanceMetrics:
    """Comprehensive performance tracking metrics"""
    # Core Performance Metrics
    discovery_quality_score: float = 0.0  # 0-100 scale
    win_rate: float = 0.0  # Percentage of profitable positions
    average_return: float = 0.0  # Average return across all positions
    explosive_growth_rate: float = 0.0  # % of positions with >50% returns
    risk_adjusted_return: float = 0.0  # Sharpe-like ratio
    thesis_accuracy: float = 0.0  # % of thesis predictions that materialize
    data_quality_score: float = 0.0  # Data accuracy/completeness score
    
    # Advanced Analytics
    market_timing_score: float = 0.0  # Entry/exit timing effectiveness
    position_sizing_effectiveness: float = 0.0  # Risk management quality
    system_health_score: float = 0.0  # Overall system performance
    
    # Comparative Analysis
    market_outperformance: float = 0.0  # vs S&P 500
    benchmark_gap: float = 0.0  # Gap to June-July baseline
    
    # Trend Analysis
    performance_trend: str = "neutral"  # improving, declining, stable
    momentum_score: float = 0.0  # Recent performance momentum
    
    # Metadata
    calculated_at: datetime = None
    period_start: datetime = None
    period_end: datetime = None
    total_positions: int = 0
    
    def __post_init__(self):
        if self.calculated_at is None:
            self.calculated_at = datetime.utcnow()

class PerformanceAnalytics:
    """Comprehensive performance analytics system for AMC-TRADER"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/amc_trader')
        self.baseline = BaselineMetrics()
        
    async def get_db_pool(self):
        """Get database connection pool"""
        try:
            return await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
        except Exception as e:
            print(f"Database connection failed: {e}")
            return None
    
    async def calculate_comprehensive_metrics(self, 
                                            period_days: int = 30,
                                            include_current_positions: bool = True) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics for specified period"""
        
        pool = await self.get_db_pool()
        if not pool:
            return self._fallback_metrics()
            
        try:
            async with pool.acquire() as conn:
                # Get period boundaries
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=period_days)
                
                # Core calculations
                positions_data = await self._get_positions_data(conn, start_date, end_date)
                discovery_metrics = await self._calculate_discovery_metrics(conn, start_date, end_date)
                thesis_metrics = await self._calculate_thesis_accuracy(conn, start_date, end_date)
                timing_metrics = await self._calculate_market_timing(conn, start_date, end_date)
                
                # Build comprehensive metrics
                metrics = PerformanceMetrics(
                    # Core metrics
                    discovery_quality_score=discovery_metrics['quality_score'],
                    win_rate=self._calculate_win_rate(positions_data),
                    average_return=self._calculate_average_return(positions_data),
                    explosive_growth_rate=self._calculate_explosive_growth_rate(positions_data),
                    risk_adjusted_return=self._calculate_risk_adjusted_return(positions_data),
                    thesis_accuracy=thesis_metrics['accuracy_score'],
                    data_quality_score=self._calculate_data_quality_score(positions_data),
                    
                    # Advanced metrics
                    market_timing_score=timing_metrics['timing_score'],
                    position_sizing_effectiveness=self._calculate_position_sizing_effectiveness(positions_data),
                    system_health_score=self._calculate_system_health_score(discovery_metrics, thesis_metrics),
                    
                    # Comparative metrics
                    market_outperformance=await self._calculate_market_outperformance(conn, positions_data),
                    benchmark_gap=self._calculate_benchmark_gap(positions_data),
                    
                    # Trend analysis
                    performance_trend=self._analyze_performance_trend(positions_data),
                    momentum_score=self._calculate_momentum_score(positions_data),
                    
                    # Metadata
                    period_start=start_date,
                    period_end=end_date,
                    total_positions=len(positions_data)
                )
                
                # Store metrics for historical tracking
                await self._store_metrics(conn, metrics)
                
                return metrics
                
        except Exception as e:
            print(f"Error calculating metrics: {e}")
            return self._fallback_metrics()
        finally:
            if pool:
                await pool.close()
    
    async def _get_positions_data(self, conn, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get all position data for the specified period"""
        query = """
        SELECT symbol, unrealized_pl_pct, market_value, last_price, avg_entry_price,
               created_at, updated_at, quantity
        FROM positions 
        WHERE created_at >= $1 AND created_at <= $2
        ORDER BY created_at DESC
        """
        
        try:
            rows = await conn.fetch(query, start_date, end_date)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error fetching positions data: {e}")
            return []
    
    async def _calculate_discovery_metrics(self, conn, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate discovery system performance metrics"""
        query = """
        SELECT symbol, composite_score, sentiment_score, technical_score,
               created_at, price, volume
        FROM recommendations 
        WHERE created_at >= $1 AND created_at <= $2
        ORDER BY composite_score DESC
        """
        
        try:
            recommendations = await conn.fetch(query, start_date, end_date)
            if not recommendations:
                return {'quality_score': 50.0, 'total_candidates': 0}
            
            # Calculate quality metrics
            scores = [row['composite_score'] for row in recommendations if row['composite_score']]
            avg_composite_score = statistics.mean(scores) if scores else 50.0
            
            # Quality score based on composite scores and subsequent performance
            quality_score = min(100.0, max(0.0, avg_composite_score * 10))  # Scale to 0-100
            
            return {
                'quality_score': quality_score,
                'total_candidates': len(recommendations),
                'avg_composite_score': avg_composite_score
            }
            
        except Exception as e:
            print(f"Error calculating discovery metrics: {e}")
            return {'quality_score': 50.0, 'total_candidates': 0}
    
    async def _calculate_thesis_accuracy(self, conn, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate thesis prediction accuracy"""
        # This would compare thesis predictions to actual outcomes
        # For now, return placeholder metrics
        return {
            'accuracy_score': 65.0,  # Placeholder - would calculate actual accuracy
            'total_predictions': 0,
            'correct_predictions': 0
        }
    
    async def _calculate_market_timing(self, conn, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate market entry/exit timing effectiveness"""
        # Analyze entry timing vs optimal entry points
        return {
            'timing_score': 70.0,  # Placeholder - would calculate actual timing effectiveness
            'avg_entry_delay': 0.0,  # Days from optimal entry
            'avg_exit_delay': 0.0   # Days from optimal exit
        }
    
    def _calculate_win_rate(self, positions_data: List[Dict]) -> float:
        """Calculate percentage of profitable positions"""
        if not positions_data:
            return 0.0
            
        profitable = sum(1 for pos in positions_data if pos.get('unrealized_pl_pct', 0) > 0)
        return (profitable / len(positions_data)) * 100
    
    def _calculate_average_return(self, positions_data: List[Dict]) -> float:
        """Calculate average return across all positions"""
        if not positions_data:
            return 0.0
            
        returns = [pos.get('unrealized_pl_pct', 0) for pos in positions_data]
        return statistics.mean(returns)
    
    def _calculate_explosive_growth_rate(self, positions_data: List[Dict]) -> float:
        """Calculate percentage of positions with >50% returns"""
        if not positions_data:
            return 0.0
            
        explosive = sum(1 for pos in positions_data if pos.get('unrealized_pl_pct', 0) > 50)
        return (explosive / len(positions_data)) * 100
    
    def _calculate_risk_adjusted_return(self, positions_data: List[Dict]) -> float:
        """Calculate risk-adjusted return (Sharpe-like ratio)"""
        if not positions_data:
            return 0.0
            
        returns = [pos.get('unrealized_pl_pct', 0) for pos in positions_data]
        if len(returns) < 2:
            return returns[0] if returns else 0.0
            
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        # Risk-free rate approximation (2% annual)
        risk_free_rate = 2.0
        
        if std_return == 0:
            return mean_return
            
        return (mean_return - risk_free_rate) / std_return
    
    def _calculate_data_quality_score(self, positions_data: List[Dict]) -> float:
        """Calculate data quality and completeness score"""
        if not positions_data:
            return 0.0
        
        total_fields = 0
        complete_fields = 0
        
        for pos in positions_data:
            required_fields = ['symbol', 'unrealized_pl_pct', 'market_value', 'last_price']
            for field in required_fields:
                total_fields += 1
                if pos.get(field) is not None:
                    complete_fields += 1
        
        return (complete_fields / total_fields) * 100 if total_fields > 0 else 0.0
    
    def _calculate_position_sizing_effectiveness(self, positions_data: List[Dict]) -> float:
        """Calculate effectiveness of position sizing strategy"""
        if not positions_data:
            return 50.0
            
        # Analyze if position sizes align with performance
        # Larger positions should be in better performers
        position_values = []
        returns = []
        
        for pos in positions_data:
            value = pos.get('market_value', 0)
            return_pct = pos.get('unrealized_pl_pct', 0)
            if value > 0:
                position_values.append(value)
                returns.append(return_pct)
        
        if len(position_values) < 2:
            return 50.0
        
        # Calculate correlation between position size and performance
        # Positive correlation indicates good sizing
        try:
            correlation = statistics.correlation(position_values, returns)
            # Convert correlation (-1 to 1) to score (0 to 100)
            return max(0, min(100, (correlation + 1) * 50))
        except:
            return 50.0
    
    def _calculate_system_health_score(self, discovery_metrics: Dict, thesis_metrics: Dict) -> float:
        """Calculate overall system health score"""
        discovery_score = discovery_metrics.get('quality_score', 50.0)
        thesis_score = thesis_metrics.get('accuracy_score', 50.0)
        
        # Weighted average of component scores
        return (discovery_score * 0.6 + thesis_score * 0.4)
    
    async def _calculate_market_outperformance(self, conn, positions_data: List[Dict]) -> float:
        """Calculate performance vs market benchmark (S&P 500)"""
        # Placeholder - would fetch S&P 500 performance for comparison
        avg_return = self._calculate_average_return(positions_data)
        sp500_return = 8.0  # Placeholder annual S&P 500 return
        
        return avg_return - sp500_return
    
    def _calculate_benchmark_gap(self, positions_data: List[Dict]) -> float:
        """Calculate gap between current performance and June-July baseline"""
        current_avg_return = self._calculate_average_return(positions_data)
        return current_avg_return - self.baseline.average_return
    
    def _analyze_performance_trend(self, positions_data: List[Dict]) -> str:
        """Analyze whether performance is improving, declining, or stable"""
        if not positions_data:
            return "neutral"
            
        # Sort by creation date and analyze trend
        sorted_positions = sorted(positions_data, key=lambda x: x.get('created_at', datetime.min))
        
        if len(sorted_positions) < 3:
            return "neutral"
        
        # Compare first third vs last third performance
        third_size = len(sorted_positions) // 3
        early_returns = [pos.get('unrealized_pl_pct', 0) for pos in sorted_positions[:third_size]]
        recent_returns = [pos.get('unrealized_pl_pct', 0) for pos in sorted_positions[-third_size:]]
        
        if not early_returns or not recent_returns:
            return "neutral"
            
        early_avg = statistics.mean(early_returns)
        recent_avg = statistics.mean(recent_returns)
        
        improvement = recent_avg - early_avg
        
        if improvement > 5:
            return "improving"
        elif improvement < -5:
            return "declining"
        else:
            return "stable"
    
    def _calculate_momentum_score(self, positions_data: List[Dict]) -> float:
        """Calculate recent performance momentum"""
        if not positions_data:
            return 0.0
        
        # Focus on positions created in last 7 days
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        recent_positions = [
            pos for pos in positions_data 
            if pos.get('created_at', datetime.min) > recent_cutoff
        ]
        
        if not recent_positions:
            return 0.0
            
        recent_returns = [pos.get('unrealized_pl_pct', 0) for pos in recent_positions]
        avg_recent_return = statistics.mean(recent_returns)
        
        # Convert to momentum score (0-100 scale)
        return max(0, min(100, avg_recent_return + 50))
    
    async def _store_metrics(self, conn, metrics: PerformanceMetrics):
        """Store calculated metrics in database for historical tracking"""
        try:
            query = """
            INSERT INTO performance_metrics 
            (calculated_at, period_start, period_end, metrics_json)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (calculated_at) DO UPDATE SET
            metrics_json = EXCLUDED.metrics_json
            """
            
            metrics_json = json.dumps(asdict(metrics), default=str)
            
            await conn.execute(query, 
                             metrics.calculated_at,
                             metrics.period_start, 
                             metrics.period_end,
                             metrics_json)
                             
        except Exception as e:
            print(f"Error storing metrics: {e}")
    
    def _fallback_metrics(self) -> PerformanceMetrics:
        """Return fallback metrics when calculation fails"""
        return PerformanceMetrics(
            discovery_quality_score=50.0,
            win_rate=0.0,
            average_return=0.0,
            explosive_growth_rate=0.0,
            risk_adjusted_return=0.0,
            thesis_accuracy=50.0,
            data_quality_score=50.0,
            market_timing_score=50.0,
            position_sizing_effectiveness=50.0,
            system_health_score=50.0,
            market_outperformance=0.0,
            benchmark_gap=-63.8,  # Current gap to baseline
            performance_trend="declining",
            momentum_score=30.0,  # Below neutral indicating issues
            total_positions=0
        )
    
    async def generate_performance_report(self, metrics: PerformanceMetrics) -> Dict:
        """Generate comprehensive performance analysis report"""
        
        # Performance vs baseline analysis
        baseline_comparison = {
            'win_rate_gap': metrics.win_rate - self.baseline.win_rate,
            'return_gap': metrics.average_return - self.baseline.average_return,
            'explosive_growth_gap': metrics.explosive_growth_rate - self.baseline.explosive_growth_rate
        }
        
        # Key findings and recommendations
        findings = []
        recommendations = []
        
        # Win rate analysis
        if baseline_comparison['win_rate_gap'] < -20:
            findings.append(f"Critical: Win rate at {metrics.win_rate:.1f}% vs baseline {self.baseline.win_rate:.1f}%")
            recommendations.append("URGENT: Review discovery algorithm - candidate quality severely degraded")
        elif baseline_comparison['win_rate_gap'] < -10:
            findings.append(f"Warning: Win rate below baseline by {abs(baseline_comparison['win_rate_gap']):.1f}%")
            recommendations.append("Review candidate selection criteria and market conditions")
        
        # Return performance analysis
        if baseline_comparison['return_gap'] < -40:
            findings.append(f"Critical: Average returns {metrics.average_return:.1f}% vs baseline {self.baseline.average_return:.1f}%")
            recommendations.append("URGENT: Analyze thesis generation and position sizing strategy")
        
        # Explosive growth analysis
        if baseline_comparison['explosive_growth_gap'] < -30:
            findings.append(f"Missing explosive growth: {metrics.explosive_growth_rate:.1f}% vs baseline {self.baseline.explosive_growth_rate:.1f}%")
            recommendations.append("Focus on high-momentum candidates with VIGL-like characteristics")
        
        # Data quality issues
        if metrics.data_quality_score < 80:
            findings.append(f"Data quality issues: {metrics.data_quality_score:.1f}% completeness")
            recommendations.append("Audit data pipeline for accuracy and completeness")
        
        # System health assessment
        health_status = "CRITICAL" if metrics.system_health_score < 40 else \
                       "WARNING" if metrics.system_health_score < 60 else \
                       "GOOD" if metrics.system_health_score < 80 else "EXCELLENT"
        
        return {
            'metrics': asdict(metrics),
            'baseline_comparison': baseline_comparison,
            'health_status': health_status,
            'key_findings': findings,
            'recommendations': recommendations,
            'restoration_priority': self._calculate_restoration_priority(metrics),
            'next_actions': self._generate_next_actions(metrics, findings)
        }
    
    def _calculate_restoration_priority(self, metrics: PerformanceMetrics) -> List[Dict]:
        """Calculate priority order for restoring June-July performance"""
        priorities = []
        
        # Priority 1: Discovery Quality (most impactful)
        if metrics.discovery_quality_score < 70:
            priorities.append({
                'priority': 1,
                'area': 'Discovery Algorithm',
                'current_score': metrics.discovery_quality_score,
                'target_score': 85.0,
                'impact': 'HIGH',
                'effort': 'MEDIUM',
                'description': 'Restore VIGL-style candidate identification'
            })
        
        # Priority 2: Thesis Accuracy
        if metrics.thesis_accuracy < 70:
            priorities.append({
                'priority': 2,
                'area': 'Thesis Generation',
                'current_score': metrics.thesis_accuracy,
                'target_score': 80.0,
                'impact': 'HIGH',
                'effort': 'MEDIUM',
                'description': 'Improve prediction accuracy for explosive growth candidates'
            })
        
        # Priority 3: Market Timing
        if metrics.market_timing_score < 70:
            priorities.append({
                'priority': 3,
                'area': 'Market Timing',
                'current_score': metrics.market_timing_score,
                'target_score': 75.0,
                'impact': 'MEDIUM',
                'effort': 'HIGH',
                'description': 'Optimize entry and exit timing'
            })
        
        # Priority 4: Data Quality
        if metrics.data_quality_score < 85:
            priorities.append({
                'priority': 4,
                'area': 'Data Quality',
                'current_score': metrics.data_quality_score,
                'target_score': 95.0,
                'impact': 'MEDIUM',
                'effort': 'LOW',
                'description': 'Ensure accurate, complete market data'
            })
        
        return sorted(priorities, key=lambda x: x['priority'])
    
    def _generate_next_actions(self, metrics: PerformanceMetrics, findings: List[str]) -> List[str]:
        """Generate specific next actions based on performance analysis"""
        actions = []
        
        if metrics.win_rate < 40:
            actions.append("IMMEDIATE: Audit discovery algorithm parameters vs June-July settings")
        
        if metrics.explosive_growth_rate < 20:
            actions.append("IMMEDIATE: Restore VIGL pattern detection with >20x volume threshold")
        
        if metrics.average_return < -10:
            actions.append("IMMEDIATE: Review position sizing - may be overweighting poor performers")
        
        if metrics.data_quality_score < 70:
            actions.append("THIS WEEK: Implement data validation pipeline")
        
        actions.append("ONGOING: Daily tracking of discovery quality vs baseline metrics")
        actions.append("WEEKLY: Performance review against restoration targets")
        
        return actions

# Database table creation for metrics storage
CREATE_PERFORMANCE_METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL UNIQUE,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    metrics_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_calculated_at 
ON performance_metrics(calculated_at);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_period 
ON performance_metrics(period_start, period_end);
"""
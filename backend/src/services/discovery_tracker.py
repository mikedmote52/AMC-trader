import asyncio
import asyncpg
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import statistics

@dataclass
class DiscoveryCandidate:
    """Track individual discovery candidates and their outcomes"""
    symbol: str
    discovered_at: datetime
    composite_score: float
    sentiment_score: float
    technical_score: float
    discovery_price: float
    volume_at_discovery: int
    
    # Performance tracking
    peak_price: Optional[float] = None
    peak_return: Optional[float] = None
    current_price: Optional[float] = None
    current_return: Optional[float] = None
    days_to_peak: Optional[int] = None
    
    # Classification
    outcome_category: Optional[str] = None  # explosive, strong, moderate, poor, failed
    vigl_score: Optional[float] = None  # VIGL pattern match score
    
    # Analysis flags
    was_traded: bool = False
    trade_outcome: Optional[str] = None
    lessons_learned: Optional[str] = None

@dataclass
class DiscoveryBatch:
    """Track performance of discovery batches"""
    batch_date: datetime
    total_candidates: int
    avg_composite_score: float
    
    # Outcome distribution
    explosive_count: int = 0  # >50% return
    strong_count: int = 0     # 10-50% return  
    moderate_count: int = 0   # 0-10% return
    poor_count: int = 0       # -10-0% return
    failed_count: int = 0     # <-10% return
    
    # Quality metrics
    hit_rate: float = 0.0     # % with positive returns
    explosive_rate: float = 0.0  # % with >50% returns
    avg_return: float = 0.0
    best_performer: Optional[str] = None
    worst_performer: Optional[str] = None
    
    # VIGL pattern analysis
    vigl_candidates: int = 0
    vigl_success_rate: float = 0.0

class DiscoveryPerformanceTracker:
    """Comprehensive tracking of discovery system performance"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'postgresql://localhost/amc_trader')
        
    async def get_db_pool(self):
        """Get database connection pool"""
        try:
            return await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
        except Exception as e:
            print(f"Database connection failed: {e}")
            return None
    
    async def track_discovery_batch(self, batch_date: datetime = None) -> DiscoveryBatch:
        """Track performance of a specific discovery batch"""
        if batch_date is None:
            batch_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
        pool = await self.get_db_pool()
        if not pool:
            return self._empty_batch(batch_date)
            
        try:
            async with pool.acquire() as conn:
                # Get all recommendations for this batch
                candidates = await self._get_batch_candidates(conn, batch_date)
                
                if not candidates:
                    return self._empty_batch(batch_date)
                
                # Track performance for each candidate
                tracked_candidates = []
                for candidate in candidates:
                    tracked = await self._track_candidate_performance(conn, candidate)
                    tracked_candidates.append(tracked)
                
                # Analyze batch performance
                batch = await self._analyze_batch_performance(batch_date, tracked_candidates)
                
                # Store batch analysis
                await self._store_batch_analysis(conn, batch)
                
                return batch
                
        except Exception as e:
            print(f"Error tracking discovery batch: {e}")
            return self._empty_batch(batch_date)
        finally:
            if pool:
                await pool.close()
    
    async def _get_batch_candidates(self, conn, batch_date: datetime) -> List[Dict]:
        """Get all candidates discovered on a specific date"""
        start_date = batch_date
        end_date = batch_date + timedelta(days=1)
        
        query = """
        SELECT symbol, composite_score, sentiment_score, technical_score,
               price, volume, created_at
        FROM recommendations 
        WHERE created_at >= $1 AND created_at < $2
        ORDER BY composite_score DESC
        """
        
        rows = await conn.fetch(query, start_date, end_date)
        return [dict(row) for row in rows]
    
    async def _track_candidate_performance(self, conn, candidate_data: Dict) -> DiscoveryCandidate:
        """Track individual candidate performance since discovery"""
        symbol = candidate_data['symbol']
        discovery_date = candidate_data['created_at']
        discovery_price = candidate_data['price']
        
        # Create candidate object
        candidate = DiscoveryCandidate(
            symbol=symbol,
            discovered_at=discovery_date,
            composite_score=candidate_data['composite_score'],
            sentiment_score=candidate_data.get('sentiment_score', 0.0),
            technical_score=candidate_data.get('technical_score', 0.0),
            discovery_price=discovery_price,
            volume_at_discovery=candidate_data.get('volume', 0)
        )
        
        # Get current and peak performance
        performance_data = await self._get_candidate_performance_data(conn, symbol, discovery_date)
        
        if performance_data:
            candidate.current_price = performance_data.get('current_price')
            candidate.peak_price = performance_data.get('peak_price')
            candidate.days_to_peak = performance_data.get('days_to_peak')
            
            # Calculate returns
            if candidate.current_price and discovery_price > 0:
                candidate.current_return = ((candidate.current_price - discovery_price) / discovery_price) * 100
            
            if candidate.peak_price and discovery_price > 0:
                candidate.peak_return = ((candidate.peak_price - discovery_price) / discovery_price) * 100
        
        # Classify outcome
        candidate.outcome_category = self._classify_candidate_outcome(candidate.peak_return or candidate.current_return)
        
        # Calculate VIGL score
        candidate.vigl_score = self._calculate_vigl_score(candidate)
        
        # Check if was traded
        candidate.was_traded = await self._check_if_traded(conn, symbol, discovery_date)
        
        return candidate
    
    async def _get_candidate_performance_data(self, conn, symbol: str, discovery_date: datetime) -> Optional[Dict]:
        """Get performance data for a candidate since discovery"""
        try:
            # Look for current position data
            position_query = """
            SELECT last_price, unrealized_pl_pct, created_at
            FROM positions 
            WHERE symbol = $1 AND created_at >= $2
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            position_row = await conn.fetchrow(position_query, symbol, discovery_date)
            
            if position_row:
                return {
                    'current_price': position_row['last_price'],
                    'peak_price': position_row['last_price'],  # Simplified - would need historical data
                    'days_to_peak': (datetime.utcnow() - discovery_date).days,
                    'current_return': position_row['unrealized_pl_pct']
                }
            
            # If no position, try to get market data (placeholder)
            # In production, this would fetch from market data API
            return None
            
        except Exception as e:
            print(f"Error getting performance data for {symbol}: {e}")
            return None
    
    def _classify_candidate_outcome(self, return_pct: Optional[float]) -> str:
        """Classify candidate outcome based on performance"""
        if return_pct is None:
            return "unknown"
        
        if return_pct > 50:
            return "explosive"  # VIGL-like performance
        elif return_pct > 10:
            return "strong"     # Good performance
        elif return_pct > 0:
            return "moderate"   # Small gains
        elif return_pct > -10:
            return "poor"       # Small losses
        else:
            return "failed"     # Significant losses
    
    def _calculate_vigl_score(self, candidate: DiscoveryCandidate) -> float:
        """Calculate how well candidate matches VIGL pattern characteristics"""
        score = 0.0
        
        # High composite score (VIGL had very high scores)
        if candidate.composite_score > 8.0:
            score += 30
        elif candidate.composite_score > 6.0:
            score += 20
        elif candidate.composite_score > 4.0:
            score += 10
        
        # Volume characteristics (VIGL had massive volume)
        if candidate.volume_at_discovery > 1000000:  # 1M+ volume
            score += 25
        elif candidate.volume_at_discovery > 500000:
            score += 15
        elif candidate.volume_at_discovery > 100000:
            score += 5
        
        # Technical score component
        if candidate.technical_score > 7.0:
            score += 20
        elif candidate.technical_score > 5.0:
            score += 10
        
        # Sentiment component
        if candidate.sentiment_score > 7.0:
            score += 15
        elif candidate.sentiment_score > 5.0:
            score += 10
        
        # Price range (VIGL was in $2.94-$4.66 range)
        if 2.50 <= candidate.discovery_price <= 5.00:
            score += 10
        
        return min(100.0, score)
    
    async def _check_if_traded(self, conn, symbol: str, discovery_date: datetime) -> bool:
        """Check if candidate was actually traded"""
        query = """
        SELECT COUNT(*) 
        FROM positions 
        WHERE symbol = $1 AND created_at >= $2
        """
        
        try:
            count = await conn.fetchval(query, symbol, discovery_date)
            return count > 0
        except:
            return False
    
    async def _analyze_batch_performance(self, batch_date: datetime, candidates: List[DiscoveryCandidate]) -> DiscoveryBatch:
        """Analyze overall batch performance"""
        if not candidates:
            return self._empty_batch(batch_date)
        
        batch = DiscoveryBatch(
            batch_date=batch_date,
            total_candidates=len(candidates),
            avg_composite_score=statistics.mean([c.composite_score for c in candidates])
        )
        
        # Count outcomes
        outcomes = [c.outcome_category for c in candidates if c.outcome_category]
        batch.explosive_count = outcomes.count('explosive')
        batch.strong_count = outcomes.count('strong')
        batch.moderate_count = outcomes.count('moderate') 
        batch.poor_count = outcomes.count('poor')
        batch.failed_count = outcomes.count('failed')
        
        # Calculate rates
        total_with_outcomes = len(outcomes)
        if total_with_outcomes > 0:
            batch.hit_rate = ((batch.explosive_count + batch.strong_count + batch.moderate_count) / total_with_outcomes) * 100
            batch.explosive_rate = (batch.explosive_count / total_with_outcomes) * 100
        
        # Calculate average return
        returns = [c.peak_return or c.current_return for c in candidates if (c.peak_return or c.current_return) is not None]
        if returns:
            batch.avg_return = statistics.mean(returns)
            
            # Find best/worst performers
            best_return = max(returns)
            worst_return = min(returns)
            
            for c in candidates:
                candidate_return = c.peak_return or c.current_return
                if candidate_return == best_return:
                    batch.best_performer = c.symbol
                if candidate_return == worst_return:
                    batch.worst_performer = c.symbol
        
        # VIGL analysis
        vigl_candidates = [c for c in candidates if c.vigl_score and c.vigl_score > 70]
        batch.vigl_candidates = len(vigl_candidates)
        
        if vigl_candidates:
            vigl_successes = len([c for c in vigl_candidates if c.outcome_category in ['explosive', 'strong']])
            batch.vigl_success_rate = (vigl_successes / len(vigl_candidates)) * 100
        
        return batch
    
    async def _store_batch_analysis(self, conn, batch: DiscoveryBatch):
        """Store batch analysis in database"""
        try:
            query = """
            INSERT INTO discovery_batch_analysis 
            (batch_date, analysis_json, created_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (batch_date) DO UPDATE SET
            analysis_json = EXCLUDED.analysis_json,
            updated_at = NOW()
            """
            
            analysis_json = json.dumps(asdict(batch), default=str)
            await conn.execute(query, batch.batch_date, analysis_json)
            
        except Exception as e:
            print(f"Error storing batch analysis: {e}")
    
    def _empty_batch(self, batch_date: datetime) -> DiscoveryBatch:
        """Return empty batch for error cases"""
        return DiscoveryBatch(
            batch_date=batch_date,
            total_candidates=0,
            avg_composite_score=0.0
        )
    
    async def get_discovery_quality_trends(self, days_back: int = 30) -> Dict:
        """Get discovery quality trends over time"""
        pool = await self.get_db_pool()
        if not pool:
            return {}
            
        try:
            async with pool.acquire() as conn:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days_back)
                
                # Get batch analyses
                query = """
                SELECT batch_date, analysis_json
                FROM discovery_batch_analysis
                WHERE batch_date >= $1 AND batch_date <= $2
                ORDER BY batch_date DESC
                """
                
                rows = await conn.fetch(query, start_date, end_date)
                
                if not rows:
                    return {'trend': 'no_data', 'batches': []}
                
                batches = []
                for row in rows:
                    try:
                        batch_data = json.loads(row['analysis_json'])
                        batches.append(batch_data)
                    except:
                        continue
                
                # Analyze trends
                trends = self._analyze_quality_trends(batches)
                
                return {
                    'trend': trends['overall_trend'],
                    'batches': batches,
                    'key_metrics': trends['key_metrics'],
                    'recommendations': trends['recommendations']
                }
                
        except Exception as e:
            print(f"Error getting quality trends: {e}")
            return {}
        finally:
            if pool:
                await pool.close()
    
    def _analyze_quality_trends(self, batches: List[Dict]) -> Dict:
        """Analyze trends in discovery quality"""
        if len(batches) < 3:
            return {
                'overall_trend': 'insufficient_data',
                'key_metrics': {},
                'recommendations': ['Need more data for trend analysis']
            }
        
        # Extract key metrics over time
        hit_rates = [b.get('hit_rate', 0) for b in batches if b.get('hit_rate') is not None]
        explosive_rates = [b.get('explosive_rate', 0) for b in batches if b.get('explosive_rate') is not None]
        avg_scores = [b.get('avg_composite_score', 0) for b in batches if b.get('avg_composite_score') is not None]
        
        # Trend analysis
        trend_indicators = []
        
        if len(hit_rates) >= 3:
            recent_hit_rate = statistics.mean(hit_rates[:3])  # Last 3 batches
            older_hit_rate = statistics.mean(hit_rates[-3:])  # First 3 batches
            hit_rate_trend = recent_hit_rate - older_hit_rate
            trend_indicators.append(hit_rate_trend)
        
        if len(explosive_rates) >= 3:
            recent_explosive = statistics.mean(explosive_rates[:3])
            older_explosive = statistics.mean(explosive_rates[-3:])
            explosive_trend = recent_explosive - older_explosive
            trend_indicators.append(explosive_trend * 2)  # Weight explosive growth more
        
        # Overall trend determination
        if not trend_indicators:
            overall_trend = 'insufficient_data'
        else:
            avg_trend = statistics.mean(trend_indicators)
            if avg_trend > 5:
                overall_trend = 'improving'
            elif avg_trend < -5:
                overall_trend = 'declining'
            else:
                overall_trend = 'stable'
        
        # Key metrics
        key_metrics = {
            'current_hit_rate': hit_rates[0] if hit_rates else 0,
            'current_explosive_rate': explosive_rates[0] if explosive_rates else 0,
            'avg_hit_rate': statistics.mean(hit_rates) if hit_rates else 0,
            'avg_explosive_rate': statistics.mean(explosive_rates) if explosive_rates else 0,
            'best_batch': max(batches, key=lambda x: x.get('hit_rate', 0)) if batches else None
        }
        
        # Recommendations
        recommendations = []
        
        current_hit_rate = key_metrics['current_hit_rate']
        current_explosive_rate = key_metrics['current_explosive_rate']
        
        if current_hit_rate < 50:  # Below 50% hit rate
            recommendations.append("CRITICAL: Hit rate below 50% - review discovery algorithm parameters")
        
        if current_explosive_rate < 10:  # Below 10% explosive growth rate (target: 46.7%)
            recommendations.append("URGENT: No explosive growth candidates - restore VIGL pattern detection")
        
        if overall_trend == 'declining':
            recommendations.append("WARNING: Discovery quality declining - compare current vs June-July parameters")
        
        if not recommendations:
            recommendations.append("Continue monitoring discovery quality metrics")
        
        return {
            'overall_trend': overall_trend,
            'key_metrics': key_metrics,
            'recommendations': recommendations
        }
    
    async def generate_discovery_report(self, days_back: int = 7) -> Dict:
        """Generate comprehensive discovery performance report"""
        
        # Track recent batches
        recent_batches = []
        end_date = datetime.utcnow()
        
        for i in range(days_back):
            batch_date = end_date - timedelta(days=i)
            batch = await self.track_discovery_batch(batch_date)
            recent_batches.append(batch)
        
        # Get trend analysis
        trends = await self.get_discovery_quality_trends(30)
        
        # Calculate summary statistics
        total_candidates = sum(b.total_candidates for b in recent_batches)
        total_explosive = sum(b.explosive_count for b in recent_batches)
        
        # Performance vs baseline
        baseline_explosive_rate = 46.7  # June-July baseline
        current_explosive_rate = (total_explosive / total_candidates * 100) if total_candidates > 0 else 0
        explosive_gap = current_explosive_rate - baseline_explosive_rate
        
        return {
            'summary': {
                'period_days': days_back,
                'total_candidates': total_candidates,
                'explosive_candidates': total_explosive,
                'current_explosive_rate': current_explosive_rate,
                'baseline_explosive_rate': baseline_explosive_rate,
                'explosive_gap': explosive_gap,
                'status': 'CRITICAL' if explosive_gap < -30 else 'WARNING' if explosive_gap < -15 else 'GOOD'
            },
            'recent_batches': [asdict(b) for b in recent_batches],
            'trends': trends,
            'vigl_analysis': self._analyze_vigl_patterns(recent_batches),
            'recommendations': self._generate_discovery_recommendations(recent_batches, explosive_gap)
        }
    
    def _analyze_vigl_patterns(self, batches: List[DiscoveryBatch]) -> Dict:
        """Analyze VIGL pattern detection effectiveness"""
        total_vigl = sum(b.vigl_candidates for b in batches)
        total_candidates = sum(b.total_candidates for b in batches)
        
        vigl_rates = [b.vigl_success_rate for b in batches if b.vigl_success_rate > 0]
        avg_vigl_success = statistics.mean(vigl_rates) if vigl_rates else 0
        
        return {
            'total_vigl_candidates': total_vigl,
            'vigl_detection_rate': (total_vigl / total_candidates * 100) if total_candidates > 0 else 0,
            'avg_vigl_success_rate': avg_vigl_success,
            'target_vigl_rate': 20.0,  # Target 20% of candidates should have high VIGL scores
            'status': 'GOOD' if avg_vigl_success > 70 else 'WARNING' if avg_vigl_success > 50 else 'CRITICAL'
        }
    
    def _generate_discovery_recommendations(self, batches: List[DiscoveryBatch], explosive_gap: float) -> List[str]:
        """Generate specific recommendations for improving discovery performance"""
        recommendations = []
        
        if explosive_gap < -30:
            recommendations.append("IMMEDIATE: Discovery algorithm severely underperforming - restore June-July parameters")
            recommendations.append("URGENT: Review volume threshold - VIGL required 20.9x average volume")
            recommendations.append("URGENT: Check price range filter - focus on $2.94-$4.66 range like VIGL")
        
        total_candidates = sum(b.total_candidates for b in batches)
        if total_candidates < 5 * len(batches):  # Less than 5 candidates per day
            recommendations.append("Increase candidate pool - current discovery rate too low")
        
        avg_composite_score = statistics.mean([b.avg_composite_score for b in batches if b.avg_composite_score > 0])
        if avg_composite_score < 6.0:
            recommendations.append("Raise composite score threshold - successful candidates typically score >6.0")
        
        hit_rates = [b.hit_rate for b in batches if b.hit_rate > 0]
        if hit_rates and statistics.mean(hit_rates) < 60:
            recommendations.append("Review sentiment and technical scoring - hit rate below target")
        
        if not recommendations:
            recommendations.append("Continue current discovery approach - performance within acceptable range")
        
        return recommendations

# Database tables for discovery tracking
CREATE_DISCOVERY_TABLES = """
CREATE TABLE IF NOT EXISTS discovery_batch_analysis (
    id SERIAL PRIMARY KEY,
    batch_date DATE NOT NULL UNIQUE,
    analysis_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS discovery_candidate_tracking (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    discovered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    composite_score FLOAT NOT NULL,
    discovery_price FLOAT NOT NULL,
    peak_price FLOAT,
    peak_return FLOAT,
    current_return FLOAT,
    outcome_category VARCHAR(20),
    vigl_score FLOAT,
    was_traded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, discovered_at)
);

CREATE INDEX IF NOT EXISTS idx_discovery_batch_date ON discovery_batch_analysis(batch_date);
CREATE INDEX IF NOT EXISTS idx_candidate_symbol_date ON discovery_candidate_tracking(symbol, discovered_at);
CREATE INDEX IF NOT EXISTS idx_candidate_outcome ON discovery_candidate_tracking(outcome_category);
CREATE INDEX IF NOT EXISTS idx_candidate_vigl_score ON discovery_candidate_tracking(vigl_score);
"""
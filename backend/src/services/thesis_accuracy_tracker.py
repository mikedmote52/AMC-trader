import asyncio
import asyncpg
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
import json
import statistics
from enum import Enum

class ThesisPrediction(Enum):
    BUY_MORE = "BUY_MORE"
    HOLD = "HOLD"
    TRIM = "TRIM"
    LIQUIDATE = "LIQUIDATE"

class ActualOutcome(Enum):
    EXPLOSIVE_GROWTH = "explosive_growth"    # >50% gains
    STRONG_PERFORMANCE = "strong_performance"  # 10-50% gains
    MODERATE_GAINS = "moderate_gains"        # 0-10% gains
    SIDEWAYS = "sideways"                    # -5% to 5%
    DECLINE = "decline"                      # -15% to -5%
    MAJOR_LOSS = "major_loss"               # <-15%

@dataclass
class ThesisAccuracyRecord:
    """Track accuracy of individual thesis predictions"""
    # Required fields first
    symbol: str
    position_date: datetime
    thesis_generated_at: datetime
    original_thesis: str
    predicted_recommendation: str  # BUY_MORE, HOLD, TRIM, LIQUIDATE
    confidence_score: float
    reasoning: str
    sector: str
    risk_level: str
    market_context: Dict
    initial_price: float
    initial_pl_pct: float
    
    # Optional fields after all required fields
    outcome_measured_at: Optional[datetime] = None
    actual_outcome: Optional[str] = None
    final_pl_pct: Optional[float] = None
    peak_pl_pct: Optional[float] = None
    days_to_peak: Optional[int] = None
    prediction_accuracy: Optional[float] = None  # 0-100 score
    accuracy_category: Optional[str] = None  # excellent, good, fair, poor, wrong
    lessons_learned: Optional[str] = None

@dataclass 
class ThesisAccuracyMetrics:
    """Aggregate thesis accuracy metrics"""
    period_start: datetime
    period_end: datetime
    total_predictions: int
    
    # Overall accuracy
    overall_accuracy: float = 0.0  # 0-100 scale
    accuracy_by_recommendation: Optional[Dict[str, float]] = field(default=None)
    accuracy_by_sector: Optional[Dict[str, float]] = field(default=None)
    accuracy_by_confidence: Optional[Dict[str, float]] = field(default=None)
    
    # Prediction quality
    avg_confidence: float = 0.0
    high_confidence_accuracy: float = 0.0  # Accuracy when confidence >80%
    low_confidence_accuracy: float = 0.0   # Accuracy when confidence <50%
    
    # Performance insights
    best_sector_predictions: Optional[str] = None
    worst_sector_predictions: Optional[str] = None
    most_accurate_recommendation: Optional[str] = None
    least_accurate_recommendation: Optional[str] = None
    
    # Trend analysis
    accuracy_trend: str = "stable"  # improving, declining, stable
    recent_accuracy: float = 0.0
    
    def __post_init__(self):
        if self.accuracy_by_recommendation is None:
            self.accuracy_by_recommendation = {}
        if self.accuracy_by_sector is None:
            self.accuracy_by_sector = {}
        if self.accuracy_by_confidence is None:
            self.accuracy_by_confidence = {}

class ThesisAccuracyTracker:
    """Comprehensive tracking of thesis prediction accuracy"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'postgresql://localhost/amc_trader')
        
        # Define accuracy scoring rules
        self.accuracy_rules = {
            # Rules for scoring prediction accuracy based on recommendation vs outcome
            ('BUY_MORE', 'explosive_growth'): 100,
            ('BUY_MORE', 'strong_performance'): 90,
            ('BUY_MORE', 'moderate_gains'): 80,
            ('BUY_MORE', 'sideways'): 40,
            ('BUY_MORE', 'decline'): 10,
            ('BUY_MORE', 'major_loss'): 0,
            
            ('HOLD', 'explosive_growth'): 70,  # Missed opportunity but not wrong
            ('HOLD', 'strong_performance'): 85,
            ('HOLD', 'moderate_gains'): 95,
            ('HOLD', 'sideways'): 100,
            ('HOLD', 'decline'): 60,
            ('HOLD', 'major_loss'): 20,
            
            ('TRIM', 'explosive_growth'): 30,  # Major missed opportunity
            ('TRIM', 'strong_performance'): 50,
            ('TRIM', 'moderate_gains'): 70,
            ('TRIM', 'sideways'): 85,
            ('TRIM', 'decline'): 95,
            ('TRIM', 'major_loss'): 100,
            
            ('LIQUIDATE', 'explosive_growth'): 0,   # Completely wrong
            ('LIQUIDATE', 'strong_performance'): 10,
            ('LIQUIDATE', 'moderate_gains'): 30,
            ('LIQUIDATE', 'sideways'): 60,
            ('LIQUIDATE', 'decline'): 85,
            ('LIQUIDATE', 'major_loss'): 100,
        }
    
    async def get_db_pool(self):
        """Get database connection pool"""
        try:
            return await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
        except Exception as e:
            print(f"Database connection failed: {e}")
            return None
    
    async def record_thesis_prediction(self, symbol: str, thesis_data: Dict, position_data: Dict):
        """Record a thesis prediction for accuracy tracking"""
        pool = await self.get_db_pool()
        if not pool:
            return
            
        try:
            async with pool.acquire() as conn:
                record = ThesisAccuracyRecord(
                    symbol=symbol,
                    position_date=position_data.get('created_at', datetime.utcnow()),
                    thesis_generated_at=datetime.utcnow(),
                    original_thesis=thesis_data.get('thesis', ''),
                    predicted_recommendation=thesis_data.get('recommendation', 'HOLD'),
                    confidence_score=thesis_data.get('confidence', 0.5),
                    reasoning=thesis_data.get('reasoning', ''),
                    sector=thesis_data.get('sector', 'Unknown'),
                    risk_level=thesis_data.get('risk_level', 'MODERATE'),
                    market_context=thesis_data.get('market_context', {}),
                    initial_price=position_data.get('last_price', 0.0),
                    initial_pl_pct=position_data.get('unrealized_pl_pct', 0.0)
                )
                
                await self._store_thesis_record(conn, record)
                
        except Exception as e:
            print(f"Error recording thesis prediction: {e}")
        finally:
            if pool:
                await pool.close()
    
    async def _store_thesis_record(self, conn, record: ThesisAccuracyRecord):
        """Store thesis record in database"""
        query = """
        INSERT INTO thesis_accuracy_tracking 
        (symbol, position_date, thesis_generated_at, original_thesis, predicted_recommendation,
         confidence_score, reasoning, sector, risk_level, market_context_json, 
         initial_price, initial_pl_pct)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (symbol, position_date) DO UPDATE SET
        thesis_generated_at = EXCLUDED.thesis_generated_at,
        original_thesis = EXCLUDED.original_thesis,
        predicted_recommendation = EXCLUDED.predicted_recommendation,
        confidence_score = EXCLUDED.confidence_score,
        reasoning = EXCLUDED.reasoning,
        updated_at = NOW()
        """
        
        market_context_json = json.dumps(record.market_context)
        
        await conn.execute(query,
                         record.symbol, record.position_date, record.thesis_generated_at,
                         record.original_thesis, record.predicted_recommendation,
                         record.confidence_score, record.reasoning, record.sector,
                         record.risk_level, market_context_json, record.initial_price,
                         record.initial_pl_pct)
    
    async def update_thesis_outcomes(self, evaluation_period_days: int = 30):
        """Update thesis records with actual outcomes for accuracy evaluation"""
        pool = await self.get_db_pool()
        if not pool:
            return 0
            
        updated_count = 0
        
        try:
            async with pool.acquire() as conn:
                # Get thesis records that need outcome evaluation
                cutoff_date = datetime.utcnow() - timedelta(days=evaluation_period_days)
                
                query = """
                SELECT t.*, p.unrealized_pl_pct as current_pl_pct, p.last_price as current_price
                FROM thesis_accuracy_tracking t
                LEFT JOIN positions p ON t.symbol = p.symbol
                WHERE t.thesis_generated_at <= $1 AND t.outcome_measured_at IS NULL
                ORDER BY t.thesis_generated_at ASC
                """
                
                records = await conn.fetch(query, cutoff_date)
                
                for record_row in records:
                    record = self._row_to_thesis_record(record_row)
                    
                    # Determine actual outcome
                    actual_outcome = self._determine_actual_outcome(record, record_row)
                    
                    if actual_outcome:
                        # Calculate prediction accuracy
                        accuracy_score = self._calculate_prediction_accuracy(
                            record.predicted_recommendation, actual_outcome
                        )
                        
                        # Update record with outcomes
                        await self._update_thesis_outcome(conn, record, actual_outcome, accuracy_score)
                        updated_count += 1
                
        except Exception as e:
            print(f"Error updating thesis outcomes: {e}")
        finally:
            if pool:
                await pool.close()
                
        return updated_count
    
    def _row_to_thesis_record(self, row) -> ThesisAccuracyRecord:
        """Convert database row to ThesisAccuracyRecord"""
        return ThesisAccuracyRecord(
            symbol=row['symbol'],
            position_date=row['position_date'],
            thesis_generated_at=row['thesis_generated_at'],
            original_thesis=row['original_thesis'],
            predicted_recommendation=row['predicted_recommendation'],
            confidence_score=row['confidence_score'],
            reasoning=row['reasoning'],
            sector=row['sector'],
            risk_level=row['risk_level'],
            market_context=json.loads(row.get('market_context_json', '{}')),
            initial_price=row['initial_price'],
            initial_pl_pct=row['initial_pl_pct']
        )
    
    def _determine_actual_outcome(self, record: ThesisAccuracyRecord, current_data) -> Optional[str]:
        """Determine actual outcome category based on performance"""
        current_pl_pct = current_data.get('current_pl_pct')
        if current_pl_pct is None:
            return None
        
        # Calculate performance change since thesis generation
        performance_change = current_pl_pct - record.initial_pl_pct
        
        # Categorize outcome
        if performance_change > 50:
            return ActualOutcome.EXPLOSIVE_GROWTH.value
        elif performance_change > 10:
            return ActualOutcome.STRONG_PERFORMANCE.value
        elif performance_change > 0:
            return ActualOutcome.MODERATE_GAINS.value
        elif performance_change > -5:
            return ActualOutcome.SIDEWAYS.value
        elif performance_change > -15:
            return ActualOutcome.DECLINE.value
        else:
            return ActualOutcome.MAJOR_LOSS.value
    
    def _calculate_prediction_accuracy(self, predicted_recommendation: str, actual_outcome: str) -> float:
        """Calculate accuracy score for prediction vs outcome"""
        return self.accuracy_rules.get((predicted_recommendation, actual_outcome), 50.0)
    
    async def _update_thesis_outcome(self, conn, record: ThesisAccuracyRecord, 
                                   actual_outcome: str, accuracy_score: float):
        """Update thesis record with actual outcome and accuracy"""
        
        accuracy_category = self._categorize_accuracy(accuracy_score)
        
        query = """
        UPDATE thesis_accuracy_tracking 
        SET outcome_measured_at = NOW(),
            actual_outcome = $1,
            final_pl_pct = $2,
            prediction_accuracy = $3,
            accuracy_category = $4,
            updated_at = NOW()
        WHERE symbol = $5 AND position_date = $6
        """
        
        await conn.execute(query, actual_outcome, record.initial_pl_pct,
                         accuracy_score, accuracy_category,
                         record.symbol, record.position_date)
    
    def _categorize_accuracy(self, accuracy_score: float) -> str:
        """Categorize accuracy score"""
        if accuracy_score >= 90:
            return "excellent"
        elif accuracy_score >= 75:
            return "good"
        elif accuracy_score >= 60:
            return "fair"
        elif accuracy_score >= 40:
            return "poor"
        else:
            return "wrong"
    
    async def calculate_thesis_accuracy_metrics(self, period_days: int = 30) -> ThesisAccuracyMetrics:
        """Calculate comprehensive thesis accuracy metrics"""
        pool = await self.get_db_pool()
        if not pool:
            return self._empty_metrics()
            
        try:
            async with pool.acquire() as conn:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=period_days)
                
                # Get all thesis records with outcomes in period
                query = """
                SELECT * FROM thesis_accuracy_tracking
                WHERE thesis_generated_at >= $1 AND thesis_generated_at <= $2
                AND prediction_accuracy IS NOT NULL
                ORDER BY thesis_generated_at DESC
                """
                
                records = await conn.fetch(query, start_date, end_date)
                
                if not records:
                    return self._empty_metrics(start_date, end_date)
                
                metrics = ThesisAccuracyMetrics(
                    period_start=start_date,
                    period_end=end_date,
                    total_predictions=len(records)
                )
                
                # Calculate overall accuracy
                accuracy_scores = [r['prediction_accuracy'] for r in records]
                metrics.overall_accuracy = statistics.mean(accuracy_scores)
                
                # Calculate accuracy by recommendation type
                by_recommendation = {}
                for rec_type in ['BUY_MORE', 'HOLD', 'TRIM', 'LIQUIDATE']:
                    rec_records = [r for r in records if r['predicted_recommendation'] == rec_type]
                    if rec_records:
                        by_recommendation[rec_type] = statistics.mean([r['prediction_accuracy'] for r in rec_records])
                
                metrics.accuracy_by_recommendation = by_recommendation
                
                # Calculate accuracy by sector
                by_sector = {}
                sectors = set(r['sector'] for r in records)
                for sector in sectors:
                    sector_records = [r for r in records if r['sector'] == sector]
                    if sector_records:
                        by_sector[sector] = statistics.mean([r['prediction_accuracy'] for r in sector_records])
                
                metrics.accuracy_by_sector = by_sector
                
                # Confidence analysis
                confidence_scores = [r['confidence_score'] for r in records]
                metrics.avg_confidence = statistics.mean(confidence_scores)
                
                high_conf_records = [r for r in records if r['confidence_score'] > 0.8]
                if high_conf_records:
                    metrics.high_confidence_accuracy = statistics.mean([r['prediction_accuracy'] for r in high_conf_records])
                
                low_conf_records = [r for r in records if r['confidence_score'] < 0.5]
                if low_conf_records:
                    metrics.low_confidence_accuracy = statistics.mean([r['prediction_accuracy'] for r in low_conf_records])
                
                # Find best/worst performing categories
                if by_sector:
                    metrics.best_sector_predictions = max(by_sector, key=by_sector.get)
                    metrics.worst_sector_predictions = min(by_sector, key=by_sector.get)
                
                if by_recommendation:
                    metrics.most_accurate_recommendation = max(by_recommendation, key=by_recommendation.get)
                    metrics.least_accurate_recommendation = min(by_recommendation, key=by_recommendation.get)
                
                # Trend analysis
                if len(records) >= 10:
                    recent_records = records[:len(records)//2]  # More recent half
                    older_records = records[len(records)//2:]  # Older half
                    
                    recent_accuracy = statistics.mean([r['prediction_accuracy'] for r in recent_records])
                    older_accuracy = statistics.mean([r['prediction_accuracy'] for r in older_records])
                    
                    metrics.recent_accuracy = recent_accuracy
                    
                    accuracy_change = recent_accuracy - older_accuracy
                    if accuracy_change > 5:
                        metrics.accuracy_trend = "improving"
                    elif accuracy_change < -5:
                        metrics.accuracy_trend = "declining"
                    else:
                        metrics.accuracy_trend = "stable"
                
                return metrics
                
        except Exception as e:
            print(f"Error calculating thesis accuracy metrics: {e}")
            return self._empty_metrics()
        finally:
            if pool:
                await pool.close()
    
    def _empty_metrics(self, start_date: datetime = None, end_date: datetime = None) -> ThesisAccuracyMetrics:
        """Return empty metrics for error cases"""
        end_date = end_date or datetime.utcnow()
        start_date = start_date or (end_date - timedelta(days=30))
        
        return ThesisAccuracyMetrics(
            period_start=start_date,
            period_end=end_date,
            total_predictions=0,
            overall_accuracy=50.0,  # Neutral baseline
            accuracy_trend="insufficient_data"
        )
    
    async def generate_thesis_accuracy_report(self, period_days: int = 30) -> Dict:
        """Generate comprehensive thesis accuracy report"""
        
        # Update outcomes first
        updated_count = await self.update_thesis_outcomes(period_days)
        
        # Calculate metrics
        metrics = await self.calculate_thesis_accuracy_metrics(period_days)
        
        # Analyze performance vs baseline
        baseline_accuracy = 75.0  # Target thesis accuracy
        accuracy_gap = metrics.overall_accuracy - baseline_accuracy
        
        # Generate insights and recommendations
        insights = []
        recommendations = []
        
        # Overall accuracy assessment
        if metrics.overall_accuracy < 50:
            insights.append(f"CRITICAL: Thesis accuracy at {metrics.overall_accuracy:.1f}% - below random chance")
            recommendations.append("URGENT: Complete review of thesis generation algorithm")
        elif metrics.overall_accuracy < 65:
            insights.append(f"WARNING: Thesis accuracy at {metrics.overall_accuracy:.1f}% - below target")
            recommendations.append("Review and retrain thesis generation parameters")
        elif metrics.overall_accuracy > 85:
            insights.append(f"EXCELLENT: Thesis accuracy at {metrics.overall_accuracy:.1f}% - exceeding targets")
            recommendations.append("Document current approach for replication")
        
        # Confidence analysis
        if metrics.high_confidence_accuracy < metrics.overall_accuracy:
            insights.append("High confidence predictions performing worse than average")
            recommendations.append("Recalibrate confidence scoring - overconfident in poor predictions")
        
        # Recommendation type analysis
        if metrics.accuracy_by_recommendation:
            worst_rec = min(metrics.accuracy_by_recommendation, key=metrics.accuracy_by_recommendation.get)
            worst_accuracy = metrics.accuracy_by_recommendation[worst_rec]
            
            if worst_accuracy < 40:
                insights.append(f"{worst_rec} recommendations severely underperforming at {worst_accuracy:.1f}%")
                recommendations.append(f"Review {worst_rec} prediction logic - may be too aggressive/conservative")
        
        # Sector analysis
        if metrics.accuracy_by_sector:
            best_sector = metrics.best_sector_predictions
            worst_sector = metrics.worst_sector_predictions
            
            if worst_sector and metrics.accuracy_by_sector[worst_sector] < 50:
                insights.append(f"{worst_sector} sector predictions failing at {metrics.accuracy_by_sector[worst_sector]:.1f}%")
                recommendations.append(f"Improve {worst_sector} sector analysis - may need specialized approach")
        
        # Trend analysis
        if metrics.accuracy_trend == "declining":
            insights.append("Thesis accuracy declining over time - systematic degradation")
            recommendations.append("Investigate recent changes to thesis generation system")
        
        return {
            'period_summary': {
                'period_days': period_days,
                'total_predictions': metrics.total_predictions,
                'updated_outcomes': updated_count,
                'overall_accuracy': metrics.overall_accuracy,
                'baseline_accuracy': baseline_accuracy,
                'accuracy_gap': accuracy_gap,
                'status': 'CRITICAL' if accuracy_gap < -20 else 'WARNING' if accuracy_gap < -10 else 'GOOD'
            },
            'detailed_metrics': asdict(metrics),
            'performance_insights': insights,
            'recommendations': recommendations,
            'accuracy_breakdown': {
                'by_recommendation': metrics.accuracy_by_recommendation,
                'by_sector': metrics.accuracy_by_sector,
                'by_confidence': {
                    'high_confidence': metrics.high_confidence_accuracy,
                    'low_confidence': metrics.low_confidence_accuracy,
                    'avg_confidence': metrics.avg_confidence
                }
            },
            'improvement_priorities': self._generate_improvement_priorities(metrics)
        }
    
    def _generate_improvement_priorities(self, metrics: ThesisAccuracyMetrics) -> List[Dict]:
        """Generate prioritized improvement recommendations"""
        priorities = []
        
        # Priority 1: Overall accuracy
        if metrics.overall_accuracy < 60:
            priorities.append({
                'priority': 1,
                'area': 'Overall Thesis Quality',
                'current_score': metrics.overall_accuracy,
                'target_score': 75.0,
                'impact': 'CRITICAL',
                'description': 'Fundamental thesis generation needs improvement'
            })
        
        # Priority 2: Confidence calibration
        if (metrics.high_confidence_accuracy > 0 and 
            metrics.high_confidence_accuracy < metrics.overall_accuracy):
            priorities.append({
                'priority': 2,
                'area': 'Confidence Calibration',
                'current_score': metrics.high_confidence_accuracy,
                'target_score': 85.0,
                'impact': 'HIGH',
                'description': 'High confidence predictions should outperform average'
            })
        
        # Priority 3: Recommendation accuracy
        if metrics.accuracy_by_recommendation:
            worst_rec_accuracy = min(metrics.accuracy_by_recommendation.values())
            if worst_rec_accuracy < 50:
                priorities.append({
                    'priority': 3,
                    'area': 'Recommendation Logic',
                    'current_score': worst_rec_accuracy,
                    'target_score': 70.0,
                    'impact': 'HIGH',
                    'description': 'Specific recommendation types underperforming'
                })
        
        return sorted(priorities, key=lambda x: x['priority'])

# Database table for thesis accuracy tracking
CREATE_THESIS_ACCURACY_TABLE = """
CREATE TABLE IF NOT EXISTS thesis_accuracy_tracking (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    position_date TIMESTAMP WITH TIME ZONE NOT NULL,
    thesis_generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Original thesis data
    original_thesis TEXT NOT NULL,
    predicted_recommendation VARCHAR(20) NOT NULL,
    confidence_score FLOAT NOT NULL,
    reasoning TEXT,
    sector VARCHAR(50),
    risk_level VARCHAR(20),
    market_context_json JSONB,
    initial_price FLOAT,
    initial_pl_pct FLOAT,
    
    -- Outcome tracking
    outcome_measured_at TIMESTAMP WITH TIME ZONE,
    actual_outcome VARCHAR(30),
    final_pl_pct FLOAT,
    peak_pl_pct FLOAT,
    days_to_peak INTEGER,
    
    -- Accuracy assessment
    prediction_accuracy FLOAT,
    accuracy_category VARCHAR(20),
    lessons_learned TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(symbol, position_date)
);

CREATE INDEX IF NOT EXISTS idx_thesis_accuracy_symbol ON thesis_accuracy_tracking(symbol);
CREATE INDEX IF NOT EXISTS idx_thesis_accuracy_generated_at ON thesis_accuracy_tracking(thesis_generated_at);
CREATE INDEX IF NOT EXISTS idx_thesis_accuracy_recommendation ON thesis_accuracy_tracking(predicted_recommendation);
CREATE INDEX IF NOT EXISTS idx_thesis_accuracy_sector ON thesis_accuracy_tracking(sector);
CREATE INDEX IF NOT EXISTS idx_thesis_accuracy_score ON thesis_accuracy_tracking(prediction_accuracy);
CREATE INDEX IF NOT EXISTS idx_thesis_accuracy_category ON thesis_accuracy_tracking(accuracy_category);
"""
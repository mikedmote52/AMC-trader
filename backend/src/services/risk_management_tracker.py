import asyncio
import asyncpg
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import statistics
from enum import Enum
import os

class RiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"

class PositionSizeCategory(Enum):
    MICRO = "micro"        # <$500
    SMALL = "small"        # $500-$1000
    MEDIUM = "medium"      # $1000-$2500
    LARGE = "large"        # $2500-$5000
    OVERSIZED = "oversized" # >$5000

@dataclass
class RiskAssessment:
    """Individual position risk assessment"""
    symbol: str
    assessment_date: datetime
    position_date: datetime
    
    # Position sizing risk
    position_value: float
    position_size_category: str
    position_pct_of_portfolio: float
    size_risk_score: float  # 0-100, higher = more risky
    
    # Performance risk
    current_pl_pct: float
    max_drawdown: float
    risk_level: str  # LOW, MODERATE, ELEVATED, HIGH, CRITICAL
    stop_loss_recommended: Optional[float] = None
    
    # Concentration risk
    sector: str
    sector_concentration: float  # % of portfolio in same sector
    correlation_risk: float  # Risk from correlated positions
    
    # Volatility risk
    price_volatility: float
    volume_stability: float
    volatility_risk_score: float
    
    # Thesis risk
    confidence_score: float
    thesis_risk_score: float  # Risk that thesis is wrong
    
    # Overall risk metrics
    composite_risk_score: float  # Combined risk score 0-100
    risk_adjusted_position_score: float  # Position quality adjusted for risk
    
    # Recommendations
    position_action: str  # HOLD, TRIM, ADD, LIQUIDATE
    risk_management_notes: str

@dataclass
class PortfolioRiskMetrics:
    """Portfolio-wide risk metrics"""
    assessment_date: datetime
    total_portfolio_value: float
    
    # Position sizing risk
    avg_position_size: float
    largest_position_pct: float
    oversized_position_count: int
    position_sizing_risk_score: float
    
    # Concentration risk
    sector_concentration_risk: float
    top_sector_pct: float
    symbol_concentration_risk: float
    
    # Performance risk
    total_unrealized_pl_pct: float
    positions_at_risk_count: int  # Positions with >15% loss
    critical_positions_count: int  # Positions with >25% loss
    max_portfolio_drawdown: float
    
    # Volatility risk
    portfolio_volatility_score: float
    high_volatility_positions: int
    
    # Risk capacity
    risk_budget_used: float  # % of risk budget used
    risk_capacity_remaining: float
    
    # VIGL comparison
    vigl_risk_profile: Dict  # VIGL baseline risk metrics
    risk_vs_vigl_gap: float  # How much riskier than VIGL approach
    
    # Overall assessment
    portfolio_risk_grade: str  # A, B, C, D, F
    primary_risk_factors: List[str]
    immediate_actions_needed: List[str]

class RiskManagementTracker:
    """Comprehensive portfolio risk management tracking"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'postgresql://localhost/amc_trader')
        
        # VIGL baseline risk profile (low-risk, high-reward example)
        self.vigl_risk_baseline = {
            'position_size_pct': 10.0,  # 10% of portfolio
            'max_drawdown': -5.0,       # Never went below -5%
            'volatility_score': 30.0,   # Moderate volatility
            'stop_loss_used': False,    # No stop loss needed
            'hold_duration_days': 45,   # Held for 45 days
            'risk_score': 25.0,         # Low risk score
            'reward_ratio': 13.0        # 13:1 reward to risk ratio
        }
        
        # Risk tolerance thresholds
        self.risk_thresholds = {
            'position_size_max': 15.0,      # Max 15% per position
            'sector_concentration_max': 40.0, # Max 40% per sector
            'max_drawdown_warning': -15.0,   # Warning at -15%
            'max_drawdown_critical': -25.0,  # Critical at -25%
            'portfolio_risk_budget': 75.0,   # Max 75% risk budget usage
            'volatility_warning': 60.0       # Warning at 60+ volatility score
        }
    
    async def get_db_pool(self):
        """Get database connection pool"""
        try:
            return await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
        except Exception as e:
            print(f"Database connection failed: {e}")
            return None
    
    async def assess_position_risk(self, symbol: str) -> Optional[RiskAssessment]:
        """Assess risk for individual position"""
        pool = await self.get_db_pool()
        if not pool:
            return None
            
        try:
            async with pool.acquire() as conn:
                # Get current position data
                position_data = await self._get_position_data(conn, symbol)
                if not position_data:
                    return None
                
                # Get portfolio context for risk assessment
                portfolio_context = await self._get_portfolio_context(conn)
                
                # Get thesis data for confidence scoring
                thesis_data = await self._get_thesis_data(conn, symbol)
                
                # Calculate risk assessment
                assessment = await self._calculate_position_risk(
                    position_data, portfolio_context, thesis_data
                )
                
                # Store risk assessment
                await self._store_risk_assessment(conn, assessment)
                
                return assessment
                
        except Exception as e:
            print(f"Error assessing risk for {symbol}: {e}")
            return None
        finally:
            if pool:
                await pool.close()
    
    async def _get_position_data(self, conn, symbol: str) -> Optional[Dict]:
        """Get current position data"""
        query = """
        SELECT symbol, market_value, quantity, avg_entry_price, last_price,
               unrealized_pl_pct, created_at, updated_at
        FROM positions
        WHERE symbol = $1
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        row = await conn.fetchrow(query, symbol)
        return dict(row) if row else None
    
    async def _get_portfolio_context(self, conn) -> Dict:
        """Get portfolio-wide context for risk assessment"""
        # Total portfolio value
        total_value_query = "SELECT SUM(market_value) as total FROM positions"
        total_value = await conn.fetchval(total_value_query) or 0.0
        
        # Sector breakdown
        sector_query = """
        SELECT 
            COALESCE(t.sector, 'Unknown') as sector,
            SUM(p.market_value) as sector_value,
            COUNT(*) as position_count
        FROM positions p
        LEFT JOIN (
            SELECT DISTINCT symbol, sector 
            FROM thesis_accuracy_tracking 
            WHERE sector IS NOT NULL
        ) t ON p.symbol = t.symbol
        GROUP BY COALESCE(t.sector, 'Unknown')
        ORDER BY sector_value DESC
        """
        
        sectors = await conn.fetch(sector_query)
        sector_breakdown = {row['sector']: row['sector_value'] for row in sectors}
        
        # Risk positions count
        risk_positions_query = """
        SELECT COUNT(*) as count
        FROM positions
        WHERE unrealized_pl_pct < -15.0
        """
        risk_count = await conn.fetchval(risk_positions_query) or 0
        
        return {
            'total_portfolio_value': total_value,
            'sector_breakdown': sector_breakdown,
            'positions_at_risk': risk_count,
            'position_count': await conn.fetchval("SELECT COUNT(*) FROM positions") or 0
        }
    
    async def _get_thesis_data(self, conn, symbol: str) -> Optional[Dict]:
        """Get thesis confidence data"""
        query = """
        SELECT confidence_score, predicted_recommendation, risk_level, sector
        FROM thesis_accuracy_tracking
        WHERE symbol = $1
        ORDER BY thesis_generated_at DESC
        LIMIT 1
        """
        
        row = await conn.fetchrow(query, symbol)
        return dict(row) if row else {}
    
    async def _calculate_position_risk(self, position_data: Dict, portfolio_context: Dict, thesis_data: Dict) -> RiskAssessment:
        """Calculate comprehensive position risk assessment"""
        
        symbol = position_data['symbol']
        position_value = position_data['market_value']
        current_pl_pct = position_data['unrealized_pl_pct']
        
        # Position sizing risk
        portfolio_value = portfolio_context['total_portfolio_value']
        position_pct = (position_value / portfolio_value * 100) if portfolio_value > 0 else 0
        
        size_category = self._categorize_position_size(position_value)
        size_risk_score = self._calculate_size_risk_score(position_pct)
        
        # Performance risk
        risk_level = self._assess_performance_risk_level(current_pl_pct)
        max_drawdown = min(0, current_pl_pct)  # Simplified - would track actual max drawdown
        
        # Concentration risk
        sector = thesis_data.get('sector', 'Unknown')
        sector_value = portfolio_context['sector_breakdown'].get(sector, 0)
        sector_concentration = (sector_value / portfolio_value * 100) if portfolio_value > 0 else 0
        correlation_risk = self._calculate_correlation_risk(sector_concentration)
        
        # Volatility risk (simplified calculation)
        volatility_risk_score = self._calculate_volatility_risk(current_pl_pct, max_drawdown)
        
        # Thesis risk
        confidence_score = thesis_data.get('confidence_score', 0.5)
        thesis_risk_score = (1 - confidence_score) * 100  # Lower confidence = higher risk
        
        # Composite risk score
        composite_risk = self._calculate_composite_risk_score(
            size_risk_score, volatility_risk_score, thesis_risk_score, correlation_risk
        )
        
        # Risk-adjusted position score
        position_score = max(0, current_pl_pct + 50)  # Base score adjusted for performance
        risk_adjusted_score = position_score * (100 - composite_risk) / 100
        
        # Generate recommendations
        position_action, risk_notes = self._generate_risk_recommendations(
            current_pl_pct, position_pct, composite_risk, confidence_score
        )
        
        assessment = RiskAssessment(
            symbol=symbol,
            assessment_date=datetime.utcnow(),
            position_date=position_data['created_at'],
            position_value=position_value,
            position_size_category=size_category,
            position_pct_of_portfolio=position_pct,
            size_risk_score=size_risk_score,
            current_pl_pct=current_pl_pct,
            max_drawdown=max_drawdown,
            risk_level=risk_level,
            sector=sector,
            sector_concentration=sector_concentration,
            correlation_risk=correlation_risk,
            price_volatility=0.0,  # Would calculate from market data
            volume_stability=0.0,  # Would calculate from market data
            volatility_risk_score=volatility_risk_score,
            confidence_score=confidence_score,
            thesis_risk_score=thesis_risk_score,
            composite_risk_score=composite_risk,
            risk_adjusted_position_score=risk_adjusted_score,
            position_action=position_action,
            risk_management_notes=risk_notes
        )
        
        # Add stop loss recommendation if needed
        if current_pl_pct < -10:
            assessment.stop_loss_recommended = position_data['last_price'] * 0.95  # 5% below current
        
        return assessment
    
    def _categorize_position_size(self, position_value: float) -> str:
        """Categorize position by size"""
        if position_value < 500:
            return PositionSizeCategory.MICRO.value
        elif position_value < 1000:
            return PositionSizeCategory.SMALL.value
        elif position_value < 2500:
            return PositionSizeCategory.MEDIUM.value
        elif position_value < 5000:
            return PositionSizeCategory.LARGE.value
        else:
            return PositionSizeCategory.OVERSIZED.value
    
    def _calculate_size_risk_score(self, position_pct: float) -> float:
        """Calculate risk score based on position size"""
        if position_pct < 5:
            return 10.0  # Low risk
        elif position_pct < 10:
            return 25.0  # Moderate risk
        elif position_pct < 15:
            return 50.0  # Elevated risk
        elif position_pct < 20:
            return 75.0  # High risk
        else:
            return 100.0  # Critical risk
    
    def _assess_performance_risk_level(self, current_pl_pct: float) -> str:
        """Assess risk level based on current performance"""
        if current_pl_pct > 50:
            return RiskLevel.ELEVATED.value  # High gains can be risky too
        elif current_pl_pct > 10:
            return RiskLevel.LOW.value
        elif current_pl_pct > 0:
            return RiskLevel.MODERATE.value
        elif current_pl_pct > -10:
            return RiskLevel.MODERATE.value
        elif current_pl_pct > -20:
            return RiskLevel.HIGH.value
        else:
            return RiskLevel.CRITICAL.value
    
    def _calculate_correlation_risk(self, sector_concentration: float) -> float:
        """Calculate correlation risk from sector concentration"""
        if sector_concentration < 20:
            return 10.0
        elif sector_concentration < 40:
            return 30.0
        elif sector_concentration < 60:
            return 60.0
        else:
            return 90.0
    
    def _calculate_volatility_risk(self, current_pl_pct: float, max_drawdown: float) -> float:
        """Calculate volatility risk score"""
        # Higher volatility if large swings
        volatility_indicator = abs(current_pl_pct - max_drawdown)
        
        if volatility_indicator < 10:
            return 20.0  # Low volatility
        elif volatility_indicator < 25:
            return 40.0  # Moderate volatility
        elif volatility_indicator < 50:
            return 70.0  # High volatility
        else:
            return 90.0  # Very high volatility
    
    def _calculate_composite_risk_score(self, size_risk: float, volatility_risk: float, 
                                      thesis_risk: float, correlation_risk: float) -> float:
        """Calculate weighted composite risk score"""
        weights = {
            'size': 0.3,
            'volatility': 0.25,
            'thesis': 0.25,
            'correlation': 0.2
        }
        
        composite = (size_risk * weights['size'] + 
                    volatility_risk * weights['volatility'] +
                    thesis_risk * weights['thesis'] +
                    correlation_risk * weights['correlation'])
        
        return min(100.0, max(0.0, composite))
    
    def _generate_risk_recommendations(self, current_pl_pct: float, position_pct: float, 
                                     composite_risk: float, confidence: float) -> Tuple[str, str]:
        """Generate position action and risk management notes"""
        
        # Critical situations first
        if current_pl_pct < -25:
            return "LIQUIDATE", "Critical loss level - preserve remaining capital"
        
        if position_pct > 20:
            return "TRIM", f"Oversized position at {position_pct:.1f}% of portfolio"
        
        if composite_risk > 80:
            return "TRIM", f"High composite risk score ({composite_risk:.0f}) requires reduction"
        
        # Profitable positions with high risk
        if current_pl_pct > 50 and composite_risk > 60:
            return "TRIM", "Lock in profits due to elevated risk profile"
        
        # High confidence, good performance
        if confidence > 0.8 and current_pl_pct > 10:
            return "ADD", "High confidence position performing well"
        
        # Low confidence positions
        if confidence < 0.3:
            return "TRIM", f"Low confidence ({confidence:.1f}) warrants risk reduction"
        
        # Default hold with monitoring
        return "HOLD", f"Risk score {composite_risk:.0f} within acceptable range"
    
    async def _store_risk_assessment(self, conn, assessment: RiskAssessment):
        """Store risk assessment in database"""
        try:
            query = """
            INSERT INTO risk_assessments 
            (symbol, assessment_date, position_date, position_value, position_size_category,
             position_pct_of_portfolio, size_risk_score, current_pl_pct, max_drawdown,
             risk_level, sector, sector_concentration, correlation_risk, 
             volatility_risk_score, confidence_score, thesis_risk_score,
             composite_risk_score, risk_adjusted_position_score, position_action,
             risk_management_notes, stop_loss_recommended)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
            ON CONFLICT (symbol, assessment_date) DO UPDATE SET
            composite_risk_score = EXCLUDED.composite_risk_score,
            position_action = EXCLUDED.position_action,
            risk_management_notes = EXCLUDED.risk_management_notes,
            updated_at = NOW()
            """
            
            await conn.execute(query,
                             assessment.symbol, assessment.assessment_date,
                             assessment.position_date, assessment.position_value,
                             assessment.position_size_category, assessment.position_pct_of_portfolio,
                             assessment.size_risk_score, assessment.current_pl_pct,
                             assessment.max_drawdown, assessment.risk_level,
                             assessment.sector, assessment.sector_concentration,
                             assessment.correlation_risk, assessment.volatility_risk_score,
                             assessment.confidence_score, assessment.thesis_risk_score,
                             assessment.composite_risk_score, assessment.risk_adjusted_position_score,
                             assessment.position_action, assessment.risk_management_notes,
                             assessment.stop_loss_recommended)
                             
        except Exception as e:
            print(f"Error storing risk assessment: {e}")
    
    async def calculate_portfolio_risk_metrics(self) -> PortfolioRiskMetrics:
        """Calculate comprehensive portfolio-wide risk metrics"""
        pool = await self.get_db_pool()
        if not pool:
            return self._empty_portfolio_metrics()
            
        try:
            async with pool.acquire() as conn:
                # Get all current risk assessments
                assessments = await self._get_current_risk_assessments(conn)
                
                # Get portfolio totals
                portfolio_context = await self._get_portfolio_context(conn)
                
                metrics = PortfolioRiskMetrics(
                    assessment_date=datetime.utcnow(),
                    total_portfolio_value=portfolio_context['total_portfolio_value']
                )
                
                if not assessments:
                    return metrics
                
                # Position sizing metrics
                position_values = [a['position_value'] for a in assessments]
                position_pcts = [a['position_pct_of_portfolio'] for a in assessments]
                
                metrics.avg_position_size = statistics.mean(position_values)
                metrics.largest_position_pct = max(position_pcts) if position_pcts else 0
                metrics.oversized_position_count = len([p for p in position_pcts if p > 15])
                
                # Calculate position sizing risk score
                oversized_risk = (metrics.oversized_position_count / len(assessments)) * 100
                size_concentration_risk = max(0, metrics.largest_position_pct - 10) * 5  # Penalty for >10%
                metrics.position_sizing_risk_score = min(100, oversized_risk + size_concentration_risk)
                
                # Concentration risk
                sector_values = {}
                for a in assessments:
                    sector = a['sector']
                    if sector not in sector_values:
                        sector_values[sector] = 0
                    sector_values[sector] += a['position_value']
                
                if sector_values:
                    top_sector_value = max(sector_values.values())
                    metrics.top_sector_pct = (top_sector_value / metrics.total_portfolio_value) * 100
                    metrics.sector_concentration_risk = max(0, metrics.top_sector_pct - 30) * 2  # Penalty for >30%
                
                # Performance risk
                pl_pcts = [a['current_pl_pct'] for a in assessments]
                metrics.total_unrealized_pl_pct = sum(pl_pcts) / len(pl_pcts) if pl_pcts else 0
                metrics.positions_at_risk_count = len([p for p in pl_pcts if p < -15])
                metrics.critical_positions_count = len([p for p in pl_pcts if p < -25])
                metrics.max_portfolio_drawdown = min(pl_pcts) if pl_pcts else 0
                
                # Volatility risk
                volatility_scores = [a['volatility_risk_score'] for a in assessments]
                metrics.portfolio_volatility_score = statistics.mean(volatility_scores) if volatility_scores else 0
                metrics.high_volatility_positions = len([v for v in volatility_scores if v > 70])
                
                # Risk budget calculation
                risk_scores = [a['composite_risk_score'] for a in assessments]
                weighted_risk = sum(score * (pct/100) for score, pct in zip(risk_scores, position_pcts))
                metrics.risk_budget_used = min(100, weighted_risk)
                metrics.risk_capacity_remaining = max(0, 100 - metrics.risk_budget_used)
                
                # VIGL comparison
                metrics.vigl_risk_profile = self.vigl_risk_baseline
                avg_position_risk = statistics.mean(risk_scores) if risk_scores else 50
                metrics.risk_vs_vigl_gap = avg_position_risk - self.vigl_risk_baseline['risk_score']
                
                # Overall grading and actions
                metrics.portfolio_risk_grade = self._grade_portfolio_risk(metrics)
                metrics.primary_risk_factors = self._identify_primary_risks(metrics)
                metrics.immediate_actions_needed = self._generate_immediate_actions(metrics)
                
                return metrics
                
        except Exception as e:
            print(f"Error calculating portfolio risk metrics: {e}")
            return self._empty_portfolio_metrics()
        finally:
            if pool:
                await pool.close()
    
    async def _get_current_risk_assessments(self, conn) -> List[Dict]:
        """Get latest risk assessments for all positions"""
        query = """
        SELECT DISTINCT ON (symbol) *
        FROM risk_assessments
        ORDER BY symbol, assessment_date DESC
        """
        
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    
    def _grade_portfolio_risk(self, metrics: PortfolioRiskMetrics) -> str:
        """Grade overall portfolio risk"""
        risk_factors = 0
        
        if metrics.critical_positions_count > 0:
            risk_factors += 3
        if metrics.positions_at_risk_count > 2:
            risk_factors += 2
        if metrics.oversized_position_count > 1:
            risk_factors += 2
        if metrics.sector_concentration_risk > 50:
            risk_factors += 2
        if metrics.risk_budget_used > 80:
            risk_factors += 1
        
        if risk_factors >= 6:
            return "F"  # Failing - critical risk
        elif risk_factors >= 4:
            return "D"  # Poor risk management
        elif risk_factors >= 2:
            return "C"  # Acceptable but concerning
        elif risk_factors >= 1:
            return "B"  # Good risk management
        else:
            return "A"  # Excellent risk management
    
    def _identify_primary_risks(self, metrics: PortfolioRiskMetrics) -> List[str]:
        """Identify primary risk factors"""
        risks = []
        
        if metrics.critical_positions_count > 0:
            risks.append(f"Critical losses: {metrics.critical_positions_count} positions <-25%")
        
        if metrics.oversized_position_count > 1:
            risks.append(f"Position concentration: {metrics.oversized_position_count} oversized positions")
        
        if metrics.sector_concentration_risk > 50:
            risks.append(f"Sector concentration: {metrics.top_sector_pct:.1f}% in top sector")
        
        if metrics.risk_budget_used > 80:
            risks.append(f"Risk budget overused: {metrics.risk_budget_used:.1f}% of capacity")
        
        if metrics.portfolio_volatility_score > 70:
            risks.append(f"High volatility: {metrics.high_volatility_positions} volatile positions")
        
        return risks
    
    def _generate_immediate_actions(self, metrics: PortfolioRiskMetrics) -> List[str]:
        """Generate immediate action items"""
        actions = []
        
        if metrics.critical_positions_count > 0:
            actions.append("URGENT: Liquidate critical loss positions to preserve capital")
        
        if metrics.oversized_position_count > 1:
            actions.append("IMMEDIATE: Trim oversized positions to reduce concentration risk")
        
        if metrics.sector_concentration_risk > 60:
            actions.append("THIS WEEK: Diversify sector allocation - too concentrated")
        
        if metrics.risk_budget_used > 90:
            actions.append("IMMEDIATE: Stop new positions - risk budget exceeded")
        
        if not actions:
            actions.append("Continue monitoring - risk levels acceptable")
        
        return actions
    
    def _empty_portfolio_metrics(self) -> PortfolioRiskMetrics:
        """Return empty portfolio metrics"""
        return PortfolioRiskMetrics(
            assessment_date=datetime.utcnow(),
            total_portfolio_value=0.0,
            vigl_risk_profile=self.vigl_risk_baseline,
            portfolio_risk_grade="C",
            primary_risk_factors=["Insufficient data for analysis"],
            immediate_actions_needed=["Collect position data for risk assessment"]
        )
    
    async def generate_risk_management_report(self) -> Dict:
        """Generate comprehensive risk management report"""
        
        # Get all current positions and assess their risk
        pool = await self.get_db_pool()
        if not pool:
            return {'error': 'Database connection failed'}
        
        position_assessments = []
        
        try:
            async with pool.acquire() as conn:
                # Get all current positions
                positions = await conn.fetch("SELECT DISTINCT symbol FROM positions")
                
                # Assess risk for each position
                for pos in positions:
                    assessment = await self.assess_position_risk(pos['symbol'])
                    if assessment:
                        position_assessments.append(assessment)
        except Exception as e:
            print(f"Error in risk report generation: {e}")
        finally:
            if pool:
                await pool.close()
        
        # Calculate portfolio metrics
        portfolio_metrics = await self.calculate_portfolio_risk_metrics()
        
        # Analyze vs VIGL baseline
        vigl_comparison = self._analyze_vigl_risk_comparison(portfolio_metrics, position_assessments)
        
        # Generate insights and recommendations
        insights = []
        recommendations = []
        
        # Portfolio-level insights
        if portfolio_metrics.portfolio_risk_grade in ['D', 'F']:
            insights.append(f"CRITICAL: Portfolio risk grade {portfolio_metrics.portfolio_risk_grade}")
            recommendations.append("IMMEDIATE: Implement emergency risk reduction measures")
        
        if portfolio_metrics.critical_positions_count > 0:
            insights.append(f"{portfolio_metrics.critical_positions_count} positions in critical loss territory")
            recommendations.append("Liquidate critical positions to stop bleeding")
        
        if portfolio_metrics.risk_vs_vigl_gap > 30:
            insights.append(f"Risk profile {portfolio_metrics.risk_vs_vigl_gap:.0f} points higher than VIGL baseline")
            recommendations.append("URGENT: Adopt VIGL-style risk management approach")
        
        # Position-level insights
        high_risk_positions = [p for p in position_assessments if p.composite_risk_score > 70]
        if high_risk_positions:
            insights.append(f"{len(high_risk_positions)} positions have high risk scores")
            recommendations.append("Review and trim high-risk positions")
        
        return {
            'executive_summary': {
                'portfolio_risk_grade': portfolio_metrics.portfolio_risk_grade,
                'total_positions': len(position_assessments),
                'critical_positions': portfolio_metrics.critical_positions_count,
                'risk_budget_used': portfolio_metrics.risk_budget_used,
                'vigl_risk_gap': portfolio_metrics.risk_vs_vigl_gap,
                'immediate_action_required': len(portfolio_metrics.immediate_actions_needed) > 1
            },
            'portfolio_metrics': asdict(portfolio_metrics),
            'position_assessments': [asdict(p) for p in position_assessments],
            'vigl_comparison': vigl_comparison,
            'risk_insights': insights,
            'recommendations': recommendations,
            'action_priorities': self._prioritize_risk_actions(portfolio_metrics, position_assessments)
        }
    
    def _analyze_vigl_risk_comparison(self, portfolio_metrics: PortfolioRiskMetrics, 
                                    position_assessments: List[RiskAssessment]) -> Dict:
        """Compare current risk profile to VIGL baseline"""
        
        current_profile = {
            'avg_position_risk': statistics.mean([p.composite_risk_score for p in position_assessments]) if position_assessments else 50,
            'largest_position_pct': portfolio_metrics.largest_position_pct,
            'max_drawdown': portfolio_metrics.max_portfolio_drawdown,
            'positions_at_risk_rate': (portfolio_metrics.positions_at_risk_count / len(position_assessments)) * 100 if position_assessments else 0
        }
        
        return {
            'vigl_baseline': self.vigl_risk_baseline,
            'current_profile': current_profile,
            'risk_gaps': {
                'position_risk': current_profile['avg_position_risk'] - self.vigl_risk_baseline['risk_score'],
                'position_size': current_profile['largest_position_pct'] - self.vigl_risk_baseline['position_size_pct'],
                'drawdown': current_profile['max_drawdown'] - self.vigl_risk_baseline['max_drawdown']
            },
            'vigl_success_factors': [
                'Conservative position sizing (10% max)',
                'Low volatility tolerance',
                'Quick profit taking on large gains',
                'No emotional holding of losers',
                'High conviction, low risk entries'
            ]
        }
    
    def _prioritize_risk_actions(self, portfolio_metrics: PortfolioRiskMetrics, 
                                position_assessments: List[RiskAssessment]) -> List[Dict]:
        """Prioritize risk management actions"""
        priorities = []
        
        # Priority 1: Critical losses
        if portfolio_metrics.critical_positions_count > 0:
            priorities.append({
                'priority': 1,
                'action': 'Liquidate Critical Positions',
                'urgency': 'IMMEDIATE',
                'impact': 'Prevent further capital destruction',
                'positions_affected': portfolio_metrics.critical_positions_count
            })
        
        # Priority 2: Oversized positions
        if portfolio_metrics.oversized_position_count > 0:
            priorities.append({
                'priority': 2,
                'action': 'Trim Oversized Positions',
                'urgency': 'THIS WEEK',
                'impact': 'Reduce concentration risk',
                'positions_affected': portfolio_metrics.oversized_position_count
            })
        
        # Priority 3: Sector concentration
        if portfolio_metrics.sector_concentration_risk > 50:
            priorities.append({
                'priority': 3,
                'action': 'Diversify Sector Allocation',
                'urgency': 'THIS MONTH',
                'impact': 'Reduce correlation risk',
                'target': f"Reduce top sector from {portfolio_metrics.top_sector_pct:.1f}% to <30%"
            })
        
        # Priority 4: Risk budget management
        if portfolio_metrics.risk_budget_used > 80:
            priorities.append({
                'priority': 4,
                'action': 'Manage Risk Budget',
                'urgency': 'ONGOING',
                'impact': 'Maintain risk capacity',
                'target': f"Reduce usage from {portfolio_metrics.risk_budget_used:.1f}% to <75%"
            })
        
        return priorities

# Database table for risk assessments
CREATE_RISK_TABLES = """
CREATE TABLE IF NOT EXISTS risk_assessments (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    assessment_date DATE NOT NULL,
    position_date TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Position sizing risk
    position_value FLOAT NOT NULL,
    position_size_category VARCHAR(20),
    position_pct_of_portfolio FLOAT,
    size_risk_score FLOAT,
    
    -- Performance risk  
    current_pl_pct FLOAT,
    max_drawdown FLOAT,
    risk_level VARCHAR(20),
    stop_loss_recommended FLOAT,
    
    -- Concentration risk
    sector VARCHAR(50),
    sector_concentration FLOAT,
    correlation_risk FLOAT,
    
    -- Volatility risk
    price_volatility FLOAT,
    volume_stability FLOAT,
    volatility_risk_score FLOAT,
    
    -- Thesis risk
    confidence_score FLOAT,
    thesis_risk_score FLOAT,
    
    -- Overall assessment
    composite_risk_score FLOAT,
    risk_adjusted_position_score FLOAT,
    position_action VARCHAR(20),
    risk_management_notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(symbol, assessment_date)
);

CREATE INDEX IF NOT EXISTS idx_risk_symbol ON risk_assessments(symbol);
CREATE INDEX IF NOT EXISTS idx_risk_assessment_date ON risk_assessments(assessment_date);
CREATE INDEX IF NOT EXISTS idx_risk_composite_score ON risk_assessments(composite_risk_score);
CREATE INDEX IF NOT EXISTS idx_risk_action ON risk_assessments(position_action);
CREATE INDEX IF NOT EXISTS idx_risk_level ON risk_assessments(risk_level);
"""
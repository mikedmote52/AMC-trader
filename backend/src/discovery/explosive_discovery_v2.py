#!/usr/bin/env python3
"""
Explosive Growth Discovery System V2 - Polygon MCP Implementation
Focus: Find explosive growth stocks using only available Polygon data
Strategy: Volume surge + Price momentum + News catalysts
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal
import statistics
import math

logger = logging.getLogger(__name__)

@dataclass
class ExplosiveCandidate:
    """Explosive growth candidate with focused metrics"""
    symbol: str
    score: float
    confidence: float
    action_tag: str  # "explosive", "momentum", "watch", "skip"

    # Core explosive indicators
    price_change_pct: float
    volume_surge_ratio: float
    momentum_acceleration: float
    news_catalyst_score: float
    technical_breakout_score: float

    # Risk assessment
    volatility_risk: str  # "low", "medium", "high", "extreme"
    liquidity_score: float
    market_cap_category: str  # "micro", "small", "mid", "large"

    # Supporting data
    current_price: float
    volume: int
    market_cap: Optional[float]
    avg_volume_30d: float
    news_count_24h: int

class ExplosiveDiscoveryEngine:
    """
    Explosive Growth Discovery Engine using Polygon MCP
    Focuses on finding stocks with parabolic potential
    """

    def __init__(self):
        # Detection thresholds for explosive moves
        self.EXPLOSIVE_THRESHOLDS = {
            # Volume surge detection
            'min_volume_surge': 3.0,      # 3x average volume minimum
            'extreme_volume_surge': 10.0,  # 10x = extreme signal

            # Price momentum thresholds
            'min_price_change': 8.0,       # 8% minimum daily move
            'strong_price_change': 15.0,   # 15% = strong signal
            'explosive_price_change': 25.0, # 25% = explosive signal

            # Momentum acceleration (3-day trend)
            'min_acceleration': 0.5,       # Positive acceleration required
            'strong_acceleration': 2.0,    # Strong acceleration

            # News catalyst requirements
            'min_news_score': 30.0,        # Minimum catalyst score
            'strong_news_score': 60.0,     # Strong catalyst score

            # Liquidity filters
            'min_dollar_volume': 1_000_000,  # $1M minimum daily volume
            'min_avg_volume': 100_000,       # 100K average volume

            # Price range filters
            'min_price': 0.50,             # No penny stocks below $0.50
            'max_price': 500.00,           # Avoid expensive stocks > $500
        }

        # Scoring weights for final score calculation
        self.SCORING_WEIGHTS = {
            'volume_surge': 0.35,      # Volume surge is primary signal
            'price_momentum': 0.25,    # Price momentum second
            'momentum_acceleration': 0.20, # Acceleration trend
            'news_catalyst': 0.15,     # News catalyst support
            'technical_breakout': 0.05 # Technical confirmation
        }

    async def discover_explosive_candidates(self, limit: int = 50) -> Dict[str, Any]:
        """
        Main discovery method - find explosive growth candidates
        """
        try:
            start_time = datetime.now()
            logger.info(f"🚀 Starting explosive discovery scan for {limit} candidates")

            # Step 1: Get market universe with volume pre-filtering
            universe = await self._get_filtered_universe()
            logger.info(f"📊 Screened {len(universe)} stocks from market universe")

            # Step 2: Calculate explosive indicators for each stock
            candidates = []
            for ticker_data in universe:
                try:
                    candidate = await self._analyze_explosive_potential(ticker_data)
                    if candidate:
                        candidates.append(candidate)
                except Exception as e:
                    logger.warning(f"Failed to analyze {ticker_data.get('symbol', 'UNKNOWN')}: {e}")
                    continue

            # Step 3: Rank by explosive score and apply final filters
            candidates.sort(key=lambda x: x.score, reverse=True)

            # Step 4: Apply final explosive screening
            explosive_candidates = self._apply_explosive_filters(candidates)

            # Step 5: Limit results and categorize
            final_candidates = explosive_candidates[:limit]

            # Step 6: Convert to API format
            api_candidates = [self._to_api_format(c) for c in final_candidates]

            execution_time = (datetime.now() - start_time).total_seconds()

            result = {
                'status': 'success',
                'count': len(api_candidates),
                'candidates': api_candidates,
                'execution_time_sec': execution_time,
                'pipeline_stats': {
                    'universe_size': len(universe),
                    'analyzed': len(candidates),
                    'explosive_filtered': len(explosive_candidates),
                    'final_count': len(final_candidates)
                },
                'strategy': 'explosive_growth_v2',
                'engine': 'Polygon MCP Explosive Discovery'
            }

            logger.info(f"✅ Explosive discovery completed in {execution_time:.2f}s")
            logger.info(f"📈 Found {len(final_candidates)} explosive candidates")

            return result

        except Exception as e:
            logger.error(f"❌ Explosive discovery failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'count': 0,
                'candidates': []
            }

    async def _get_filtered_universe(self) -> List[Dict[str, Any]]:
        """
        Get market universe with initial volume/price filtering
        Uses Polygon snapshot data for efficient pre-screening
        """
        try:
            # Use MCP functions directly - these should be available in Claude Code environment
            try:
                # Try to call MCP function directly
                snapshot_data = await mcp__polygon__get_snapshot_all(
                    market_type='stocks',
                    include_otc=False
                )
            except NameError:
                # Fallback: try importing from global scope
                import builtins
                if hasattr(builtins, 'mcp__polygon__get_snapshot_all'):
                    snapshot_data = await builtins.mcp__polygon__get_snapshot_all(
                        market_type='stocks',
                        include_otc=False
                    )
                else:
                    raise Exception("MCP function mcp__polygon__get_snapshot_all not available")

            if not snapshot_data.get('tickers'):
                logger.warning("No market snapshot data available")
                return []

            filtered_universe = []

            for ticker in snapshot_data['tickers']:
                symbol = ticker.get('ticker', '')

                # Extract current day data
                day_data = ticker.get('day', {})
                current_price = day_data.get('c', 0)
                volume = day_data.get('v', 0)

                # Extract previous day for comparison
                prev_day = ticker.get('prevDay', {})
                prev_close = prev_day.get('c', 0)
                prev_volume = prev_day.get('v', 0)

                # Apply basic filters
                if not self._passes_basic_filters(symbol, current_price, volume, prev_volume):
                    continue

                # Calculate preliminary indicators
                price_change_pct = 0
                volume_ratio = 1.0

                if prev_close > 0:
                    price_change_pct = ((current_price - prev_close) / prev_close) * 100

                if prev_volume > 0:
                    volume_ratio = volume / prev_volume

                # Pre-filter for potential explosive moves
                if (abs(price_change_pct) >= self.EXPLOSIVE_THRESHOLDS['min_price_change'] or
                    volume_ratio >= self.EXPLOSIVE_THRESHOLDS['min_volume_surge']):

                    filtered_universe.append({
                        'symbol': symbol,
                        'current_price': current_price,
                        'volume': volume,
                        'price_change_pct': price_change_pct,
                        'volume_ratio': volume_ratio,
                        'day_data': day_data,
                        'prev_day': prev_day,
                        'snapshot': ticker
                    })

            logger.info(f"Pre-filtered {len(filtered_universe)} potential explosive candidates")
            return filtered_universe

        except Exception as e:
            logger.error(f"Failed to get filtered universe: {e}")
            return []

    def _passes_basic_filters(self, symbol: str, price: float, volume: int, prev_volume: int) -> bool:
        """Apply basic filtering criteria"""

        # Price range filter
        if not (self.EXPLOSIVE_THRESHOLDS['min_price'] <= price <= self.EXPLOSIVE_THRESHOLDS['max_price']):
            return False

        # Volume filter
        dollar_volume = price * volume
        if dollar_volume < self.EXPLOSIVE_THRESHOLDS['min_dollar_volume']:
            return False

        # Average volume estimate (using previous day as proxy)
        avg_volume_estimate = max(prev_volume, volume) * 0.8  # Conservative estimate
        if avg_volume_estimate < self.EXPLOSIVE_THRESHOLDS['min_avg_volume']:
            return False

        # Symbol pattern exclusions
        excluded_patterns = ['SPXU', 'SQQQ', 'TQQQ', 'UVXY', 'VIX', 'QQQ', 'SPY', 'IWM', 'DIA']
        if any(pattern in symbol for pattern in excluded_patterns):
            return False

        # Skip symbols that are too short or too long
        if len(symbol) < 1 or len(symbol) > 5:
            return False

        return True

    async def _analyze_explosive_potential(self, ticker_data: Dict[str, Any]) -> Optional[ExplosiveCandidate]:
        """
        Analyze individual stock for explosive potential
        """
        symbol = ticker_data['symbol']

        try:
            # Get historical data for momentum analysis
            historical_data = await self._get_historical_data(symbol, days=30)

            # Get news data for catalyst analysis
            news_data = await self._get_news_analysis(symbol)

            # Calculate all explosive indicators
            volume_surge_score = self._calculate_volume_surge_score(ticker_data, historical_data)
            price_momentum_score = self._calculate_price_momentum_score(ticker_data, historical_data)
            acceleration_score = self._calculate_momentum_acceleration_score(historical_data)
            news_catalyst_score = self._calculate_news_catalyst_score(news_data)
            technical_score = self._calculate_technical_breakout_score(ticker_data, historical_data)

            # Calculate composite explosive score
            explosive_score = (
                volume_surge_score * self.SCORING_WEIGHTS['volume_surge'] +
                price_momentum_score * self.SCORING_WEIGHTS['price_momentum'] +
                acceleration_score * self.SCORING_WEIGHTS['momentum_acceleration'] +
                news_catalyst_score * self.SCORING_WEIGHTS['news_catalyst'] +
                technical_score * self.SCORING_WEIGHTS['technical_breakout']
            )

            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(ticker_data, historical_data, news_data)

            # Determine action tag
            action_tag = self._determine_action_tag(explosive_score, volume_surge_score, price_momentum_score)

            # Risk assessment
            volatility_risk = self._assess_volatility_risk(historical_data)
            liquidity_score = self._calculate_liquidity_score(ticker_data)
            market_cap_category = self._categorize_market_cap(ticker_data)

            # Create candidate
            candidate = ExplosiveCandidate(
                symbol=symbol,
                score=explosive_score,
                confidence=confidence,
                action_tag=action_tag,
                price_change_pct=ticker_data['price_change_pct'],
                volume_surge_ratio=ticker_data['volume_ratio'],
                momentum_acceleration=acceleration_score,
                news_catalyst_score=news_catalyst_score,
                technical_breakout_score=technical_score,
                volatility_risk=volatility_risk,
                liquidity_score=liquidity_score,
                market_cap_category=market_cap_category,
                current_price=ticker_data['current_price'],
                volume=ticker_data['volume'],
                market_cap=self._estimate_market_cap(ticker_data),
                avg_volume_30d=self._calculate_avg_volume(historical_data),
                news_count_24h=len(news_data) if news_data else 0
            )

            return candidate

        except Exception as e:
            logger.warning(f"Failed to analyze explosive potential for {symbol}: {e}")
            return None

    async def _get_historical_data(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get historical price/volume data"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Call MCP function directly
            try:
                data = await mcp__polygon__get_aggs(
                    ticker=symbol,
                    multiplier=1,
                    timespan='day',
                    from_=start_date.strftime('%Y-%m-%d'),
                    to=end_date.strftime('%Y-%m-%d'),
                    adjusted=True
                )
            except NameError:
                # Fallback approach
                import builtins
                if hasattr(builtins, 'mcp__polygon__get_aggs'):
                    data = await builtins.mcp__polygon__get_aggs(
                        ticker=symbol,
                        multiplier=1,
                        timespan='day',
                        from_=start_date.strftime('%Y-%m-%d'),
                        to=end_date.strftime('%Y-%m-%d'),
                        adjusted=True
                    )
                else:
                    raise Exception("MCP function mcp__polygon__get_aggs not available")

            if data and data.get('results'):
                return data['results']

            return []

        except Exception as e:
            logger.warning(f"Failed to get historical data for {symbol}: {e}")
            return []

    async def _get_news_analysis(self, symbol: str) -> List[Dict[str, Any]]:
        """Get recent news for catalyst analysis"""
        try:
            # Call MCP function directly
            try:
                data = await mcp__polygon__list_ticker_news(
                    ticker=symbol,
                    limit=10
                )
            except NameError:
                # Fallback approach
                import builtins
                if hasattr(builtins, 'mcp__polygon__list_ticker_news'):
                    data = await builtins.mcp__polygon__list_ticker_news(
                        ticker=symbol,
                        limit=10
                    )
                else:
                    raise Exception("MCP function mcp__polygon__list_ticker_news not available")

            if data and data.get('results'):
                return data['results']

            return []

        except Exception as e:
            logger.warning(f"Failed to get news for {symbol}: {e}")
            return []

    def _calculate_volume_surge_score(self, ticker_data: Dict[str, Any], historical_data: List[Dict[str, Any]]) -> float:
        """Calculate volume surge score (0-100)"""
        volume_ratio = ticker_data['volume_ratio']

        # Get 30-day average volume for better baseline
        if historical_data:
            volumes = [bar.get('v', 0) for bar in historical_data[-20:]]  # Last 20 days
            avg_volume = statistics.mean(volumes) if volumes else ticker_data['volume']
            current_volume = ticker_data['volume']
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Score based on volume surge intensity
        if volume_ratio >= self.EXPLOSIVE_THRESHOLDS['extreme_volume_surge']:
            return 100  # Extreme volume = max score
        elif volume_ratio >= self.EXPLOSIVE_THRESHOLDS['min_volume_surge']:
            # Scale from 60-100 for volume surge between 3x-10x
            ratio_range = self.EXPLOSIVE_THRESHOLDS['extreme_volume_surge'] - self.EXPLOSIVE_THRESHOLDS['min_volume_surge']
            score_range = 40  # 60-100
            excess_ratio = volume_ratio - self.EXPLOSIVE_THRESHOLDS['min_volume_surge']
            return 60 + (excess_ratio / ratio_range) * score_range
        else:
            # Linear scaling from 0-60 for volume ratio 0-3x
            return min(60, (volume_ratio / self.EXPLOSIVE_THRESHOLDS['min_volume_surge']) * 60)

    def _calculate_price_momentum_score(self, ticker_data: Dict[str, Any], historical_data: List[Dict[str, Any]]) -> float:
        """Calculate price momentum score (0-100)"""
        price_change = abs(ticker_data['price_change_pct'])

        # Bonus for upward moves (we want explosive growth, not crashes)
        direction_bonus = 1.2 if ticker_data['price_change_pct'] > 0 else 0.8

        # Score based on price move intensity
        if price_change >= self.EXPLOSIVE_THRESHOLDS['explosive_price_change']:
            return min(100, 100 * direction_bonus)
        elif price_change >= self.EXPLOSIVE_THRESHOLDS['strong_price_change']:
            # Scale from 70-100 for moves between 15%-25%
            ratio_range = self.EXPLOSIVE_THRESHOLDS['explosive_price_change'] - self.EXPLOSIVE_THRESHOLDS['strong_price_change']
            score_range = 30  # 70-100
            excess_change = price_change - self.EXPLOSIVE_THRESHOLDS['strong_price_change']
            return min(100, (70 + (excess_change / ratio_range) * score_range) * direction_bonus)
        elif price_change >= self.EXPLOSIVE_THRESHOLDS['min_price_change']:
            # Scale from 40-70 for moves between 8%-15%
            ratio_range = self.EXPLOSIVE_THRESHOLDS['strong_price_change'] - self.EXPLOSIVE_THRESHOLDS['min_price_change']
            score_range = 30  # 40-70
            excess_change = price_change - self.EXPLOSIVE_THRESHOLDS['min_price_change']
            return min(100, (40 + (excess_change / ratio_range) * score_range) * direction_bonus)
        else:
            # Linear scaling from 0-40 for moves 0-8%
            return min(100, (price_change / self.EXPLOSIVE_THRESHOLDS['min_price_change']) * 40 * direction_bonus)

    def _calculate_momentum_acceleration_score(self, historical_data: List[Dict[str, Any]]) -> float:
        """Calculate momentum acceleration (are moves getting bigger?)"""
        if len(historical_data) < 3:
            return 50  # Neutral score if insufficient data

        try:
            # Get last 3 days of price changes
            recent_data = historical_data[-3:]
            daily_changes = []

            for i in range(1, len(recent_data)):
                prev_close = recent_data[i-1].get('c', 0)
                curr_close = recent_data[i].get('c', 0)

                if prev_close > 0:
                    change_pct = ((curr_close - prev_close) / prev_close) * 100
                    daily_changes.append(abs(change_pct))

            if len(daily_changes) < 2:
                return 50

            # Calculate acceleration (is momentum increasing?)
            acceleration = daily_changes[-1] - daily_changes[0]  # Latest vs earliest

            # Score acceleration
            if acceleration >= self.EXPLOSIVE_THRESHOLDS['strong_acceleration']:
                return 100
            elif acceleration >= self.EXPLOSIVE_THRESHOLDS['min_acceleration']:
                return 70 + (acceleration / self.EXPLOSIVE_THRESHOLDS['strong_acceleration']) * 30
            elif acceleration >= 0:
                return 50 + (acceleration / self.EXPLOSIVE_THRESHOLDS['min_acceleration']) * 20
            else:
                # Negative acceleration (momentum slowing)
                return max(0, 50 + acceleration * 10)  # Penalize deceleration

        except Exception as e:
            logger.warning(f"Failed to calculate acceleration: {e}")
            return 50

    def _calculate_news_catalyst_score(self, news_data: List[Dict[str, Any]]) -> float:
        """Calculate news catalyst score based on recent news sentiment"""
        if not news_data:
            return 25  # Low score for no news

        try:
            catalyst_score = 0
            total_weight = 0

            for article in news_data:
                # Get article age for recency weighting
                published = article.get('published_utc', '')
                hours_ago = self._hours_since_published(published)

                # Skip old news (>24 hours)
                if hours_ago > 24:
                    continue

                # Recency weight (newer = higher weight)
                if hours_ago <= 2:
                    recency_weight = 1.0
                elif hours_ago <= 6:
                    recency_weight = 0.8
                elif hours_ago <= 12:
                    recency_weight = 0.6
                else:
                    recency_weight = 0.4

                # Extract sentiment from insights
                insights = article.get('insights', [])
                article_score = 50  # Neutral baseline

                for insight in insights:
                    sentiment = insight.get('sentiment', 'neutral')
                    if sentiment == 'positive':
                        article_score = 80
                    elif sentiment == 'negative':
                        article_score = 30  # Negative news can still create explosive moves

                # Weight by recency
                weighted_score = article_score * recency_weight
                catalyst_score += weighted_score
                total_weight += recency_weight

            if total_weight > 0:
                final_score = catalyst_score / total_weight
                # Boost score for multiple recent articles (momentum)
                article_bonus = min(20, len([a for a in news_data if self._hours_since_published(a.get('published_utc', '')) <= 24]) * 5)
                return min(100, final_score + article_bonus)

            return 25

        except Exception as e:
            logger.warning(f"Failed to calculate news catalyst score: {e}")
            return 25

    def _calculate_technical_breakout_score(self, ticker_data: Dict[str, Any], historical_data: List[Dict[str, Any]]) -> float:
        """Calculate technical breakout score"""
        if len(historical_data) < 20:
            return 50  # Neutral if insufficient data

        try:
            current_price = ticker_data['current_price']

            # Get 20-day high/low for breakout detection
            recent_highs = [bar.get('h', 0) for bar in historical_data[-20:]]
            recent_lows = [bar.get('l', 0) for bar in historical_data[-20:]]

            if not recent_highs or not recent_lows:
                return 50

            max_high = max(recent_highs[:-1])  # Exclude today
            min_low = min(recent_lows[:-1])    # Exclude today

            # Check for breakouts
            if current_price > max_high * 1.02:  # 2% above 20-day high
                breakout_strength = ((current_price - max_high) / max_high) * 100
                return min(100, 80 + breakout_strength * 2)  # 80-100 for breakouts
            elif current_price < min_low * 0.98:  # 2% below 20-day low (breakdown)
                return 30  # Low score for breakdowns
            else:
                # No clear breakout - score based on position in range
                if max_high > min_low:
                    position_in_range = (current_price - min_low) / (max_high - min_low)
                    return 40 + position_in_range * 20  # 40-60 based on range position

            return 50

        except Exception as e:
            logger.warning(f"Failed to calculate technical score: {e}")
            return 50

    def _hours_since_published(self, published_utc: str) -> float:
        """Calculate hours since article publication"""
        try:
            if not published_utc:
                return 999  # Very old if no timestamp

            # Parse ISO timestamp
            if published_utc.endswith('Z'):
                published_utc = published_utc[:-1] + '+00:00'

            published_dt = datetime.fromisoformat(published_utc)
            now = datetime.now(published_dt.tzinfo)

            return (now - published_dt).total_seconds() / 3600

        except Exception as e:
            logger.warning(f"Failed to parse published time {published_utc}: {e}")
            return 999

    def _calculate_confidence(self, ticker_data: Dict[str, Any], historical_data: List[Dict[str, Any]], news_data: List[Dict[str, Any]]) -> float:
        """Calculate confidence score based on data quality"""
        confidence = 0.5  # Base confidence

        # Historical data quality
        if len(historical_data) >= 20:
            confidence += 0.2
        elif len(historical_data) >= 10:
            confidence += 0.1

        # News data availability
        if news_data:
            confidence += 0.1
            if len(news_data) >= 3:
                confidence += 0.1

        # Volume quality (higher volume = higher confidence)
        if ticker_data['volume'] > 1_000_000:
            confidence += 0.1

        return min(1.0, confidence)

    def _determine_action_tag(self, explosive_score: float, volume_score: float, price_score: float) -> str:
        """Determine action tag based on scores"""
        if explosive_score >= 80 and volume_score >= 70 and price_score >= 60:
            return "explosive"
        elif explosive_score >= 65 and (volume_score >= 60 or price_score >= 60):
            return "momentum"
        elif explosive_score >= 45:
            return "watch"
        else:
            return "skip"

    def _assess_volatility_risk(self, historical_data: List[Dict[str, Any]]) -> str:
        """Assess volatility risk level"""
        if len(historical_data) < 10:
            return "unknown"

        try:
            # Calculate daily price changes
            daily_changes = []
            for i in range(1, len(historical_data)):
                prev_close = historical_data[i-1].get('c', 0)
                curr_close = historical_data[i].get('c', 0)

                if prev_close > 0:
                    change_pct = abs((curr_close - prev_close) / prev_close) * 100
                    daily_changes.append(change_pct)

            if not daily_changes:
                return "unknown"

            avg_volatility = statistics.mean(daily_changes)

            if avg_volatility >= 10:
                return "extreme"
            elif avg_volatility >= 5:
                return "high"
            elif avg_volatility >= 2:
                return "medium"
            else:
                return "low"

        except Exception as e:
            logger.warning(f"Failed to assess volatility: {e}")
            return "unknown"

    def _calculate_liquidity_score(self, ticker_data: Dict[str, Any]) -> float:
        """Calculate liquidity score (0-100)"""
        dollar_volume = ticker_data['current_price'] * ticker_data['volume']

        if dollar_volume >= 50_000_000:  # $50M+
            return 100
        elif dollar_volume >= 10_000_000:  # $10M+
            return 80
        elif dollar_volume >= 5_000_000:   # $5M+
            return 60
        elif dollar_volume >= 1_000_000:   # $1M+
            return 40
        else:
            return 20

    def _categorize_market_cap(self, ticker_data: Dict[str, Any]) -> str:
        """Categorize by estimated market cap"""
        # This is a rough estimate - would need actual shares outstanding for precision
        estimated_market_cap = ticker_data['current_price'] * ticker_data['volume'] * 100  # Very rough estimate

        if estimated_market_cap >= 10_000_000_000:  # $10B+
            return "large"
        elif estimated_market_cap >= 2_000_000_000:  # $2B+
            return "mid"
        elif estimated_market_cap >= 300_000_000:    # $300M+
            return "small"
        else:
            return "micro"

    def _estimate_market_cap(self, ticker_data: Dict[str, Any]) -> Optional[float]:
        """Rough market cap estimate"""
        # This is very rough - real implementation would need shares outstanding
        return ticker_data['current_price'] * ticker_data['volume'] * 100

    def _calculate_avg_volume(self, historical_data: List[Dict[str, Any]]) -> float:
        """Calculate average volume from historical data"""
        if not historical_data:
            return 0

        volumes = [bar.get('v', 0) for bar in historical_data[-20:]]  # Last 20 days
        return statistics.mean(volumes) if volumes else 0

    def _apply_explosive_filters(self, candidates: List[ExplosiveCandidate]) -> List[ExplosiveCandidate]:
        """Apply final filters for explosive candidates"""
        filtered = []

        for candidate in candidates:
            # Skip low-scoring candidates
            if candidate.score < 30:
                continue

            # Skip if no volume surge and no price momentum
            if candidate.volume_surge_ratio < 2.0 and abs(candidate.price_change_pct) < 5.0:
                continue

            # Skip extreme penny stocks (even if they pass initial filter)
            if candidate.current_price < 1.0 and candidate.market_cap_category == "micro":
                continue

            # Skip if liquidity too low
            if candidate.liquidity_score < 30:
                continue

            filtered.append(candidate)

        return filtered

    def _to_api_format(self, candidate: ExplosiveCandidate) -> Dict[str, Any]:
        """Convert candidate to API format"""
        return {
            'symbol': candidate.symbol,
            'score': round(candidate.score, 2),
            'action_tag': candidate.action_tag,
            'confidence': round(candidate.confidence, 3),
            'price': candidate.current_price,
            'price_change_pct': round(candidate.price_change_pct, 2),
            'volume': candidate.volume,
            'volume_surge_ratio': round(candidate.volume_surge_ratio, 2),
            'market_cap_m': round(candidate.market_cap / 1_000_000, 2) if candidate.market_cap else None,
            'liquidity_score': round(candidate.liquidity_score, 1),
            'volatility_risk': candidate.volatility_risk,
            'market_cap_category': candidate.market_cap_category,
            'news_count_24h': candidate.news_count_24h,
            'subscores': {
                'volume_surge': round(candidate.volume_surge_ratio * 10, 1),  # Convert to 0-100 scale
                'price_momentum': round(abs(candidate.price_change_pct) * 2, 1),  # Convert to 0-100 scale
                'momentum_acceleration': round(candidate.momentum_acceleration, 1),
                'news_catalyst': round(candidate.news_catalyst_score, 1),
                'technical_breakout': round(candidate.technical_breakout_score, 1)
            },
            'risk_flags': self._generate_risk_flags(candidate)
        }

    def _generate_risk_flags(self, candidate: ExplosiveCandidate) -> List[str]:
        """Generate risk warning flags"""
        flags = []

        if candidate.volatility_risk == "extreme":
            flags.append("EXTREME_VOLATILITY")

        if candidate.liquidity_score < 40:
            flags.append("LOW_LIQUIDITY")

        if candidate.current_price < 2.0:
            flags.append("PENNY_STOCK")

        if candidate.market_cap_category == "micro":
            flags.append("MICRO_CAP")

        if candidate.news_count_24h == 0 and candidate.news_catalyst_score > 60:
            flags.append("STALE_NEWS_DATA")

        if candidate.volume_surge_ratio > 20:
            flags.append("EXTREME_VOLUME")

        return flags


# Factory function for integration
def create_explosive_discovery_engine():
    """Factory function to create discovery engine"""
    return ExplosiveDiscoveryEngine()
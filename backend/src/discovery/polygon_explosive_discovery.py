#!/usr/bin/env python3
"""
Polygon-based Explosive Discovery System
Uses available Polygon MCP functions to find explosive growth stocks
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import statistics
import math

logger = logging.getLogger(__name__)

# --- Scoring Utils (No External Dependencies) ---
def _combine_subscores(weighted_parts):
    """
    weighted_parts: list of tuples (name, weight, value_or_none)
    Returns (total_score_0_100, subscores_dict, meta_dict)
    - Omits parts with value is None
    - Reweights remaining parts to sum to 100
    """
    active = [(n, w, v) for (n, w, v) in weighted_parts if v is not None]
    missing = [n for (n, w, v) in weighted_parts if v is None]

    if not active:
        return 0.0, {n: None for (n, _, _) in weighted_parts}, {"missing": missing, "active_weights": {}}

    total_w = sum(w for (_, w, _) in active)
    scale = 100.0 / total_w if total_w > 0 else 0.0

    score = 0.0
    subs = {}
    active_weights = {}
    for (n, w, v) in active:
        subs[n] = v
        active_weights[n] = round(w * scale, 4)
        score += (w * scale) * (v / 100.0)

    return round(score, 2), subs | {n: None for n in missing}, {"missing": missing, "active_weights": active_weights}

@dataclass
class ExplosiveStock:
    symbol: str
    score: float
    action_tag: str
    confidence: float

    # Core metrics
    price: float
    price_change_pct: float
    volume: int
    volume_surge_ratio: float

    # Analysis scores
    momentum_score: float
    volume_score: float
    catalyst_score: float
    technical_score: float

    # Risk metrics
    volatility_risk: str
    liquidity_score: float
    news_count: int
    risk_flags: List[str]

class PolygonExplosiveDiscovery:
    """
    Explosive stock discovery using Polygon MCP functions
    Designed to find stocks with parabolic potential
    """

    def __init__(self):
        # Use environment-adaptive weights from deployment config
        try:
            from backend.src.config.mcp_deployment import mcp_config
            self.ALPHASTACK_WEIGHTS = mcp_config.get_scoring_weights_for_environment()
        except:
            # Fallback to full 8-pillar system
            self.ALPHASTACK_WEIGHTS = {
                "price_momentum": 20,
                "volume_surge": 20,
                "float_short": 15,
                "catalyst": 15,
                "sentiment": 10,
                "technical": 10,
                "options_flow": 5,
                "realtime_momentum": 5,
            }

        self.EXPLOSIVE_THRESHOLDS = {
            'min_price_move': 5.0,        # 5% minimum price move
            'strong_price_move': 10.0,    # 10% strong move
            'explosive_price_move': 20.0, # 20% explosive move
            'min_volume_surge': 2.0,      # 2x volume surge minimum
            'strong_volume_surge': 5.0,   # 5x volume surge strong
            'min_dollar_volume': 1_000_000, # $1M minimum daily volume
            'min_price': 0.50,            # No penny stocks below $0.50
            'max_price': 500.00           # Avoid expensive stocks
        }

    async def discover_explosive_stocks(self, limit: int = 50) -> Dict[str, Any]:
        """
        Main discovery method using Polygon MCP data
        """
        try:
            start_time = datetime.now()
            logger.info(f"💥 Starting explosive stock discovery (limit={limit})")

            # Step 1: Get high-momentum stocks from market snapshot
            high_momentum_stocks = await self._get_high_momentum_stocks()
            logger.info(f"📊 Found {len(high_momentum_stocks)} high-momentum stocks")

            if not high_momentum_stocks:
                return self._empty_result("No high-momentum stocks found")

            # Step 2: Analyze each for explosive potential
            explosive_candidates = []
            for stock_data in high_momentum_stocks[:100]:  # Limit to top 100 for analysis
                try:
                    candidate = await self._analyze_explosive_potential(stock_data)
                    if candidate and candidate.score >= 40:  # Minimum score threshold
                        explosive_candidates.append(candidate)
                except Exception as e:
                    logger.warning(f"Failed to analyze {stock_data.get('symbol', 'UNKNOWN')}: {e}")
                    continue

            # Step 3: Rank and filter
            explosive_candidates.sort(key=lambda x: x.score, reverse=True)
            final_candidates = explosive_candidates[:limit]

            # Step 4: Convert to API format
            api_candidates = [self._to_api_format(c) for c in final_candidates]

            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                'status': 'success',
                'count': len(api_candidates),
                'candidates': api_candidates,
                'execution_time_sec': execution_time,
                'pipeline_stats': {
                    'universe_size': len(high_momentum_stocks),
                    'analyzed': len(explosive_candidates),
                    'explosive_filtered': len(final_candidates),
                    'final_count': len(final_candidates)
                },
                'engine': 'Polygon MCP Explosive Discovery',
                'strategy': 'explosive_momentum_v1'
            }

        except Exception as e:
            logger.error(f"💥 Explosive discovery failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'count': 0,
                'candidates': []
            }

    async def _get_high_momentum_stocks(self) -> List[Dict[str, Any]]:
        """
        Get stocks with high momentum from real market universe
        """
        try:
            # Get real universe of active stocks from Polygon
            logger.info("📊 Fetching real market universe from Polygon...")
            universe_tickers = await self._get_real_universe()

            if not universe_tickers:
                logger.warning("Failed to get real universe, falling back to liquid subset")
                universe_tickers = await self._get_liquid_subset()

            logger.info(f"📈 Analyzing {len(universe_tickers)} stocks for explosive potential")

            # Get snapshot data for these tickers using real MCP Polygon bridge
            from backend.src.services.mcp_polygon_bridge import mcp_polygon_bridge
            snapshot_data = await mcp_polygon_bridge.get_market_snapshot(
                tickers=universe_tickers,
                market_type='stocks',
                include_otc=False
            )

            if not snapshot_data or not snapshot_data.get('tickers'):
                logger.warning("No snapshot data available")
                return []

            high_momentum = []
            for ticker_info in snapshot_data['tickers']:
                symbol = ticker_info.get('ticker', '')

                # Extract price and volume data
                day_data = ticker_info.get('day', {})
                prev_data = ticker_info.get('prevDay', {})

                current_price = day_data.get('c', 0)
                current_volume = day_data.get('v', 0)
                prev_close = prev_data.get('c', 0)
                prev_volume = prev_data.get('v', 0)

                # Calculate change metrics
                price_change_pct = 0
                volume_ratio = 1.0

                if prev_close > 0:
                    price_change_pct = ((current_price - prev_close) / prev_close) * 100

                if prev_volume > 0:
                    volume_ratio = current_volume / prev_volume

                # Filter for momentum
                if (abs(price_change_pct) >= self.EXPLOSIVE_THRESHOLDS['min_price_move'] or
                    volume_ratio >= self.EXPLOSIVE_THRESHOLDS['min_volume_surge']):

                    # Basic filters
                    if (self.EXPLOSIVE_THRESHOLDS['min_price'] <= current_price <= self.EXPLOSIVE_THRESHOLDS['max_price'] and
                        current_price * current_volume >= self.EXPLOSIVE_THRESHOLDS['min_dollar_volume']):

                        high_momentum.append({
                            'symbol': symbol,
                            'current_price': current_price,
                            'price_change_pct': price_change_pct,
                            'current_volume': current_volume,
                            'volume_ratio': volume_ratio,
                            'snapshot_data': ticker_info
                        })

            # Sort by combined momentum score
            high_momentum.sort(key=lambda x: abs(x['price_change_pct']) + x['volume_ratio'], reverse=True)

            logger.info(f"Pre-filtered {len(high_momentum)} high-momentum stocks")
            return high_momentum

        except Exception as e:
            logger.error(f"Failed to get high-momentum stocks: {e}")
            return []

    async def _get_real_universe(self) -> List[str]:
        """
        Get real universe of active, liquid stocks from Polygon
        Returns top liquid stocks that can actually move explosively
        """
        try:
            logger.info("🔍 Building explosive discovery universe...")

            # Use MCP bridge to get active tickers list
            from backend.src.services.mcp_polygon_bridge import mcp_polygon_bridge
            liquid_universe = mcp_polygon_bridge._get_liquid_universe()

            # Expand with additional explosive candidates
            additional_tickers = [
                # High-momentum small/mid caps
                'SMCI', 'ARM', 'AVGO', 'PANW', 'FTNT', 'CYBR', 'S', 'MDB',
                'MARA', 'RIOT', 'CLSK', 'HUT', 'BITF', 'COIN',

                # Biotech with explosive potential
                'SAVA', 'BIIB', 'VRTX', 'GILD', 'REGN', 'AMGN', 'BMY',

                # Recent IPOs and growth stocks
                'RBLX', 'ABNB', 'DASH', 'UBER', 'LYFT', 'AFRM', 'UPST',

                # Energy and commodities
                'XOM', 'CVX', 'SLB', 'HAL', 'OXY', 'COP', 'EOG',

                # Semiconductor and AI
                'NVDA', 'AMD', 'INTC', 'QCOM', 'MRVL', 'ON', 'MU',

                # Cloud and enterprise software
                'CRM', 'NOW', 'WDAY', 'VEEV', 'TEAM', 'DDOG', 'NET'
            ]

            # Combine and deduplicate
            all_tickers = list(set(liquid_universe + additional_tickers))

            # Filter out known invalid tickers
            verified_universe = [t for t in all_tickers if self._is_valid_ticker(t)]

            logger.info(f"✅ Built explosive discovery universe of {len(verified_universe)} stocks")
            return verified_universe

        except Exception as e:
            logger.error(f"Failed to build real universe: {e}")
            # Fallback to known good universe
            return self._get_liquid_subset()

    async def _get_liquid_subset(self) -> List[str]:
        """
        Get subset of stocks with explosive potential for discovery
        Focused on small/mid caps and high-beta stocks that can move explosively
        """
        return [
            # AI/Quantum stocks (high volatility, explosive potential)
            'QUBT', 'IONQ', 'RGTI', 'BBAI', 'SOUN', 'LUNR', 'ARQQ', 'IBA',

            # Crypto mining and blockchain (high-beta)
            'MARA', 'RIOT', 'CLSK', 'HUT', 'BITF', 'COIN', 'HOOD',

            # Biotech with breakout potential (small/mid cap)
            'SAVA', 'BIIB', 'MRNA', 'BNTX', 'NVAX', 'VRTX', 'REGN',

            # High-beta momentum plays
            'RIVN', 'LCID', 'SOFI', 'RBLX', 'SPCE', 'NKLA',

            # Volatile small/mid caps
            'SMCI', 'ARM', 'S', 'MDB', 'SNOW', 'CRWD', 'ZS', 'NET',

            # Energy/EV (smaller players)
            'NIO', 'XPEV', 'LI', 'PLUG', 'FCEL', 'BE', 'CHPT', 'BLNK',

            # Media/Entertainment with volatility
            'WBD', 'PARA', 'ROKU', 'SNAP', 'SPOT', 'ZM',

            # Fintech growth stocks
            'SQ', 'AFRM', 'UPST', 'LMND', 'LC',

            # Retail/E-commerce disruptors
            'SHOP', 'ETSY', 'CHWY', 'CVNA', 'W', 'OPEN',

            # Recent SPACs and growth stocks
            'WISH', 'CLOV', 'SKLZ', 'DKNG', 'PLTR',

            # Semiconductor growth plays
            'AMD', 'MRVL', 'ON', 'MU', 'AMAT'
        ]

    def _is_valid_ticker(self, ticker: str) -> bool:
        """
        Basic validation to exclude known delisted/problematic tickers
        """
        # Exclude known delisted or problematic tickers
        invalid_tickers = {
            'VIGL',  # Delisted
            'TWTR',  # Acquired/delisted
            'DIDI',  # Delisted from US
        }
        return ticker not in invalid_tickers and len(ticker) <= 5

    async def _analyze_explosive_potential(self, stock_data: Dict[str, Any]) -> Optional[ExplosiveStock]:
        """
        Analyze individual stock for explosive potential
        """
        symbol = stock_data['symbol']

        try:
            # Get historical data for trend analysis
            historical_data = await self._get_historical_data(symbol, days=20)

            # Get news data for catalyst analysis
            news_data = await self._get_news_data(symbol)

            # Get enhanced data sources concurrently for better performance
            short_interest_task = asyncio.create_task(self._get_short_interest_data(symbol))
            sentiment_task = asyncio.create_task(self._get_sentiment_data(symbol))

            # Add new enhanced data sources using official Polygon MCP
            options_task = asyncio.create_task(self._get_options_activity_data(symbol))
            trades_task = asyncio.create_task(self._get_realtime_trades_data(symbol))

            # Wait for all data to arrive
            short_interest_data, sentiment_data, options_data, trades_data = await asyncio.gather(
                short_interest_task, sentiment_task, options_task, trades_task, return_exceptions=True
            )

            # Handle exceptions from concurrent tasks
            if isinstance(short_interest_data, Exception):
                logger.warning(f"Short interest task failed for {symbol}: {short_interest_data}")
                short_interest_data = {'available': False}
            if isinstance(sentiment_data, Exception):
                logger.warning(f"Sentiment task failed for {symbol}: {sentiment_data}")
                sentiment_data = {'available': False}
            if isinstance(options_data, Exception):
                logger.warning(f"Options data task failed for {symbol}: {options_data}")
                options_data = {'available': False}
            if isinstance(trades_data, Exception):
                logger.warning(f"Trades data task failed for {symbol}: {trades_data}")
                trades_data = {'available': False}

            # Calculate component scores with enhanced AlphaStack approach
            sub_price = self._calculate_momentum_score(stock_data, historical_data)
            sub_volume = self._calculate_volume_score(stock_data, historical_data)
            sub_float = self._calculate_float_short_score(symbol, short_interest_data)
            sub_cat = self._calculate_catalyst_score(news_data)  # Basic catalyst without enhancement
            sub_sent = self._calculate_sentiment_score(symbol, sentiment_data)
            sub_tech = self._calculate_technical_score(stock_data, historical_data)
            sub_options = self._calculate_options_flow_score(symbol, options_data)
            sub_realtime = self._calculate_realtime_momentum_score(symbol, trades_data)

            # Apply Enhanced AlphaStack 8-pillar weighted scoring with dynamic reweighting
            weighted = [
                ("price_momentum", self.ALPHASTACK_WEIGHTS["price_momentum"], sub_price),
                ("volume_surge", self.ALPHASTACK_WEIGHTS["volume_surge"], sub_volume),
                ("float_short", self.ALPHASTACK_WEIGHTS["float_short"], sub_float),
                ("catalyst", self.ALPHASTACK_WEIGHTS["catalyst"], sub_cat),
                ("sentiment", self.ALPHASTACK_WEIGHTS["sentiment"], sub_sent),
                ("technical", self.ALPHASTACK_WEIGHTS["technical"], sub_tech),
                ("options_flow", self.ALPHASTACK_WEIGHTS["options_flow"], sub_options),
                ("realtime_momentum", self.ALPHASTACK_WEIGHTS["realtime_momentum"], sub_realtime),
            ]
            explosive_score, subscores, meta = _combine_subscores(weighted)

            # Determine action tag
            if explosive_score >= 80:
                action_tag = "explosive"
            elif explosive_score >= 65:
                action_tag = "momentum"
            elif explosive_score >= 50:
                action_tag = "watch"
            else:
                action_tag = "skip"

            # Calculate confidence and risk metrics
            confidence = self._calculate_confidence(stock_data, historical_data, news_data)
            volatility_risk = self._assess_volatility_risk(historical_data)
            liquidity_score = self._calculate_liquidity_score(stock_data)
            risk_flags = self._generate_risk_flags(stock_data, volatility_risk)

            return ExplosiveStock(
                symbol=symbol,
                score=explosive_score,
                action_tag=action_tag,
                confidence=confidence,
                price=stock_data['current_price'],
                price_change_pct=stock_data['price_change_pct'],
                volume=stock_data['current_volume'],
                volume_surge_ratio=stock_data['volume_ratio'],
                momentum_score=subscores.get("price_momentum", 0) or 0,
                volume_score=subscores.get("volume_surge", 0) or 0,
                catalyst_score=subscores.get("catalyst", 0) or 0,
                technical_score=subscores.get("technical", 0) or 0,
                volatility_risk=volatility_risk,
                liquidity_score=liquidity_score,
                news_count=len(news_data) if news_data else 0,
                risk_flags=risk_flags
            )

        except Exception as e:
            logger.warning(f"Failed to analyze explosive potential for {symbol}: {e}")
            return None

    async def _get_historical_data(self, symbol: str, days: int = 20) -> List[Dict[str, Any]]:
        """Get historical price/volume data using real MCP bridge"""
        try:
            from backend.src.services.mcp_polygon_bridge import mcp_polygon_bridge
            prev_close_data = await mcp_polygon_bridge.get_previous_close(symbol)

            # For now, return basic data structure
            # In the future, we can add proper historical aggregates through MCP bridge
            if prev_close_data and 'results' in prev_close_data:
                return [prev_close_data['results']]

            return []

        except Exception as e:
            logger.warning(f"Failed to get historical data for {symbol}: {e}")
            return []

    async def _get_news_data(self, symbol: str) -> List[Dict[str, Any]]:
        """Get recent news data using real MCP bridge"""
        try:
            from backend.src.services.mcp_polygon_bridge import mcp_polygon_bridge
            news_articles = await mcp_polygon_bridge.get_ticker_news(symbol, limit=10)
            return news_articles if news_articles else []

        except Exception as e:
            logger.warning(f"Failed to get news for {symbol}: {e}")
            return []

    def _calculate_momentum_score(self, stock_data: Dict[str, Any], historical_data: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate price momentum score (0-100)"""
        try:
            price_change = abs(stock_data['price_change_pct'])

            # Base score from price movement
            if price_change >= self.EXPLOSIVE_THRESHOLDS['explosive_price_move']:
                base_score = 100
            elif price_change >= self.EXPLOSIVE_THRESHOLDS['strong_price_move']:
                base_score = 70 + (price_change - self.EXPLOSIVE_THRESHOLDS['strong_price_move']) * 3
            elif price_change >= self.EXPLOSIVE_THRESHOLDS['min_price_move']:
                base_score = 40 + (price_change - self.EXPLOSIVE_THRESHOLDS['min_price_move']) * 6
            else:
                base_score = price_change * 8

            # Direction bonus (we prefer up moves)
            direction_bonus = 1.2 if stock_data['price_change_pct'] > 0 else 0.9

            # Multi-day momentum bonus
            momentum_bonus = 1.0
            if len(historical_data) >= 3:
                recent_closes = [bar.get('c', 0) for bar in historical_data[-3:]]
                if len(recent_closes) == 3:
                    if recent_closes[2] > recent_closes[1] > recent_closes[0]:
                        momentum_bonus = 1.3  # 3-day uptrend
                    elif recent_closes[2] > recent_closes[0]:
                        momentum_bonus = 1.1  # Net positive

            return min(100, base_score * direction_bonus * momentum_bonus)
        except Exception as e:
            logger.warning(f"Momentum score calculation failed: {e}")
            return None

    def _calculate_volume_score(self, stock_data: Dict[str, Any], historical_data: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate volume surge score (0-100)"""
        try:
            volume_ratio = stock_data['volume_ratio']

            # Enhanced volume ratio with historical context
            if historical_data:
                historical_volumes = [bar.get('v', 0) for bar in historical_data[-10:]]
                if historical_volumes:
                    avg_volume = statistics.mean(historical_volumes)
                    if avg_volume > 0:
                        volume_ratio = stock_data['current_volume'] / avg_volume

            # Score based on volume surge
            if volume_ratio >= 10:
                return 100  # Extreme volume
            elif volume_ratio >= self.EXPLOSIVE_THRESHOLDS['strong_volume_surge']:
                return 80 + (volume_ratio - 5) * 4
            elif volume_ratio >= self.EXPLOSIVE_THRESHOLDS['min_volume_surge']:
                return 50 + (volume_ratio - 2) * 10
            else:
                return volume_ratio * 25
        except Exception as e:
            logger.warning(f"Volume score calculation failed: {e}")
            return None

    def _calculate_catalyst_score(self, news_data: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate news catalyst score (0-100)"""
        try:
            if not news_data:
                return None  # No news data available

            score = 0
            total_weight = 0

            for article in news_data:
                # Calculate recency weight
                published_utc = article.get('published_utc', '')
                hours_ago = self._hours_since_published(published_utc)

                if hours_ago > 48:  # Skip old news
                    continue

                # Recency weight
                if hours_ago <= 2:
                    weight = 1.0
                elif hours_ago <= 6:
                    weight = 0.8
                elif hours_ago <= 24:
                    weight = 0.6
                else:
                    weight = 0.3

                # Sentiment analysis
                article_score = 50  # Neutral baseline
                insights = article.get('insights', [])

                for insight in insights:
                    sentiment = insight.get('sentiment', 'neutral')
                    if sentiment == 'positive':
                        article_score = 80
                    elif sentiment == 'negative':
                        article_score = 70  # Negative news can still drive volume

                score += article_score * weight
                total_weight += weight

            if total_weight > 0:
                final_score = score / total_weight
                # Bonus for multiple recent articles
                article_count_bonus = min(20, len(news_data) * 3)
                return min(100, final_score + article_count_bonus)

            return 20
        except Exception as e:
            logger.warning(f"Catalyst score calculation failed: {e}")
            return None

    def _calculate_technical_score(self, stock_data: Dict[str, Any], historical_data: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate technical breakout score (0-100)"""
        try:
            if len(historical_data) < 10:
                return None  # Insufficient data

            current_price = stock_data['current_price']

            # Calculate resistance levels
            recent_highs = [bar.get('h', 0) for bar in historical_data[-20:]]
            recent_lows = [bar.get('l', 0) for bar in historical_data[-20:]]

            if not recent_highs or not recent_lows:
                return None

            max_high = max(recent_highs[:-1])  # Exclude today
            min_low = min(recent_lows[:-1])

            # Breakout detection
            if current_price > max_high * 1.02:  # 2% above resistance
                breakout_strength = ((current_price - max_high) / max_high) * 100
                return min(100, 80 + breakout_strength * 2)
            elif current_price < min_low * 0.98:  # Breakdown
                return 20
            else:
                # Position in range
                if max_high > min_low:
                    position = (current_price - min_low) / (max_high - min_low)
                    return 30 + position * 40  # 30-70 based on position

                return 50
        except Exception as e:
            logger.warning(f"Technical score calculation failed: {e}")
            return None

    def _calculate_confidence(self, stock_data: Dict[str, Any], historical_data: List[Dict[str, Any]], news_data: List[Dict[str, Any]]) -> float:
        """Calculate confidence score (0-1)"""
        confidence = 0.5  # Base confidence

        # Historical data quality
        if len(historical_data) >= 15:
            confidence += 0.2
        elif len(historical_data) >= 5:
            confidence += 0.1

        # News availability
        if news_data:
            confidence += 0.1
            if len(news_data) >= 3:
                confidence += 0.1

        # Volume quality
        dollar_volume = stock_data['current_price'] * stock_data['current_volume']
        if dollar_volume >= 10_000_000:  # $10M+
            confidence += 0.1

        return min(1.0, confidence)

    def _assess_volatility_risk(self, historical_data: List[Dict[str, Any]]) -> str:
        """Assess volatility risk level"""
        if len(historical_data) < 5:
            return "unknown"

        try:
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

            if avg_volatility >= 15:
                return "extreme"
            elif avg_volatility >= 8:
                return "high"
            elif avg_volatility >= 4:
                return "medium"
            else:
                return "low"

        except Exception:
            return "unknown"

    def _calculate_liquidity_score(self, stock_data: Dict[str, Any]) -> float:
        """Calculate liquidity score (0-100)"""
        dollar_volume = stock_data['current_price'] * stock_data['current_volume']

        if dollar_volume >= 100_000_000:  # $100M+
            return 100
        elif dollar_volume >= 50_000_000:  # $50M+
            return 90
        elif dollar_volume >= 10_000_000:  # $10M+
            return 80
        elif dollar_volume >= 5_000_000:   # $5M+
            return 60
        elif dollar_volume >= 1_000_000:   # $1M+
            return 40
        else:
            return 20

    def _generate_risk_flags(self, stock_data: Dict[str, Any], volatility_risk: str) -> List[str]:
        """Generate risk warning flags"""
        flags = []

        if volatility_risk == "extreme":
            flags.append("EXTREME_VOLATILITY")

        if stock_data['current_price'] < 2.0:
            flags.append("PENNY_STOCK")

        dollar_volume = stock_data['current_price'] * stock_data['current_volume']
        if dollar_volume < 5_000_000:  # Less than $5M
            flags.append("LOW_LIQUIDITY")

        if stock_data['volume_ratio'] > 20:
            flags.append("EXTREME_VOLUME")

        if abs(stock_data['price_change_pct']) > 30:
            flags.append("EXTREME_MOVE")

        return flags

    def _hours_since_published(self, published_utc: str) -> float:
        """Calculate hours since publication"""
        try:
            if not published_utc:
                return 999

            if published_utc.endswith('Z'):
                published_utc = published_utc[:-1] + '+00:00'

            published_dt = datetime.fromisoformat(published_utc)
            now = datetime.now(published_dt.tzinfo)

            return (now - published_dt).total_seconds() / 3600

        except Exception:
            return 999

    def _to_api_format(self, candidate: ExplosiveStock) -> Dict[str, Any]:
        """Convert to API format"""
        return {
            'symbol': candidate.symbol,
            'score': round(candidate.score, 2),
            'action_tag': candidate.action_tag,
            'confidence': round(candidate.confidence, 3),
            'price': candidate.price,
            'price_change_pct': round(candidate.price_change_pct, 2),
            'volume': candidate.volume,
            'volume_surge_ratio': round(candidate.volume_surge_ratio, 2),
            'market_cap_m': None,  # Not available without shares outstanding
            'liquidity_score': round(candidate.liquidity_score, 1),
            'volatility_risk': candidate.volatility_risk,
            'news_count_24h': candidate.news_count,
            'subscores': {
                'volume_surge': round(candidate.volume_score, 1),
                'price_momentum': round(candidate.momentum_score, 1),
                'news_catalyst': round(candidate.catalyst_score, 1),
                'technical_breakout': round(candidate.technical_score, 1)
            },
            'risk_flags': candidate.risk_flags
        }

    def _empty_result(self, reason: str) -> Dict[str, Any]:
        """Return empty result with reason"""
        return {
            'status': 'success',
            'count': 0,
            'candidates': [],
            'execution_time_sec': 0,
            'pipeline_stats': {'universe_size': 0, 'analyzed': 0, 'final_count': 0},
            'engine': 'Polygon MCP Explosive Discovery',
            'error_reason': reason
        }

    async def _get_short_interest_data(self, symbol: str) -> Dict[str, Any]:
        """Get short interest data using HTTP MCP client"""
        try:
            from backend.src.mcp_http_client import mcp_http_client
            return await mcp_http_client.get_short_interest(symbol)
        except Exception as e:
            logger.warning(f"Failed to get short interest for {symbol}: {e}")
            return {'available': False}

    async def _get_sentiment_data(self, symbol: str) -> Dict[str, Any]:
        """Get news sentiment data using HTTP MCP client"""
        try:
            from backend.src.mcp_http_client import mcp_http_client
            return await mcp_http_client.get_news_sentiment(symbol, hours_back=24)
        except Exception as e:
            logger.warning(f"Failed to get sentiment for {symbol}: {e}")
            return {'available': False}

    async def _get_options_activity_data(self, symbol: str) -> Dict[str, Any]:
        """Get options activity data using HTTP MCP client"""
        try:
            from backend.src.mcp_http_client import mcp_http_client
            # Note: HTTP MCP client doesn't have options_activity method yet
            # Return unavailable for now until we implement it
            logger.info(f"Options activity not available in HTTP MCP client for {symbol}")
            return {'available': False}
        except Exception as e:
            logger.warning(f"Failed to get options activity for {symbol}: {e}")
            return {'available': False}

    async def _get_realtime_trades_data(self, symbol: str) -> Dict[str, Any]:
        """Get real-time trade data using HTTP MCP client"""
        try:
            from backend.src.mcp_http_client import mcp_http_client
            # Use detailed aggregates for real-time momentum analysis
            agg_data = await mcp_http_client.get_detailed_aggregates(symbol, days_back=2)
            if agg_data.get('available') and agg_data.get('data'):
                # Calculate momentum from recent price data
                data_points = agg_data['data']
                if len(data_points) >= 2:
                    latest = data_points[-1]
                    previous = data_points[-2]

                    momentum = ((latest.get('c', 0) - previous.get('c', 0)) / previous.get('c', 1)) * 100
                    volume_surge = latest.get('v', 0) / max(previous.get('v', 1), 1)

                    return {
                        'available': True,
                        'momentum_pct': momentum,
                        'volume_surge': volume_surge,
                        'latest_price': latest.get('c', 0),
                        'latest_volume': latest.get('v', 0)
                    }

            return {'available': False}
        except Exception as e:
            logger.warning(f"Failed to get realtime trades for {symbol}: {e}")
            return {'available': False}

    def _calculate_enhanced_catalyst_score(self, news_data: List[Dict], short_interest_data: Dict, sentiment_data: Dict) -> float:
        """Enhanced catalyst scoring with short interest and sentiment"""
        base_score = self._calculate_catalyst_score(news_data)  # Keep existing news scoring

        # Add short interest boost for squeeze potential
        short_boost = 0
        if short_interest_data.get('available') and short_interest_data.get('days_to_cover', 0) > 1:
            days_to_cover = short_interest_data['days_to_cover']
            if days_to_cover >= 3:
                short_boost = 25  # High squeeze potential
            elif days_to_cover >= 2:
                short_boost = 15  # Medium squeeze potential
            else:
                short_boost = 5   # Low squeeze potential

        # Add sentiment boost
        sentiment_boost = 0
        if sentiment_data.get('available'):
            sentiment_score = sentiment_data.get('sentiment_score', 0)
            news_count = sentiment_data.get('news_count', 0)

            if news_count >= 3:  # Significant news volume
                if sentiment_score > 0.5:
                    sentiment_boost = 20  # Very positive
                elif sentiment_score > 0.2:
                    sentiment_boost = 10  # Positive
                elif sentiment_score < -0.2:
                    sentiment_boost = -10  # Negative news can also drive moves
            elif news_count >= 1:
                sentiment_boost = sentiment_score * 10  # Proportional boost

        # Combine scores (max 100)
        enhanced_score = base_score + short_boost + sentiment_boost
        return min(100, max(0, enhanced_score))

    def _calculate_enhanced_technical_score(self, stock_data: Dict[str, Any], historical_data: List[Dict]) -> float:
        """Enhanced technical scoring with better analysis"""
        base_score = self._calculate_technical_score(stock_data, historical_data)

        # Add VWAP analysis if available
        vwap_boost = 0
        current_price = stock_data['current_price']

        if historical_data:
            # Calculate simple VWAP from available data
            total_pv = sum(bar.get('c', 0) * bar.get('v', 0) for bar in historical_data)
            total_v = sum(bar.get('v', 0) for bar in historical_data)

            if total_v > 0:
                vwap = total_pv / total_v
                price_vs_vwap = ((current_price - vwap) / vwap) * 100

                if price_vs_vwap > 2:  # Above VWAP
                    vwap_boost = 15
                elif price_vs_vwap > 0:
                    vwap_boost = 5
                elif price_vs_vwap < -5:  # Potential bounce candidate
                    vwap_boost = 10

        return min(100, base_score + vwap_boost)

    def _calculate_float_short_score(self, symbol: str, short_interest_data: Dict) -> Optional[float]:
        """Calculate float/short squeeze potential score (0-100)"""
        try:
            if not short_interest_data.get('available'):
                return None  # Data not available, will be omitted from scoring

            score = 0

            # Days to cover is primary signal for squeeze potential
            days_to_cover = short_interest_data.get('days_to_cover', 0)
            if days_to_cover >= 5:
                score += 50  # Very high squeeze potential
            elif days_to_cover >= 3:
                score += 35  # High squeeze potential
            elif days_to_cover >= 2:
                score += 20  # Medium squeeze potential
            elif days_to_cover >= 1:
                score += 10  # Low squeeze potential

            # Short interest percentage
            short_interest = short_interest_data.get('short_interest', 0)
            avg_daily_volume = short_interest_data.get('avg_daily_volume', 1)
            if avg_daily_volume > 0:
                short_pct_float = (short_interest / avg_daily_volume) * 100
                if short_pct_float >= 25:
                    score += 30  # Very high short interest
                elif short_pct_float >= 15:
                    score += 20  # High short interest
                elif short_pct_float >= 10:
                    score += 10  # Medium short interest

            # Volume surge can amplify squeeze
            volume_bonus = min(20, short_interest_data.get('volume_surge_ratio', 1) * 5)
            score += volume_bonus

            return min(100, score)

        except Exception as e:
            logger.warning(f"Float/short score calculation failed for {symbol}: {e}")
            return None

    def _calculate_sentiment_score(self, symbol: str, sentiment_data: Dict) -> Optional[float]:
        """Calculate sentiment score from news and social data (0-100)"""
        try:
            if not sentiment_data.get('available'):
                return None  # Data not available, will be omitted from scoring

            sentiment_score = sentiment_data.get('sentiment_score', 0)
            news_count = sentiment_data.get('news_count', 0)

            if news_count == 0:
                return None  # No news to analyze

            # Base score from sentiment
            base_score = ((sentiment_score + 1) / 2) * 100  # Convert -1,1 to 0,100

            # News volume multiplier
            volume_multiplier = min(1.5, 1 + (news_count / 10))

            # Recent news gets higher weight
            final_score = base_score * volume_multiplier

            return min(100, max(0, final_score))

        except Exception as e:
            logger.warning(f"Sentiment score calculation failed for {symbol}: {e}")
            return None

    def _calculate_options_flow_score(self, symbol: str, options_data: Dict) -> Optional[float]:
        """Calculate options flow unusual activity score (0-100)"""
        try:
            if not options_data.get('available'):
                return None  # Options data not available

            call_put_ratio = options_data.get('call_put_ratio', 1.0)
            total_volume = options_data.get('total_options_volume', 0)
            contracts_count = options_data.get('contracts_count', 0)

            score = 0

            # Call/Put ratio analysis
            if call_put_ratio >= 3.0:
                score += 40  # Very bullish options flow
            elif call_put_ratio >= 2.0:
                score += 25  # Bullish options flow
            elif call_put_ratio >= 1.5:
                score += 15  # Moderately bullish
            elif call_put_ratio <= 0.3:
                score += 30  # Heavy put buying (potential squeeze setup)
            elif call_put_ratio <= 0.5:
                score += 20  # Moderate put buying

            # Volume intensity
            if total_volume >= 50000:
                score += 30  # Very high options volume
            elif total_volume >= 20000:
                score += 20  # High options volume
            elif total_volume >= 5000:
                score += 10  # Moderate options volume

            # Contract diversity (more contracts = more interest)
            if contracts_count >= 20:
                score += 20  # Wide options interest
            elif contracts_count >= 10:
                score += 10  # Moderate options interest

            return min(100, score)

        except Exception as e:
            logger.warning(f"Options flow score calculation failed for {symbol}: {e}")
            return None

    def _calculate_realtime_momentum_score(self, symbol: str, trades_data: Dict) -> Optional[float]:
        """Calculate real-time momentum from recent trades (0-100)"""
        try:
            if not trades_data.get('available'):
                return None  # Trade data not available

            momentum_pct = trades_data.get('recent_momentum_pct', 0)
            avg_trade_size = trades_data.get('avg_trade_size', 0)
            trade_count = trades_data.get('trade_count', 0)

            score = 0

            # Price momentum
            if momentum_pct >= 2.0:
                score += 40  # Strong upward momentum
            elif momentum_pct >= 1.0:
                score += 25  # Moderate upward momentum
            elif momentum_pct >= 0.5:
                score += 15  # Weak upward momentum
            elif momentum_pct <= -1.0:
                score += 10  # Downward momentum (potential reversal setup)

            # Trade size analysis
            if avg_trade_size >= 10000:
                score += 30  # Large institutional trades
            elif avg_trade_size >= 5000:
                score += 20  # Medium institutional trades
            elif avg_trade_size >= 1000:
                score += 10  # Small institutional trades

            # Trade frequency
            if trade_count >= 100:
                score += 20  # High trading activity
            elif trade_count >= 50:
                score += 15  # Moderate trading activity
            elif trade_count >= 20:
                score += 10  # Some trading activity

            return min(100, score)

        except Exception as e:
            logger.warning(f"Realtime momentum score calculation failed for {symbol}: {e}")
            return None

# Factory function
def create_polygon_explosive_discovery():
    """Create explosive discovery engine"""
    return PolygonExplosiveDiscovery()
#!/usr/bin/env python3
"""
Enhanced MCP Client Integration for Polygon Data
Fixes existing integration and adds short interest + news sentiment
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PolygonMCPClient:
    """Enhanced Polygon MCP client with real integration"""

    def __init__(self):
        self.cache = {}
        self.mcp_available = self._check_mcp_availability()

    def _check_mcp_availability(self) -> bool:
        """Check if MCP functions are available in the environment"""
        try:
            # Try to import and call MCP functions to test availability
            # This will work when deployed where MCP functions are actually available
            try:
                # Test if we can access the functions (will be available in deployed environment)
                import builtins
                if hasattr(builtins, 'mcp__polygon__get_aggs'):
                    return True
            except:
                pass

            # Fallback: check global namespace (works in Claude environment)
            if 'mcp__polygon__get_aggs' in globals():
                return True

            # If running in AMC-TRADER backend with proper deployment, assume available
            # This ensures production deployment uses MCP functions
            import os
            if os.getenv('RENDER_SERVICE_NAME') or os.getenv('AMC_TRADER_ENV'):
                return True

            return False
        except:
            return False

    def _is_mcp_environment(self) -> bool:
        """Check if we're running in Claude environment vs Render deployment"""
        try:
            # MCP functions are available in both environments now
            # Check if we can access MCP functions directly
            return 'mcp__polygon__get_aggs' in globals()
        except:
            return False

    async def get_market_snapshots(self, tickers: List[str] = None) -> Dict[str, Any]:
        """Get market snapshots for explosive discovery"""
        try:
            # Use real MCP function directly (available in Claude environment)
            if tickers:
                result = await mcp__polygon__get_snapshot_all(
                    market_type="stocks",
                    tickers=tickers
                )
            else:
                result = await mcp__polygon__get_snapshot_all(market_type="stocks")

            return result

        except Exception as e:
            logger.error(f"Failed to get market snapshots: {e}")
            return {'tickers': [], 'status': 'ERROR'}

    async def get_short_interest(self, ticker: str) -> Dict[str, Any]:
        """Get latest short interest data for squeeze detection"""
        if not self.mcp_available:
            return {'available': False, 'reason': 'MCP not available in environment'}

        try:
            # Get most recent short interest data using global MCP function
            result = await mcp__polygon__list_short_interest(
                ticker=ticker,
                limit=1,
                order="desc"
            )

            if result.get('results'):
                latest = result['results'][0]
                return {
                    'short_interest': latest.get('short_interest', 0),
                    'avg_daily_volume': latest.get('avg_daily_volume', 0),
                    'days_to_cover': latest.get('days_to_cover', 0),
                    'settlement_date': latest.get('settlement_date'),
                    'available': True
                }

            return {'available': False}

        except Exception as e:
            logger.error(f"Failed to get short interest for {ticker}: {e}")
            return {'available': False}

    async def get_news_sentiment(self, ticker: str, hours_back: int = 24) -> Dict[str, Any]:
        """Get recent news with sentiment analysis"""
        if not self.mcp_available:
            return {'sentiment_score': 0, 'news_count': 0, 'available': False, 'reason': 'MCP not available'}

        try:
            result = await mcp__polygon__list_ticker_news(
                ticker=ticker,
                limit=10,
                sort="published_utc",
                order="desc"
            )

            if not result.get('results'):
                return {'sentiment_score': 0, 'news_count': 0, 'available': False}

            # Analyze sentiment from insights
            positive_count = 0
            negative_count = 0
            total_news = 0

            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

            for article in result['results']:
                # Check if recent enough
                pub_time = datetime.fromisoformat(article['published_utc'].replace('Z', '+00:00'))
                if pub_time < cutoff_time:
                    continue

                total_news += 1

                # Check insights for sentiment
                insights = article.get('insights', [])
                for insight in insights:
                    if insight.get('ticker') == ticker:
                        sentiment = insight.get('sentiment', 'neutral')
                        if sentiment == 'positive':
                            positive_count += 1
                        elif sentiment == 'negative':
                            negative_count += 1

            # Calculate sentiment score (-1 to 1)
            if total_news > 0:
                sentiment_score = (positive_count - negative_count) / max(total_news, 1)
            else:
                sentiment_score = 0

            return {
                'sentiment_score': sentiment_score,
                'news_count': total_news,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'available': True
            }

        except Exception as e:
            logger.error(f"Failed to get news sentiment for {ticker}: {e}")
            return {'sentiment_score': 0, 'news_count': 0, 'available': False}

    async def get_detailed_aggregates(self, ticker: str, days_back: int = 5) -> Dict[str, Any]:
        """Get detailed price/volume data for technical analysis"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            result = await mcp__polygon__get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=start_date.strftime("%Y-%m-%d"),
                to=end_date.strftime("%Y-%m-%d"),
                adjusted=True
            )

            if result.get('results'):
                return {
                    'data': result['results'],
                    'available': True
                }

            return {'available': False}

        except Exception as e:
            logger.error(f"Failed to get aggregates for {ticker}: {e}")
            return {'available': False}

    async def get_corporate_actions(self, ticker: str) -> Dict[str, Any]:
        """Get upcoming dividends and recent splits"""
        try:
            # Check for upcoming dividends (next 30 days)
            future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

            div_result = await mcp__polygon__list_dividends(
                ticker=ticker,
                ex_dividend_date_gte=datetime.now().strftime("%Y-%m-%d"),
                ex_dividend_date_lte=future_date,
                limit=5
            )

            # Check for recent splits (last 90 days)
            past_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

            split_result = await mcp__polygon__list_splits(
                ticker=ticker,
                execution_date_gte=past_date,
                limit=5
            )

            return {
                'upcoming_dividends': div_result.get('results', []),
                'recent_splits': split_result.get('results', []),
                'available': True
            }

        except Exception as e:
            logger.error(f"Failed to get corporate actions for {ticker}: {e}")
            return {'available': False}

    async def get_options_activity(self, ticker: str) -> Dict[str, Any]:
        """Get options activity and unusual volume (requires premium Polygon plan)"""
        if not self.mcp_available:
            return {'available': False, 'reason': 'MCP not available'}

        # Try to get options data - will handle authorization errors gracefully

        try:
            # Get options snapshots for the underlying ticker
            result = await mcp__polygon__get_snapshot_option(
                underlying_asset=ticker,
                option_contract="*",  # Get all option contracts
                limit=50
            )

            # Handle authorization errors gracefully
            if isinstance(result, dict) and result.get('error'):
                error_msg = result.get('error', '')
                if 'NOT_AUTHORIZED' in error_msg:
                    return {'available': False, 'reason': 'Options data requires premium Polygon plan'}

            if result.get('results'):
                options_data = result['results']

                # Analyze for unusual activity
                total_call_volume = sum(opt.get('day', {}).get('volume', 0)
                                      for opt in options_data if opt.get('details', {}).get('contract_type') == 'call')
                total_put_volume = sum(opt.get('day', {}).get('volume', 0)
                                     for opt in options_data if opt.get('details', {}).get('contract_type') == 'put')

                call_put_ratio = total_call_volume / max(total_put_volume, 1)

                return {
                    'available': True,
                    'call_volume': total_call_volume,
                    'put_volume': total_put_volume,
                    'call_put_ratio': call_put_ratio,
                    'total_options_volume': total_call_volume + total_put_volume,
                    'contracts_count': len(options_data)
                }

            return {'available': False, 'reason': 'No options data returned'}

        except Exception as e:
            logger.error(f"Failed to get options activity for {ticker}: {e}")
            return {'available': False, 'reason': str(e)}

    async def get_realtime_trades(self, ticker: str, limit: int = 10) -> Dict[str, Any]:
        """Get recent trade data for momentum analysis (requires premium Polygon plan)"""
        if not self.mcp_available:
            return {'available': False, 'reason': 'MCP not available'}

        # Try realtime trades first, fall back to aggregates if not available

        try:
            # Get recent trades
            result = await mcp__polygon__list_trades(
                ticker=ticker,
                limit=limit,
                sort="timestamp",
                order="desc"
            )

            # Handle authorization errors gracefully
            if isinstance(result, dict) and result.get('error'):
                error_msg = result.get('error', '')
                if 'NOT_AUTHORIZED' in error_msg:
                    # Fall back to aggregates data
                    return await self._get_momentum_from_aggregates(ticker)

            if result.get('results'):
                trades = result['results']

                # Calculate trade momentum indicators
                prices = [trade.get('price', 0) for trade in trades]
                volumes = [trade.get('size', 0) for trade in trades]

                if len(prices) >= 2:
                    recent_momentum = (prices[0] - prices[-1]) / prices[-1] * 100
                    avg_trade_size = sum(volumes) / len(volumes)

                    return {
                        'available': True,
                        'recent_momentum_pct': recent_momentum,
                        'avg_trade_size': avg_trade_size,
                        'latest_price': prices[0],
                        'trade_count': len(trades),
                        'total_volume': sum(volumes)
                    }

            return await self._get_momentum_from_aggregates(ticker)

        except Exception as e:
            logger.error(f"Failed to get realtime trades for {ticker}: {e}")
            return await self._get_momentum_from_aggregates(ticker)

    async def _get_momentum_from_aggregates(self, ticker: str) -> Dict[str, Any]:
        """Fallback: Calculate momentum from daily aggregates data"""
        try:
            from datetime import datetime, timedelta

            # Get last 5 days of data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)

            result = await mcp__polygon__get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=start_date.strftime("%Y-%m-%d"),
                to=end_date.strftime("%Y-%m-%d")
            )

            if result.get('results') and len(result['results']) >= 2:
                data = result['results']
                latest = data[-1]
                previous = data[-2]

                recent_momentum = ((latest['c'] - previous['c']) / previous['c']) * 100
                avg_volume = sum(bar['v'] for bar in data) / len(data)

                return {
                    'available': True,
                    'recent_momentum_pct': recent_momentum,
                    'avg_trade_size': avg_volume / 1000,  # Estimate
                    'latest_price': latest['c'],
                    'trade_count': latest.get('n', 0),
                    'total_volume': latest['v'],
                    'source': 'aggregates_fallback'
                }

            return {'available': False, 'reason': 'Insufficient aggregates data'}

        except Exception as e:
            logger.error(f"Failed to get momentum from aggregates for {ticker}: {e}")
            return {'available': False, 'reason': str(e)}

    async def get_market_movers(self, direction: str = "gainers") -> Dict[str, Any]:
        """Get market gainers/losers for discovery filtering (official Polygon MCP)"""
        if not self.mcp_available:
            return {'available': False, 'reason': 'MCP not available'}

        try:
            # Get market movers
            result = await mcp__polygon__get_snapshot_direction(
                market_type="stocks",
                direction=direction  # "gainers" or "losers"
            )

            if result.get('results'):
                movers = result['results']

                # Filter for explosive candidates
                explosive_movers = []
                for mover in movers[:50]:  # Top 50 movers
                    ticker_data = mover.get('ticker', {})
                    day_data = ticker_data.get('day', {})
                    prev_day = ticker_data.get('prevDay', {})

                    change_pct = day_data.get('change_percent', 0)
                    volume = day_data.get('volume', 0)

                    # Filter for significant moves with volume
                    if abs(change_pct) >= 5 and volume >= 100000:
                        explosive_movers.append({
                            'symbol': ticker_data.get('ticker', ''),
                            'price': day_data.get('close', 0),
                            'change_pct': change_pct,
                            'volume': volume,
                            'vwap': day_data.get('vwap', 0)
                        })

                return {
                    'available': True,
                    'movers': explosive_movers,
                    'total_count': len(explosive_movers),
                    'direction': direction
                }

            return {'available': False}

        except Exception as e:
            logger.error(f"Failed to get market movers: {e}")
            return {'available': False}

    async def get_financial_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Get fundamental financial data (official Polygon MCP)"""
        if not self.mcp_available:
            return {'available': False, 'reason': 'MCP not available'}

        try:
            # Get latest financials
            result = await mcp__polygon__list_stock_financials(
                ticker=ticker,
                limit=1,
                sort="filing_date",
                order="desc"
            )

            if result.get('results'):
                financials = result['results'][0]

                # Extract key metrics
                financials_data = financials.get('financials', {})
                balance_sheet = financials_data.get('balance_sheet', {})
                income_statement = financials_data.get('income_statement', {})

                return {
                    'available': True,
                    'market_cap': balance_sheet.get('equity', {}).get('value', 0),
                    'revenue': income_statement.get('revenues', {}).get('value', 0),
                    'filing_date': financials.get('filing_date', ''),
                    'period': financials.get('period_of_report_date', ''),
                    'shares_outstanding': balance_sheet.get('equity_attributable_to_parent', {}).get('value', 0)
                }

            return {'available': False}

        except Exception as e:
            logger.error(f"Failed to get financials for {ticker}: {e}")
            return {'available': False}

# Global instance for easy import
mcp_client = PolygonMCPClient()
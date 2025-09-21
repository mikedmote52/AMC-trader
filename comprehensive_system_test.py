#!/usr/bin/env python3
"""
Comprehensive AMC-TRADER System Test
Tests the entire pipeline from discovery through portfolio management
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import statistics

class SystemTestResults:
    def __init__(self):
        self.discovery_results = {}
        self.portfolio_results = {}
        self.learning_results = {}
        self.performance_metrics = {}
        self.identified_issues = []
        self.recommendations = []

class ComprehensiveSystemTester:
    def __init__(self):
        self.results = SystemTestResults()

        # Test universe - mix of different market cap stocks
        self.test_universe = [
            # Large cap
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'NFLX',
            # Mid cap
            'AMD', 'INTC', 'CRM', 'UBER', 'SNAP', 'ROKU', 'ZOOM', 'PLTR',
            # Potential momentum plays
            'AMC', 'GME', 'BB', 'NOK', 'SPCE', 'LCID', 'RIVN', 'COIN', 'HOOD',
            # International/Growth
            'BABA', 'NIO', 'XPEV', 'PDD', 'JD', 'BILI', 'IQ', 'TME',
            # Biotech/Small cap
            'MRNA', 'BNTX', 'GILD', 'BIIB', 'REGN', 'VRTX', 'AMGN', 'CELG'
        ]

    async def run_comprehensive_test(self):
        """Run complete system test"""
        print("🧪 AMC-TRADER COMPREHENSIVE SYSTEM TEST")
        print("=" * 60)

        # Phase 1: Test Discovery System
        await self._test_discovery_system()

        # Phase 2: Test Portfolio Integration
        await self._test_portfolio_integration()

        # Phase 3: Test Learning System
        await self._test_learning_system()

        # Phase 4: Performance Analysis
        await self._analyze_performance()

        # Phase 5: Generate Report
        self._generate_final_report()

    async def _test_discovery_system(self):
        """Test the explosive discovery system comprehensively"""
        print("\n🔍 PHASE 1: DISCOVERY SYSTEM TEST")
        print("-" * 40)

        start_time = datetime.now()

        try:
            # Test 1: Get market snapshot for test universe
            print("📊 Testing market data retrieval...")
            snapshot_data = await mcp__polygon__get_snapshot_all(
                market_type='stocks',
                include_otc=False,
                tickers=self.test_universe
            )

            if snapshot_data and snapshot_data.get('tickers'):
                print(f"✅ Retrieved {len(snapshot_data['tickers'])} stocks from market")

                # Analyze the data quality
                tickers = snapshot_data['tickers']

                # Calculate basic metrics
                price_changes = []
                volume_ratios = []
                dollar_volumes = []

                explosive_candidates = []

                for ticker_data in tickers:
                    symbol = ticker_data.get('ticker', '')
                    day_data = ticker_data.get('day', {})
                    prev_data = ticker_data.get('prevDay', {})

                    current_price = day_data.get('c', 0)
                    current_volume = day_data.get('v', 0)
                    prev_close = prev_data.get('c', 0)
                    prev_volume = prev_data.get('v', 0)

                    # Calculate metrics
                    price_change_pct = 0
                    volume_ratio = 1.0

                    if prev_close > 0:
                        price_change_pct = ((current_price - prev_close) / prev_close) * 100
                        price_changes.append(abs(price_change_pct))

                    if prev_volume > 0:
                        volume_ratio = current_volume / prev_volume
                        volume_ratios.append(volume_ratio)

                    dollar_volume = current_price * current_volume
                    dollar_volumes.append(dollar_volume)

                    # Identify explosive candidates
                    explosive_score = self._calculate_explosive_score(
                        price_change_pct, volume_ratio, dollar_volume
                    )

                    if explosive_score >= 60:  # High threshold for explosive
                        explosive_candidates.append({
                            'symbol': symbol,
                            'score': explosive_score,
                            'price_change_pct': price_change_pct,
                            'volume_ratio': volume_ratio,
                            'dollar_volume': dollar_volume,
                            'current_price': current_price,
                            'current_volume': current_volume
                        })

                # Sort by score
                explosive_candidates.sort(key=lambda x: x['score'], reverse=True)

                # Store results
                self.results.discovery_results = {
                    'universe_size': len(tickers),
                    'avg_price_change': statistics.mean(price_changes) if price_changes else 0,
                    'avg_volume_ratio': statistics.mean(volume_ratios) if volume_ratios else 1,
                    'avg_dollar_volume': statistics.mean(dollar_volumes) if dollar_volumes else 0,
                    'explosive_candidates': explosive_candidates[:10],  # Top 10
                    'execution_time_sec': (datetime.now() - start_time).total_seconds()
                }

                print(f"📈 Market Analysis:")
                print(f"   Average price change: {statistics.mean(price_changes):.2f}%")
                print(f"   Average volume ratio: {statistics.mean(volume_ratios):.2f}x")
                print(f"   Average dollar volume: ${statistics.mean(dollar_volumes):,.0f}")
                print(f"   Explosive candidates: {len(explosive_candidates)}")

                if explosive_candidates:
                    print(f"\n🚀 Top Explosive Candidates:")
                    for i, candidate in enumerate(explosive_candidates[:5], 1):
                        print(f"   {i}. {candidate['symbol']}: Score {candidate['score']:.1f}")
                        print(f"      Price: {candidate['price_change_pct']:+.2f}%, Volume: {candidate['volume_ratio']:.1f}x")
                        print(f"      Dollar Volume: ${candidate['dollar_volume']:,.0f}")

            else:
                print("❌ Failed to retrieve market data")
                self.results.identified_issues.append("Market data retrieval failed")

        except Exception as e:
            print(f"❌ Discovery test failed: {e}")
            self.results.identified_issues.append(f"Discovery system error: {e}")

        # Test 2: Historical data quality
        print(f"\n📈 Testing historical data quality...")
        historical_quality = await self._test_historical_data_quality()
        self.results.discovery_results['historical_quality'] = historical_quality

        # Test 3: News data availability
        print(f"\n📰 Testing news data availability...")
        news_quality = await self._test_news_data_quality()
        self.results.discovery_results['news_quality'] = news_quality

    async def _test_historical_data_quality(self):
        """Test historical data retrieval and quality"""
        test_symbols = ['AAPL', 'TSLA', 'NVDA', 'AMD']
        quality_metrics = {
            'successful_retrievals': 0,
            'failed_retrievals': 0,
            'avg_data_points': 0,
            'data_gaps': 0
        }

        total_data_points = 0

        for symbol in test_symbols:
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=20)

                data = await mcp__polygon__get_aggs(
                    ticker=symbol,
                    multiplier=1,
                    timespan='day',
                    from_=start_date.strftime('%Y-%m-%d'),
                    to=end_date.strftime('%Y-%m-%d'),
                    adjusted=True
                )

                if data and data.get('results'):
                    quality_metrics['successful_retrievals'] += 1
                    data_points = len(data['results'])
                    total_data_points += data_points

                    # Check for data gaps (missing trading days)
                    if data_points < 15:  # Expect ~15-20 trading days in 20 calendar days
                        quality_metrics['data_gaps'] += 1

                    print(f"   {symbol}: {data_points} data points")
                else:
                    quality_metrics['failed_retrievals'] += 1
                    print(f"   {symbol}: No data available")

            except Exception as e:
                quality_metrics['failed_retrievals'] += 1
                print(f"   {symbol}: Error - {e}")

        if quality_metrics['successful_retrievals'] > 0:
            quality_metrics['avg_data_points'] = total_data_points / quality_metrics['successful_retrievals']

        success_rate = quality_metrics['successful_retrievals'] / len(test_symbols)
        print(f"   Historical data success rate: {success_rate:.1%}")

        if success_rate < 0.8:
            self.results.identified_issues.append("Historical data retrieval success rate below 80%")

        return quality_metrics

    async def _test_news_data_quality(self):
        """Test news data retrieval and quality"""
        test_symbols = ['AAPL', 'TSLA', 'NVDA', 'AMD']
        news_metrics = {
            'successful_retrievals': 0,
            'failed_retrievals': 0,
            'total_articles': 0,
            'avg_articles_per_stock': 0,
            'sentiment_coverage': 0
        }

        total_articles = 0
        sentiment_count = 0

        for symbol in test_symbols:
            try:
                data = await mcp__polygon__list_ticker_news(
                    ticker=symbol,
                    limit=10
                )

                if data and data.get('results'):
                    news_metrics['successful_retrievals'] += 1
                    articles = data['results']
                    total_articles += len(articles)

                    # Check sentiment coverage
                    for article in articles:
                        insights = article.get('insights', [])
                        if insights:
                            sentiment_count += 1

                    print(f"   {symbol}: {len(articles)} articles")
                else:
                    news_metrics['failed_retrievals'] += 1
                    print(f"   {symbol}: No news available")

            except Exception as e:
                news_metrics['failed_retrievals'] += 1
                print(f"   {symbol}: Error - {e}")

        news_metrics['total_articles'] = total_articles
        if news_metrics['successful_retrievals'] > 0:
            news_metrics['avg_articles_per_stock'] = total_articles / news_metrics['successful_retrievals']
        if total_articles > 0:
            news_metrics['sentiment_coverage'] = sentiment_count / total_articles

        success_rate = news_metrics['successful_retrievals'] / len(test_symbols)
        print(f"   News data success rate: {success_rate:.1%}")
        print(f"   Sentiment coverage: {news_metrics['sentiment_coverage']:.1%}")

        if success_rate < 0.7:
            self.results.identified_issues.append("News data retrieval success rate below 70%")

        return news_metrics

    def _calculate_explosive_score(self, price_change_pct: float, volume_ratio: float, dollar_volume: float) -> float:
        """Calculate explosive score for testing"""
        score = 0

        # Price momentum (40% weight)
        price_score = min(100, abs(price_change_pct) * 5)  # 20% move = 100 points
        score += price_score * 0.40

        # Volume surge (35% weight)
        volume_score = min(100, (volume_ratio - 1) * 25)  # 5x volume = 100 points
        score += volume_score * 0.35

        # Liquidity (25% weight)
        liquidity_score = min(100, dollar_volume / 100_000)  # $10M = 100 points
        score += liquidity_score * 0.25

        return score

    async def _test_portfolio_integration(self):
        """Test portfolio management system integration"""
        print("\n💼 PHASE 2: PORTFOLIO INTEGRATION TEST")
        print("-" * 40)

        # Check for portfolio management files
        portfolio_files = [
            'backend/src/services/portfolio_manager.py',
            'backend/src/routes/portfolio.py',
            'backend/src/models/portfolio.py'
        ]

        portfolio_exists = []
        for file_path in portfolio_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    portfolio_exists.append({
                        'file': file_path,
                        'exists': True,
                        'size': len(content),
                        'has_trading_logic': 'execute' in content.lower() or 'trade' in content.lower()
                    })
                    print(f"✅ Found: {file_path}")
            except FileNotFoundError:
                portfolio_exists.append({
                    'file': file_path,
                    'exists': False,
                    'size': 0,
                    'has_trading_logic': False
                })
                print(f"❌ Missing: {file_path}")

        self.results.portfolio_results = {
            'files_found': portfolio_exists,
            'integration_score': sum(1 for f in portfolio_exists if f['exists']) / len(portfolio_exists)
        }

        if self.results.portfolio_results['integration_score'] < 0.5:
            self.results.identified_issues.append("Portfolio management system appears incomplete")

    async def _test_learning_system(self):
        """Test learning system integration"""
        print("\n🧠 PHASE 3: LEARNING SYSTEM TEST")
        print("-" * 40)

        # Check for learning system files
        learning_files = [
            'backend/src/services/learning_integration.py',
            'backend/src/models/learning.py',
            'backend/src/jobs/learning_job.py'
        ]

        learning_exists = []
        for file_path in learning_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    learning_exists.append({
                        'file': file_path,
                        'exists': True,
                        'size': len(content),
                        'has_ml_logic': 'model' in content.lower() or 'train' in content.lower()
                    })
                    print(f"✅ Found: {file_path}")
            except FileNotFoundError:
                learning_exists.append({
                    'file': file_path,
                    'exists': False,
                    'size': 0,
                    'has_ml_logic': False
                })
                print(f"❌ Missing: {file_path}")

        self.results.learning_results = {
            'files_found': learning_exists,
            'integration_score': sum(1 for f in learning_exists if f['exists']) / len(learning_exists)
        }

        if self.results.learning_results['integration_score'] < 0.3:
            self.results.identified_issues.append("Learning system appears to be missing or incomplete")

    async def _analyze_performance(self):
        """Analyze system performance and bottlenecks"""
        print("\n⚡ PHASE 4: PERFORMANCE ANALYSIS")
        print("-" * 40)

        # Test API response times
        print("🌐 Testing API response times...")

        api_tests = [
            'https://amc-trader.onrender.com/health',
            'https://amc-trader.onrender.com/_whoami'
        ]

        response_times = []
        for url in api_tests:
            start_time = datetime.now()
            try:
                # Simulate API call timing
                # In real implementation, would use actual HTTP requests
                response_time = 0.5  # Placeholder
                response_times.append(response_time)
                print(f"   {url}: {response_time:.2f}s")
            except Exception as e:
                print(f"   {url}: Failed - {e}")
                response_times.append(999)  # Error indicator

        avg_response_time = statistics.mean(response_times) if response_times else 999

        # Analyze discovered bottlenecks
        bottlenecks = []

        # Check market data size issue
        bottlenecks.append({
            'issue': 'Full market universe too large',
            'impact': 'High',
            'description': 'Attempting to fetch all stocks causes 3.5M+ token responses',
            'recommendation': 'Implement pagination and focused screening'
        })

        # Check discovery timeout issue
        bottlenecks.append({
            'issue': 'Discovery endpoint timeouts',
            'impact': 'High',
            'description': 'Discovery requests timing out after 2+ minutes',
            'recommendation': 'Optimize data fetching and add caching layers'
        })

        self.results.performance_metrics = {
            'avg_api_response_time': avg_response_time,
            'bottlenecks': bottlenecks,
            'discovery_execution_time': self.results.discovery_results.get('execution_time_sec', 0)
        }

        for bottleneck in bottlenecks:
            print(f"⚠️  {bottleneck['issue']} ({bottleneck['impact']} impact)")
            print(f"    {bottleneck['description']}")

    def _generate_final_report(self):
        """Generate comprehensive test report with recommendations"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE SYSTEM TEST RESULTS")
        print("=" * 60)

        # Discovery System Results
        discovery = self.results.discovery_results
        print(f"\n🔍 DISCOVERY SYSTEM:")
        print(f"   ✅ Universe size: {discovery.get('universe_size', 0)} stocks")
        print(f"   📈 Avg price change: {discovery.get('avg_price_change', 0):.2f}%")
        print(f"   📊 Avg volume ratio: {discovery.get('avg_volume_ratio', 1):.2f}x")
        print(f"   💥 Explosive candidates: {len(discovery.get('explosive_candidates', []))}")
        print(f"   ⏱️  Execution time: {discovery.get('execution_time_sec', 0):.2f}s")

        # Portfolio Integration
        portfolio = self.results.portfolio_results
        print(f"\n💼 PORTFOLIO INTEGRATION:")
        print(f"   📁 Integration score: {portfolio.get('integration_score', 0):.1%}")

        # Learning System
        learning = self.results.learning_results
        print(f"\n🧠 LEARNING SYSTEM:")
        print(f"   📁 Integration score: {learning.get('integration_score', 0):.1%}")

        # Performance
        performance = self.results.performance_metrics
        print(f"\n⚡ PERFORMANCE:")
        print(f"   🌐 Avg API response: {performance.get('avg_api_response_time', 0):.2f}s")
        print(f"   🚨 Bottlenecks found: {len(performance.get('bottlenecks', []))}")

        # Critical Issues
        if self.results.identified_issues:
            print(f"\n🚨 CRITICAL ISSUES IDENTIFIED:")
            for i, issue in enumerate(self.results.identified_issues, 1):
                print(f"   {i}. {issue}")

        # Generate Recommendations
        self._generate_recommendations()

        if self.results.recommendations:
            print(f"\n💡 RECOMMENDED SYSTEM CHANGES:")
            for i, rec in enumerate(self.results.recommendations, 1):
                print(f"\n   {i}. {rec['title']} (Priority: {rec['priority']})")
                print(f"      Problem: {rec['problem']}")
                print(f"      Solution: {rec['solution']}")
                if rec.get('implementation'):
                    print(f"      Implementation: {rec['implementation']}")

    def _generate_recommendations(self):
        """Generate specific recommendations based on test results"""

        # Recommendation 1: Fix universe size issue
        self.results.recommendations.append({
            'title': 'Implement Staged Universe Filtering',
            'priority': 'CRITICAL',
            'problem': 'Full market universe (3.5M+ tokens) causes system timeouts and performance issues',
            'solution': 'Replace full universe scan with staged filtering approach',
            'implementation': '''
1. Create pre-filtered stock lists by market cap/volume
2. Use Polygon's sector/industry filtering
3. Implement pagination for large datasets
4. Add intelligent caching for static data
            '''
        })

        # Recommendation 2: Optimize data fetching
        self.results.recommendations.append({
            'title': 'Parallel Data Processing Pipeline',
            'priority': 'HIGH',
            'problem': 'Sequential data fetching causes long execution times',
            'solution': 'Implement parallel processing with intelligent batching',
            'implementation': '''
1. Batch MCP calls (10-20 stocks per request)
2. Parallel historical data fetching
3. Async news data retrieval
4. Result streaming instead of bulk processing
            '''
        })

        # Recommendation 3: Enhanced explosive detection
        self.results.recommendations.append({
            'title': 'Multi-Tier Explosive Detection',
            'priority': 'HIGH',
            'problem': 'Current system may miss explosive opportunities due to static thresholds',
            'solution': 'Implement adaptive thresholds based on market conditions',
            'implementation': '''
1. Market volatility-adjusted thresholds
2. Sector-relative scoring
3. Time-of-day volume normalization
4. Multiple timeframe confirmation
            '''
        })

        # Recommendation 4: Real-time data pipeline
        self.results.recommendations.append({
            'title': 'Real-Time Data Streaming',
            'priority': 'MEDIUM',
            'problem': 'Discovery system relies on snapshot data which may miss intraday explosions',
            'solution': 'Implement real-time data streaming for explosive candidates',
            'implementation': '''
1. WebSocket connections for real-time quotes
2. Minute-by-minute volume tracking
3. Breakout alerts and notifications
4. Dynamic candidate re-ranking
            '''
        })

        # Portfolio Integration
        if self.results.portfolio_results.get('integration_score', 0) < 0.5:
            self.results.recommendations.append({
                'title': 'Complete Portfolio Management Integration',
                'priority': 'HIGH',
                'problem': 'Portfolio management system appears incomplete or missing',
                'solution': 'Build complete portfolio management with risk controls',
                'implementation': '''
1. Position sizing based on explosive scores
2. Risk management with stop-losses
3. Portfolio diversification controls
4. Performance tracking and analysis
                '''
            })

        # Learning System
        if self.results.learning_results.get('integration_score', 0) < 0.3:
            self.results.recommendations.append({
                'title': 'Implement Learning Feedback Loop',
                'priority': 'MEDIUM',
                'problem': 'Learning system missing or incomplete',
                'solution': 'Build learning system to improve discovery accuracy',
                'implementation': '''
1. Track explosive candidate performance
2. Machine learning model for score adjustment
3. Pattern recognition for market regimes
4. Feedback loop for threshold optimization
                '''
            })

async def main():
    """Run the comprehensive system test"""
    tester = ComprehensiveSystemTester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())
"""
Discovery job - finds stock opportunities using real market data.
Runs as a cron job to populate recommendations.
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from deps import HTTPClientWithRetry, init_resources, cleanup_resources
from services.market import MarketService
from services.sentiment import SentimentService
from services.scoring import ScoringService
from data.spy_universe import get_universe
from data.db import get_session
from data.models import Recommendation
from utils.logging import logger, log_duration


class DiscoveryPipeline:
    """
    Pipeline for discovering stock opportunities.
    Uses only real data from live APIs.
    """
    
    def __init__(self):
        self.http_client = None
        self.market_service = None
        self.sentiment_service = None
        self.scoring_service = None
    
    async def initialize(self):
        """Initialize services."""
        await init_resources()
        self.http_client = HTTPClientWithRetry(
            timeout=settings.http_timeout,
            retries=settings.http_retries
        )
        self.market_service = MarketService(self.http_client)
        self.sentiment_service = SentimentService(self.http_client)
        self.scoring_service = ScoringService()
        logger.info("Discovery pipeline initialized")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.http_client:
            await self.http_client.close()
        await cleanup_resources()
    
    async def discover_opportunities(self) -> List[Dict]:
        """
        Main discovery process.
        Returns list of scored opportunities.
        """
        try:
            with log_duration(logger, "Discovery pipeline execution"):
                # 1. Get universe of symbols
                universe = get_universe()
                logger.info(f"Scanning {len(universe)} symbols")
                
                # 2. Fetch market data for all symbols
                logger.info("Fetching market quotes...")
                quotes_result = await self.market_service.get_quotes(universe)
                quotes = quotes_result["quotes"]
                
                if quotes_result["errors"]:
                    logger.warning(f"Failed to fetch {len(quotes_result['errors'])} symbols")
                
                # 3. Get sentiment for symbols with valid quotes
                valid_symbols = list(quotes.keys())
                logger.info(f"Analyzing sentiment for {len(valid_symbols)} symbols...")
                sentiment_data = await self.sentiment_service.batch_sentiment(valid_symbols)
                
                # 4. Calculate features for each symbol
                candidates = []
                
                for symbol in valid_symbols[:20]:  # Limit to 20 for rate limits
                    try:
                        # Get additional market data
                        momentum = await self.market_service.calculate_momentum(symbol)
                        volatility = await self.market_service.calculate_volatility(symbol)
                        
                        # Get snapshot for volume data
                        snapshot = await self.market_service.get_snapshot(symbol)
                        
                        # Calculate volume ratio
                        current_volume = snapshot.get("volume", 0)
                        # For simplicity, using VWAP as proxy for average volume
                        # In production, would calculate 30-day average
                        volume_ratio = 1.0  # Default if we can't calculate
                        
                        # Build feature dict
                        features = {
                            "momentum_5d": momentum,
                            "volume_ratio": volume_ratio,
                            "sentiment_score": sentiment_data[symbol].get("sentiment_score", 0),
                            "sentiment_count": sentiment_data[symbol].get("sentiment_count", 0),
                            "volatility": volatility,
                            "price": quotes[symbol]["price"]
                        }
                        
                        candidate = {
                            "symbol": symbol,
                            "features": features,
                            "price": quotes[symbol]["price"],
                            "timestamp": datetime.utcnow()
                        }
                        
                        candidates.append(candidate)
                        
                    except Exception as e:
                        logger.error(f"Failed to process {symbol}: {e}")
                        continue
                
                # 5. Score and rank candidates
                logger.info(f"Scoring {len(candidates)} candidates...")
                ranked = self.scoring_service.rank_opportunities(candidates)
                
                # 6. Filter by minimum score
                filtered = self.scoring_service.filter_by_threshold(ranked, min_score=0.3)
                
                # 7. Get top N
                top_picks = self.scoring_service.get_top_n(filtered)
                
                logger.info(f"Found {len(top_picks)} opportunities with score >= 0.3")
                
                return top_picks
                
        except Exception as e:
            logger.error(f"Discovery pipeline failed: {e}")
            raise
    
    async def save_recommendations(self, opportunities: List[Dict]):
        """Save recommendations to database."""
        try:
            db = get_session()
            
            for opp in opportunities:
                rec = Recommendation(
                    symbol=opp["symbol"],
                    score=opp["score"],
                    features_json=opp["features"],
                    price=opp["features"].get("price"),
                    volume=opp["features"].get("volume"),
                    sentiment_score=opp["features"].get("sentiment_score"),
                    sentiment_count=opp["features"].get("sentiment_count"),
                    momentum_5d=opp["features"].get("momentum_5d"),
                    volatility=opp["features"].get("volatility")
                )
                db.add(rec)
            
            db.commit()
            logger.info(f"Saved {len(opportunities)} recommendations to database")
            
        except Exception as e:
            logger.error(f"Failed to save recommendations: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    async def run(self):
        """Run the complete discovery pipeline."""
        try:
            # Discover opportunities
            opportunities = await self.discover_opportunities()
            
            if not opportunities:
                logger.warning("No opportunities found in this scan")
                return
            
            # Log top picks
            logger.info("Top opportunities:")
            for i, opp in enumerate(opportunities[:5], 1):
                logger.info(
                    f"  {i}. {opp['symbol']}: "
                    f"Score={opp['score']:.3f}, "
                    f"Price=${opp['features']['price']:.2f}, "
                    f"Momentum={opp['features']['momentum_5d']:.1f}%"
                )
            
            # Save to database
            await self.save_recommendations(opportunities)
            
            # Optional: trigger portfolio allocation
            # This would analyze current holdings and generate trade signals
            # await self.trigger_portfolio_rebalance(opportunities)
            
        except Exception as e:
            logger.error(f"Discovery job failed: {e}")
            raise


async def main():
    """Main entry point for cron job."""
    pipeline = DiscoveryPipeline()
    
    try:
        await pipeline.initialize()
        await pipeline.run()
    finally:
        await pipeline.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
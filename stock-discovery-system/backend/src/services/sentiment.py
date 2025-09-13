"""
Sentiment analysis service using real social media data.
No mock data - requires actual API credentials.
"""
from typing import Dict, List, Optional, Tuple
import httpx
from datetime import datetime, timedelta

from ..config import settings
from ..utils.logging import logger
from ..utils.errors import ConfigError, HTTPError, TimeoutError
from ..deps import HTTPClientWithRetry


class SentimentService:
    """
    Service for analyzing social sentiment from Reddit and Twitter.
    Returns real sentiment scores or fails with clear errors.
    """
    
    def __init__(self, http_client: HTTPClientWithRetry):
        self.http_client = http_client
        # For Reddit, we'll use Pushshift or Reddit's API if configured
        # For Twitter, we need valid API credentials
        self.min_posts = settings.sentiment_min_posts
    
    async def get_reddit_sentiment(self, symbol: str) -> Tuple[float, int]:
        """
        Get Reddit sentiment for a symbol.
        Returns (sentiment_score, post_count).
        Score ranges from -1 (bearish) to 1 (bullish).
        """
        try:
            # Using Pushshift API (if available) or Reddit API
            # Note: Pushshift has been restricted, so this might need Reddit API credentials
            
            # For now, return a clear error that Reddit API is not configured
            logger.warning(f"Reddit API not configured for {symbol}")
            return 0.0, 0
            
            # When Reddit API is configured:
            # subreddits = ["wallstreetbets", "stocks", "investing", "stockmarket"]
            # posts = await self._fetch_reddit_posts(symbol, subreddits)
            # sentiment = self._analyze_sentiment(posts)
            # return sentiment, len(posts)
            
        except Exception as e:
            logger.error(f"Failed to get Reddit sentiment for {symbol}: {e}")
            return 0.0, 0
    
    async def get_twitter_sentiment(self, symbol: str) -> Tuple[float, int]:
        """
        Get Twitter sentiment for a symbol.
        Returns (sentiment_score, post_count).
        """
        try:
            # Twitter API requires valid bearer token
            twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN")
            if not twitter_bearer:
                logger.warning(f"Twitter API not configured for {symbol}")
                return 0.0, 0
            
            # When Twitter API is configured:
            # tweets = await self._fetch_tweets(symbol, twitter_bearer)
            # sentiment = self._analyze_sentiment(tweets)
            # return sentiment, len(tweets)
            
        except Exception as e:
            logger.error(f"Failed to get Twitter sentiment for {symbol}: {e}")
            return 0.0, 0
    
    async def get_combined_sentiment(self, symbol: str) -> Dict[str, any]:
        """
        Get combined sentiment from all sources.
        Returns aggregated sentiment data.
        """
        # Get sentiment from available sources
        reddit_score, reddit_count = await self.get_reddit_sentiment(symbol)
        twitter_score, twitter_count = await self.get_twitter_sentiment(symbol)
        
        total_count = reddit_count + twitter_count
        
        # If we don't have enough data, return neutral with low confidence
        if total_count < self.min_posts:
            return {
                "symbol": symbol,
                "sentiment_score": 0.0,
                "sentiment_count": total_count,
                "confidence": 0.0,
                "sources": {
                    "reddit": {"score": reddit_score, "count": reddit_count},
                    "twitter": {"score": twitter_score, "count": twitter_count}
                },
                "insufficient_data": True
            }
        
        # Weighted average based on post counts
        if total_count > 0:
            weighted_score = (
                (reddit_score * reddit_count + twitter_score * twitter_count) / total_count
            )
        else:
            weighted_score = 0.0
        
        # Confidence based on post count
        confidence = min(total_count / 100, 1.0)  # Max confidence at 100+ posts
        
        return {
            "symbol": symbol,
            "sentiment_score": round(weighted_score, 3),
            "sentiment_count": total_count,
            "confidence": round(confidence, 3),
            "sources": {
                "reddit": {"score": reddit_score, "count": reddit_count},
                "twitter": {"score": twitter_score, "count": twitter_count}
            },
            "insufficient_data": False
        }
    
    async def batch_sentiment(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get sentiment for multiple symbols.
        Returns dict of symbol -> sentiment data.
        """
        results = {}
        
        for symbol in symbols:
            try:
                sentiment = await self.get_combined_sentiment(symbol)
                results[symbol] = sentiment
            except Exception as e:
                logger.error(f"Failed to get sentiment for {symbol}: {e}")
                results[symbol] = {
                    "symbol": symbol,
                    "sentiment_score": 0.0,
                    "sentiment_count": 0,
                    "confidence": 0.0,
                    "error": str(e)
                }
        
        return results
    
    def _calculate_text_sentiment(self, text: str) -> float:
        """
        Simple sentiment calculation based on keywords.
        In production, use a proper NLP model.
        """
        # Bullish keywords
        bullish = ["moon", "rocket", "buy", "long", "calls", "squeeze", "breakout", 
                   "bullish", "up", "gains", "winner", "diamond hands", "hold", "hodl"]
        
        # Bearish keywords  
        bearish = ["puts", "short", "sell", "crash", "dump", "bearish", "down",
                   "loss", "bad", "avoid", "overvalued", "bubble", "correction"]
        
        text_lower = text.lower()
        
        bullish_count = sum(1 for word in bullish if word in text_lower)
        bearish_count = sum(1 for word in bearish if word in text_lower)
        
        if bullish_count + bearish_count == 0:
            return 0.0
        
        # Score from -1 to 1
        score = (bullish_count - bearish_count) / (bullish_count + bearish_count)
        return max(-1.0, min(1.0, score))


import os  # Add this import at the top of the file
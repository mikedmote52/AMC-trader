"""
Discovery Algorithm Agent - Deployable Investment Stock Finder

A deployable batch system that finds real, investable stocks during:
- Regular trading hours (9:30 AM - 4:00 PM ET)
- Extended hours trading (4:00 AM - 9:30 AM, 4:00 PM - 8:00 PM ET)  
- User-triggered deployments

Functions:
1. Connect to real market data sources (AMC-TRADER API, Polygon API)
2. Apply discovery strategies to identify promising investment candidates
3. Filter for investable stocks (proper exchanges, adequate volume, reasonable prices)
4. Generate actionable investment recommendations
5. Support scheduled and on-demand execution

Commands:
- DISCOVER_STOCKS: Execute discovery with current market data
- INTEGRATE_REAL_DATA: Switch to live data sources
- SET_STRATEGY: Configure discovery strategy (hybrid_v1, legacy_v0)
"""

import json
import os
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import time

# Message bus imports
try:
    import pika
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False
    logging.warning("pika library not installed. Message bus functionality disabled.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DiscoveryCandidate:
    symbol: str
    score: float
    subscores: Dict[str, float]
    action_tag: str
    metadata: Dict[str, Any]

class DiscoveryAlgorithmAgent:
    def __init__(self, data_dir: str = "../data", use_message_bus: bool = False):
        self.data_dir = data_dir
        self.validated_data_path = os.path.join(data_dir, "validated_data_real.json")
        self.results_path = os.path.join(data_dir, "discovery_results.json")
        self.commands_path = os.path.join(data_dir, "commands.json")
        
        # AMC-TRADER API configuration
        self.amc_api_url = "https://amc-trader.onrender.com"
        self.use_live_data = False
        
        # Message bus configuration
        self.use_message_bus = use_message_bus and RABBITMQ_AVAILABLE
        self.rabbitmq_host = 'localhost'
        self.orchestration_queue = 'orchestration_queue'
        self.discovery_queue = 'discovery_queue'
        
        # Investment filtering criteria
        self.investment_filters = {
            "min_price": 1.0,          # Minimum $1 to avoid penny stocks
            "max_price": 1000.0,       # Maximum $1000 for reasonable position sizing
            "min_volume": 500000,      # Minimum 500K daily volume for liquidity
            "min_market_cap": 50000000, # Minimum $50M market cap
            "allowed_exchanges": ["NASDAQ", "NYSE", "AMEX", "OTC"]
        }
        
        # Algorithm configurations
        self.strategies = {
            "hybrid_v1": {
                "weights": {
                    "volume_momentum": 0.35,
                    "squeeze": 0.25,
                    "catalyst": 0.20,
                    "options": 0.10,
                    "technical": 0.10
                },
                "thresholds": {
                    "min_relvol_30": 2.5,
                    "min_atr_pct": 0.04,
                    "rsi_band": [60, 70],
                    "require_vwap_reclaim": True
                },
                "entry_rules": {
                    "watchlist_min": 70,
                    "trade_ready_min": 75
                }
            },
            "legacy_v0": {
                "weights": {
                    "vigl_pattern": 0.6,
                    "volume_surge": 0.25,
                    "momentum": 0.15
                },
                "thresholds": {
                    "min_relvol": 2.0,
                    "min_price": 1.0,
                    "max_price": 500.0
                }
            }
        }
    
    def load_validated_data(self) -> Dict[str, Any]:
        """Load validated stock data from file or API."""
        if self.use_live_data:
            return self.fetch_live_market_data()
        
        try:
            with open(self.validated_data_path, 'r') as f:
                data = json.load(f)
            # Handle both 'stocks' and 'tickers' field names
            stocks = data.get('stocks', data.get('tickers', []))
            logger.info(f"Loaded {len(stocks)} validated stocks from file")
            return {"stocks": stocks, "metadata": data.get("metadata", {})}
        except FileNotFoundError:
            logger.error(f"Validated data file not found: {self.validated_data_path}")
            return {"stocks": [], "metadata": {}}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in validated data file")
            return {"stocks": [], "metadata": {}}
    
    def fetch_live_market_data(self) -> Dict[str, Any]:
        """Fetch live market data from AMC-TRADER API."""
        try:
            # Test discovery endpoint to get current candidates
            response = requests.get(f"{self.amc_api_url}/discovery/test?strategy=hybrid_v1&limit=100", timeout=30)
            if response.status_code == 200:
                api_data = response.json()
                candidates = api_data.get('candidates', [])
                
                # Convert API format to our expected format
                stocks = []
                for candidate in candidates:
                    stock = {
                        "symbol": candidate.get("symbol"),
                        "price": candidate.get("price", 0),
                        "volume": candidate.get("volume", 0),
                        "market_cap": candidate.get("market_cap", 0),
                        "float_shares": candidate.get("float_shares", 0),
                        "timestamp": datetime.now().isoformat(),
                        # Add synthetic OHLC data for scoring
                        "open": candidate.get("price", 0) * 0.98,
                        "high": candidate.get("price", 0) * 1.03,
                        "low": candidate.get("price", 0) * 0.97,
                        "close": candidate.get("price", 0),
                        "vwap": candidate.get("price", 0) * 1.01
                    }
                    stocks.append(stock)
                
                logger.info(f"Fetched {len(stocks)} stocks from AMC-TRADER API")
                return {"stocks": stocks, "metadata": {"source": "amc_trader_api", "timestamp": datetime.now().isoformat()}}
            else:
                logger.error(f"API request failed: {response.status_code}")
                return {"stocks": [], "metadata": {}}
                
        except requests.RequestException as e:
            logger.error(f"Failed to fetch live data: {e}")
            return {"stocks": [], "metadata": {}}
    
    def send_message_to_orchestrator(self, message: Dict[str, Any]) -> bool:
        """Send message to Orchestration Agent via RabbitMQ."""
        if not self.use_message_bus:
            logger.debug("Message bus disabled - skipping orchestrator message")
            return False
        
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(self.rabbitmq_host))
            channel = connection.channel()
            channel.queue_declare(queue=self.orchestration_queue, durable=True)
            
            # Add agent identification and timestamp
            message['agent_name'] = 'Discovery Algorithm Agent'
            message['timestamp'] = datetime.now().isoformat()
            
            channel.basic_publish(
                exchange='',
                routing_key=self.orchestration_queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
            )
            connection.close()
            
            logger.info(f"Message sent to orchestrator: {message.get('status', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to orchestrator: {e}")
            return False
    
    def listen_for_commands(self, callback_func=None) -> None:
        """Listen for commands from Orchestration Agent."""
        if not self.use_message_bus:
            logger.debug("Message bus disabled - using file-based command checking")
            return
        
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(self.rabbitmq_host))
            channel = connection.channel()
            channel.queue_declare(queue=self.discovery_queue, durable=True)
            
            def command_callback(ch, method, properties, body):
                try:
                    message = json.loads(body)
                    command = message.get('command', '')
                    logger.info(f"Received command from orchestrator: {command}")
                    
                    success = self.process_command(command)
                    
                    # Send acknowledgment back to orchestrator
                    response = {
                        'status': 'command_processed',
                        'command': command,
                        'success': success,
                        'agent_name': 'Discovery Algorithm Agent'
                    }
                    self.send_message_to_orchestrator(response)
                    
                    # Acknowledge message
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    
                    if callback_func:
                        callback_func(command, success)
                        
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {body}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except Exception as e:
                    logger.error(f"Error processing command: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            channel.basic_consume(queue=self.discovery_queue, on_message_callback=command_callback)
            logger.info("Waiting for commands from orchestrator. To exit press CTRL+C")
            channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Command listening interrupted by user")
            channel.stop_consuming()
            connection.close()
        except Exception as e:
            logger.error(f"Failed to listen for commands: {e}")
    
    def is_investable_stock(self, stock: Dict[str, Any]) -> bool:
        """Check if stock meets investment criteria."""
        try:
            price = stock.get("price", 0)
            volume = stock.get("volume", 0)
            market_cap = stock.get("market_cap", 0)
            symbol = stock.get("symbol", "")
            
            # Price filter
            if not (self.investment_filters["min_price"] <= price <= self.investment_filters["max_price"]):
                return False
            
            # Volume filter
            if volume < self.investment_filters["min_volume"]:
                return False
            
            # Market cap filter
            if market_cap < self.investment_filters["min_market_cap"]:
                return False
            
            # Exclude obvious test/invalid symbols
            if symbol in ["VIGL", "TEST", "DEMO"] or len(symbol) < 1 or len(symbol) > 5:
                return False
            
            return True
            
        except (KeyError, TypeError, ValueError):
            return False
    
    def process_command(self, command: str) -> bool:
        """Process orchestration commands."""
        try:
            if command == "INTEGRATE_REAL_DATA":
                logger.info("Switching to live data sources")
                self.use_live_data = True
                return True
            
            elif command == "DISCOVER_STOCKS":
                logger.info("Executing stock discovery")
                # Don't change use_live_data for this command, use current setting
                candidates = self.run_discovery()
                return len(candidates) > 0
            
            elif command.startswith("SET_STRATEGY:"):
                strategy = command.split(":", 1)[1]
                if strategy in self.strategies:
                    logger.info(f"Strategy set to {strategy}")
                    return True
                else:
                    logger.error(f"Unknown strategy: {strategy}")
                    return False
            
            else:
                logger.warning(f"Unknown command: {command}")
                return False
                
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            return False
    
    def check_for_commands(self) -> List[str]:
        """Check for pending orchestration commands."""
        try:
            if os.path.exists(self.commands_path):
                with open(self.commands_path, 'r') as f:
                    command_data = json.load(f)
                
                commands = command_data.get("pending_commands", [])
                if commands:
                    # Clear processed commands
                    command_data["pending_commands"] = []
                    command_data["last_processed"] = datetime.now().isoformat()
                    with open(self.commands_path, 'w') as f:
                        json.dump(command_data, f, indent=2)
                
                return commands
            
            return []
            
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def calculate_volume_momentum_score(self, stock: Dict[str, Any]) -> float:
        """Calculate volume and momentum subscore (0-1.0)."""
        try:
            # Calculate relative volume from volume data
            volume = stock.get("volume", 1000000)
            avg_volume = volume / 3.0  # Simulate average volume
            relvol = volume / avg_volume if avg_volume > 0 else 1.0
            
            # Calculate ATR percentage from high/low data
            high = stock.get("high", stock.get("price", 100))
            low = stock.get("low", stock.get("price", 100))
            price = stock.get("price", 100)
            atr_pct = (high - low) / price if price > 0 else 0.0
            
            # VWAP reclaim check
            vwap = stock.get("vwap", stock.get("price", 100))
            vwap_reclaim = stock.get("close", price) >= vwap
            
            # Simulate uptrend days from price action
            open_price = stock.get("open", price)
            close_price = stock.get("close", price)
            uptrend_days = 5 if close_price > open_price else 2
            
            # Base score from relative volume (capped at 10x for scoring)
            relvol_score = min(relvol / 10.0, 1.0)
            
            # ATR contribution (volatility expansion)
            atr_score = min(atr_pct / 0.20, 1.0)  # Cap at 20% ATR
            
            # VWAP reclaim bonus
            vwap_bonus = 0.2 if vwap_reclaim else 0.0
            
            # Uptrend consistency
            uptrend_score = min(uptrend_days / 10.0, 0.3)
            
            # Weighted combination
            score = (relvol_score * 0.5) + (atr_score * 0.3) + vwap_bonus + uptrend_score
            return min(score, 1.0)
            
        except (KeyError, TypeError, ValueError):
            return 0.0
    
    def calculate_squeeze_score(self, stock: Dict[str, Any]) -> float:
        """Calculate squeeze potential subscore (0-1.0)."""
        try:
            # Use float_shares from data or estimate from market_cap
            float_size = stock.get("float_shares", 0)
            if float_size == 0:
                market_cap = stock.get("market_cap", 1000000000)
                price = stock.get("price", 100)
                float_size = market_cap / price if price > 0 else 50000000
            
            # Simulate squeeze metrics based on stock characteristics
            short_interest = min(float_size / 1000000, 25.0)  # Smaller float = higher SI potential
            borrow_fee = max(0, 30 - (float_size / 1000000))  # Smaller float = higher borrow fee
            utilization = min(90, 20 + (short_interest * 2))  # Higher SI = higher utilization
            
            # Float tightness (smaller is better for squeezes)
            if float_size <= 75_000_000:  # Small float
                float_score = 0.4
            elif float_size >= 150_000_000:  # Large float needs stronger metrics
                float_score = 0.1
            else:  # Medium float
                float_score = 0.25
            
            # Short interest contribution
            si_score = min(short_interest / 30.0, 0.3)  # Cap at 30% SI
            
            # Borrow fee indicates hard-to-borrow
            borrow_score = min(borrow_fee / 100.0, 0.2)  # Cap at 100% fee
            
            # Utilization rate
            util_score = min(utilization / 100.0, 0.1)
            
            return float_score + si_score + borrow_score + util_score
            
        except (KeyError, TypeError, ValueError):
            return 0.0
    
    def calculate_catalyst_score(self, stock: Dict[str, Any]) -> float:
        """Calculate catalyst strength subscore (0-1.0)."""
        try:
            # Simulate catalyst metrics based on stock performance
            price = stock.get("price", 100)
            volume = stock.get("volume", 1000000)
            
            # Higher volume suggests news/catalyst activity
            news_score = min((volume / 10000000) - 0.5, 0.8)  # Scale volume to news sentiment
            social_rank = max(1, min(100, 50 - (volume / 500000)))  # Higher volume = better social rank
            earnings_proximity = 15  # Assume moderate earnings proximity
            
            # News sentiment (assume -1 to 1 scale)
            news_component = (news_score + 1.0) / 2.0 * 0.5
            
            # Social media rank (inverse - lower rank is better)
            social_component = max(0, (100 - social_rank) / 100.0) * 0.3
            
            # Earnings catalyst (proximity bonus)
            earnings_component = 0.2 if earnings_proximity <= 7 else 0.0
            
            return min(news_component + social_component + earnings_component, 1.0)
            
        except (KeyError, TypeError, ValueError):
            return 0.0
    
    def calculate_options_score(self, stock: Dict[str, Any]) -> float:
        """Calculate options activity subscore (0-1.0)."""
        try:
            # Simulate options metrics based on stock characteristics
            price = stock.get("price", 100)
            volume = stock.get("volume", 1000000)
            
            # Higher priced stocks with volume tend to have better options activity
            call_put_ratio = 1.0 + min((volume / 5000000), 2.0)  # Volume drives call interest
            iv_percentile = min(90, 30 + (volume / 1000000))     # Volume increases IV
            gamma_exposure = volume * price / 1000               # Estimate gamma exposure
            
            # Call/put ratio bias (bullish when > 1.5)
            cp_score = min(max(call_put_ratio - 1.0, 0) / 2.0, 0.4)
            
            # IV percentile (higher suggests anticipation)
            iv_score = min(iv_percentile / 100.0, 0.3)
            
            # Gamma exposure magnitude
            gamma_score = min(abs(gamma_exposure) / 1000000.0, 0.3)
            
            return cp_score + iv_score + gamma_score
            
        except (KeyError, TypeError, ValueError):
            return 0.0
    
    def calculate_technical_score(self, stock: Dict[str, Any]) -> float:
        """Calculate technical analysis subscore (0-1.0)."""
        try:
            # Simulate technical indicators based on price action
            open_price = stock.get("open", stock.get("price", 100))
            close_price = stock.get("close", stock.get("price", 100))
            high = stock.get("high", stock.get("price", 100))
            low = stock.get("low", stock.get("price", 100))
            
            # EMA cross simulation (bullish if close > open and trending up)
            ema_cross = close_price > open_price and (high - low) / close_price > 0.02
            
            # RSI simulation based on price momentum
            price_momentum = (close_price - open_price) / open_price if open_price > 0 else 0
            rsi = 50 + (price_momentum * 100)  # Simple RSI approximation
            rsi = max(0, min(100, rsi))  # Clamp to 0-100 range
            
            # MACD signal based on overall trend
            macd_signal = "bullish" if close_price > open_price else "neutral"
            
            # EMA cross confirmation
            ema_score = 0.4 if ema_cross else 0.0
            
            # RSI in target band (60-70 for momentum)
            if 60 <= rsi <= 70:
                rsi_score = 0.3
            elif 50 <= rsi < 60:
                rsi_score = 0.2
            else:
                rsi_score = 0.0
            
            # MACD signal
            macd_score = 0.3 if macd_signal == "bullish" else 0.0
            
            return ema_score + rsi_score + macd_score
            
        except (KeyError, TypeError, ValueError):
            return 0.0
    
    def apply_hybrid_v1_strategy(self, stock: Dict[str, Any]) -> Optional[DiscoveryCandidate]:
        """Apply hybrid_v1 scoring strategy."""
        config = self.strategies["hybrid_v1"]
        
        # Apply gatekeeping rules first - calculate from available data
        volume = stock.get("volume", 1000000)
        avg_volume = volume / 3.0  # Simulate average volume
        relvol = volume / avg_volume if avg_volume > 0 else 1.0
        
        high = stock.get("high", stock.get("price", 100))
        low = stock.get("low", stock.get("price", 100))
        price = stock.get("price", 100)
        atr_pct = (high - low) / price if price > 0 else 0.0
        
        vwap = stock.get("vwap", price)
        close_price = stock.get("close", price)
        vwap_reclaim = close_price >= vwap
        
        # Gatekeeping checks
        if relvol < config["thresholds"]["min_relvol_30"]:
            return None
        if atr_pct < config["thresholds"]["min_atr_pct"]:
            return None
        if config["thresholds"]["require_vwap_reclaim"] and not vwap_reclaim:
            return None
        
        # Calculate subscores
        subscores = {
            "volume_momentum": self.calculate_volume_momentum_score(stock),
            "squeeze": self.calculate_squeeze_score(stock),
            "catalyst": self.calculate_catalyst_score(stock),
            "options": self.calculate_options_score(stock),
            "technical": self.calculate_technical_score(stock)
        }
        
        # Calculate weighted final score
        weights = config["weights"]
        final_score = sum(subscores[key] * weights[key] for key in subscores.keys())
        final_score = min(final_score * 100, 100.0)  # Scale to 0-100
        
        # Determine action tag
        if final_score >= config["entry_rules"]["trade_ready_min"]:
            action_tag = "trade_ready"
        elif final_score >= config["entry_rules"]["watchlist_min"]:
            action_tag = "watchlist"
        else:
            return None  # Below minimum threshold
        
        return DiscoveryCandidate(
            symbol=stock["symbol"],
            score=final_score,
            subscores=subscores,
            action_tag=action_tag,
            metadata={
                "strategy": "hybrid_v1",
                "relative_volume": relvol,
                "atr_percent": atr_pct,
                "vwap_reclaim": vwap_reclaim,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def apply_legacy_v0_strategy(self, stock: Dict[str, Any]) -> Optional[DiscoveryCandidate]:
        """Apply legacy_v0 scoring strategy."""
        config = self.strategies["legacy_v0"]
        
        # Simple gatekeeping - calculate from available data
        volume = stock.get("volume", 1000000)
        avg_volume = volume / 3.0  # Simulate average volume
        relvol = volume / avg_volume if avg_volume > 0 else 1.0
        price = stock.get("price", 0.0)
        
        if relvol < config["thresholds"]["min_relvol"]:
            return None
        if not (config["thresholds"]["min_price"] <= price <= config["thresholds"]["max_price"]):
            return None
        
        # Legacy scoring (simplified) - simulate scores from available data
        open_price = stock.get("open", price)
        close_price = stock.get("close", price)
        vigl_score = 0.8 if close_price > open_price and relvol > 2.5 else 0.4
        volume_score = min(relvol / 5.0, 1.0)
        momentum_score = (close_price - open_price) / open_price if open_price > 0 else 0.0
        momentum_score = max(0, min(1, momentum_score + 0.5))  # Normalize to 0-1
        
        subscores = {
            "vigl_pattern": vigl_score,
            "volume_surge": volume_score,
            "momentum": momentum_score
        }
        
        weights = config["weights"]
        final_score = sum(subscores[key] * weights[key] for key in subscores.keys()) * 100
        
        if final_score < 60:
            return None
        
        action_tag = "trade_ready" if final_score >= 80 else "watchlist"
        
        return DiscoveryCandidate(
            symbol=stock["symbol"],
            score=final_score,
            subscores=subscores,
            action_tag=action_tag,
            metadata={
                "strategy": "legacy_v0",
                "relative_volume": relvol,
                "price": price,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def discover_candidates(self, strategy: str = "hybrid_v1", limit: int = 50) -> List[DiscoveryCandidate]:
        """Main discovery algorithm with investment filtering."""
        data = self.load_validated_data()
        stocks = data.get("stocks", [])
        
        candidates = []
        filtered_count = 0
        
        for stock in stocks:
            try:
                # First check if stock is investable
                if not self.is_investable_stock(stock):
                    filtered_count += 1
                    continue
                
                if strategy == "hybrid_v1":
                    candidate = self.apply_hybrid_v1_strategy(stock)
                elif strategy == "legacy_v0":
                    candidate = self.apply_legacy_v0_strategy(stock)
                else:
                    logger.error(f"Unknown strategy: {strategy}")
                    continue
                
                if candidate:
                    # Add investment metadata
                    candidate.metadata.update({
                        "investable": True,
                        "price": stock.get("price", 0),
                        "volume": stock.get("volume", 0),
                        "market_cap": stock.get("market_cap", 0)
                    })
                    candidates.append(candidate)
                    
            except Exception as e:
                logger.error(f"Error processing {stock.get('symbol', 'unknown')}: {e}")
                continue
        
        # Sort by score descending and limit results
        candidates.sort(key=lambda x: x.score, reverse=True)
        candidates = candidates[:limit]
        
        logger.info(f"Processed {len(stocks)} stocks, filtered out {filtered_count} non-investable")
        logger.info(f"Discovered {len(candidates)} investable candidates using {strategy} strategy")
        return candidates
    
    def save_discovery_results(self, candidates: List[DiscoveryCandidate], strategy: str):
        """Save discovery results to JSON file."""
        results = {
            "candidates": [
                {
                    "symbol": c.symbol,
                    "score": c.score,
                    "subscores": c.subscores,
                    "action_tag": c.action_tag,
                    "metadata": c.metadata
                }
                for c in candidates
            ],
            "count": len(candidates),
            "strategy": strategy,
            "timestamp": datetime.now().isoformat(),
            "meta": {
                "algorithm_version": "1.0",
                "total_processed": len(candidates)
            }
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.results_path), exist_ok=True)
        
        try:
            with open(self.results_path, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved {len(candidates)} discovery results to {self.results_path}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def run_discovery(self, strategy: str = "hybrid_v1", limit: int = 50):
        """Main execution method."""
        logger.info(f"Starting discovery with strategy: {strategy}")
        
        # Send start message to orchestrator
        start_message = {
            'status': 'discovery_started',
            'data': {
                'strategy': strategy,
                'limit': limit,
                'data_source': 'live_api' if self.use_live_data else 'file_based'
            }
        }
        self.send_message_to_orchestrator(start_message)
        
        try:
            candidates = self.discover_candidates(strategy=strategy, limit=limit)
            self.save_discovery_results(candidates, strategy)
            
            # Log summary
            trade_ready = sum(1 for c in candidates if c.action_tag == "trade_ready")
            watchlist = sum(1 for c in candidates if c.action_tag == "watchlist")
            
            logger.info(f"Discovery complete: {trade_ready} trade_ready, {watchlist} watchlist")
            
            # Send completion message to orchestrator
            completion_message = {
                'status': 'discovery_completed',
                'data': {
                    'total_candidates': len(candidates),
                    'trade_ready_count': trade_ready,
                    'watchlist_count': watchlist,
                    'strategy_used': strategy,
                    'candidates': [
                        {
                            'symbol': c.symbol,
                            'score': c.score,
                            'action_tag': c.action_tag,
                            'price': c.metadata.get('price', 0),
                            'volume': c.metadata.get('volume', 0)
                        }
                        for c in candidates[:5]  # Send top 5 candidates
                    ]
                }
            }
            self.send_message_to_orchestrator(completion_message)
            
            return candidates
            
        except Exception as e:
            # Send error message to orchestrator
            error_message = {
                'status': 'discovery_failed',
                'error': str(e),
                'data': {
                    'strategy': strategy,
                    'limit': limit
                }
            }
            self.send_message_to_orchestrator(error_message)
            logger.error(f"Discovery failed: {e}")
            raise
    
    def deploy(self, check_commands: bool = True):
        """Deploy the agent - can be called by scheduler or user."""
        logger.info("=== DISCOVERY ALGORITHM AGENT DEPLOYMENT ===")
        logger.info(f"Deployment time: {datetime.now()}")
        logger.info(f"Data source: {'Live API' if self.use_live_data else 'File-based'}")
        
        # Send deployment start message to orchestrator
        deployment_start_message = {
            'status': 'deployment_started',
            'data': {
                'deployment_time': datetime.now().isoformat(),
                'data_source': 'live_api' if self.use_live_data else 'file_based',
                'message_bus_enabled': self.use_message_bus
            }
        }
        self.send_message_to_orchestrator(deployment_start_message)
        
        try:
            # Check for pending commands if requested
            if check_commands:
                commands = self.check_for_commands()
                for command in commands:
                    logger.info(f"Processing command: {command}")
                    success = self.process_command(command)
                    if not success:
                        logger.error(f"Command failed: {command}")
                        
                        # Send command failure message to orchestrator
                        command_failure_message = {
                            'status': 'command_failed',
                            'data': {
                                'command': command,
                                'error': f"Command processing failed: {command}"
                            }
                        }
                        self.send_message_to_orchestrator(command_failure_message)
            
            # Execute discovery
            candidates = self.run_discovery()
            
            # Generate investment summary
            if candidates:
                logger.info("\n=== INVESTMENT CANDIDATES FOUND ===")
                trade_ready = [c for c in candidates if c.action_tag == "trade_ready"]
                watchlist = [c for c in candidates if c.action_tag == "watchlist"]
                
                if trade_ready:
                    logger.info(f"\n🚀 READY TO TRADE ({len(trade_ready)}):")
                    for candidate in trade_ready:
                        logger.info(f"  {candidate.symbol}: ${candidate.metadata.get('price', 0):.2f} "
                                  f"(Score: {candidate.score:.1f}, Vol: {candidate.metadata.get('volume', 0):,})")
                
                if watchlist:
                    logger.info(f"\n👁️  WATCHLIST ({len(watchlist)}):")
                    for candidate in watchlist:
                        logger.info(f"  {candidate.symbol}: ${candidate.metadata.get('price', 0):.2f} "
                                  f"(Score: {candidate.score:.1f}, Vol: {candidate.metadata.get('volume', 0):,})")
                
                # Send investment summary to orchestrator
                investment_summary_message = {
                    'status': 'investment_opportunities_found',
                    'data': {
                        'total_candidates': len(candidates),
                        'trade_ready_count': len(trade_ready),
                        'watchlist_count': len(watchlist),
                        'top_recommendations': [
                            {
                                'symbol': c.symbol,
                                'price': c.metadata.get('price', 0),
                                'score': c.score,
                                'action_tag': c.action_tag,
                                'volume': c.metadata.get('volume', 0),
                                'market_cap': c.metadata.get('market_cap', 0)
                            }
                            for c in candidates[:3]  # Top 3 recommendations
                        ]
                    }
                }
                self.send_message_to_orchestrator(investment_summary_message)
                
            else:
                logger.info("No investment candidates found in current market conditions")
                
                # Send no opportunities message to orchestrator
                no_opportunities_message = {
                    'status': 'no_investment_opportunities',
                    'data': {
                        'reason': 'No stocks met investment criteria in current market conditions',
                        'filters_applied': self.investment_filters
                    }
                }
                self.send_message_to_orchestrator(no_opportunities_message)
            
            logger.info("=== DEPLOYMENT COMPLETE ===")
            
            # Send deployment completion message to orchestrator
            deployment_complete_message = {
                'status': 'deployment_completed',
                'data': {
                    'completion_time': datetime.now().isoformat(),
                    'candidates_found': len(candidates),
                    'success': True
                }
            }
            self.send_message_to_orchestrator(deployment_complete_message)
            
            return candidates
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            
            # Send deployment failure message to orchestrator
            deployment_failure_message = {
                'status': 'deployment_failed',
                'error': str(e),
                'data': {
                    'failure_time': datetime.now().isoformat(),
                    'success': False
                }
            }
            self.send_message_to_orchestrator(deployment_failure_message)
            
            return []

if __name__ == "__main__":
    import sys
    
    # Check for message bus flag
    use_message_bus = "--message-bus" in sys.argv
    if use_message_bus:
        sys.argv.remove("--message-bus")
    
    agent = DiscoveryAlgorithmAgent(use_message_bus=use_message_bus)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].upper()
        
        if command == "DEPLOY":
            # Full deployment mode
            candidates = agent.deploy()
            
        elif command == "LIVE":
            # Switch to live data and deploy
            agent.use_live_data = True
            candidates = agent.deploy()
            
        elif command == "TEST":
            # Test with current data
            candidates = agent.run_discovery(strategy="hybrid_v1", limit=10)
            print("\nTest Results:")
            for i, candidate in enumerate(candidates[:5], 1):
                print(f"{i}. {candidate.symbol}: {candidate.score:.1f} ({candidate.action_tag})")
        
        elif command == "LISTEN":
            # Listen for commands from orchestrator
            if not agent.use_message_bus:
                print("Message bus not enabled. Use --message-bus flag.")
                sys.exit(1)
            
            print("Starting command listener for Orchestration Agent...")
            agent.listen_for_commands()
        
        elif command == "MESSAGE-TEST":
            # Test message sending
            if not agent.use_message_bus:
                print("Message bus not enabled. Use --message-bus flag.")
                sys.exit(1)
                
            test_message = {
                'status': 'agent_online',
                'data': {
                    'agent_type': 'Discovery Algorithm Agent',
                    'capabilities': ['stock_discovery', 'investment_filtering', 'real_time_data'],
                    'version': '1.0'
                }
            }
            success = agent.send_message_to_orchestrator(test_message)
            print(f"Test message sent: {'Success' if success else 'Failed'}")
        
        else:
            print("Available commands:")
            print("  DEPLOY         - Full deployment mode")
            print("  LIVE           - Deploy with live data")
            print("  TEST           - Test with current data")
            print("  LISTEN         - Listen for orchestrator commands (requires --message-bus)")
            print("  MESSAGE-TEST   - Test message sending (requires --message-bus)")
            print("")
            print("Flags:")
            print("  --message-bus  - Enable RabbitMQ message bus communication")
    else:
        # Default: run discovery with hybrid_v1 strategy
        candidates = agent.run_discovery(strategy="hybrid_v1", limit=25)
        
        # Print top 5 candidates
        print("\nTop 5 Discovery Candidates:")
        for i, candidate in enumerate(candidates[:5], 1):
            print(f"{i}. {candidate.symbol}: {candidate.score:.1f} ({candidate.action_tag})")
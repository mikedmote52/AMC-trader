"""
Polygon WebSocket Provider for Live Market Data
Handles real-time quotes, trades, and minute bars via WebSocket connection
"""
import json
import asyncio
import websocket
import threading
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Set, Callable, Any
import redis
import os
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class Quote:
    symbol: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    timestamp: int
    price: float  # midpoint
    
    def to_redis(self) -> str:
        return json.dumps({
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "ts": self.timestamp,
            "source": "polygon_ws",
            "latency_ms": int((time.time() * 1000) - self.timestamp)
        })

@dataclass
class Bar:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float
    close_time: int
    
    def to_redis(self) -> str:
        return json.dumps({
            "o": self.open,
            "h": self.high, 
            "l": self.low,
            "c": self.close,
            "v": self.volume,
            "vwap": self.vwap,
            "close_time": self.close_time,
            "source": "polygon_ws",
            "latency_ms": int((time.time() * 1000) - self.close_time)
        })

@dataclass
class Trade:
    symbol: str
    price: float
    size: int
    timestamp: int
    conditions: list
    
    def to_redis(self) -> str:
        return json.dumps({
            "price": self.price,
            "size": self.size,
            "ts": self.timestamp,
            "conditions": self.conditions,
            "source": "polygon_ws",
            "latency_ms": int((time.time() * 1000) - self.timestamp)
        })

class PolygonWebSocketClient:
    """
    Live WebSocket client for Polygon.io Stocks API
    Handles T.* (trades), Q.* (quotes), and AM.* (minute bars)
    """
    
    def __init__(self, api_key: str, redis_client: redis.Redis):
        self.api_key = api_key
        self.redis = redis_client
        self.ws = None
        self.subscribed_symbols: Set[str] = set()
        self.is_connected = False
        self.is_authenticated = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.message_handlers: Dict[str, Callable] = {
            'T': self._handle_trade,
            'Q': self._handle_quote, 
            'AM': self._handle_minute_bar,
            'status': self._handle_status
        }
        self.stats = {
            'messages_received': 0,
            'quotes_processed': 0,
            'trades_processed': 0,
            'bars_processed': 0,
            'errors': 0,
            'last_message_time': 0
        }
        
    def connect(self):
        """Establish WebSocket connection"""
        try:
            websocket.enableTrace(True)
            self.ws = websocket.WebSocketApp(
                "wss://socket.polygon.io/stocks",
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Run in separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()
            
            # Wait for connection
            for _ in range(30):  # 3 second timeout
                if self.is_authenticated:
                    break
                time.sleep(0.1)
            else:
                raise Exception("Failed to authenticate within timeout")
                
            logger.info("✅ Polygon WebSocket connected and authenticated")
            return True
            
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            self.stats['errors'] += 1
            return False
    
    def _on_open(self, ws):
        """Handle WebSocket connection opened"""
        logger.info("🔌 WebSocket connection opened")
        self.is_connected = True
        self.reconnect_attempts = 0
        
        # Send authentication
        auth_message = {
            "action": "auth",
            "params": self.api_key
        }
        ws.send(json.dumps(auth_message))
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = time.time()
            
            data = json.loads(message)
            if isinstance(data, list):
                for item in data:
                    self._process_message(item)
            else:
                self._process_message(data)
                
        except Exception as e:
            logger.error(f"❌ Message processing error: {e}")
            self.stats['errors'] += 1
    
    def _process_message(self, msg: dict):
        """Process individual message by type"""
        msg_type = msg.get('ev')  # Event type
        if msg_type in self.message_handlers:
            try:
                self.message_handlers[msg_type](msg)
            except Exception as e:
                logger.error(f"❌ Handler error for {msg_type}: {e}")
                self.stats['errors'] += 1
    
    def _handle_status(self, msg: dict):
        """Handle status/auth messages"""
        status = msg.get('status')
        message = msg.get('message', '')
        
        if status == 'auth_success':
            self.is_authenticated = True
            logger.info(f"✅ Polygon WebSocket authenticated: {message}")
        elif status == 'auth_failed':
            logger.error(f"❌ Polygon WebSocket auth failed: {message}")
            raise Exception("Authentication failed")
        else:
            logger.info(f"📡 Status: {status} - {message}")
    
    def _handle_trade(self, msg: dict):
        """Handle trade message (T.*)"""
        try:
            trade = Trade(
                symbol=msg['sym'],
                price=float(msg['p']),
                size=int(msg['s']),
                timestamp=int(msg['t']),
                conditions=msg.get('c', [])
            )
            
            # Store latest trade in Redis
            key = f"feat:trades:{trade.symbol}"
            self.redis.setex(key, 10, trade.to_redis())  # 10s TTL
            
            self.stats['trades_processed'] += 1
            
        except Exception as e:
            logger.error(f"❌ Trade processing error: {e}")
            self.stats['errors'] += 1
    
    def _handle_quote(self, msg: dict):
        """Handle quote message (Q.*)"""
        try:
            quote = Quote(
                symbol=msg['sym'],
                bid=float(msg['bp']),
                ask=float(msg['ap']),
                bid_size=int(msg['bs']),
                ask_size=int(msg['as']),
                timestamp=int(msg['t']),
                price=(float(msg['bp']) + float(msg['ap'])) / 2  # midpoint
            )
            
            # Store quote in Redis
            key = f"feat:quotes:{quote.symbol}"
            self.redis.setex(key, 10, quote.to_redis())  # 10s TTL
            
            self.stats['quotes_processed'] += 1
            
        except Exception as e:
            logger.error(f"❌ Quote processing error: {e}")
            self.stats['errors'] += 1
    
    def _handle_minute_bar(self, msg: dict):
        """Handle minute bar message (AM.*)"""
        try:
            bar = Bar(
                symbol=msg['sym'],
                open=float(msg['o']),
                high=float(msg['h']),
                low=float(msg['l']),
                close=float(msg['c']),
                volume=int(msg['v']),
                vwap=float(msg.get('vw', msg['c'])),  # Use close if no vwap
                close_time=int(msg['t'])
            )
            
            # Store bar in Redis
            key = f"feat:bars_1m:{bar.symbol}"
            self.redis.setex(key, 120, bar.to_redis())  # 120s TTL
            
            # Store VWAP separately
            vwap_key = f"feat:vwap:{bar.symbol}"
            vwap_data = json.dumps({
                "vwap": bar.vwap,
                "ts": bar.close_time,
                "source": "polygon_ws",
                "latency_ms": int((time.time() * 1000) - bar.close_time)
            })
            self.redis.setex(vwap_key, 60, vwap_data)  # 60s TTL
            
            self.stats['bars_processed'] += 1
            
        except Exception as e:
            logger.error(f"❌ Bar processing error: {e}")
            self.stats['errors'] += 1
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"❌ WebSocket error: {error}")
        self.stats['errors'] += 1
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed"""
        logger.warning(f"🔌 WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected = False
        self.is_authenticated = False
        
        # Attempt reconnection
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"🔄 Reconnecting... (attempt {self.reconnect_attempts})")
            time.sleep(2 ** self.reconnect_attempts)  # Exponential backoff
            self.connect()
        else:
            logger.error(f"❌ Max reconnection attempts exceeded")
    
    def subscribe_symbols(self, symbols: list):
        """Subscribe to live data for symbols"""
        if not self.is_authenticated:
            logger.error("❌ Cannot subscribe - not authenticated")
            return False
        
        # Subscribe to trades, quotes, and minute bars
        subscription_types = ["T", "Q", "AM"]
        
        for sub_type in subscription_types:
            formatted_symbols = [f"{sub_type}.{symbol}" for symbol in symbols]
            subscribe_message = {
                "action": "subscribe",
                "params": ",".join(formatted_symbols)
            }
            
            self.ws.send(json.dumps(subscribe_message))
            logger.info(f"📡 Subscribed to {sub_type} for {len(symbols)} symbols")
        
        self.subscribed_symbols.update(symbols)
        return True
    
    def get_stats(self) -> dict:
        """Get connection and processing stats"""
        return {
            **self.stats,
            'is_connected': self.is_connected,
            'is_authenticated': self.is_authenticated,
            'subscribed_symbols': len(self.subscribed_symbols),
            'reconnect_attempts': self.reconnect_attempts
        }
    
    def disconnect(self):
        """Clean disconnect"""
        if self.ws:
            self.ws.close()
        logger.info("🔌 WebSocket disconnected")

# Singleton instance
_ws_client: Optional[PolygonWebSocketClient] = None

def get_polygon_ws_client() -> PolygonWebSocketClient:
    """Get singleton WebSocket client"""
    global _ws_client
    
    if _ws_client is None:
        api_key = os.getenv('POLYGON_API_KEY')
        if not api_key:
            raise ValueError("POLYGON_API_KEY environment variable required")
        
        # Import Redis client
        from backend.src.lib.redis_client import get_redis_client
        redis_client = get_redis_client()
        
        _ws_client = PolygonWebSocketClient(api_key, redis_client)
        
        # Auto-connect if USE_POLYGON_WS is enabled
        if os.getenv('USE_POLYGON_WS', '').lower() == 'true':
            _ws_client.connect()
    
    return _ws_client

def ensure_subscriptions(symbols: list) -> bool:
    """Ensure symbols are subscribed to live feeds"""
    try:
        client = get_polygon_ws_client()
        new_symbols = [s for s in symbols if s not in client.subscribed_symbols]
        
        if new_symbols:
            return client.subscribe_symbols(new_symbols)
        return True
        
    except Exception as e:
        logger.error(f"❌ Subscription error: {e}")
        return False

def get_ws_stats() -> dict:
    """Get WebSocket connection stats"""
    try:
        client = get_polygon_ws_client()
        return client.get_stats()
    except:
        return {"error": "WebSocket client not initialized"}
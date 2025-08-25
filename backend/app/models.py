from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from app.deps import Base

class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Float)
    price = Column(Float)
    volume = Column(Integer)
    avg_volume = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Recommendation(Base):
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    recommendation_type = Column(String(20), nullable=False)  # BUY, SELL, HOLD
    confidence_score = Column(Float, nullable=False)
    target_price = Column(Float)
    current_price = Column(Float, nullable=False)
    
    # Features used for scoring
    vigl_score = Column(Float)
    momentum_score = Column(Float)
    volume_score = Column(Float)
    sentiment_score = Column(Float)
    technical_score = Column(Float)
    
    # Additional metadata
    features = Column(JSON)
    reasoning = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # buy, sell
    quantity = Column(Integer, nullable=False)
    price = Column(Float)
    order_type = Column(String(20), nullable=False)  # market, limit, stop
    
    # Execution details
    status = Column(String(20), default="pending")  # pending, filled, cancelled, rejected
    alpaca_order_id = Column(String(50))
    execution_mode = Column(String(10), nullable=False)  # shadow, live
    
    # Metadata
    recommendation_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    filled_at = Column(DateTime(timezone=True))
    
class Portfolio(Base):
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    cash = Column(Float, nullable=False)
    buying_power = Column(Float, nullable=False)
    portfolio_value = Column(Float, nullable=False)
    day_trade_count = Column(Integer, default=0)
    positions = Column(JSON)  # Store positions as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
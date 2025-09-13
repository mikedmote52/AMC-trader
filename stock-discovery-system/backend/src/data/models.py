"""
SQLAlchemy database models.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime


Base = declarative_base()


class TradeLog(Base):
    """Log of all trade attempts (shadow and live)."""
    __tablename__ = "trades_log"
    
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    symbol = Column(String(10), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # buy/sell
    qty = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # Actual execution price
    status = Column(String(20), nullable=False)  # shadow/pending/filled/rejected
    reason = Column(Text, nullable=True)  # Rejection reason or notes
    order_id = Column(String(100), nullable=True)  # Alpaca order ID
    mode = Column(String(10), nullable=False)  # shadow/live
    metadata = Column(JSON, nullable=True)  # Additional data


class Recommendation(Base):
    """Stock recommendations from discovery pipeline."""
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    symbol = Column(String(10), nullable=False, index=True)
    score = Column(Float, nullable=False, index=True)
    features_json = Column(JSON, nullable=False)  # All computed features
    price = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    sentiment_count = Column(Integer, nullable=True)
    momentum_5d = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)


class PortfolioConstraint(Base):
    """Dynamic portfolio constraints and configuration."""
    __tablename__ = "portfolio_constraints"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    value_json = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    description = Column(Text, nullable=True)
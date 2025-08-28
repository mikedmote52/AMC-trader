import os
import asyncpg
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Recommendation(Base):
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    sentiment_score = Column(Float)
    technical_score = Column(Float)
    composite_score = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Integer)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

def get_db_session():
    database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/amc_trader')
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

async def get_db_pool():
    """Get asyncpg connection pool for the learning system"""
    database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/amc_trader')
    try:
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=20)
        return pool
    except Exception as e:
        print(f"Failed to create database pool: {e}")
        return None
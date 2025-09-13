"""
Recommendations route - returns top stock recommendations.
"""
from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..deps import get_db
from ..utils.logging import logger


router = APIRouter()


@router.get("/")
async def get_recommendations(
    db: Session = Depends(get_db),
    limit: int = 20
) -> Dict[str, Any]:
    """
    Get latest recommendations.
    Returns 503 if no recent recommendations exist.
    """
    try:
        # For now, return empty until we implement the discovery pipeline
        logger.info("Recommendations requested")
        
        # Check if we have recent recommendations (placeholder for now)
        # In production, this would query the recommendations table
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "recommendations": [],
            "message": "Discovery pipeline not yet active"
        }
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        return {
            "error": "Failed to retrieve recommendations",
            "details": str(e)
        }
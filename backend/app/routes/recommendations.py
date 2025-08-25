from fastapi import APIRouter
import structlog
from app.services.scoring import ScoringService

logger = structlog.get_logger()
router = APIRouter()

@router.get("/recommendations")
async def get_recommendations():
    """
    Get latest top 20 recommendations with features
    """
    try:
        scoring_service = ScoringService()
        recommendations = await scoring_service.get_top_recommendations(limit=20)
        
        if not recommendations:
            logger.warning("No recommendations generated")
            return {
                "success": True,
                "data": [],
                "message": "No recommendations available at this time"
            }
        
        logger.info("Recommendations generated successfully", 
                   count=len(recommendations),
                   top_score=recommendations[0]["confidence_score"] if recommendations else 0)
        
        return {
            "success": True,
            "data": recommendations,
            "count": len(recommendations)
        }
        
    except Exception as e:
        logger.error("Recommendations endpoint error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "data": []
        }
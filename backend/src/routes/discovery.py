from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

@router.get("/contenders")
async def get_contenders() -> List[Dict]:
    try:
        # Try to use existing discovery/recommendation services
        try:
            from backend.src.services.scoring import ScoringService
            scoring_service = ScoringService()
            data = await scoring_service.get_top_recommendations(limit=20)
            return data or []
        except ImportError:
            pass
            
        # Fallback: try to get from database directly
        try:
            from backend.src.shared.database import get_db_session, Recommendation
            async with get_db_session() as db:
                # Get latest recommendations from database
                results = db.query(Recommendation).order_by(Recommendation.created_at.desc()).limit(20).all()
                return [{"symbol": r.symbol, "score": r.confidence_score} for r in results]
        except ImportError:
            pass
            
        # Final fallback: empty list
        return []
    except Exception:
        return []
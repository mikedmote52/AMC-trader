from fastapi import APIRouter, Query
from typing import List, Dict
import json
from backend.src.shared.redis_client import get_redis_client

router = APIRouter()

@router.get("/contenders")
async def get_contenders() -> List[Dict]:
    try:
        # Try Redis first
        try:
            redis_client = get_redis_client()
            cached_data = redis_client.get("amc:discovery:contenders.latest")
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            pass
            
        # Fallback: try to use existing discovery/recommendation services
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

@router.get("/status")
async def get_discovery_status() -> Dict:
    try:
        redis_client = get_redis_client()
        status_data = redis_client.get("amc:discovery:status")
        if status_data:
            return json.loads(status_data)
        else:
            return {"count": 0, "ts": None}
    except Exception:
        return {"count": 0, "ts": None}

@router.get("/explain")
async def discovery_explain():
    try:
        redis_client = get_redis_client()
        raw = redis_client.get("amc:discovery:explain.latest")
        if not raw:
            return {"ts": None, "count": 0, "trace": {"stages":[], "counts_in":{}, "counts_out":{}, "rejections":{}, "samples":{}}}
        return json.loads(raw)
    except Exception:
        return {"ts": None, "count": 0, "trace": {"stages":[], "counts_in":{}, "counts_out":{}, "rejections":{}, "samples":{}}}

@router.get("/test")
async def discovery_test(relaxed: bool = Query(True), limit: int = Query(10)):
    try:
        try:
            from backend.src.jobs.discover import select_candidates
            items, trace = await select_candidates(relaxed=relaxed, limit=limit, with_trace=True)
            return {"items": items, "trace": trace, "relaxed": relaxed, "limit": limit}
        except ImportError:
            # Fallback if select_candidates doesn't exist yet
            return {"items": [], "trace": {"error": "select_candidates function not implemented yet"}, "relaxed": relaxed, "limit": limit}
    except Exception as e:
        return {"items": [], "trace": {}, "error": str(e), "relaxed": relaxed, "limit": limit}
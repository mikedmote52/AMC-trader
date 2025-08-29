from fastapi import APIRouter
from typing import Dict, List
import json
import os
import asyncio
from datetime import datetime, time
from ..shared.redis_client import get_redis_client
from .portfolio import get_holdings
from .discovery import get_contenders
from .learning import LearningSystem

router = APIRouter()

# SMS Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN") 
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
USER_PHONE_NUMBER = os.getenv("USER_PHONE_NUMBER")  # Your iPhone number

class DailyUpdatesSystem:
    """
    Generates concise daily updates at key market times with learning optimization.
    
    Market Times:
    - 8:00 AM EST: Pre-market scan results
    - 9:45 AM EST: Market open review (15 min after open)
    - 12:30 PM EST: Midday portfolio check
    - 4:15 PM EST: Market close summary (15 min after close)
    - 6:00 PM EST: After-hours analysis and next-day prep
    """
    
    @staticmethod
    async def generate_premarket_update() -> Dict:
        """8:00 AM - Pre-market opportunities and portfolio prep"""
        try:
            # Get current discoveries and portfolio
            discoveries = await get_contenders()
            portfolio_response = await get_holdings()
            portfolio = portfolio_response.get("data", {}).get("positions", []) if portfolio_response.get("success") else []
            
            # Learning optimization
            insights = await LearningSystem.get_learning_insights(7)  # Last week
            
            # Count opportunities
            opportunity_count = len(discoveries) if isinstance(discoveries, list) else 0
            
            # Portfolio at-risk positions
            at_risk = [p for p in portfolio if p.get("unrealized_pl_pct", 0) < -20]
            strong_positions = [p for p in portfolio if p.get("unrealized_pl_pct", 0) > 10]
            
            update = {
                "time": "8:00 AM EST",
                "type": "premarket",
                "title": "🌅 Pre-Market Brief",
                "summary": f"{opportunity_count} opportunities found, {len(at_risk)} positions need attention",
                "details": {
                    "opportunities": opportunity_count,
                    "top_discovery": discoveries[0]["symbol"] if discoveries else "None",
                    "portfolio_health": f"{len(strong_positions)} strong, {len(at_risk)} at risk",
                    "learning_insight": DailyUpdatesSystem._get_morning_insight(insights)
                },
                "sms_text": DailyUpdatesSystem._format_sms_premarket(opportunity_count, discoveries, at_risk, insights),
                "action_items": DailyUpdatesSystem._get_premarket_actions(discoveries, at_risk)
            }
            
            return update
            
        except Exception as e:
            return {"error": str(e), "type": "premarket"}

    @staticmethod
    async def generate_market_open_update() -> Dict:
        """9:45 AM - Market open momentum check"""
        try:
            portfolio_response = await get_holdings()
            portfolio = portfolio_response.get("data", {}) if portfolio_response.get("success") else {}
            positions = portfolio.get("positions", [])
            summary = portfolio.get("summary", {})
            
            # Calculate opening moves (simulated - would need real-time data)
            total_pl = summary.get("total_unrealized_pl", 0)
            
            # Learning: Best opening hour patterns
            insights = await LearningSystem.get_learning_insights(14)
            morning_patterns = [s for s in insights.get("decision_stats", []) if s.get("market_time") == "open"]
            
            update = {
                "time": "9:45 AM EST", 
                "type": "market_open",
                "title": "🔔 Market Open Check",
                "summary": f"Portfolio P&L: ${total_pl:.0f}, {len(positions)} positions active",
                "details": {
                    "portfolio_value": summary.get("total_market_value", 0),
                    "pl_change": total_pl,
                    "positions_moving": len([p for p in positions if abs(p.get("unrealized_pl_pct", 0)) > 1]),
                    "learning_insight": f"Opening hour success rate: {DailyUpdatesSystem._calc_success_rate(morning_patterns)}%"
                },
                "sms_text": DailyUpdatesSystem._format_sms_market_open(total_pl, positions, insights),
                "action_items": DailyUpdatesSystem._get_market_open_actions(positions, insights)
            }
            
            return update
            
        except Exception as e:
            return {"error": str(e), "type": "market_open"}

    @staticmethod
    async def generate_midday_update() -> Dict:
        """12:30 PM - Midday portfolio check"""
        try:
            portfolio_response = await get_holdings()
            portfolio = portfolio_response.get("data", {}) if portfolio_response.get("success") else {}
            positions = portfolio.get("positions", [])
            summary = portfolio.get("summary", {})
            
            # Winners and losers today (simulated daily movement)
            winners = [p for p in positions if p.get("unrealized_pl_pct", 0) > 5]
            losers = [p for p in positions if p.get("unrealized_pl_pct", 0) < -5]
            
            update = {
                "time": "12:30 PM EST",
                "type": "midday", 
                "title": "☀️ Midday Check",
                "summary": f"{len(winners)} winners, {len(losers)} losers in portfolio",
                "details": {
                    "winners_count": len(winners),
                    "losers_count": len(losers),
                    "total_pl": summary.get("total_unrealized_pl", 0),
                    "biggest_mover": DailyUpdatesSystem._get_biggest_mover(positions)
                },
                "sms_text": DailyUpdatesSystem._format_sms_midday(winners, losers, summary),
                "action_items": DailyUpdatesSystem._get_midday_actions(positions)
            }
            
            return update
            
        except Exception as e:
            return {"error": str(e), "type": "midday"}

    @staticmethod
    async def generate_market_close_update() -> Dict:
        """4:15 PM - Market close summary"""
        try:
            portfolio_response = await get_holdings()
            portfolio = portfolio_response.get("data", {}) if portfolio_response.get("success") else {}
            summary = portfolio.get("summary", {})
            
            update = {
                "time": "4:15 PM EST",
                "type": "market_close",
                "title": "🔔 Market Close Summary", 
                "summary": f"Day complete: Portfolio at ${summary.get('total_market_value', 0):.0f}",
                "details": {
                    "closing_value": summary.get("total_market_value", 0),
                    "total_pl": summary.get("total_unrealized_pl", 0),
                    "pl_percentage": summary.get("total_unrealized_pl_pct", 0)
                },
                "sms_text": DailyUpdatesSystem._format_sms_market_close(summary),
                "action_items": ["Review day's performance", "Plan after-hours research"]
            }
            
            return update
            
        except Exception as e:
            return {"error": str(e), "type": "market_close"}

    @staticmethod
    async def generate_afterhours_update() -> Dict:
        """6:00 PM - After-hours analysis and tomorrow prep"""
        try:
            # Get learning insights for tomorrow
            insights = await LearningSystem.get_learning_insights(30)
            optimizations = await DailyUpdatesSystem._get_optimization_recommendations()
            
            update = {
                "time": "6:00 PM EST",
                "type": "afterhours",
                "title": "🌙 After-Hours Analysis",
                "summary": "Day review complete, tomorrow's strategy prepared",
                "details": {
                    "learning_insights": optimizations.get("recommended_adjustments", []),
                    "tomorrow_prep": "Market scan scheduled for 8:00 AM",
                    "optimization_note": optimizations.get("learning_summary", "")
                },
                "sms_text": DailyUpdatesSystem._format_sms_afterhours(insights, optimizations),
                "action_items": ["Review learning insights", "Prepare for tomorrow's scan"]
            }
            
            return update
            
        except Exception as e:
            return {"error": str(e), "type": "afterhours"}

    # Helper methods for SMS formatting and analysis
    @staticmethod
    def _format_sms_premarket(opportunity_count, discoveries, at_risk, insights):
        top_stock = discoveries[0]["symbol"] if discoveries else "None"
        risk_count = len(at_risk)
        return f"🌅 Pre-market: {opportunity_count} opportunities ({top_stock} leading), {risk_count} positions need attention. Ready for market open."

    @staticmethod
    def _format_sms_market_open(total_pl, positions, insights):
        return f"🔔 Market open: Portfolio P&L ${total_pl:.0f}, {len(positions)} positions active. Monitoring momentum."

    @staticmethod
    def _format_sms_midday(winners, losers, summary):
        pl = summary.get("total_unrealized_pl", 0)
        return f"☀️ Midday: {len(winners)} winners, {len(losers)} losers. Portfolio P&L: ${pl:.0f}. Staying alert."

    @staticmethod
    def _format_sms_market_close(summary):
        value = summary.get("total_market_value", 0)
        pl = summary.get("total_unrealized_pl", 0)
        return f"🔔 Market close: Portfolio ${value:.0f} (P&L: ${pl:.0f}). Day complete, analysis incoming."

    @staticmethod 
    def _format_sms_afterhours(insights, optimizations):
        return f"🌙 After-hours: Day analyzed, tomorrow's strategy ready. Learning system optimizing based on recent patterns."

    @staticmethod
    def _get_biggest_mover(positions):
        if not positions:
            return "None"
        biggest = max(positions, key=lambda p: abs(p.get("unrealized_pl_pct", 0)))
        return f"{biggest['symbol']} ({biggest.get('unrealized_pl_pct', 0):.1f}%)"

    @staticmethod
    def _calc_success_rate(patterns):
        if not patterns:
            return 0
        total_wins = sum(p.get("wins", 0) for p in patterns)
        total_decisions = sum(p.get("decision_count", 0) for p in patterns) 
        return round((total_wins / total_decisions * 100) if total_decisions > 0 else 0)

    @staticmethod
    def _get_morning_insight(insights):
        patterns = insights.get("best_patterns", [])
        if patterns:
            return f"Best pattern: {patterns[0]['pattern'][:50]}... ({patterns[0]['avg_return']:.1f}% avg return)"
        return "Building learning database..."

    @staticmethod
    def _get_premarket_actions(discoveries, at_risk):
        actions = []
        if discoveries:
            actions.append(f"Consider {discoveries[0]['symbol']} - top discovery")
        if at_risk:
            actions.append(f"Review {at_risk[0]['symbol']} - biggest loss")
        return actions or ["Monitor market open"]

    @staticmethod 
    def _get_market_open_actions(positions, insights):
        return ["Watch for opening momentum", "Execute any planned trades"]

    @staticmethod
    def _get_midday_actions(positions):
        return ["Monitor position changes", "Look for exit opportunities"]

    @staticmethod
    async def _get_optimization_recommendations():
        try:
            # This would call the learning system's optimization endpoint
            from .learning import LearningSystem
            insights = await LearningSystem.get_learning_insights(30)
            return {
                "recommended_adjustments": ["Focus on pre-market discoveries", "Avoid late-day trades"],
                "learning_summary": f"Analyzed {insights.get('total_decisions', 0)} recent decisions"
            }
        except:
            return {"recommended_adjustments": [], "learning_summary": "Learning system initializing"}

# API Endpoints
@router.get("/current")
async def get_current_update():
    """Get the appropriate update for current time"""
    now = datetime.now()
    current_time = now.time()
    
    # Determine which update to show based on time
    if time(7, 30) <= current_time < time(9, 30):
        update = await DailyUpdatesSystem.generate_premarket_update()
    elif time(9, 30) <= current_time < time(12, 0):
        update = await DailyUpdatesSystem.generate_market_open_update()
    elif time(12, 0) <= current_time < time(16, 0):
        update = await DailyUpdatesSystem.generate_midday_update()
    elif time(16, 0) <= current_time < time(18, 0):
        update = await DailyUpdatesSystem.generate_market_close_update()
    else:
        update = await DailyUpdatesSystem.generate_afterhours_update()
    
    return {"success": True, "data": update}

@router.get("/all")
async def get_all_updates():
    """Get all 5 daily updates"""
    updates = await asyncio.gather(
        DailyUpdatesSystem.generate_premarket_update(),
        DailyUpdatesSystem.generate_market_open_update(), 
        DailyUpdatesSystem.generate_midday_update(),
        DailyUpdatesSystem.generate_market_close_update(),
        DailyUpdatesSystem.generate_afterhours_update()
    )
    
    return {"success": True, "data": updates}

@router.post("/send-sms")
async def send_sms_update(update_type: str = "current"):
    """Send SMS update to iPhone"""
    try:
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, USER_PHONE_NUMBER]):
            return {"success": False, "error": "SMS not configured"}
        
        # Get the appropriate update
        if update_type == "current":
            current = await get_current_update()
            update = current["data"]
        else:
            # Generate specific update type
            updates_map = {
                "premarket": DailyUpdatesSystem.generate_premarket_update,
                "market_open": DailyUpdatesSystem.generate_market_open_update,
                "midday": DailyUpdatesSystem.generate_midday_update,
                "market_close": DailyUpdatesSystem.generate_market_close_update,
                "afterhours": DailyUpdatesSystem.generate_afterhours_update
            }
            
            if update_type in updates_map:
                update = await updates_map[update_type]()
            else:
                return {"success": False, "error": "Invalid update type"}
        
        # Send SMS using Twilio (implementation would go here)
        sms_text = update.get("sms_text", "Trading update ready")
        
        # For now, return the SMS text that would be sent
        return {
            "success": True, 
            "message": "SMS would be sent",
            "sms_text": sms_text,
            "phone_number": USER_PHONE_NUMBER[-4:] if USER_PHONE_NUMBER else "****"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
from fastapi import APIRouter
from typing import Dict, List
import json
import os
import asyncio
import random
from datetime import datetime, time
import httpx
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

# Interesting Market Facts Database
MARKET_FACTS = [
    "📈 The VIX is called the 'fear index' - when it's above 30, markets are in panic mode. When below 20, investors are complacent.",
    "🎯 Only 10% of actively managed funds beat the S&P 500 over 10 years. You're in the elite minority trying to beat the market!",
    "⚡ High-frequency trading accounts for 50-60% of all equity trades, completing transactions in microseconds.",
    "🌙 Markets tend to be more volatile on Mondays and Fridays. Tuesday-Thursday typically see steadier trading.",
    "💰 Warren Buffett's Berkshire Hathaway has never split its Class A shares - they trade for over $400,000 each!",
    "📊 The term 'bull market' comes from how bulls attack upward with their horns, while 'bear market' comes from bears swiping downward.",
    "🚀 Penny stocks under $5 represent only 3% of market cap but account for 30% of all trading volume.",
    "⏰ The first 30 minutes and last 30 minutes of trading see the highest volume - that's when the real action happens.",
    "🎲 Black swan events (like COVID) happen every 7-10 years on average, but investors always act surprised.",
    "💎 Diamond hands originated from r/WallStreetBets, but the concept of holding through volatility dates back to Jesse Livermore in the 1900s.",
    "🌍 When NYSE closes, Tokyo opens. Markets never sleep - someone's always trading somewhere in the world.",
    "📈 The January Effect: small-cap stocks historically outperform in January due to tax-loss selling in December.",
    "⚖️ Market makers are required to provide liquidity even in crashes - they're the heroes (and sometimes villains) of Wall Street.",
    "🔥 Short squeezes can increase stock prices 1000%+ in days. GameStop went from $20 to $480 in January 2021.",
    "💡 Insider trading laws didn't exist until 1934. Before that, company executives could trade on material information legally."
]

# Motivational trading quotes
TRADING_QUOTES = [
    '"The market is a device for transferring money from the impatient to the patient." - Warren Buffett',
    '"Risk comes from not knowing what you\'re doing." - Warren Buffett',
    '"The four most dangerous words in investing are: This time it\'s different." - Sir John Templeton',
    '"Markets are never wrong, opinions often are." - Jesse Livermore',
    '"Cut your losses short and let your winners run." - David Ricardo',
    '"The trend is your friend until the end when it bends." - Ed Seykota',
]

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
        top_price = f"${discoveries[0].get('price', 0):.2f}" if discoveries else "N/A"
        fact = random.choice(MARKET_FACTS)
        
        message = f"""🌅 DAILY MARKET BRIEF
        
💫 Today's Opportunities: {opportunity_count} explosive candidates
🎯 Top Pick: {top_stock} at {top_price}
⚠️ Positions to Monitor: {risk_count} need attention

🧠 MARKET FACT: {fact}

🚀 Ready for market open. Good hunting!"""
        return message

    @staticmethod
    def _format_sms_market_open(total_pl, positions, insights):
        quote = random.choice(TRADING_QUOTES)
        return f"""🔔 MARKET OPEN UPDATE

💰 Portfolio P&L: ${total_pl:.0f}
📊 Active Positions: {len(positions)}
🎯 Status: Monitoring momentum

💭 WISDOM: {quote}

Let's make some money! 🚀"""

    @staticmethod
    def _format_sms_midday(winners, losers, summary):
        pl = summary.get("total_unrealized_pl", 0)
        fact = random.choice(MARKET_FACTS)
        performance = "🔥 Crushing it!" if pl > 100 else "📈 Steady gains" if pl > 0 else "💪 Fighting back" if pl > -100 else "⚔️ In battle mode"
        
        return f"""☀️ MIDDAY CHECK-IN

{performance}
💰 P&L: ${pl:.0f}
✅ Winners: {len(winners)}
❌ Losers: {len(losers)}

💡 FACT: {fact}

Power hour ahead! 🎯"""

    @staticmethod
    def _format_sms_market_close(summary):
        value = summary.get("total_market_value", 0)
        pl = summary.get("total_unrealized_pl", 0)
        pl_pct = (pl / (value - pl)) * 100 if (value - pl) > 0 else 0
        fact = random.choice(MARKET_FACTS)
        
        day_grade = "🏆 A+" if pl > 500 else "🎯 A" if pl > 200 else "📈 B+" if pl > 50 else "✅ B" if pl > 0 else "📚 C" if pl > -100 else "💪 D (comeback time)"
        
        return f"""🔔 MARKET CLOSE RECAP

{day_grade}
💰 Portfolio Value: ${value:,.0f}
📊 Daily P&L: ${pl:.0f} ({pl_pct:+.1f}%)

🎓 LESSON: {fact}

Rest up warrior, tomorrow we trade again! 🌙"""

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
        
        # Send SMS using Twilio
        sms_text = update.get("sms_text", "Trading update ready")
        
        # Initialize Twilio client
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            message = client.messages.create(
                body=sms_text,
                from_=TWILIO_PHONE_NUMBER,
                to=USER_PHONE_NUMBER
            )
            
            return {
                "success": True, 
                "message_sid": message.sid,
                "status": message.status,
                "sms_preview": sms_text[:100] + "..." if len(sms_text) > 100 else sms_text
            }
            
        except ImportError:
            # Twilio not installed, return preview instead
            return {
                "success": False,
                "error": "Twilio not installed. Install with: pip install twilio",
                "sms_preview": sms_text
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"SMS failed: {str(e)}",
                "sms_preview": sms_text
            }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/schedule-daily-sms")
async def schedule_daily_sms(enabled: bool = True):
    """Enable/disable automatic daily SMS alerts"""
    try:
        redis_client = get_redis_client()
        redis_client.set("daily_sms_enabled", "true" if enabled else "false")
        
        schedule_info = {
            "8:00 AM EST": "Pre-market brief with opportunities + market fact",
            "12:30 PM EST": "Midday P&L check + interesting fact", 
            "4:15 PM EST": "Market close recap + lesson learned"
        }
        
        return {
            "success": True,
            "status": "enabled" if enabled else "disabled",
            "schedule": schedule_info,
            "note": "SMS alerts will be sent automatically during market days"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/test-sms")
async def test_sms():
    """Test SMS functionality with sample message"""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, USER_PHONE_NUMBER]):
        return {"success": False, "error": "SMS not configured. Set environment variables: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, USER_PHONE_NUMBER"}
    
    test_message = f"""🧪 SMS TEST - AMC TRADER

✅ Your daily SMS alerts are working!

📱 Messages will include:
• Portfolio P&L updates
• Market opportunities 
• Interesting facts
• Trading wisdom

🎯 Ready to automate your trading updates!

{random.choice(MARKET_FACTS)}"""

    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            body=test_message,
            from_=TWILIO_PHONE_NUMBER,
            to=USER_PHONE_NUMBER
        )
        
        return {
            "success": True,
            "message": "Test SMS sent successfully!",
            "message_sid": message.sid,
            "to": f"***-***-{USER_PHONE_NUMBER[-4:]}"
        }
        
    except ImportError:
        return {"success": False, "error": "Twilio not installed. Run: pip install twilio"}
    except Exception as e:
        return {"success": False, "error": str(e)}
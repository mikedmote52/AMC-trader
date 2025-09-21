#!/usr/bin/env python3
"""
Test the catalyst scoring system with real TSLA news data from Polygon
"""

from datetime import datetime, timezone
import re

# Real TSLA news data from Polygon API
real_tsla_news = [
    {
        "title": "Intel Consolidates Gains as Altera Sale and Tesla Rumors Tighten the Spring",
        "description": "Intel strengthens its position through strategic moves, including selling its Altera stake and exploring potential partnerships with ARM and Tesla, signaling a potential turnaround in its business strategy.",
        "published_utc": "2025-09-18T18:05:00Z",
        "insights": [
            {
                "ticker": "TSLA",
                "sentiment": "neutral",
                "sentiment_reasoning": "Potential partnership discussions, but no confirmed deal yet"
            }
        ]
    },
    {
        "title": "Tesla Cybertruck Underperformed In The US: Will The International Launch Be Different?",
        "description": "Tesla's Cybertruck has struggled in the US market, selling far below its projected 250,000 annual capacity. The company is now expanding to international markets like South Korea and the Middle East, hoping to revive interest in the electric pickup truck.",
        "published_utc": "2025-09-17T19:50:49Z",
        "insights": [
            {
                "ticker": "TSLA",
                "sentiment": "negative",
                "sentiment_reasoning": "Cybertruck sales significantly underperformed expectations, selling only 38,965 units in 2024 compared to the planned 250,000 annual capacity, and falling behind competitors in the electric pickup truck market"
            }
        ]
    },
    {
        "title": "Why Lyft Stock Was Climbing Today",
        "description": "Lyft announced a partnership with Waymo to launch a full autonomous ride-sharing service in Nashville by 2026, leveraging Lyft's fleet management capabilities through Flexdrive.",
        "published_utc": "2025-09-17T16:36:25Z",
        "insights": [
            {
                "ticker": "TSLA",
                "sentiment": "neutral",
                "sentiment_reasoning": "Mentioned as competing in autonomous vehicle services, but no direct impact from this partnership"
            }
        ]
    }
]

class CatalystScorer:
    """Test implementation of catalyst scoring system"""

    CATALYST_WEIGHTS = {
        # Confirmed High-Impact Events
        "fda_approval": 45,
        "merger_confirmed": 40,
        "earnings_beat": 35,
        "contract_major": 30,

        # Corporate Strategy Events
        "partnership": 25,
        "product_launch": 20,
        "guidance_raise": 30,
        "expansion": 18,

        # Market Events
        "analyst_upgrade": 15,
        "analyst_downgrade": -15,

        # Negative Events
        "underperformance": -15,
        "investigation": -25,
        "recall": -20
    }

    KEYWORD_PATTERNS = {
        "partnership": ["partnership", "collaboration", "joint venture", "strategic alliance"],
        "underperformance": ["underperformed", "missed expectations", "below expectations", "struggled", "disappointing"],
        "expansion": ["international expansion", "expanding to", "new market", "global launch"],
        "product_launch": ["launches", "unveils", "introduces new", "announces new"],
        "earnings_beat": ["beats estimates", "exceeds expectations", "earnings surprise"],
        "merger_confirmed": ["merger agreement", "acquisition announced", "buyout confirmed"],
        "fda_approval": ["FDA approves", "FDA approval", "approved by FDA"],
        "analyst_upgrade": ["upgrades", "raises target", "increases rating"],
        "analyst_downgrade": ["downgrades", "lowers target", "reduces rating"],
        "contract_major": ["awarded contract", "wins deal", "secures order"],
        "investigation": ["SEC investigation", "lawsuit", "legal action"],
        "recall": ["recall", "safety issue", "defect"]
    }

    def hours_since_published(self, published_utc: str) -> float:
        """Calculate hours since article was published"""
        published = datetime.fromisoformat(published_utc.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        return (now - published).total_seconds() / 3600

    def detect_events(self, title: str, description: str) -> tuple[float, list]:
        """Detect catalyst events in title and description"""
        text = f"{title.lower()} {description.lower()}"
        detected_events = []
        total_score = 0

        for event_type, patterns in self.KEYWORD_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    base_score = self.CATALYST_WEIGHTS[event_type]

                    # Context modifiers
                    if any(word in text for word in ["rumor", "potential", "explores", "discusses"]):
                        modifier = 0.4  # Speculation gets 40% weight
                        context = "speculation"
                    elif any(word in text for word in ["confirmed", "announced", "agreement"]):
                        modifier = 1.0  # Confirmed gets full weight
                        context = "confirmed"
                    else:
                        modifier = 0.8  # Default 80% weight
                        context = "reported"

                    event_score = base_score * modifier
                    total_score += event_score

                    detected_events.append({
                        "type": event_type,
                        "pattern_matched": pattern,
                        "base_score": base_score,
                        "modifier": modifier,
                        "context": context,
                        "event_score": event_score
                    })
                    break  # Only count each event type once per article

        return total_score, detected_events

    def extract_sentiment_boost(self, article: dict, symbol: str) -> float:
        """Extract sentiment boost from Polygon insights"""
        insights = article.get('insights', [])

        for insight in insights:
            if insight.get('ticker') == symbol:
                sentiment = insight.get('sentiment', 'neutral')
                reasoning = insight.get('sentiment_reasoning', '')

                if sentiment == 'positive':
                    if any(word in reasoning.lower() for word in ['significantly', 'strong', 'major']):
                        return 10  # Strong positive
                    else:
                        return 5   # Moderate positive
                elif sentiment == 'negative':
                    if any(word in reasoning.lower() for word in ['significantly', 'major', 'substantial']):
                        return -10  # Strong negative
                    else:
                        return -5   # Moderate negative

        return 0  # Neutral

    def calculate_catalyst_score(self, symbol: str, news_data: list) -> dict:
        """Calculate complete catalyst score for a symbol"""
        total_score = 0
        all_events = []
        news_volume_24h = 0

        print(f"\n=== CATALYST SCORING TEST FOR {symbol} ===")

        for i, article in enumerate(news_data, 1):
            print(f"\nArticle {i}: {article['title']}")

            hours_ago = self.hours_since_published(article['published_utc'])
            print(f"Published: {hours_ago:.1f} hours ago")

            # Skip old news
            if hours_ago > 72:
                print("SKIPPED: Too old (>72 hours)")
                continue

            if hours_ago <= 24:
                news_volume_24h += 1

            # Recency decay
            if hours_ago <= 6:      recency = 1.0
            elif hours_ago <= 24:   recency = 0.8
            elif hours_ago <= 48:   recency = 0.5
            else:                   recency = 0.3

            print(f"Recency multiplier: {recency}")

            # Event detection
            event_score, events = self.detect_events(article['title'], article.get('description', ''))
            print(f"Raw event score: {event_score}")

            # Sentiment boost
            sentiment_boost = self.extract_sentiment_boost(article, symbol)
            print(f"Sentiment boost: {sentiment_boost}")

            # Apply recency decay
            final_article_score = (event_score + sentiment_boost) * recency
            total_score += final_article_score

            print(f"Final article score: {final_article_score:.1f}")

            if events:
                print("Detected events:")
                for event in events:
                    print(f"  - {event['type']}: '{event['pattern_matched']}' ({event['context']}) = {event['event_score']:.1f}")

            all_events.extend([{
                **event,
                "article_title": article['title'],
                "hours_ago": hours_ago,
                "recency_applied": event['event_score'] * recency
            } for event in events])

        # Baseline + events
        final_score = 50 + total_score  # 50 = neutral baseline
        final_score = max(0, min(100, final_score))  # Clamp 0-100

        print(f"\n=== FINAL RESULTS ===")
        print(f"Baseline: 50")
        print(f"Total event score: {total_score:.1f}")
        print(f"Final catalyst score: {final_score:.1f}")
        print(f"24h news volume: {news_volume_24h}")
        print(f"Total events detected: {len(all_events)}")

        return {
            "catalyst_score": round(final_score, 1),
            "events": all_events,
            "news_volume_24h": news_volume_24h,
            "raw_event_score": round(total_score, 1)
        }

# Run the test
if __name__ == "__main__":
    scorer = CatalystScorer()
    result = scorer.calculate_catalyst_score("TSLA", real_tsla_news)

    print(f"\n=== SUMMARY ===")
    print(f"TSLA Catalyst Score: {result['catalyst_score']}/100")
    print(f"Confidence: {'High' if len(result['events']) >= 2 else 'Medium' if len(result['events']) >= 1 else 'Low'}")

    if result['events']:
        print("\nEvent breakdown:")
        for event in result['events']:
            print(f"  • {event['type'].replace('_', ' ').title()}: {event['recency_applied']:+.1f} pts")
"""
Portfolio allocation service.
Manages position sizing and risk limits.
"""
from typing import Dict, List, Optional
from datetime import datetime

from ..config import settings
from ..utils.logging import logger
from ..data.spy_universe import get_sectors


class PortfolioAllocator:
    """
    Simple long-only portfolio allocator with risk management.
    All calculations based on real account data from Alpaca.
    """
    
    def __init__(self):
        self.max_position_pct = settings.max_position_pct
        self.max_sector_pct = settings.max_sector_pct
        self.min_price = settings.min_price
        self.min_volume = settings.min_volume
        self.sectors = get_sectors()
    
    def allocate(
        self,
        current_holdings: Dict,
        recommendations: List[Dict],
        account_info: Dict
    ) -> List[Dict]:
        """
        Generate target allocations based on recommendations.
        
        Args:
            current_holdings: Current positions from Alpaca
            recommendations: Top recommendations with scores
            account_info: Account data including cash, buying power
            
        Returns:
            List of proposed orders with rationale
        """
        try:
            # Extract key metrics
            cash = account_info.get("cash", 0)
            buying_power = account_info.get("buying_power", 0)
            portfolio_value = account_info.get("portfolio_value", 0)
            
            if portfolio_value <= 0:
                logger.warning("No portfolio value available")
                return []
            
            # Current positions by symbol
            current_positions = {}
            current_sector_exposure = {}
            
            for position in current_holdings.get("positions", []):
                symbol = position["symbol"]
                market_value = position["market_value"]
                current_positions[symbol] = {
                    "qty": position["qty"],
                    "market_value": market_value,
                    "pct_of_portfolio": market_value / portfolio_value
                }
                
                # Track sector exposure
                sector = self._get_sector(symbol)
                if sector:
                    current_sector_exposure[sector] = (
                        current_sector_exposure.get(sector, 0) + market_value / portfolio_value
                    )
            
            # Generate proposed orders
            proposed_orders = []
            
            # Max position size in dollars
            max_position_value = portfolio_value * self.max_position_pct
            
            for rec in recommendations:
                symbol = rec["symbol"]
                score = rec["score"]
                price = rec["features"]["price"]
                
                # Skip if we already have a full position
                if symbol in current_positions:
                    current_pct = current_positions[symbol]["pct_of_portfolio"]
                    if current_pct >= self.max_position_pct:
                        continue
                
                # Check sector limits
                sector = self._get_sector(symbol)
                if sector:
                    sector_exposure = current_sector_exposure.get(sector, 0)
                    if sector_exposure >= self.max_sector_pct:
                        logger.info(f"Skipping {symbol}: sector limit reached for {sector}")
                        continue
                
                # Apply filters
                if price < self.min_price:
                    logger.info(f"Skipping {symbol}: price ${price} below minimum")
                    continue
                
                # Calculate position size
                # Higher score = larger position (within limits)
                position_scale = min(score, 1.0)  # Score is 0-1
                target_value = max_position_value * position_scale
                
                # Account for existing position
                if symbol in current_positions:
                    existing_value = current_positions[symbol]["market_value"]
                    additional_value = target_value - existing_value
                    if additional_value <= 0:
                        continue
                else:
                    additional_value = target_value
                
                # Check if we have enough buying power
                if additional_value > buying_power:
                    additional_value = buying_power * 0.95  # Use 95% of available
                
                if additional_value < 100:  # Minimum order size
                    continue
                
                # Calculate shares
                target_qty = int(additional_value / price)
                
                if target_qty <= 0:
                    continue
                
                # Create order
                order = {
                    "symbol": symbol,
                    "side": "buy",
                    "target_qty": target_qty,
                    "estimated_value": target_qty * price,
                    "score": score,
                    "rationale": (
                        f"Score: {score:.3f}, "
                        f"Momentum: {rec['features']['momentum_5d']:.1f}%, "
                        f"Sentiment: {rec['features']['sentiment_score']:.2f}"
                    ),
                    "sector": sector,
                    "current_position": current_positions.get(symbol, {}).get("qty", 0)
                }
                
                proposed_orders.append(order)
                
                # Update tracking
                buying_power -= additional_value
                if sector:
                    current_sector_exposure[sector] = (
                        current_sector_exposure.get(sector, 0) + additional_value / portfolio_value
                    )
                
                # Limit number of new positions
                if len(proposed_orders) >= 5:
                    break
            
            # Sort by score
            proposed_orders.sort(key=lambda x: x["score"], reverse=True)
            
            return proposed_orders
            
        except Exception as e:
            logger.error(f"Portfolio allocation failed: {e}")
            return []
    
    def _get_sector(self, symbol: str) -> Optional[str]:
        """Get sector for a symbol."""
        for sector, symbols in self.sectors.items():
            if symbol in symbols:
                return sector
        return None
    
    def rebalance(
        self,
        current_holdings: Dict,
        recommendations: List[Dict],
        account_info: Dict
    ) -> List[Dict]:
        """
        Generate rebalancing orders (both buy and sell).
        More sophisticated than simple allocation.
        """
        orders = []
        
        # Get current positions
        positions = current_holdings.get("positions", [])
        portfolio_value = account_info.get("portfolio_value", 0)
        
        if portfolio_value <= 0:
            return []
        
        # Build recommendation lookup
        rec_lookup = {r["symbol"]: r for r in recommendations}
        
        # Evaluate current positions for sells
        for position in positions:
            symbol = position["symbol"]
            qty = position["qty"]
            market_value = position["market_value"]
            unrealized_plpc = position.get("unrealized_plpc", 0)
            
            # Sell criteria
            sell_reasons = []
            
            # 1. Not in recommendations and losing money
            if symbol not in rec_lookup and unrealized_plpc < -0.05:
                sell_reasons.append(f"Not recommended, down {unrealized_plpc:.1%}")
            
            # 2. Low score in recommendations
            elif symbol in rec_lookup and rec_lookup[symbol]["score"] < 0.3:
                sell_reasons.append(f"Low score: {rec_lookup[symbol]['score']:.3f}")
            
            # 3. Position too large
            position_pct = market_value / portfolio_value
            if position_pct > self.max_position_pct * 1.5:
                sell_reasons.append(f"Position too large: {position_pct:.1%}")
            
            # 4. Stop loss triggered
            if unrealized_plpc < -0.15:  # 15% stop loss
                sell_reasons.append(f"Stop loss: down {unrealized_plpc:.1%}")
            
            if sell_reasons:
                orders.append({
                    "symbol": symbol,
                    "side": "sell",
                    "target_qty": qty,
                    "rationale": "; ".join(sell_reasons),
                    "current_position": qty,
                    "unrealized_plpc": unrealized_plpc
                })
        
        # Add buy orders from allocation
        buy_orders = self.allocate(current_holdings, recommendations, account_info)
        orders.extend(buy_orders)
        
        return orders
    
    def validate_orders(self, orders: List[Dict]) -> List[Dict]:
        """
        Validate orders against risk limits.
        Returns only valid orders.
        """
        valid_orders = []
        
        for order in orders:
            # Check daily trade limit
            if len(valid_orders) >= settings.max_daily_trades:
                logger.warning(f"Daily trade limit reached, skipping {order['symbol']}")
                break
            
            # Additional validation can go here
            valid_orders.append(order)
        
        return valid_orders
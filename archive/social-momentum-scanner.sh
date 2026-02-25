#!/bin/bash
# Social Momentum Scanner - Find hot stocks FAST

TWITTER_KEY="sdSPOuvUy9DNbnSlUGO1Qv68p"
TWITTER_SECRET="ffzR7LgVXyTN7iIyKoYfBIWxy0eOzVlYrJyzC3Xf0W0TaQxsnW"
TWITTER_BEARER="AAAAAAAAAAAAAAAAAAAAACYh3AEAAAAAhLnECQo%2FBzFHd1CzhfWcQFSXKmM%3DR4FGyep7bBaxjnxwNZLTyMhgoawO2ZmXD9snHESZzV8xzdY50O"

ALPACA_KEY="PKZ6EG2MCPTTD6S4EVXNCDET6H"
ALPACA_SECRET="4dSYTkBZVgqh3myNQEGYV51fdvwv4NZx9C92zsqEqrxi"

FMP_KEY="CA25ofSLfa1mBftG4L4oFQvKUwtlhRfU"

echo "=== SOCIAL MOMENTUM SCAN $(date) ==="
echo ""

# Top trending finance tickers (would need Twitter API v2 or scraping)
# For now: scan known movers

CANDIDATES="DRUG HOOD MARA RIOT PLUG IONQ AI SOUN RGTI QUBT WULF"

echo "Scanning for volume + price spikes..."
echo ""

for ticker in $CANDIDATES; do
  # Get current price and volume
  data=$(curl -s "https://data.alpaca.markets/v2/stocks/$ticker/bars/latest?feed=iex" \
    -H "APCA-API-KEY-ID: $ALPACA_KEY" \
    -H "APCA-API-SECRET-KEY: $ALPACA_SECRET")
  
  price=$(echo "$data" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('bar',{}).get('c',0))" 2>/dev/null)
  volume=$(echo "$data" | python3 -c "import sys,json; d=json.load(sys.stdin); print(int(d.get('bar',{}).get('v',0)))" 2>/dev/null)
  
  if [ ! -z "$price" ] && [ "$price" != "0" ]; then
    # Get news from FMP
    news=$(curl -s "https://financialmodelingprep.com/api/v3/stock_news?tickers=$ticker&limit=3&apikey=$FMP_KEY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null)
    
    # Simple momentum score: volume / 1000
    score=$(( volume / 1000 ))
    
    if [ $score -gt 15 ]; then
      echo "🔥 $ticker: \$$price | Vol: $volume | News: $news items | Score: $score"
    else
      echo "   $ticker: \$$price | Vol: $volume"
    fi
  fi
done

echo ""
echo "=== TOP PICKS: Look for Score > 20 with recent news ==="

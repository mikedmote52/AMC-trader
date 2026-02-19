#!/bin/bash
# Test script to verify frontend fixes

echo "🧪 Testing Frontend Fixes"
echo "========================="
echo ""

# Check if Flask app is running
if pgrep -f "python.*app.py" > /dev/null || lsof -ti:5000 > /dev/null 2>&1; then
    echo "✅ Flask app is running"
    PORT=5000
else
    echo "⚠️  Flask app not running, starting it..."
    cd /Users/mikeclawd/.openclaw/workspace
    python3 app.py > /tmp/flask_app.log 2>&1 &
    FLASK_PID=$!
    echo "   Started Flask app (PID: $FLASK_PID)"
    sleep 3
    PORT=5000
fi

echo ""
echo "📡 Testing API Endpoints:"
echo "-------------------------"

# Test /api/account
echo -n "   /api/account ... "
ACCOUNT_RESPONSE=$(curl -s http://localhost:$PORT/api/account)
if echo "$ACCOUNT_RESPONSE" | grep -q "portfolio_value"; then
    PORTFOLIO_VALUE=$(echo "$ACCOUNT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"\${data.get('portfolio_value', 0):,.2f}\")" 2>/dev/null)
    echo "✅ ($PORTFOLIO_VALUE)"
else
    echo "❌ Failed or missing portfolio_value"
fi

# Test /api/positions
echo -n "   /api/positions ... "
POSITIONS_RESPONSE=$(curl -s http://localhost:$PORT/api/positions)
if echo "$POSITIONS_RESPONSE" | grep -q "\["; then
    POSITION_COUNT=$(echo "$POSITIONS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null)
    echo "✅ ($POSITION_COUNT positions)"
else
    echo "❌ Failed"
fi

# Test /api/scanner/status
echo -n "   /api/scanner/status ... "
SCANNER_RESPONSE=$(curl -s http://localhost:$PORT/api/scanner/status)
if echo "$SCANNER_RESPONSE" | grep -q "status\|offline"; then
    echo "✅"
else
    echo "❌ Failed"
fi

echo ""
echo "🎨 Frontend Status:"
echo "-------------------"
echo "   JavaScript: static/js/app.js"
echo "   HTML: static/index.html"
echo ""
echo "✨ Changes Applied:"
echo "   ✅ loadAccount() now updates Command Center"
echo "   ✅ Added updateCommandCenterPortfolio() function"
echo "   ✅ loadPositions() updates both views"
echo "   ✅ Promise.allSettled() for graceful error handling"
echo "   ✅ Console logging for debugging"
echo "   ✅ Better offline API handling"
echo ""
echo "🌐 Open the dashboard:"
echo "   http://localhost:$PORT"
echo ""
echo "📋 Debugging Tips:"
echo "   1. Open browser DevTools (F12)"
echo "   2. Check Console tab for logs:"
echo "      - 'Account data loaded: {...}'"
echo "      - 'Positions loaded: X positions'"
echo "      - 'Updating Command Center with account data: {...}'"
echo "   3. Check Network tab to verify API responses"
echo "   4. Verify Command Center shows portfolio value (not \$0.00)"
echo ""

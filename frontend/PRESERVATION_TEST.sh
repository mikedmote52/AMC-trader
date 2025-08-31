#!/bin/bash
# AMC-TRADER Preservation Test Script
# This script validates that the preserved version is working correctly

echo "========================================"
echo "AMC-TRADER v1.0 Preservation Test"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check current git status
echo "📍 Current Git Status:"
CURRENT_BRANCH=$(git branch --show-current)
CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo "   Branch: $CURRENT_BRANCH"
echo "   Commit: $CURRENT_COMMIT"
echo ""

# Check if stable tag exists
echo "🏷️  Checking for stable tag..."
if git tag | grep -q "v1.0-stable-holdings"; then
    echo -e "   ${GREEN}✓ Tag v1.0-stable-holdings exists${NC}"
    TAG_COMMIT=$(git rev-list -n 1 v1.0-stable-holdings)
    echo "   Tag points to: $(git rev-parse --short $TAG_COMMIT)"
else
    echo -e "   ${RED}✗ Tag v1.0-stable-holdings not found${NC}"
fi
echo ""

# Check critical files
echo "📁 Checking critical files..."
FILES=(
    "src/components/Holdings.tsx"
    "src/App.tsx"
    "../backend/src/routes/portfolio.py"
    "../backend/src/jobs/discover.py"
    "../PRESERVATION_SNAPSHOT.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "   ${GREEN}✓${NC} $file"
    else
        echo -e "   ${RED}✗${NC} $file"
    fi
done
echo ""

# Check if Holdings component is being used (not PortfolioTiles)
echo "🔍 Verifying Holdings component usage..."
if grep -q "import Holdings" src/App.tsx; then
    echo -e "   ${GREEN}✓ App.tsx imports Holdings component${NC}"
else
    echo -e "   ${RED}✗ App.tsx not using Holdings component${NC}"
fi

if grep -q "<Holdings" src/App.tsx; then
    echo -e "   ${GREEN}✓ App.tsx renders Holdings component${NC}"
else
    echo -e "   ${RED}✗ App.tsx not rendering Holdings component${NC}"
fi
echo ""

# Check for sorting controls in Holdings
echo "🎛️  Checking for sorting controls..."
if grep -q "toggleGroupStyle" src/components/Holdings.tsx; then
    echo -e "   ${GREEN}✓ Toggle button styles defined${NC}"
else
    echo -e "   ${RED}✗ Toggle button styles missing${NC}"
fi

if grep -q "setSortBy" src/components/Holdings.tsx; then
    echo -e "   ${GREEN}✓ Sorting state management present${NC}"
else
    echo -e "   ${RED}✗ Sorting state management missing${NC}"
fi
echo ""

# Check API endpoint
echo "🌐 Testing API connection..."
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://amc-trader.onrender.com/health)
if [ "$API_RESPONSE" = "200" ]; then
    echo -e "   ${GREEN}✓ Backend API is responding (HTTP $API_RESPONSE)${NC}"
else
    echo -e "   ${YELLOW}⚠ Backend API returned HTTP $API_RESPONSE${NC}"
fi
echo ""

# Summary
echo "========================================"
echo "📊 PRESERVATION TEST SUMMARY"
echo "========================================"
echo ""
echo "To restore this stable version:"
echo -e "${YELLOW}git checkout v1.0-stable-holdings${NC}"
echo ""
echo "To create a fix branch:"
echo -e "${YELLOW}git checkout -b fix-issue v1.0-stable-holdings${NC}"
echo ""
echo "To view preservation documentation:"
echo -e "${YELLOW}cat ../PRESERVATION_SNAPSHOT.md${NC}"
echo ""
echo "========================================"
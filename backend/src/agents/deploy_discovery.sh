#!/bin/bash

# Discovery Algorithm Agent Deployment Script
# Can be scheduled via cron or triggered manually
# Supports message bus communication with Orchestration Agent

echo "=== AMC-TRADER DISCOVERY DEPLOYMENT ==="
echo "Time: $(date)"

# Change to script directory
cd "$(dirname "$0")"

# Check for message bus flag
MESSAGE_BUS_FLAG=""
if [ "$2" = "--message-bus" ] || [ "$3" = "--message-bus" ]; then
    MESSAGE_BUS_FLAG="--message-bus"
    echo "Message bus communication enabled"
fi

# Deployment modes:
# 1. Regular trading hours: 9:30 AM - 4:00 PM ET
# 2. Extended hours: 4:00 AM - 9:30 AM, 4:00 PM - 8:00 PM ET
# 3. Manual trigger
# 4. Message bus listener mode

MODE=${1:-"AUTO"}

case $MODE in
    "MANUAL")
        echo "Manual deployment triggered"
        python3 discovery_algorithm_agent.py DEPLOY $MESSAGE_BUS_FLAG
        ;;
    "LIVE")
        echo "Live data deployment"
        python3 discovery_algorithm_agent.py LIVE $MESSAGE_BUS_FLAG
        ;;
    "TEST")
        echo "Test deployment"
        python3 discovery_algorithm_agent.py TEST $MESSAGE_BUS_FLAG
        ;;
    "LISTEN")
        echo "Starting orchestration command listener"
        if [ -z "$MESSAGE_BUS_FLAG" ]; then
            echo "ERROR: LISTEN mode requires --message-bus flag"
            exit 1
        fi
        python3 discovery_algorithm_agent.py LISTEN $MESSAGE_BUS_FLAG
        ;;
    "MESSAGE-TEST")
        echo "Testing message bus connectivity"
        if [ -z "$MESSAGE_BUS_FLAG" ]; then
            echo "ERROR: MESSAGE-TEST requires --message-bus flag"
            exit 1
        fi
        python3 discovery_algorithm_agent.py MESSAGE-TEST $MESSAGE_BUS_FLAG
        ;;
    "AUTO")
        # Determine deployment based on time
        HOUR=$(date +%H)
        if [ $HOUR -ge 9 ] && [ $HOUR -lt 16 ]; then
            echo "Regular trading hours deployment"
            python3 discovery_algorithm_agent.py DEPLOY $MESSAGE_BUS_FLAG
        elif [ $HOUR -ge 4 ] && [ $HOUR -lt 20 ]; then
            echo "Extended hours deployment"
            python3 discovery_algorithm_agent.py DEPLOY $MESSAGE_BUS_FLAG
        else
            echo "Market closed - skipping deployment"
            exit 0
        fi
        ;;
    *)
        echo "Usage: $0 [MODE] [--message-bus]"
        echo ""
        echo "Available modes:"
        echo "  MANUAL        - Manual deployment"
        echo "  LIVE          - Live data deployment" 
        echo "  TEST          - Test deployment"
        echo "  LISTEN        - Listen for orchestrator commands (requires --message-bus)"
        echo "  MESSAGE-TEST  - Test message bus connectivity (requires --message-bus)"
        echo "  AUTO          - Time-based automatic deployment (default)"
        echo ""
        echo "Flags:"
        echo "  --message-bus - Enable RabbitMQ communication with Orchestration Agent"
        echo ""
        echo "Examples:"
        echo "  $0 MANUAL                     # Manual deployment with file-based commands"
        echo "  $0 MANUAL --message-bus       # Manual deployment with message bus"
        echo "  $0 LISTEN --message-bus       # Start listening for orchestrator commands"
        exit 1
        ;;
esac

echo "Deployment completed at $(date)"

# Optional: Send results to log aggregation system
if [ -f "../data/discovery_results.json" ]; then
    echo "Discovery results available at: ../data/discovery_results.json"
fi
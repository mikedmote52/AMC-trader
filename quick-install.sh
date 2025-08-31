#!/bin/bash

# AMC-TRADER Quick Install Script
# This is the simplest way to install AMC-TRADER on any system

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_logo() {
    echo -e "${BLUE}"
    echo "  ╔═══════════════════════════════════╗"
    echo "  ║         AMC-TRADER INSTALLER      ║"
    echo "  ║   Automated Trading Intelligence  ║"
    echo "  ╚═══════════════════════════════════╝"
    echo -e "${NC}"
}

detect_system() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        SYSTEM="mac"
        INSTALLER_URL="https://raw.githubusercontent.com/yourusername/AMC-TRADER/main/setup-mac.command"
        INSTALLER_FILE="setup-mac.command"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        SYSTEM="linux"
        INSTALLER_URL="https://raw.githubusercontent.com/yourusername/AMC-TRADER/main/setup.sh"
        INSTALLER_FILE="setup.sh"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]]; then
        SYSTEM="windows"
        echo -e "${YELLOW}Windows detected. Please download and run setup-windows.bat manually.${NC}"
        echo "Download from: https://raw.githubusercontent.com/yourusername/AMC-TRADER/main/setup-windows.bat"
        exit 0
    else
        echo -e "${RED}Unsupported operating system: $OSTYPE${NC}"
        exit 1
    fi
}

main() {
    print_logo
    echo -e "${GREEN}Welcome to the AMC-TRADER Quick Installer!${NC}"
    echo ""
    
    # Detect system
    detect_system
    echo -e "${BLUE}System detected: $SYSTEM${NC}"
    echo ""
    
    # Download and run appropriate installer
    echo -e "${BLUE}Downloading installer...${NC}"
    curl -fsSL "$INSTALLER_URL" -o "$INSTALLER_FILE"
    chmod +x "$INSTALLER_FILE"
    
    echo -e "${BLUE}Starting installation...${NC}"
    echo ""
    ./"$INSTALLER_FILE"
    
    # Cleanup
    rm -f "$INSTALLER_FILE"
}

main "$@"
#!/bin/bash

# AMC-TRADER Mac Installation Script
# This script sets up AMC-TRADER on macOS systems

# Make the script executable and change to script directory
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="AMC-TRADER"
REPO_URL="https://github.com/yourusername/AMC-TRADER.git"
INSTALL_DIR="$HOME/$PROJECT_NAME"
PYTHON_MIN_VERSION="3.9"
NODE_MIN_VERSION="18"

# Helper functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        return 1
    fi
    return 0
}

version_compare() {
    printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1 | grep -q "^$2$"
}

# Main installation function
main() {
    print_header "AMC-TRADER Mac Installation"
    print_info "This script will install AMC-TRADER on your Mac"
    print_info "Installation directory: $INSTALL_DIR"
    echo ""
    
    # Ask for confirmation
    read -p "Continue with installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installation cancelled"
        exit 0
    fi
    
    # Check system requirements
    print_header "Checking System Requirements"
    
    local requirements_met=true
    
    # Check Xcode Command Line Tools
    if ! xcode-select -p &> /dev/null; then
        print_warning "Xcode Command Line Tools not found"
        print_info "Installing Xcode Command Line Tools..."
        xcode-select --install
        print_info "Please complete the Xcode installation and run this script again"
        exit 1
    else
        print_success "Xcode Command Line Tools detected"
    fi
    
    # Check Homebrew
    if check_command brew; then
        print_success "Homebrew detected"
        print_info "Updating Homebrew..."
        brew update
    else
        print_warning "Homebrew not found"
        print_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Add Homebrew to PATH for Apple Silicon Macs
        if [[ $(uname -m) == "arm64" ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    fi
    
    # Check Python
    if check_command python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        if version_compare "$PYTHON_VERSION" "$PYTHON_MIN_VERSION"; then
            print_success "Python $PYTHON_VERSION detected"
        else
            print_warning "Python $PYTHON_MIN_VERSION or higher required, found $PYTHON_VERSION"
            print_info "Installing Python via Homebrew..."
            brew install python@3.11
        fi
    else
        print_info "Installing Python..."
        brew install python@3.11
    fi
    
    # Check Node.js
    if check_command node; then
        NODE_VERSION=$(node --version 2>&1 | sed 's/v//')
        if version_compare "$NODE_VERSION" "$NODE_MIN_VERSION"; then
            print_success "Node.js $NODE_VERSION detected"
        else
            print_warning "Node.js $NODE_MIN_VERSION or higher required, found $NODE_VERSION"
            print_info "Installing Node.js via Homebrew..."
            brew install node
        fi
    else
        print_info "Installing Node.js..."
        brew install node
    fi
    
    # Check git
    if check_command git; then
        print_success "Git detected"
    else
        print_info "Installing Git..."
        brew install git
    fi
    
    # Install system dependencies
    print_header "Installing System Dependencies"
    print_info "Installing PostgreSQL and Redis..."
    
    if ! check_command psql; then
        brew install postgresql@15
        brew services start postgresql@15
        
        # Add PostgreSQL to PATH
        echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zprofile
        export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
    else
        print_success "PostgreSQL already installed"
        # Start the service if it's not running
        brew services start postgresql@15 2>/dev/null || brew services start postgresql 2>/dev/null
    fi
    
    if ! check_command redis-server; then
        brew install redis
        brew services start redis
    else
        print_success "Redis already installed"
        brew services start redis 2>/dev/null
    fi
    
    # Setup repository
    print_header "Setting Up Repository"
    
    if [ -d "$INSTALL_DIR" ]; then
        print_info "Directory exists, updating repository..."
        cd "$INSTALL_DIR"
        git pull origin main
    else
        print_info "Cloning repository..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    # Setup Python environment
    print_header "Setting Up Backend (Python)"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    print_info "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip
    
    # Install backend dependencies
    print_info "Installing Python dependencies..."
    cd backend
    pip install -r requirements.txt
    cd ..
    
    # Setup Node.js environment
    print_header "Setting Up Frontend (Node.js)"
    
    cd frontend
    print_info "Installing Node.js dependencies..."
    npm install
    
    print_info "Building frontend..."
    npm run build
    cd ..
    
    # Setup environment
    print_header "Setting Up Environment Configuration"
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.template" ]; then
            cp .env.template .env
        else
            print_warning ".env.template not found, creating basic .env file"
            cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://localhost:5432/amc_trader

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# API Keys (REQUIRED - Replace with your actual keys)
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
POLYGON_API_KEY=your_polygon_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here

# Application Configuration
ENVIRONMENT=development
DEBUG=true

# Data Configuration
UNIVERSE_FILE=data/universe.txt
EOF
        fi
        print_success "Environment file created"
        print_warning "IMPORTANT: Edit .env file with your actual API keys!"
    else
        print_info "Environment file already exists"
    fi
    
    # Setup database
    print_header "Setting Up Database"
    
    print_info "Creating database..."
    createdb amc_trader 2>/dev/null || print_info "Database may already exist"
    
    # Run migrations if they exist
    source venv/bin/activate
    cd backend
    if [ -f "alembic.ini" ]; then
        print_info "Running database migrations..."
        alembic upgrade head
    fi
    cd ..
    
    # Create launch scripts
    print_header "Creating Launch Scripts"
    
    # Make this script's directory the working directory for relative paths
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Backend launch script
    cat > start-backend.command << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
source venv/bin/activate
cd backend
echo "Starting AMC-TRADER Backend..."
echo "Backend will be available at http://localhost:8000"
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
EOF
    chmod +x start-backend.command
    
    # Frontend launch script  
    cat > start-frontend.command << EOF
#!/bin/bash
cd "$SCRIPT_DIR/frontend"
echo "Starting AMC-TRADER Frontend..."
echo "Frontend will be available at http://localhost:3000"
npm run dev
EOF
    chmod +x start-frontend.command
    
    # Combined launch script
    cat > start-amc-trader.command << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

echo "Starting AMC-TRADER System..."
echo "This will start both backend and frontend services."
echo ""

# Check if .env file has been configured
if grep -q "your_.*_api_key_here" .env 2>/dev/null; then
    echo "⚠️  WARNING: Please configure your API keys in .env file first!"
    echo "   Edit .env and replace placeholder values with your actual API keys."
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to exit and configure..."
fi

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "Stopping AMC-TRADER services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start backend in background
echo "Starting backend server..."
source venv/bin/activate
cd backend
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend in background
echo "Starting frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait a bit more for frontend to start
sleep 5

echo ""
echo "🚀 AMC-TRADER is now running!"
echo ""
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Open browser
open "http://localhost:3000"

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID
EOF
    chmod +x start-amc-trader.command
    
    print_success "Launch scripts created"
    
    # Final instructions
    print_header "Installation Complete!"
    print_success "AMC-TRADER has been successfully installed"
    echo ""
    print_info "Next steps:"
    print_info "1. Edit $SCRIPT_DIR/.env with your API keys"
    print_info "2. Double-click: $SCRIPT_DIR/start-amc-trader.command"
    echo ""
    print_info "API Keys needed:"
    print_info "• Alpaca Trading API (for trading)"
    print_info "• Polygon API (for market data)"
    print_info "• Claude API (optional, for AI analysis)"
    echo ""
    print_success "Happy Trading! 🚀"
    
    # Keep terminal open
    echo ""
    echo "Press any key to close this window..."
    read -n 1 -s
}

# Run main function
main "$@"
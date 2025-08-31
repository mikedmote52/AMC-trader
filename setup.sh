#!/bin/bash

# AMC-TRADER Installation Script
# This script sets up the complete AMC-TRADER system for local use

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="AMC-TRADER"
REPO_URL="https://github.com/yourusername/AMC-TRADER.git"  # Replace with actual repo
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

# Platform detection
detect_platform() {
    case "$(uname -s)" in
        Darwin*)  PLATFORM="mac" ;;
        Linux*)   PLATFORM="linux" ;;
        CYGWIN*|MINGW*|MSYS*) PLATFORM="windows" ;;
        *)        PLATFORM="unknown" ;;
    esac
}

# System requirements check
check_system_requirements() {
    print_header "Checking System Requirements"
    
    local requirements_met=true
    
    # Check Python
    if check_command python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        if version_compare "$PYTHON_VERSION" "$PYTHON_MIN_VERSION"; then
            print_success "Python $PYTHON_VERSION detected"
        else
            print_error "Python $PYTHON_MIN_VERSION or higher required, found $PYTHON_VERSION"
            requirements_met=false
        fi
    else
        print_error "Python 3 not found"
        requirements_met=false
    fi
    
    # Check Node.js
    if check_command node; then
        NODE_VERSION=$(node --version 2>&1 | sed 's/v//')
        if version_compare "$NODE_VERSION" "$NODE_MIN_VERSION"; then
            print_success "Node.js $NODE_VERSION detected"
        else
            print_error "Node.js $NODE_MIN_VERSION or higher required, found $NODE_VERSION"
            requirements_met=false
        fi
    else
        print_error "Node.js not found"
        requirements_met=false
    fi
    
    # Check npm
    if check_command npm; then
        print_success "npm detected"
    else
        print_error "npm not found"
        requirements_met=false
    fi
    
    # Check pip
    if check_command pip3; then
        print_success "pip3 detected"
    else
        print_error "pip3 not found"
        requirements_met=false
    fi
    
    # Check git
    if check_command git; then
        print_success "git detected"
    else
        print_error "git not found"
        requirements_met=false
    fi
    
    if [ "$requirements_met" = false ]; then
        print_error "System requirements not met. Please install missing dependencies."
        print_info "Installation guides:"
        print_info "Python: https://www.python.org/downloads/"
        print_info "Node.js: https://nodejs.org/en/download/"
        print_info "Git: https://git-scm.com/downloads"
        exit 1
    fi
    
    print_success "All system requirements met!"
}

# Install system dependencies
install_system_dependencies() {
    print_header "Installing System Dependencies"
    
    case $PLATFORM in
        "mac")
            if check_command brew; then
                print_info "Updating Homebrew..."
                brew update
                
                # Install PostgreSQL and Redis if not present
                if ! check_command psql; then
                    print_info "Installing PostgreSQL..."
                    brew install postgresql
                    brew services start postgresql
                fi
                
                if ! check_command redis-server; then
                    print_info "Installing Redis..."
                    brew install redis
                    brew services start redis
                fi
                
                print_success "System dependencies installed"
            else
                print_warning "Homebrew not found. Please install PostgreSQL and Redis manually."
                print_info "PostgreSQL: https://postgresapp.com/"
                print_info "Redis: https://redis.io/download"
            fi
            ;;
        "linux")
            if check_command apt-get; then
                print_info "Updating package list..."
                sudo apt-get update
                
                print_info "Installing system dependencies..."
                sudo apt-get install -y postgresql postgresql-contrib redis-server
                
                # Start services
                sudo systemctl start postgresql
                sudo systemctl enable postgresql
                sudo systemctl start redis-server
                sudo systemctl enable redis-server
                
                print_success "System dependencies installed"
            elif check_command yum; then
                print_info "Installing system dependencies..."
                sudo yum install -y postgresql-server redis
                
                # Initialize and start PostgreSQL
                sudo postgresql-setup initdb
                sudo systemctl start postgresql
                sudo systemctl enable postgresql
                sudo systemctl start redis
                sudo systemctl enable redis
                
                print_success "System dependencies installed"
            else
                print_warning "Package manager not supported. Please install PostgreSQL and Redis manually."
            fi
            ;;
        "windows")
            print_warning "Windows detected. Please install the following manually:"
            print_info "PostgreSQL: https://www.postgresql.org/download/windows/"
            print_info "Redis: https://github.com/microsoftarchive/redis/releases"
            print_info "Or use Docker Desktop with docker-compose"
            ;;
    esac
}

# Clone or update repository
setup_repository() {
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
    
    print_success "Repository ready"
}

# Setup Python environment and dependencies
setup_backend() {
    print_header "Setting Up Backend (Python)"
    
    cd "$INSTALL_DIR"
    
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
    
    print_success "Backend setup complete"
}

# Setup Node.js environment and dependencies
setup_frontend() {
    print_header "Setting Up Frontend (Node.js)"
    
    cd "$INSTALL_DIR/frontend"
    
    # Install dependencies
    print_info "Installing Node.js dependencies..."
    npm install
    
    # Build frontend
    print_info "Building frontend..."
    npm run build
    
    cd ..
    print_success "Frontend setup complete"
}

# Setup environment configuration
setup_environment() {
    print_header "Setting Up Environment Configuration"
    
    cd "$INSTALL_DIR"
    
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
}

# Setup database
setup_database() {
    print_header "Setting Up Database"
    
    cd "$INSTALL_DIR"
    
    # Create database if it doesn't exist
    if check_command psql; then
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
        
        print_success "Database setup complete"
    else
        print_warning "PostgreSQL not available. Database setup skipped."
    fi
}

# Create launch scripts
create_launch_scripts() {
    print_header "Creating Launch Scripts"
    
    cd "$INSTALL_DIR"
    
    # Backend launch script
    cat > start-backend.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
cd backend
echo "Starting AMC-TRADER Backend..."
echo "Backend will be available at http://localhost:8000"
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
EOF
    chmod +x start-backend.sh
    
    # Frontend launch script  
    cat > start-frontend.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/frontend"
echo "Starting AMC-TRADER Frontend..."
echo "Frontend will be available at http://localhost:3000"
npm run dev
EOF
    chmod +x start-frontend.sh
    
    # Combined launch script
    cat > start-amc-trader.sh << 'EOF'
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

# Open browser (platform-specific)
case "$(uname -s)" in
    Darwin*)  open "http://localhost:3000" ;;
    Linux*)   xdg-open "http://localhost:3000" 2>/dev/null ;;
    CYGWIN*|MINGW*|MSYS*) start "http://localhost:3000" ;;
esac

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID
EOF
    chmod +x start-amc-trader.sh
    
    print_success "Launch scripts created"
}

# Main installation flow
main() {
    print_header "AMC-TRADER Installation"
    print_info "This script will install AMC-TRADER on your system"
    print_info "Installation directory: $INSTALL_DIR"
    echo ""
    
    # Detect platform
    detect_platform
    print_info "Platform detected: $PLATFORM"
    
    # Ask for confirmation
    read -p "Continue with installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installation cancelled"
        exit 0
    fi
    
    # Run installation steps
    check_system_requirements
    install_system_dependencies
    setup_repository
    setup_backend
    setup_frontend
    setup_environment
    setup_database
    create_launch_scripts
    
    # Final instructions
    print_header "Installation Complete!"
    print_success "AMC-TRADER has been successfully installed"
    echo ""
    print_info "Next steps:"
    print_info "1. Edit $INSTALL_DIR/.env with your API keys"
    print_info "2. Run: cd $INSTALL_DIR && ./start-amc-trader.sh"
    echo ""
    print_info "API Keys needed:"
    print_info "• Alpaca Trading API (for trading)"
    print_info "• Polygon API (for market data)"
    print_info "• Claude API (optional, for AI analysis)"
    echo ""
    print_info "Documentation available at: $INSTALL_DIR/README_INSTALL.md"
    echo ""
    print_success "Happy Trading! 🚀"
}

# Run main function
main "$@"
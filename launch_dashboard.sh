#!/bin/bash

# SURDAS Caregiver Dashboard Launcher
# This script helps launch the complete SURDAS system with the dashboard

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DASHBOARD_DIR="$SCRIPT_DIR/caregiver_dashboard"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored messages
print_header() {
    echo -e "${PURPLE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}  ${CYAN}$1${NC}"
    echo -e "${PURPLE}╚════════════════════════════════════════════════════════════╝${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Banner
echo -e "${PURPLE}"
cat << "EOF"
   ____  _   _ ____  ____    _    ____  
  / ___|| | | |  _ \|  _ \  / \  / ___| 
  \___ \| | | | |_) | | | |/ _ \ \___ \ 
   ___) | |_| |  _ <| |_| / ___ \ ___) |
  |____/ \___/|_| \_\____/_/   \_\____/ 
                                         
  Caregiver Dashboard Launcher v2.0
EOF
echo -e "${NC}"

print_header "System Check"

# Check if we're in the right directory
if [ ! -f "$SCRIPT_DIR/surdas_brain.py" ]; then
    print_error "Not in SURDAS directory! Please run from suradas/ folder"
    exit 1
fi
print_success "Found SURDAS directory"

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found! Please install Python 3.8+"
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js not found! Please install Node.js 18+"
    exit 1
fi
print_success "Node.js found: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    print_error "npm not found! Please install npm"
    exit 1
fi
print_success "npm found: $(npm --version)"

# Check if dashboard directory exists
if [ ! -d "$DASHBOARD_DIR" ]; then
    print_error "Dashboard directory not found at $DASHBOARD_DIR"
    exit 1
fi
print_success "Dashboard directory found"

# Check if node_modules exists
if [ ! -d "$DASHBOARD_DIR/node_modules" ]; then
    print_warning "Dashboard dependencies not installed"
    print_info "Installing dependencies..."
    cd "$DASHBOARD_DIR"
    npm install
    cd "$SCRIPT_DIR"
    print_success "Dependencies installed"
else
    print_success "Dashboard dependencies found"
fi

echo ""
print_header "Launch Options"

echo "Choose how to run SURDAS Dashboard:"
echo ""
echo "  ${GREEN}1)${NC} Full System    - Backend + Dashboard (recommended)"
echo "  ${GREEN}2)${NC} Backend Only   - Just SURDAS backend with telemetry"
echo "  ${GREEN}3)${NC} Dashboard Only - Just the dashboard (backend must be running)"
echo "  ${GREEN}4)${NC} Test Mode      - Backend + Test data generator + Dashboard"
echo "  ${GREEN}5)${NC} Production     - Build and preview production dashboard"
echo "  ${GREEN}q)${NC} Quit"
echo ""
read -p "Enter choice [1-5, q]: " choice

case $choice in
    1)
        print_header "Launching Full System"
        print_info "Starting SURDAS backend..."
        print_warning "Backend will run in background"
        
        # Start backend in background
        python3 "$SCRIPT_DIR/surdas_brain.py" > /tmp/surdas_backend.log 2>&1 &
        BACKEND_PID=$!
        print_success "Backend started (PID: $BACKEND_PID)"
        
        # Wait for backend to initialize
        print_info "Waiting for backend to initialize..."
        sleep 3
        
        # Check if backend is running
        if ps -p $BACKEND_PID > /dev/null; then
            print_success "Backend is running"
            print_info "Logs: tail -f /tmp/surdas_backend.log"
        else
            print_error "Backend failed to start! Check /tmp/surdas_backend.log"
            exit 1
        fi
        
        print_info "Starting dashboard..."
        cd "$DASHBOARD_DIR"
        
        echo ""
        print_success "Dashboard starting!"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${GREEN}Dashboard:${NC}    http://localhost:5173"
        echo -e "  ${GREEN}Backend API:${NC}  http://localhost:8000"
        echo -e "  ${GREEN}Backend PID:${NC}  $BACKEND_PID"
        echo -e "  ${GREEN}Backend Log:${NC}  /tmp/surdas_backend.log"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        print_warning "Press Ctrl+C to stop dashboard"
        print_info "Backend will continue running - kill with: kill $BACKEND_PID"
        echo ""
        
        npm run dev
        ;;
        
    2)
        print_header "Launching Backend Only"
        print_info "Starting SURDAS backend with telemetry..."
        python3 "$SCRIPT_DIR/surdas_brain.py"
        ;;
        
    3)
        print_header "Launching Dashboard Only"
        
        # Check if backend is running
        if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_warning "Backend doesn't seem to be running at http://localhost:8000"
            print_warning "Dashboard will work but won't receive data until backend starts"
            echo ""
            read -p "Continue anyway? [y/N]: " confirm
            if [[ ! $confirm =~ ^[Yy]$ ]]; then
                print_info "Cancelled. Start backend first with option 2"
                exit 0
            fi
        else
            print_success "Backend detected at http://localhost:8000"
        fi
        
        print_info "Starting dashboard..."
        cd "$DASHBOARD_DIR"
        
        echo ""
        print_success "Dashboard starting!"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${GREEN}Dashboard:${NC} http://localhost:5173"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        
        npm run dev
        ;;
        
    4)
        print_header "Launching Test Mode"
        print_info "This will start backend, test data, and dashboard"
        
        # Start test script in background
        print_info "Starting test data generator..."
        python3 "$SCRIPT_DIR/test_dashboard.py" > /tmp/surdas_test.log 2>&1 &
        TEST_PID=$!
        print_success "Test generator started (PID: $TEST_PID)"
        
        # Wait for telemetry to start
        sleep 3
        
        print_info "Starting dashboard..."
        cd "$DASHBOARD_DIR"
        
        echo ""
        print_success "Test system running!"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${GREEN}Dashboard:${NC}    http://localhost:5173"
        echo -e "  ${GREEN}Test Data:${NC}    Running (PID: $TEST_PID)"
        echo -e "  ${GREEN}Test Log:${NC}     /tmp/surdas_test.log"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        print_info "You should see test events appearing in the dashboard"
        print_warning "Press Ctrl+C to stop dashboard"
        print_info "Test generator will continue - kill with: kill $TEST_PID"
        echo ""
        
        npm run dev
        ;;
        
    5)
        print_header "Building Production Version"
        
        cd "$DASHBOARD_DIR"
        
        print_info "Building optimized production bundle..."
        npm run build
        
        if [ $? -eq 0 ]; then
            print_success "Build complete!"
            print_info "Starting production preview server..."
            
            echo ""
            print_success "Production preview running!"
            echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "  ${GREEN}Dashboard:${NC} http://localhost:3000"
            echo -e "  ${GREEN}Build:${NC}     $DASHBOARD_DIR/dist"
            echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo ""
            print_info "For deployment, see: DEPLOYMENT.md"
            echo ""
            
            npm run preview -- --host --port 3000
        else
            print_error "Build failed! Check errors above"
            exit 1
        fi
        ;;
        
    q|Q)
        print_info "Cancelled"
        exit 0
        ;;
        
    *)
        print_error "Invalid choice!"
        exit 1
        ;;
esac

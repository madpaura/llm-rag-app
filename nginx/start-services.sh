#!/bin/bash

# Start RAG Application services for nginx proxy
# Run this script to start both backend and frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Starting RAG Application Services ==="
echo "Project directory: $PROJECT_DIR"
echo ""

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Check if backend is already running
if check_port 8000; then
    echo "Backend is already running on port 8000"
else
    echo "Starting backend on port 8000..."
    cd "$PROJECT_DIR/backend"
    
    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    # Start backend in background
    nohup python3 main.py > /tmp/rag-backend.log 2>&1 &
    BACKEND_PID=$!
    echo "Backend started with PID: $BACKEND_PID"
    echo "Backend logs: /tmp/rag-backend.log"
fi

echo ""

# Check if frontend is already running
if check_port 3000; then
    echo "Frontend is already running on port 3000"
else
    echo "Starting frontend on port 3000..."
    cd "$PROJECT_DIR/frontend"
    
    # Start frontend in background
    nohup npm start > /tmp/rag-frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "Frontend started with PID: $FRONTEND_PID"
    echo "Frontend logs: /tmp/rag-frontend.log"
fi

echo ""
echo "=== Services Started ==="
echo ""
echo "Direct access (without nginx):"
echo "  - Backend:  http://localhost:8000"
echo "  - Frontend: http://localhost:3000"
echo ""
echo "Via nginx (after running setup-nginx.sh):"
echo "  - UI:   http://localhost/rag/ui"
echo "  - API:  http://localhost/rag/api"
echo "  - Docs: http://localhost/rag/api/docs"
echo ""
echo "To stop services:"
echo "  pkill -f 'python3 main.py'  # Stop backend"
echo "  pkill -f 'react-scripts'    # Stop frontend"
echo ""

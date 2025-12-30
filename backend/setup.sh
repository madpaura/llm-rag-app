#!/bin/bash

# RAG Engine Setup Script
# Automates the installation and setup process

set -e  # Exit on error

echo "=========================================="
echo "RAG Engine Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
    print_success "Python $PYTHON_VERSION"
else
    print_error "Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi

# Check if Ollama is installed
echo ""
echo "Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    print_success "Ollama is installed"
else
    print_error "Ollama is not installed"
    print_info "Installing Ollama..."
    
    # Detect OS and install
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install ollama
        else
            print_error "Homebrew not found. Please install Ollama manually from https://ollama.com"
            exit 1
        fi
    else
        print_error "Unsupported OS. Please install Ollama manually from https://ollama.com"
        exit 1
    fi
    
    print_success "Ollama installed"
fi

# Start Ollama service
echo ""
echo "Starting Ollama service..."
if pgrep -x "ollama" > /dev/null; then
    print_success "Ollama is already running"
else
    print_info "Starting Ollama in background..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
    print_success "Ollama started"
fi

# Pull required models
echo ""
echo "Pulling required models..."
print_info "This may take several minutes depending on your internet connection..."

# Pull LLM model
echo ""
echo "Pulling LLM model (llama3.2:3b)..."
if ollama list | grep -q "llama3.2:3b"; then
    print_success "llama3.2:3b already available"
else
    ollama pull llama3.2:3b
    print_success "llama3.2:3b pulled"
fi

# Pull embedding model
echo ""
echo "Pulling embedding model (nomic-embed-text)..."
if ollama list | grep -q "nomic-embed-text"; then
    print_success "nomic-embed-text already available"
else
    ollama pull nomic-embed-text
    print_success "nomic-embed-text pulled"
fi

# Create virtual environment
echo ""
echo "Setting up Python virtual environment..."
if [ -d "venv" ]; then
    print_success "Virtual environment already exists"
else
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Check and install PostgreSQL development libraries
echo ""
echo "Checking PostgreSQL development libraries..."
if ! dpkg -l | grep -q libpq-dev; then
    print_info "Installing PostgreSQL development libraries..."
    sudo apt-get update > /dev/null 2>&1
    sudo apt-get install -y libpq-dev python3-dev
    print_success "PostgreSQL libraries installed"
else
    print_success "PostgreSQL libraries already installed"
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
print_success "Dependencies installed"

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data/vector_stores
mkdir -p logs
print_success "Directories created"

# Run installation test
echo ""
echo "Running installation test..."
python test_installation.py

# Check if test passed
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    print_success "Setup completed successfully!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Activate virtual environment: source venv/bin/activate"
    echo "2. Start the server: python main.py"
    echo "3. Visit API docs: http://localhost:8000/docs"
    echo "4. Try examples: python examples/api_client_example.py"
    echo ""
    echo "Quick test:"
    echo "  curl http://localhost:8000/api/rag/models"
    echo ""
else
    echo ""
    print_error "Setup completed with errors. Please check the output above."
    exit 1
fi

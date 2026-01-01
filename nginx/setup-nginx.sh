#!/bin/bash

# Setup script for RAG Application nginx configuration
# This script installs the nginx config and restarts nginx

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/rag-app.conf"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
NGINX_CONF_D="/etc/nginx/conf.d"

echo "=== RAG Application Nginx Setup ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script requires root privileges."
    echo "Please run with: sudo $0"
    exit 1
fi

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "Error: nginx is not installed."
    echo "Install with: sudo apt install nginx"
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found: $CONFIG_FILE"
    exit 1
fi

echo "Configuration file: $CONFIG_FILE"
echo ""

# Determine nginx config directory structure
if [ -d "$NGINX_SITES_AVAILABLE" ]; then
    # Debian/Ubuntu style
    echo "Detected Debian/Ubuntu nginx structure"
    
    # Copy config to sites-available
    cp "$CONFIG_FILE" "$NGINX_SITES_AVAILABLE/rag-app.conf"
    echo "Copied config to $NGINX_SITES_AVAILABLE/rag-app.conf"
    
    # Create symlink in sites-enabled
    if [ -L "$NGINX_SITES_ENABLED/rag-app.conf" ]; then
        rm "$NGINX_SITES_ENABLED/rag-app.conf"
    fi
    ln -s "$NGINX_SITES_AVAILABLE/rag-app.conf" "$NGINX_SITES_ENABLED/rag-app.conf"
    echo "Created symlink in $NGINX_SITES_ENABLED/"
    
elif [ -d "$NGINX_CONF_D" ]; then
    # RHEL/CentOS style
    echo "Detected RHEL/CentOS nginx structure"
    
    cp "$CONFIG_FILE" "$NGINX_CONF_D/rag-app.conf"
    echo "Copied config to $NGINX_CONF_D/rag-app.conf"
else
    echo "Error: Could not determine nginx configuration directory"
    exit 1
fi

echo ""

# Test nginx configuration
echo "Testing nginx configuration..."
if nginx -t 2>&1; then
    echo "Configuration test passed!"
else
    echo "Error: nginx configuration test failed"
    exit 1
fi

echo ""

# Reload nginx
echo "Reloading nginx..."
systemctl reload nginx

echo ""
echo "=== Setup Complete ==="
echo ""
echo "The RAG application is now available at:"
echo "  - UI:   http://localhost/rag/ui"
echo "  - API:  http://localhost/rag/api"
echo "  - Docs: http://localhost/rag/api/docs"
echo ""
echo "Make sure the backend and frontend services are running:"
echo "  - Backend:  cd backend && python3 main.py"
echo "  - Frontend: cd frontend && npm start"
echo ""
echo "=== Port Configuration ==="
echo "Current config uses port 80. If port 80 is already in use:"
echo ""
echo "Option 1: Change to port 8080"
echo "  Edit rag-app.conf and change 'listen 80' to 'listen 8080'"
echo ""
echo "Option 2: Include in existing server (port 80)"
echo "  Add this line to your existing nginx server block:"
echo "    include $SCRIPT_DIR/rag-locations.conf;"
echo ""
echo "For production, build the frontend and update nginx config:"
echo "  cd frontend && npm run build"
echo "  Then uncomment the static file serving block in rag-app.conf"
echo ""

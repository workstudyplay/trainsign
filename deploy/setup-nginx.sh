#!/bin/bash
# Setup script for nginx with HTTPS on Raspberry Pi
# Run as root or with sudo

set -e

echo "=== TrainSign Nginx HTTPS Setup ==="

# Install nginx if not present
if ! command -v nginx &> /dev/null; then
    echo "Installing nginx..."
    apt-get update
    apt-get install -y nginx
fi

# Create SSL directory
mkdir -p /etc/nginx/ssl

# Check if certificates exist
if [ ! -f /etc/nginx/ssl/trainsign.crt ]; then
    echo ""
    echo "SSL certificates not found. Choose an option:"
    echo "1) Generate self-signed certificate (for local network/testing)"
    echo "2) I'll set up Let's Encrypt manually"
    echo ""
    read -p "Enter choice [1-2]: " choice

    case $choice in
        1)
            echo "Generating self-signed certificate..."
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                -keyout /etc/nginx/ssl/trainsign.key \
                -out /etc/nginx/ssl/trainsign.crt \
                -subj "/CN=trainsign/O=TrainSign/C=US"
            echo "Self-signed certificate created."
            echo "Note: Browsers will show a security warning for self-signed certs."
            ;;
        2)
            echo ""
            echo "To set up Let's Encrypt:"
            echo "  1. Install certbot: apt-get install certbot python3-certbot-nginx"
            echo "  2. Run: certbot --nginx -d yourdomain.com"
            echo "  3. Update /etc/nginx/sites-available/trainsign with cert paths"
            echo ""
            echo "Exiting. Run this script again after setting up certificates."
            exit 0
            ;;
        *)
            echo "Invalid choice. Exiting."
            exit 1
            ;;
    esac
fi

# Copy nginx config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/nginx.conf" /etc/nginx/sites-available/trainsign

# Enable the site
ln -sf /etc/nginx/sites-available/trainsign /etc/nginx/sites-enabled/trainsign

# Remove default site if it exists
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t

# Reload nginx
echo "Reloading nginx..."
systemctl reload nginx
systemctl enable nginx

echo ""
echo "=== Setup Complete ==="
echo "Nginx is now configured to:"
echo "  - Redirect HTTP (port 80) to HTTPS (port 443)"
echo "  - Proxy HTTPS requests to Flask on port 5002"
echo ""
echo "Make sure the trainsign service is running:"
echo "  sudo systemctl start trainsign"
echo ""

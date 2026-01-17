#!/bin/bash
# Script to update requirements.txt to latest compatible versions
# Usage: ./scripts/update-requirements.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REQUIREMENTS_DIR="$PROJECT_ROOT/src"

cd "$REQUIREMENTS_DIR"

echo "Updating requirements.txt to latest versions..."

# Check if pip-tools is available
if ! command -v pip-compile &> /dev/null; then
    echo "pip-tools not found. Installing..."
    pip install pip-tools
fi

# If requirements.in exists, use it; otherwise update requirements.txt directly
if [ -f "requirements.in" ]; then
    echo "Using requirements.in to generate requirements.txt..."
    pip-compile requirements.in --upgrade --output-file requirements.txt
    echo "✓ Updated requirements.txt from requirements.in"
else
    echo "requirements.in not found. Updating requirements.txt directly..."
    
    # Use pip-upgrader or similar tool
    if command -v pip-upgrader &> /dev/null; then
        pip-upgrader requirements.txt
    elif command -v pip-review &> /dev/null; then
        pip-review --auto
    else
        echo "No update tool found. Please install one of:"
        echo "  - pip-tools: pip install pip-tools"
        echo "  - pip-upgrader: pip install pip-upgrader"
        echo "  - pip-review: pip install pip-review"
        exit 1
    fi
fi

echo ""
echo "✓ Requirements updated successfully!"
echo ""
echo "Next steps:"
echo "1. Review the changes: git diff src/requirements.txt"
echo "2. Test your application"
echo "3. Commit the changes if everything works"

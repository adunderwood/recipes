#!/bin/bash
# Quick update script for when you have new recipes.json
# Just run: ./update.sh

set -e

echo "Updating recipe website..."
echo ""

# Check if new recipes.json exists
if [ ! -f "data/recipes.json" ]; then
    echo "Error: data/recipes.json not found!"
    echo "Please export your recipes from Recipe Sage and place the file in data/"
    exit 1
fi

# Run the build
./build.sh

echo ""
echo "Update complete!"
echo ""
echo "Changes:"
echo "  - Downloaded any new recipe images"
echo "  - Regenerated all HTML pages"
echo ""
echo "To view: cd public && python3 -m http.server 8000"

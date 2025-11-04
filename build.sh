#!/bin/bash
set -e

echo "================================================"
echo "Building Recipe Website"
echo "================================================"
echo ""

# Check if recipes.json exists
if [ ! -f "data/recipes.json" ]; then
    echo "Error: data/recipes.json not found!"
    echo "Please export your recipes from Recipe Sage and place the file in data/"
    exit 1
fi
echo ""

# Step 1: Download images
echo "Step 1: Downloading recipe images..."
echo "----------------------------------------"
python3 download_images.py
echo ""

# Step 2: Copy images to public directory
echo "Step 2: Copying images to public directory..."
echo "----------------------------------------"
if [ -d "images" ]; then
    mkdir -p public/images
    cp -r images/* public/images/
    echo "Images copied successfully!"
else
    echo "No images directory found. Skipping..."
fi
echo ""

# Step 3: Copy CSS to public directory
echo "Step 3: Setting up CSS..."
echo "----------------------------------------"
mkdir -p public/css
if [ -f "style.css" ]; then
    cp style.css public/css/
    echo "CSS copied successfully!"
else
    echo "style.css not found in root, skipping..."
fi
echo ""

# Step 4: Generate website
echo "Step 4: Generating website..."
echo "----------------------------------------"
python3 generate_site.py
echo ""

echo "================================================"
echo "Build complete!"
echo "================================================"
echo ""
echo "Changes:"
echo "  - Downloaded any new recipe images"
echo "  - Regenerated all HTML pages from templates"
echo ""
echo "To view your website:"
echo "  cd public && python3 -m http.server 8000"
echo ""
echo "Then open http://localhost:8000 in your browser"
echo ""

# Recipe Collection Website

A static website generator for Recipe Sage exports that creates a beautiful, searchable recipe collection.

## Features

- **Static Site Generation**: Converts Recipe Sage JSON export to a static HTML website
- **Local Image Hosting**: Downloads all recipe images to serve them locally (polite to AWS)
- **Search & Filter**: Real-time search and category filtering
- **Responsive Design**: Mobile-friendly layout that works on all devices
- **Easy Updates**: Simply re-run the build script when you add new recipes

## Quick Start

### 1. Export your recipes from Recipe Sage

Place your `recipes.json` export file in the `data/` directory.

### 2. Build the website

```bash
./build.sh
```

This script will:
1. Download all recipe images to the `images/` directory
2. Copy images to `public/images/`
3. Generate HTML pages for all recipes in the `public/` directory

### 3. View your website locally

```bash
cd public
python3 -m http.server 8000
```

Then open http://localhost:8000 in your browser.

## File Structure

```
recipes/
├── data/
│   ├── recipes.json                    # Your Recipe Sage export
│   └── recipes_with_local_images.json  # Generated with local image paths
├── images/                             # Downloaded recipe images
├── templates/                          # Editable page templates
│   └── about.html                      # About page (edit this file directly)
├── public/                             # Generated website (ready to deploy)
│   ├── index.html                      # Recipe listing page
│   ├── about.html                      # About page (copied from templates/)
│   ├── [recipe-name].html              # Individual recipe pages
│   ├── images/                         # Recipe images
│   └── css/
│       └── style.css                   # Website styling
├── download_images.py                  # Image download script
├── generate_site.py                    # Site generator script
├── style.css                           # Source CSS file
└── build.sh                            # Master build script
```

## Updating with New Recipes

When you add new recipes in Recipe Sage:

1. Export the updated `recipes.json` and place it in `data/`
2. Run `./build.sh` again
3. The script will only download new images and regenerate the site

## Deploying to the Web

The `public/` directory contains a complete static website. You can deploy it to:

- **GitHub Pages**: Push the `public/` folder to a `gh-pages` branch
- **Netlify**: Drag and drop the `public/` folder
- **Vercel**: Connect your repository and set build command to `./build.sh`
- **Any static host**: Upload the contents of `public/`

## Manual Usage

### Download images only

```bash
python3 download_images.py
```

### Generate site only (uses existing images)

```bash
python3 generate_site.py
```

## Customization

### Styling

Edit `style.css` (in the root directory) to customize colors, fonts, and layout. The CSS uses CSS variables for easy theming:

```css
:root {
    --primary-color: #00737d;
    --primary-light: #eee;
    --secondary-color: #ff6b35;
    /* ... more variables */
}
```

Changes to `style.css` will be copied to `public/css/style.css` on the next build.

### About Page

Edit `templates/about.html` to customize the about page content. This file is copied to `public/about.html` during the build process and will preserve your edits across rebuilds.

### Recipe Templates

The recipe page templates are embedded in `generate_site.py`. You can modify the `generate_recipe_page()` and `generate_index_page()` functions to customize the layout.

## Requirements

- Python 3.6+
- No additional dependencies required (uses only Python standard library)

## License

This is your personal recipe collection - use it however you'd like!

# Recipe Collection Website

A static site generator for RecipeSage exports that builds a searchable, mobile-friendly recipe website.

## Features

- **Static Site Generation**: Converts a RecipeSage JSON-LD export into a static HTML website
- **Local Image Hosting**: Downloads all recipe images to serve them locally (polite to AWS)
- **Search & Filter**: Real-time search and category filtering
- **Responsive Design**: Mobile-friendly layout that works on all devices
- **Easy Updates**: Re-run the build whenever you export updated recipe data

## Quick Start

### 1. Export your recipes from RecipeSage

1. Log in to your RecipeSage account.
2. Open the hamburger menu.
3. Choose `Settings`.
4. Choose `Export Recipe Data`.
5. Export to `JSON-LD (.json)`.
6. Copy the exported file into `data/recipes.json`.

### 2. Build the site

```bash
./build.sh
```

This script:

1. checks that `data/recipes.json` exists
2. downloads any missing recipe images to `images/`
3. copies recipe images to `public/images/`
4. copies CSS to `public/css/`
5. copies favicon and manifest assets to the root of `public/`
6. generates the static site into `public/`

### 3. Preview locally

```bash
python3 serve.py
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

### 4. Deploy

After `./build.sh` finishes, either:

- upload the contents of `public/` to your web server
- or keep testing locally with `python3 serve.py`

## File Structure

```
recipes/
├── data/
│   ├── recipes.json                    # Your RecipeSage export
│   └── recipes_with_local_images.json  # Generated with local image paths
├── images/                             # Downloaded recipe images
├── templates/                          # Editable page templates
│   ├── index.html                      # Homepage template
│   ├── recipe.html                     # Recipe detail template
│   └── partials/                       # Shared partials and intro content
├── public/                             # Generated website (ready to deploy)
│   ├── index.html                      # Recipe listing page
│   ├── [recipe-name].html              # Individual recipe pages
│   ├── favicon.ico                     # Browser/favicon assets
│   ├── site.webmanifest                # Web app manifest
│   ├── images/                         # Recipe images
│   └── css/
│       └── style.css                   # Website styling
├── download_images.py                  # Image download script
├── generate_site.py                    # Site generator script
├── serve.py                            # Local preview server with clean URL support
├── style.css                           # Source CSS file
└── build.sh                            # Master build script
```

## Updating Recipe Data

When you add or change recipes in RecipeSage:

1. export a fresh `JSON-LD (.json)` file from RecipeSage
2. copy it to `data/recipes.json`
3. run `./build.sh`

The build will download any new images and regenerate the site.

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

Edit [style.css](/Users/alanunderwood/recipes/style.css) to customize colors, fonts, and layout. The CSS uses theme tokens at the top of the file for easy theming:

```css
:root {
    --primary-color: #00737d;
    --primary-light: #eee;
    --secondary-color: #ff6b35;
    /* ... more variables */
}
```

Changes to `style.css` are copied to `public/css/style.css` on the next build.

### Site Config

Edit [data/site_config.json](/Users/alanunderwood/recipes/data/site_config.json) to customize the reusable site identity values:

- site name
- base URL
- theme color
- analytics ID
- back-link label
- brand logo alt text

This is the best place to start when adapting the project for a different site.

### Homepage Intro

Edit [templates/partials/home_intro.html](/Users/alanunderwood/recipes/templates/partials/home_intro.html) to customize the homepage intro. It stays as HTML so it can include richer branded content like a signature SVG.

### Recipe Page Template

Edit [templates/recipe.html](/Users/alanunderwood/recipes/templates/recipe.html) to customize the layout and structure of individual recipe pages. The template uses placeholders like `{{RECIPE_NAME}}`, `{{INGREDIENTS}}`, and `{{INSTRUCTIONS}}` that are replaced during the build.

### Index Page Template

Edit [templates/index.html](/Users/alanunderwood/recipes/templates/index.html) to customize the homepage layout and structure. It uses placeholders like `{{RECIPE_COUNT}}`, `{{RECIPE_CARDS}}`, and `{{CATEGORY_FILTERS}}`, while the search/filter JavaScript is generated by the build.

## Requirements

- Python 3.6+
- No additional dependencies required (uses only Python standard library)

## License

Use it however you'd like.

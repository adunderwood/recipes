#!/usr/bin/env python3
"""
Generate a static website from Recipe Sage recipes export.
"""
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import quote
from html import escape

# Configuration
BASE_URL = 'https://everything.thatrises.com'

def slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

def truncate_description(text, max_words=20):
    """Truncate description at first sentence or max words, whichever comes first."""
    if not text:
        return ''

    # Find first sentence ending (. ! or ?)
    sentence_match = re.search(r'^[^.!?]+[.!?]', text)

    # Split into words
    words = text.split()

    # If first sentence exists and is <= max_words, use it
    if sentence_match:
        first_sentence = sentence_match.group(0).strip()
        sentence_words = first_sentence.split()
        if len(sentence_words) <= max_words:
            return first_sentence

    # Otherwise truncate at max_words
    if len(words) > max_words:
        return ' '.join(words[:max_words]) + '...'

    return text

def parse_duration(duration_str):
    """Parse ISO 8601 duration to human readable format."""
    if not duration_str or duration_str == '':
        return ''

    # Simple parser for PT format (PT1H30M)
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', duration_str)
    if not match:
        return duration_str

    hours = match.group(1)
    minutes = match.group(2)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")

    return ' '.join(parts) if parts else ''

def generate_recipe_page(recipe, output_dir):
    """Generate individual recipe HTML page."""
    recipe_id = recipe.get('identifier', '')
    slug = slugify(recipe.get('name', 'recipe'))
    filename = f"{slug}"

    # Get recipe data
    name = escape(recipe.get('name', 'Untitled Recipe'))
    description = escape(recipe.get('description', ''))

    # Store the slug without extension for links
    slug_without_ext = slug

    # Get local image or fallback to remote
    image_url = recipe.get('localImage', '')
    if not image_url and recipe.get('image'):
        images = recipe.get('image', [])
        image_url = images[0] if isinstance(images, list) and images else ''

    # Full URL for meta tags
    recipe_url = f"{BASE_URL}/{slug}"
    full_image_url = f"{BASE_URL}/{image_url}" if image_url and not image_url.startswith('http') else image_url

    # Times
    prep_time = parse_duration(recipe.get('prepTime', ''))
    total_time = parse_duration(recipe.get('totalTime', ''))

    # Ingredients with checkboxes
    ingredients = recipe.get('recipeIngredient', [])
    ingredients_html = '\n'.join([
        f'<li><label class="ingredient-checkbox"><input type="checkbox" aria-label="Check off {escape(ing)}"><span>{escape(ing)}</span></label></li>'
        for ing in ingredients
    ])

    # Instructions
    instructions = recipe.get('recipeInstructions', [])
    instructions_html = ''
    for i, step in enumerate(instructions, 1):
        step_text = step.get('text', step) if isinstance(step, dict) else step
        instructions_html += f'<li><p>{escape(step_text)}</p></li>\n'

    # Yield
    recipe_yield = escape(recipe.get('recipeYield', ''))

    # Categories
    categories = recipe.get('recipeCategory', [])
    categories_html = ' '.join([f'<span class="category">{escape(cat)}</span>' for cat in categories])

    # Credit
    credit = escape(recipe.get('creditText', ''))
    source_url = recipe.get('isBasedOn', '')

    # Comments/Notes
    comments = recipe.get('comment', [])
    notes_html = ''
    for comment in comments:
        if isinstance(comment, dict):
            note_text = comment.get('text', '')
            if note_text:
                # Split by double newlines for paragraphs, or single newlines if no doubles exist
                paragraphs = note_text.split('\n\n') if '\n\n' in note_text else note_text.split('\n')
                for para in paragraphs:
                    para = para.strip()
                    if para:
                        notes_html += f'<p>{escape(para)}</p>\n'

    # Create meta description (use recipe description or first line of instructions)
    meta_description = description if description else (
        escape(instructions[0].get('text', '')[:150]) if instructions else f"Recipe for {name}"
    )
    if len(meta_description) > 155:
        meta_description = meta_description[:152] + '...'

    # Build JSON-LD structured data
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": recipe.get('name', 'Untitled Recipe'),
        "description": recipe.get('description', ''),
        "image": [full_image_url] if full_image_url else [],
        "recipeYield": recipe_yield,
        "recipeCategory": categories,
        "recipeIngredient": ingredients,
        "recipeInstructions": [
            {
                "@type": "HowToStep",
                "text": step.get('text', step) if isinstance(step, dict) else step
            }
            for step in instructions
        ]
    }

    # Add optional fields if present
    if recipe.get('prepTime'):
        json_ld["prepTime"] = recipe.get('prepTime')
    if recipe.get('totalTime'):
        json_ld["totalTime"] = recipe.get('totalTime')
    if recipe.get('cookTime'):
        json_ld["cookTime"] = recipe.get('cookTime')
    if credit:
        json_ld["author"] = {"@type": "Person", "name": recipe.get('creditText', '')}
    if source_url:
        json_ld["url"] = source_url
    if recipe.get('datePublished'):
        json_ld["datePublished"] = recipe.get('datePublished')

    json_ld_script = json.dumps(json_ld, ensure_ascii=False, indent=2)

    # Generate HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - Everything that Rises</title>
    <meta name="description" content="{meta_description}">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="article">
    <meta property="og:url" content="{recipe_url}">
    <meta property="og:title" content="{name}">
    <meta property="og:description" content="{meta_description}">
    {f'<meta property="og:image" content="{full_image_url}">' if full_image_url else ''}

    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="{recipe_url}">
    <meta property="twitter:title" content="{name}">
    <meta property="twitter:description" content="{meta_description}">
    {f'<meta property="twitter:image" content="{full_image_url}">' if full_image_url else ''}

    <!-- Canonical URL -->
    <link rel="canonical" href="{recipe_url}">

    <!-- JSON-LD Structured Data -->
    <script type="application/ld+json">
{json_ld_script}
    </script>

    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-8KBWFBFNLF"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());

      gtag('config', 'G-8KBWFBFNLF');
    </script>

    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>
    <nav class="navbar" role="navigation" aria-label="Main navigation">
        <div class="container nav-container">
            <a href="/" class="nav-brand" aria-label="Return to recipe collection homepage">← Back to All Recipes</a>
            <button onclick="window.print()" class="print-btn" aria-label="Print this recipe">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <polyline points="6 9 6 2 18 2 18 9"></polyline>
                    <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
                    <rect x="6" y="14" width="12" height="8"></rect>
                </svg>
                <span class="print-btn-text">Print</span>
            </button>
        </div>
    </nav>

    <div id="hamburgerMenu">
        <div class="hamburger-icon">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <nav class="hamburger-dropdown">
            <div class="menu-panel" id="mainMenu">
                <div class="menu">
                    <a href="/">Home</a>
                </div>
                <div class="menu">
                    <a href="/about">About</a>
                </div>
            </div>
        </nav>
    </div>

    <main id="main-content" class="container" role="main">
        <article class="recipe-detail">
            <header class="recipe-header">
                <h1>{name}</h1>
                {f'<p class="description">{description}</p>' if description else ''}
                {f'<div class="categories">{categories_html}</div>' if categories_html else ''}
            </header>

            {f'<div class="recipe-image"><img src="{image_url}" alt="Photo of {name}"></div>' if image_url else ''}

            <div class="recipe-meta">
                {f'<div class="meta-item"><strong>Prep Time:</strong> {prep_time}</div>' if prep_time else ''}
                {f'<div class="meta-item"><strong>Total Time:</strong> {total_time}</div>' if total_time else ''}
                {f'<div class="meta-item"><strong>Yield:</strong> {recipe_yield}</div>' if recipe_yield else ''}
            </div>

            <section class="recipe-section" aria-labelledby="ingredients-heading">
                <h2 id="ingredients-heading">Ingredients</h2>
                <ul class="ingredients-list" role="list">
                    {ingredients_html}
                </ul>
            </section>

            <section class="recipe-section" aria-labelledby="instructions-heading">
                <h2 id="instructions-heading">Instructions</h2>
                <ol class="instructions-list" role="list">
                    {instructions_html}
                </ol>
            </section>

            {f'<section class="recipe-section notes" aria-labelledby="notes-heading"><h2 id="notes-heading">Notes</h2>{notes_html}</section>' if notes_html else ''}

            {f'<footer class="recipe-footer" role="contentinfo">' +
                (f'<p><strong>Source:</strong> {credit}</p>' if credit else '') +
                (f'<p><a href="{source_url}" target="_blank" rel="noopener" aria-label="View original recipe on {credit if credit else "source website"}">View Original Recipe</a></p>' if source_url else '') +
            '</footer>' if (credit or source_url) else ''}
        </article>
    </main>
    <script>
        // Hamburger menu functionality
        const hamburgerMenu = document.getElementById('hamburgerMenu');
        const hamburgerIcon = hamburgerMenu.querySelector('.hamburger-icon');

        hamburgerIcon.addEventListener('click', () => {{
            hamburgerMenu.classList.toggle('active');
        }});

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {{
            if (!hamburgerMenu.contains(e.target)) {{
                hamburgerMenu.classList.remove('active');
            }}
        }});

        // Close menu when clicking on menu links
        const menuLinks = hamburgerMenu.querySelectorAll('.menu a');
        menuLinks.forEach(link => {{
            link.addEventListener('click', () => {{
                hamburgerMenu.classList.remove('active');
            }});
        }});
    </script>
</body>
</html>'''

    # Write file with .html extension
    output_path = Path(output_dir) / f"{filename}.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return {
        'name': name,
        'slug': slug,
        'filename': slug_without_ext,  # Return without .html for links
        'description': description,
        'image': image_url,
        'categories': categories,
        'ingredients': ingredients,
        'prep_time': prep_time,
        'total_time': total_time
    }

def generate_sitemap(recipes_meta, output_dir):
    """Generate sitemap.xml for SEO."""
    from datetime import datetime

    current_date = datetime.now().strftime('%Y-%m-%d')

    sitemap_entries = []

    # Add index page
    sitemap_entries.append(f'''  <url>
    <loc>{BASE_URL}/</loc>
    <lastmod>{current_date}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>''')

    # Add about page
    sitemap_entries.append(f'''  <url>
    <loc>{BASE_URL}/about</loc>
    <lastmod>{current_date}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>''')

    # Add all recipe pages
    for meta in recipes_meta:
        recipe_url = f"{BASE_URL}/{meta['filename']}"
        sitemap_entries.append(f'''  <url>
    <loc>{recipe_url}</loc>
    <lastmod>{current_date}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>''')

    sitemap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(sitemap_entries)}
</urlset>'''

    output_path = Path(output_dir) / 'sitemap.xml'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(sitemap_xml)

    print(f"Generated sitemap with {len(sitemap_entries)} URLs")

def generate_index_page(recipes_meta, output_dir):
    """Generate index page with all recipes."""

    # Build recipe cards
    cards_html = ''
    for meta in recipes_meta:
        # Better alt text for images
        alt_text = f"{meta['name']} recipe photo" if meta['image'] else ''
        image_html = f'<img src="{meta["image"]}" alt="{alt_text}">' if meta['image'] else '<div class="no-image" role="img" aria-label="No image available">No Image</div>'
        categories_html = ' '.join([f'<span class="category">{escape(cat)}</span>' for cat in meta['categories']])

        ingredients_text = ' '.join(meta['ingredients']).lower()
        cards_html += f'''
        <article class="recipe-card" role="listitem" data-categories='{json.dumps(meta["categories"])}' data-ingredients="{escape(ingredients_text)}">
            <a href="{meta['filename']}" class="card-link" aria-label="View recipe for {escape(meta['name'])}">
                <div class="card-image">
                    {image_html}
                </div>
                <div class="card-content">
                    <h2>{meta['name']}</h2>
                    {f'<p class="card-description">{truncate_description(meta["description"])}</p>' if meta['description'] else ''}
                    {f'<div class="categories">{categories_html}</div>' if categories_html else ''}
                </div>
            </a>
        </article>'''

    # Get all unique categories and count recipes per category
    all_categories = set()
    category_counts = {}
    for meta in recipes_meta:
        for cat in meta['categories']:
            all_categories.add(cat)
            category_counts[cat] = category_counts.get(cat, 0) + 1

    # Generate category filter buttons with counts
    categories_filter = '\n'.join([
        f'<button class="filter-btn" data-category="{escape(cat)}" aria-pressed="false" aria-label="Filter by {escape(cat)} recipes">{escape(cat)} ({category_counts[cat]})</button>'
        for cat in sorted(all_categories)
    ])

    # Get first recipe image for og:image if available
    first_image = next((meta['image'] for meta in recipes_meta if meta['image']), '')
    full_first_image = f"{BASE_URL}/{first_image}" if first_image and not first_image.startswith('http') else first_image

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Everything that Rises - {len(recipes_meta)} Delicious Recipes</title>
    <meta name="description" content="A curated collection of {len(recipes_meta)} delicious recipes from around the world. Browse, search, and filter recipes by category and ingredients.">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{BASE_URL}">
    <meta property="og:title" content="Everything that Rises - {len(recipes_meta)} Delicious Recipes">
    <meta property="og:description" content="A curated collection of {len(recipes_meta)} delicious recipes from around the world. Browse, search, and filter recipes by category and ingredients.">
    {f'<meta property="og:image" content="{full_first_image}">' if full_first_image else ''}

    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="{BASE_URL}">
    <meta property="twitter:title" content="Everything that Rises - {len(recipes_meta)} Delicious Recipes">
    <meta property="twitter:description" content="A curated collection of {len(recipes_meta)} delicious recipes from around the world. Browse, search, and filter recipes by category and ingredients.">
    {f'<meta property="twitter:image" content="{full_first_image}">' if full_first_image else ''}

    <!-- Canonical URL -->
    <link rel="canonical" href="{BASE_URL}">

    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-8KBWFBFNLF"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());

      gtag('config', 'G-8KBWFBFNLF');
    </script>

    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>
    <nav class="navbar" role="navigation" aria-label="Main navigation">
        <div class="container">
            <h1 class="nav-brand">Everything that Rises <img class="wheat" src="/images/wheat.svg" alt="Wheat Stalk Logo"></h1>
        </div>
    </nav>

    <div id="hamburgerMenu">
        <div class="hamburger-icon">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <nav class="hamburger-dropdown">
            <div class="menu-panel" id="mainMenu">
                <div class="menu">
                    <a href="/">Home</a>
                </div>
                <div class="menu">
                    <a href="/about">About</a>
                </div>
            </div>
        </nav>
    </div>

    <main id="main-content" class="container" role="main">
        <div class="filters" role="search" aria-label="Recipe search and filters">
            <label for="search" class="sr-only">Search recipes by name, description, or ingredients</label>
            <input type="text" id="search" placeholder="Search recipes..." class="search-input" aria-label="Search recipes by name, description, or ingredients">
            <div class="category-filters" role="group" aria-label="Filter recipes by category">
                <button class="filter-btn active" data-category="all" aria-pressed="true">All Recipes ({len(recipes_meta)})</button>
                {categories_filter}
            </div>
        </div>

        <div class="recipe-grid" id="recipe-grid" role="list" aria-label="Recipe cards">
            {cards_html}
        </div>

        <div id="no-results" class="no-results" style="display: none;">
            <p>No recipes found matching your criteria.</p>
        </div>
    </main>

    <script>
        // Search and filter functionality
        const searchInput = document.getElementById('search');
        const filterBtns = document.querySelectorAll('.filter-btn');
        const recipeCards = document.querySelectorAll('.recipe-card');
        const noResults = document.getElementById('no-results');

        let currentCategory = 'all';
        let currentSearch = '';

        function filterRecipes() {{
            let visibleCount = 0;

            recipeCards.forEach(card => {{
                const cardName = card.querySelector('h2').textContent.toLowerCase();
                const cardDesc = card.querySelector('.card-description')?.textContent.toLowerCase() || '';
                const cardIngredients = card.dataset.ingredients || '';
                const cardCategories = JSON.parse(card.dataset.categories || '[]');

                let matchesSearch = false;
                if (currentSearch === '') {{
                    matchesSearch = true;
                }} else if (currentSearch.length === 1) {{
                    // For single character, match word-initial letters in title only
                    const nameWords = cardName.split(/\\s+/);
                    matchesSearch = nameWords.some(word => word.startsWith(currentSearch));
                }} else {{
                    // For 2+ characters, search title, description, and ingredients
                    matchesSearch = cardName.includes(currentSearch) ||
                                    cardDesc.includes(currentSearch) ||
                                    cardIngredients.includes(currentSearch);
                }}

                const matchesCategory = currentCategory === 'all' ||
                    cardCategories.includes(currentCategory);

                if (matchesSearch && matchesCategory) {{
                    card.style.display = '';
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        }}

        searchInput.addEventListener('input', (e) => {{
            currentSearch = e.target.value.toLowerCase();
            filterRecipes();
        }});

        filterBtns.forEach(btn => {{
            btn.addEventListener('click', () => {{
                // If clicking an already active button (except "All Recipes"), toggle it off
                if (btn.classList.contains('active') && btn.dataset.category !== 'all') {{
                    // Find and activate the "All Recipes" button
                    filterBtns.forEach(b => {{
                        b.classList.remove('active');
                        b.setAttribute('aria-pressed', 'false');
                    }});
                    const allBtn = Array.from(filterBtns).find(b => b.dataset.category === 'all');
                    if (allBtn) {{
                        allBtn.classList.add('active');
                        allBtn.setAttribute('aria-pressed', 'true');
                        currentCategory = 'all';
                    }}
                }} else {{
                    // Normal behavior: activate the clicked button
                    filterBtns.forEach(b => {{
                        b.classList.remove('active');
                        b.setAttribute('aria-pressed', 'false');
                    }});
                    btn.classList.add('active');
                    btn.setAttribute('aria-pressed', 'true');
                    currentCategory = btn.dataset.category;
                }}
                filterRecipes();
            }});
        }});

        // Hamburger menu functionality
        const hamburgerMenu = document.getElementById('hamburgerMenu');
        const hamburgerIcon = hamburgerMenu.querySelector('.hamburger-icon');

        hamburgerIcon.addEventListener('click', () => {{
            hamburgerMenu.classList.toggle('active');
        }});

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {{
            if (!hamburgerMenu.contains(e.target)) {{
                hamburgerMenu.classList.remove('active');
            }}
        }});

        // Close menu when clicking on menu links
        const menuLinks = hamburgerMenu.querySelectorAll('.menu a');
        menuLinks.forEach(link => {{
            link.addEventListener('click', () => {{
                hamburgerMenu.classList.remove('active');
            }});
        }});
    </script>
</body>
</html>'''

    output_path = Path(output_dir) / 'index.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

def copy_about_page(output_dir):
    """Copy about page from template."""
    about_template = Path('templates/about.html')
    if about_template.exists():
        output_path = Path(output_dir) / 'about.html'
        shutil.copy(about_template, output_path)
        print("Copied about page from templates/about.html")
    else:
        print("Warning: templates/about.html not found. Skipping about page.")

def generate_site(recipes_file, output_dir):
    """Generate complete static site."""

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Copy CSS file
    css_dir = output_path / 'css'
    css_dir.mkdir(parents=True, exist_ok=True)
    css_source = Path('style.css')
    if css_source.exists():
        shutil.copy(css_source, css_dir / 'style.css')
        print("Copied style.css to public/css/")
    else:
        print("Warning: style.css not found in current directory")

    # Copy .htaccess file
    htaccess_source = Path('.htaccess')
    if htaccess_source.exists():
        shutil.copy(htaccess_source, output_path / '.htaccess')
        print("Copied .htaccess to public/")
    else:
        print("Warning: .htaccess not found in current directory")

    # Load recipes
    with open(recipes_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    recipes = data['recipes']
    print(f"Generating site for {len(recipes)} recipes...")

    # Generate individual recipe pages
    recipes_meta = []
    for i, recipe in enumerate(recipes, 1):
        name = recipe.get('name', 'Unknown')
        print(f"[{i}/{len(recipes)}] Generating page for '{name}'...")
        meta = generate_recipe_page(recipe, output_dir)
        recipes_meta.append(meta)

    # Generate index page
    print("Generating index page...")
    generate_index_page(recipes_meta, output_dir)

    # Copy about page from template
    print("Copying about page...")
    copy_about_page(output_dir)

    # Generate sitemap
    print("Generating sitemap...")
    generate_sitemap(recipes_meta, output_dir)

    print(f"\n{'='*50}")
    print(f"Site generated successfully!")
    print(f"  Output directory: {output_path.absolute()}")
    print(f"  Total pages: {len(recipes) + 1}")
    print(f"\nOpen {output_path.absolute()}/recipes in your browser to view.")

if __name__ == '__main__':
    # Use the version with local images if available, otherwise use original
    recipes_file = 'data/recipes_with_local_images.json'
    if not Path(recipes_file).exists():
        recipes_file = 'data/recipes.json'

    output_dir = 'public'
    generate_site(recipes_file, output_dir)

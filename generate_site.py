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
    """Generate individual recipe HTML page from template."""
    # Load template
    template_path = Path('templates/recipe.html')
    if not template_path.exists():
        raise FileNotFoundError("templates/recipe.html not found")

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

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

    # Prepare template replacements
    replacements = {
        '{{RECIPE_NAME}}': name,
        '{{META_DESCRIPTION}}': meta_description,
        '{{RECIPE_URL}}': recipe_url,
        '{{OG_IMAGE}}': f'<meta property="og:image" content="{full_image_url}">' if full_image_url else '',
        '{{TWITTER_IMAGE}}': f'<meta property="twitter:image" content="{full_image_url}">' if full_image_url else '',
        '{{JSON_LD}}': json_ld_script,
        '{{DESCRIPTION}}': f'<p class="description">{description}</p>' if description else '',
        '{{CATEGORIES}}': f'<div class="categories">{categories_html}</div>' if categories_html else '',
        '{{RECIPE_IMAGE}}': f'<div class="recipe-image"><img src="{image_url}" alt="Photo of {name}"></div>' if image_url else '',
        '{{PREP_TIME}}': f'<div class="meta-item"><strong>Prep Time:</strong> {prep_time}</div>' if prep_time else '',
        '{{TOTAL_TIME}}': f'<div class="meta-item"><strong>Total Time:</strong> {total_time}</div>' if total_time else '',
        '{{YIELD}}': f'<div class="meta-item"><strong>Yield:</strong> {recipe_yield}</div>' if recipe_yield else '',
        '{{INGREDIENTS}}': ingredients_html,
        '{{INSTRUCTIONS}}': instructions_html,
        '{{NOTES}}': f'<section class="recipe-section notes" aria-labelledby="notes-heading"><h2 id="notes-heading">Notes</h2>{notes_html}</section>' if notes_html else '',
        '{{FOOTER}}': (f'<footer class="recipe-footer" role="contentinfo">' +
            (f'<p><strong>Source:</strong> {credit}</p>' if credit else '') +
            (f'<p><a href="{source_url}" target="_blank" rel="noopener" aria-label="View original recipe on {credit if credit else "source website"}">View Original Recipe</a></p>' if source_url else '') +
            '</footer>') if (credit or source_url) else ''
    }

    # Apply replacements
    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

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
    """Generate index page with all recipes from template."""
    # Load template
    template_path = Path('templates/index.html')
    if not template_path.exists():
        raise FileNotFoundError("templates/index.html not found")

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

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

    # Build JavaScript (needs {{ escaping for Python f-strings)
    javascript = f'''<script>
        // Search and filter functionality
        const searchInput = document.getElementById('search');
        const filterBtns = document.querySelectorAll('.filter-btn');
        const recipeCards = document.querySelectorAll('.recipe-card');
        const noResults = document.getElementById('no-results');

        let currentCategory = 'all';
        let currentSearch = '';

        function filterRecipes() {{{{
            let visibleCount = 0;

            recipeCards.forEach(card => {{{{
                const cardName = card.querySelector('h2').textContent.toLowerCase();
                const cardDesc = card.querySelector('.card-description')?.textContent.toLowerCase() || '';
                const cardIngredients = card.dataset.ingredients || '';
                const cardCategories = JSON.parse(card.dataset.categories || '[]');

                let matchesSearch = false;
                if (currentSearch === '') {{{{
                    matchesSearch = true;
                }}}} else if (currentSearch.length === 1) {{{{
                    // For single character, match word-initial letters in title only
                    const nameWords = cardName.split(/\\s+/);
                    matchesSearch = nameWords.some(word => word.startsWith(currentSearch));
                }}}} else {{{{
                    // For 2+ characters, search title, description, and ingredients
                    matchesSearch = cardName.includes(currentSearch) ||
                                    cardDesc.includes(currentSearch) ||
                                    cardIngredients.includes(currentSearch);
                }}}}

                const matchesCategory = currentCategory === 'all' ||
                    cardCategories.includes(currentCategory);

                if (matchesSearch && matchesCategory) {{{{
                    card.style.display = '';
                    visibleCount++;
                }}}} else {{{{
                    card.style.display = 'none';
                }}}}
            }}}});

            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        }}}}

        searchInput.addEventListener('input', (e) => {{{{
            currentSearch = e.target.value.toLowerCase();
            filterRecipes();
        }}}});

        filterBtns.forEach(btn => {{{{
            btn.addEventListener('click', () => {{{{
                // If clicking an already active button (except "All Recipes"), toggle it off
                if (btn.classList.contains('active') && btn.dataset.category !== 'all') {{{{
                    // Find and activate the "All Recipes" button
                    filterBtns.forEach(b => {{{{
                        b.classList.remove('active');
                        b.setAttribute('aria-pressed', 'false');
                    }}}});
                    const allBtn = Array.from(filterBtns).find(b => b.dataset.category === 'all');
                    if (allBtn) {{{{
                        allBtn.classList.add('active');
                        allBtn.setAttribute('aria-pressed', 'true');
                        currentCategory = 'all';
                    }}}}
                }}}} else {{{{
                    // Normal behavior: activate the clicked button
                    filterBtns.forEach(b => {{{{
                        b.classList.remove('active');
                        b.setAttribute('aria-pressed', 'false');
                    }}}});
                    btn.classList.add('active');
                    btn.setAttribute('aria-pressed', 'true');
                    currentCategory = btn.dataset.category;
                }}}}
                filterRecipes();
            }}}});
        }}}});

        // Hamburger menu functionality
        const hamburgerMenu = document.getElementById('hamburgerMenu');
        const hamburgerIcon = hamburgerMenu.querySelector('.hamburger-icon');

        hamburgerIcon.addEventListener('click', () => {{{{
            hamburgerMenu.classList.toggle('active');
        }}}});

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {{{{
            if (!hamburgerMenu.contains(e.target)) {{{{
                hamburgerMenu.classList.remove('active');
            }}}}
        }}}});

        // Close menu when clicking on menu links
        const menuLinks = hamburgerMenu.querySelectorAll('.menu a');
        menuLinks.forEach(link => {{{{
            link.addEventListener('click', () => {{{{
                hamburgerMenu.classList.remove('active');
            }}}});
        }}}});
    </script>'''

    # Prepare template replacements
    replacements = {
        '{{RECIPE_COUNT}}': str(len(recipes_meta)),
        '{{BASE_URL}}': BASE_URL,
        '{{OG_IMAGE}}': f'<meta property="og:image" content="{full_first_image}">' if full_first_image else '',
        '{{TWITTER_IMAGE}}': f'<meta property="twitter:image" content="{full_first_image}">' if full_first_image else '',
        '{{CATEGORY_FILTERS}}': categories_filter,
        '{{RECIPE_CARDS}}': cards_html,
        '{{JAVASCRIPT}}': javascript
    }

    # Apply replacements
    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

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

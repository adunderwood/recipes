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
PARTIALS_DIR = Path('templates/partials')
STYLE_CSS_PATH = Path('style.css')


def load_partial(path):
    """Load a shared partial file from disk."""
    partial_path = Path(path)
    if not partial_path.exists():
        raise FileNotFoundError(f"{partial_path} not found")
    return partial_path.read_text(encoding='utf-8')


def load_template(path):
    """Load a template file and expand shared partial placeholders."""
    template_path = Path(path)
    if not template_path.exists():
        raise FileNotFoundError(f"{path} not found")

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    partials = {
        '{{PAGE_HEAD}}': PARTIALS_DIR / 'page_head.html',
        '{{HOME_NAV}}': PARTIALS_DIR / 'home_nav.html',
        '{{BACK_NAV}}': PARTIALS_DIR / 'back_nav.html',
        '{{HAMBURGER_MENU}}': PARTIALS_DIR / 'hamburger_menu.html',
        '{{HAMBURGER_MENU_SCRIPT}}': PARTIALS_DIR / 'hamburger_menu.js',
    }

    for placeholder, partial_path in partials.items():
        if placeholder in template:
            template = template.replace(placeholder, load_partial(partial_path))

    return template


def build_page_scripts(*script_parts):
    """Wrap one or more inline script fragments in a single script tag."""
    cleaned_parts = [part.strip('\n') for part in script_parts if part and part.strip()]
    if not cleaned_parts:
        return ''
    return '<script>\n' + '\n\n'.join(cleaned_parts) + '\n    </script>'


def apply_replacements(template, replacements):
    """Replace placeholders in a template string."""
    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    return html


def build_json_ld_block(data):
    """Serialize structured data into an inline JSON-LD script block."""
    if not data:
        return ''
    json_ld = json.dumps(data, ensure_ascii=False, indent=2)
    return f'<script type="application/ld+json">\n{json_ld}\n    </script>'


def build_og_extra(image_url='', image_alt=''):
    """Build optional Open Graph image tags plus the shared site name."""
    tags = []
    if image_url:
        tags.append(f'<meta property="og:image" content="{image_url}">')
        if image_alt:
            tags.append(f'<meta property="og:image:alt" content="{image_alt}">')
    tags.append('<meta property="og:site_name" content="Everything that Rises">')
    return '\n    '.join(tags)


def build_twitter_extra(image_url='', image_alt=''):
    """Build optional Twitter image tags."""
    tags = []
    if image_url:
        tags.append(f'<meta property="twitter:image" content="{image_url}">')
        if image_alt:
            tags.append(f'<meta property="twitter:image:alt" content="{image_alt}">')
    return '\n    '.join(tags)


def build_head_replacements(
    *,
    page_title,
    meta_description,
    og_type,
    page_url,
    og_title,
    og_description,
    canonical_url,
    twitter_card,
    twitter_title,
    twitter_description,
    json_ld_data=None,
    og_image_url='',
    og_image_alt='',
    twitter_image_url='',
    twitter_image_alt='',
):
    """Build the shared placeholder replacements for the page head partial."""
    style_version = str(int(STYLE_CSS_PATH.stat().st_mtime)) if STYLE_CSS_PATH.exists() else '1'
    return {
        '{{PAGE_TITLE}}': page_title,
        '{{META_DESCRIPTION}}': meta_description,
        '{{OG_TYPE}}': og_type,
        '{{PAGE_URL}}': page_url,
        '{{OG_TITLE}}': og_title,
        '{{OG_DESCRIPTION}}': og_description,
        '{{OG_EXTRA}}': build_og_extra(og_image_url, og_image_alt),
        '{{TWITTER_CARD}}': twitter_card,
        '{{TWITTER_TITLE}}': twitter_title,
        '{{TWITTER_DESCRIPTION}}': twitter_description,
        '{{TWITTER_EXTRA}}': build_twitter_extra(twitter_image_url, twitter_image_alt),
        '{{CANONICAL_URL}}': canonical_url,
        '{{JSON_LD_BLOCK}}': build_json_ld_block(json_ld_data),
        '{{STYLE_VERSION}}': style_version,
    }


def build_recipe_nav_actions():
    """Return the recipe-page print controls markup."""
    return '''<div class="print-controls">
                <button onclick="printStandard()" class="print-btn" aria-label="Print this recipe in standard format">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <polyline points="6 9 6 2 18 2 18 9"></polyline>
                        <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
                        <rect x="6" y="14" width="12" height="8"></rect>
                    </svg>
                    <span class="print-btn-text">Print</span>
                </button>
            </div>'''


def build_about_nav_actions():
    """Return invisible nav actions so the About header matches recipe-page geometry."""
    return '''<div class="print-controls about-nav-actions" aria-hidden="true">
                <button class="print-btn" tabindex="-1">Print</button>
            </div>'''


def validate_generated_page(page_path, required_strings):
    """Raise an error if a generated page is missing required metadata markers."""
    if not page_path.exists():
        raise FileNotFoundError(f"Generated page not found: {page_path}")

    page_html = page_path.read_text(encoding='utf-8')
    missing_strings = [marker for marker in required_strings if marker not in page_html]
    if missing_strings:
        raise ValueError(
            f"{page_path.name} is missing required metadata markers: {', '.join(missing_strings)}"
        )


def validate_generated_output(output_dir, recipes_meta):
    """Sanity-check generated pages for core SEO and sharing metadata."""
    output_path = Path(output_dir)
    shared_markers = [
        '<title>',
        '<meta name="description"',
        '<link rel="canonical"',
        '<meta property="og:type"',
        '<meta property="og:title"',
        '<meta property="og:description"',
        '<meta property="twitter:card"',
        '<meta property="twitter:title"',
        '<meta property="twitter:description"',
    ]

    validate_generated_page(
        output_path / 'index.html',
        shared_markers + [
            '<script type="application/ld+json">',
            '<meta property="og:image"',
            '<meta property="twitter:image"',
        ]
    )
    validate_generated_page(output_path / 'about.html', shared_markers)

    if recipes_meta:
        sample_recipe_path = output_path / f"{recipes_meta[0]['filename']}.html"
        validate_generated_page(
            sample_recipe_path,
            shared_markers + [
                '<script type="application/ld+json">',
                '"@type": "Recipe"',
                '<meta property="og:image"',
                '<meta property="twitter:image"',
            ]
        )
        print(f"Validated metadata for index, about, and sample recipe: {sample_recipe_path.name}")
    else:
        print("No recipe pages generated; skipped sample recipe metadata validation.")

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

def normalize_ingredient_text(ingredient):
    """Return a cleaned ingredient string."""
    return str(ingredient).strip()

def is_ingredient_header(ingredient):
    """Treat bracketed or dash-prefixed ingredients as section headers."""
    ingredient_text = normalize_ingredient_text(ingredient)
    return ingredient_text.startswith('-') or (
        ingredient_text.startswith('[') and ingredient_text.endswith(']')
    )

def extract_ingredient_header_text(ingredient):
    """Return display text for supported ingredient header formats."""
    ingredient_text = normalize_ingredient_text(ingredient)

    if ingredient_text.startswith('-'):
        return ingredient_text[1:].strip()

    if ingredient_text.startswith('[') and ingredient_text.endswith(']'):
        return ingredient_text[1:-1].strip()

    return ingredient_text

def is_ingredient_spacer(ingredient):
    """Treat empty ingredient rows as visual spacers."""
    return normalize_ingredient_text(ingredient) == ''

def format_ingredient_item(ingredient):
    """Render an ingredient list item, supporting header rows without checkboxes."""
    ingredient_text = normalize_ingredient_text(ingredient)

    if is_ingredient_spacer(ingredient_text):
        return '<li class="ingredient-spacer" aria-hidden="true"></li>'

    if is_ingredient_header(ingredient_text):
        header_text = extract_ingredient_header_text(ingredient_text)
        return f'<li class="ingredient-header">{escape(header_text)}</li>'

    return (
        f'<li><label class="ingredient-checkbox"><input type="checkbox" '
        f'aria-label="Check off {escape(ingredient_text)}"><span>{escape(ingredient_text)}</span></label></li>'
    )


def format_category_pill(category, linked=False):
    """Render a category pill, optionally linking to the homepage filter state."""
    category_text = escape(category)
    if linked:
        category_slug = quote(str(category).strip().lower())
        return f'<a class="category" href="/?category={category_slug}">{category_text}</a>'
    return f'<span class="category">{category_text}</span>'

def generate_recipe_page(recipe, output_dir):
    """Generate individual recipe HTML page from template."""
    template = load_template('templates/recipe.html')

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
    ingredients_html = '\n'.join([format_ingredient_item(ing) for ing in ingredients])

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
    categories_html = ' '.join([format_category_pill(cat, linked=True) for cat in categories])

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
        "url": recipe_url,
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
        json_ld["isBasedOn"] = source_url
    if recipe.get('datePublished'):
        json_ld["datePublished"] = recipe.get('datePublished')

    page_scripts = build_page_scripts(
        load_partial(PARTIALS_DIR / 'print_helpers.js'),
        load_partial(PARTIALS_DIR / 'hamburger_menu.js')
    )

    # Prepare template replacements
    replacements = {
        '{{NAV_ACTIONS}}': build_recipe_nav_actions(),
        '{{RECIPE_NAME}}': name,
        '{{RECIPE_URL}}': recipe_url,
        '{{PAGE_SCRIPTS}}': page_scripts,
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
    replacements.update(build_head_replacements(
        page_title=f'{name} - Everything that Rises',
        meta_description=meta_description,
        og_type='article',
        page_url=recipe_url,
        og_title=name,
        og_description=meta_description,
        canonical_url=recipe_url,
        twitter_card='summary_large_image',
        twitter_title=name,
        twitter_description=meta_description,
        json_ld_data=json_ld,
        og_image_url=full_image_url,
        og_image_alt=f'Photo of {name}' if full_image_url else '',
        twitter_image_url=full_image_url,
        twitter_image_alt=f'Photo of {name}' if full_image_url else '',
    ))

    # Apply replacements
    html = apply_replacements(template, replacements)

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
    template = load_template('templates/index.html')

    # Build recipe cards
    cards_html = ''
    for meta in recipes_meta:
        # Better alt text for images
        alt_text = f"{meta['name']} recipe photo" if meta['image'] else ''
        image_html = f'<img src="{meta["image"]}" alt="{alt_text}">' if meta['image'] else '<div class="no-image" role="img" aria-label="No image available">No Image</div>'
        categories_html = ' '.join([format_category_pill(cat) for cat in meta['categories']])

        searchable_ingredients = [
            normalize_ingredient_text(ingredient)
            for ingredient in meta['ingredients']
            if normalize_ingredient_text(ingredient)
            and not is_ingredient_spacer(ingredient)
            and not is_ingredient_header(ingredient)
        ]
        ingredients_text = ' '.join(searchable_ingredients).lower()
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
    website_json_ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Everything that Rises",
        "url": BASE_URL,
        "description": f"A curated collection of {len(recipes_meta)} delicious recipes from around the world."
    }
    # Build JavaScript for homepage search/filter interactions
    search_script = '''        // Search and filter functionality
        const searchInput = document.getElementById('search');
        const filterBtns = document.querySelectorAll('.filter-btn');
        const recipeCards = document.querySelectorAll('.recipe-card');
        const noResults = document.getElementById('no-results');
        const validCategories = new Set(Array.from(filterBtns).map(btn => btn.dataset.category));

        let currentCategory = 'all';
        let currentSearch = '';

        function syncActiveFilterButton() {
            filterBtns.forEach(btn => {
                const isActive = btn.dataset.category === currentCategory;
                btn.classList.toggle('active', isActive);
                btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
            });
        }

        function updateUrlState() {
            const params = new URLSearchParams(window.location.search);

            if (currentCategory && currentCategory !== 'all') {
                params.set('category', currentCategory);
            } else {
                params.delete('category');
            }

            if (currentSearch) {
                params.set('q', currentSearch);
            } else {
                params.delete('q');
            }

            const queryString = params.toString();
            const nextUrl = queryString ? `${window.location.pathname}?${queryString}` : window.location.pathname;
            window.history.replaceState({ category: currentCategory, search: currentSearch }, '', nextUrl);
        }

        function applyUrlState() {
            const params = new URLSearchParams(window.location.search);
            const requestedCategory = (params.get('category') || 'all').trim().toLowerCase();
            const requestedSearch = (params.get('q') || '').trim().toLowerCase();

            currentCategory = validCategories.has(requestedCategory) ? requestedCategory : 'all';
            currentSearch = requestedSearch;
            searchInput.value = requestedSearch;
            syncActiveFilterButton();
            filterRecipes();
        }

        function filterRecipes() {
            let visibleCount = 0;

            recipeCards.forEach(card => {
                const cardName = card.querySelector('h2').textContent.toLowerCase();
                const cardDesc = card.querySelector('.card-description')?.textContent.toLowerCase() || '';
                const cardIngredients = card.dataset.ingredients || '';
                const cardCategories = JSON.parse(card.dataset.categories || '[]');

                let matchesSearch = false;
                if (currentSearch === '') {
                    matchesSearch = true;
                } else if (currentSearch.includes(',')) {
                    // Comma-separated search: AND logic - all terms must match in ingredients
                    const searchTerms = currentSearch.split(',').map(term => term.trim()).filter(term => term.length > 0);
                    matchesSearch = searchTerms.every(term => cardIngredients.includes(term));
                } else if (currentSearch.length === 1) {
                    // For single character, match word-initial letters in title only
                    const nameWords = cardName.split(/\\s+/);
                    matchesSearch = nameWords.some(word => word.startsWith(currentSearch));
                } else {
                    // For 2+ characters, search title, description, and ingredients
                    matchesSearch = cardName.includes(currentSearch) ||
                                    cardDesc.includes(currentSearch) ||
                                    cardIngredients.includes(currentSearch);
                }

                const matchesCategory = currentCategory === 'all' ||
                    cardCategories.includes(currentCategory);

                if (matchesSearch && matchesCategory) {
                    card.style.display = '';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        }

        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value.toLowerCase();
            updateUrlState();
            filterRecipes();
        });

        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // If clicking an already active button (except "All Recipes"), toggle it off
                if (btn.classList.contains('active') && btn.dataset.category !== 'all') {
                    currentCategory = 'all';
                } else {
                    currentCategory = btn.dataset.category;
                }
                syncActiveFilterButton();
                updateUrlState();
                filterRecipes();
            });
        });

        window.addEventListener('popstate', () => {
            applyUrlState();
        });

        applyUrlState();
'''
    page_scripts = build_page_scripts(
        search_script,
        load_partial(PARTIALS_DIR / 'hamburger_menu.js')
    )

    # Prepare template replacements
    replacements = {
        '{{NAV_ACTIONS}}': '',
        '{{RECIPE_COUNT}}': str(len(recipes_meta)),
        '{{BASE_URL}}': BASE_URL,
        '{{CATEGORY_FILTERS}}': categories_filter,
        '{{RECIPE_CARDS}}': cards_html,
        '{{PAGE_SCRIPTS}}': page_scripts
    }
    index_title = f'Everything that Rises - {len(recipes_meta)} Delicious Recipes'
    index_description = (
        f'A curated collection of {len(recipes_meta)} delicious recipes from around the world. '
        'Browse, search, and filter recipes by category and ingredients.'
    )
    replacements.update(build_head_replacements(
        page_title=index_title,
        meta_description=index_description,
        og_type='website',
        page_url=BASE_URL,
        og_title=index_title,
        og_description=index_description,
        canonical_url=BASE_URL,
        twitter_card='summary_large_image',
        twitter_title=index_title,
        twitter_description=index_description,
        json_ld_data=website_json_ld,
        og_image_url=full_first_image,
        og_image_alt='Everything that Rises recipe collection preview' if full_first_image else '',
        twitter_image_url=full_first_image,
        twitter_image_alt='Everything that Rises recipe collection preview' if full_first_image else '',
    ))

    # Apply replacements
    html = apply_replacements(template, replacements)

    output_path = Path(output_dir) / 'index.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

def copy_about_page(output_dir):
    """Render about page from template."""
    about_template = Path('templates/about.html')
    if about_template.exists():
        output_path = Path(output_dir) / 'about.html'
        template = load_template(about_template)
        replacements = {
            '{{NAV_ACTIONS}}': build_about_nav_actions(),
            '{{PAGE_SCRIPTS}}': build_page_scripts(load_partial(PARTIALS_DIR / 'hamburger_menu.js')),
        }
        about_title = 'About - Everything that Rises'
        about_description = 'Learn about Everything that Rises, a curated collection of delicious recipes.'
        replacements.update(build_head_replacements(
            page_title=about_title,
            meta_description=about_description,
            og_type='website',
            page_url=f'{BASE_URL}/about',
            og_title=about_title,
            og_description=about_description,
            canonical_url=f'{BASE_URL}/about',
            twitter_card='summary',
            twitter_title=about_title,
            twitter_description=about_description,
        ))
        html = apply_replacements(template, replacements)
        output_path.write_text(html, encoding='utf-8')
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

    # Validate key metadata on generated pages
    print("Validating generated metadata...")
    validate_generated_output(output_dir, recipes_meta)

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

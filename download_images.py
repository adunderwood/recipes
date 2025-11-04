#!/usr/bin/env python3
"""
Download recipe images from Recipe Sage export and save them locally.
"""
import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse

def download_images(recipes_file, output_dir):
    """Download all recipe images from the JSON file."""

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load recipes
    with open(recipes_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Load existing image mappings if they exist
    image_map_file = output_path / '.image_urls.json'
    image_map = {}
    if image_map_file.exists():
        with open(image_map_file, 'r', encoding='utf-8') as f:
            image_map = json.load(f)

    recipes = data['recipes']
    total = len(recipes)
    downloaded = 0
    skipped = 0
    failed = 0
    updated = 0

    print(f"Processing {total} recipes...")

    for i, recipe in enumerate(recipes, 1):
        recipe_id = recipe.get('identifier', f'recipe-{i}')
        recipe_name = recipe.get('name', 'Unknown')
        images = recipe.get('image', [])

        if not images:
            print(f"[{i}/{total}] Skipping '{recipe_name}' - no image")
            skipped += 1
            continue

        # Get first image URL
        image_url = images[0] if isinstance(images, list) else images

        # Generate filename from recipe ID
        parsed = urlparse(image_url)
        ext = os.path.splitext(parsed.path)[1] or '.jpg'
        filename = f"{recipe_id}{ext}"
        output_file = output_path / filename

        # Check if we need to download (new image or URL changed)
        needs_download = False
        if not output_file.exists():
            needs_download = True
            reason = "new image"
        elif recipe_id in image_map and image_map[recipe_id] != image_url:
            needs_download = True
            reason = "URL changed"
        elif recipe_id not in image_map:
            needs_download = True
            reason = "not tracked"

        if needs_download:
            try:
                if reason == "URL changed":
                    print(f"[{i}/{total}] Updating '{recipe_name}' (image URL changed)...")
                    updated += 1
                else:
                    print(f"[{i}/{total}] Downloading '{recipe_name}'...")
                    downloaded += 1
                urllib.request.urlretrieve(image_url, output_file)
                image_map[recipe_id] = image_url
            except urllib.error.URLError as e:
                print(f"[{i}/{total}] Failed to download '{recipe_name}': {e}")
                failed += 1
                continue
            except Exception as e:
                print(f"[{i}/{total}] Error processing '{recipe_name}': {e}")
                failed += 1
                continue
        else:
            print(f"[{i}/{total}] Already exists: {filename}")
            skipped += 1

        # Update recipe with local path
        recipe['localImage'] = f"images/{filename}"

    # Save image URL mappings for future comparisons
    with open(image_map_file, 'w', encoding='utf-8') as f:
        json.dump(image_map, f, indent=2, ensure_ascii=False)

    # Save updated recipes with local image paths
    output_json = Path(recipes_file).parent / 'recipes_with_local_images.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Downloaded: {downloaded}")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Total: {total}")
    print(f"\nUpdated recipes saved to: {output_json}")

if __name__ == '__main__':
    recipes_file = 'data/recipes.json'
    output_dir = 'images'
    download_images(recipes_file, output_dir)

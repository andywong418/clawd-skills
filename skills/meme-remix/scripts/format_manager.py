#!/usr/bin/env python3
"""
Format Manager - Add, update, and query meme formats

Designed to feed into a webapp showing trending formats.

Usage:
    python format_manager.py add --name "Ghibli Transform" --desc "..." --example https://...
    python format_manager.py list --json
    python format_manager.py get <format_id>
    python format_manager.py trending
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

FORMATS_DIR = Path(__file__).parent.parent / 'formats'
FORMATS_FILE = FORMATS_DIR / 'formats.json'
TRENDING_FILE = FORMATS_DIR / 'trending.json'


def load_formats() -> dict:
    """Load formats database."""
    if FORMATS_FILE.exists():
        with open(FORMATS_FILE) as f:
            return json.load(f)
    return {'formats': [], 'metadata': {'version': '1.0'}}


def save_formats(data: dict):
    """Save formats database."""
    FORMATS_DIR.mkdir(parents=True, exist_ok=True)
    data['metadata']['last_updated'] = datetime.now(timezone.utc).isoformat()
    with open(FORMATS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_trending() -> dict:
    """Load trending data."""
    if TRENDING_FILE.exists():
        with open(TRENDING_FILE) as f:
            return json.load(f)
    return {'trending': [], 'last_updated': None}


def save_trending(data: dict):
    """Save trending data."""
    data['last_updated'] = datetime.now(timezone.utc).isoformat()
    with open(TRENDING_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def slugify(name: str) -> str:
    """Convert name to URL-safe id."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def add_format(
    name: str,
    description: str,
    structure: dict = None,
    remix_points: dict = None,
    examples: list = None,
    source_url: str = None,
    tags: list = None,
    humor_mechanic: str = None
) -> dict:
    """Add a new format to the database."""
    data = load_formats()
    
    format_id = slugify(name)
    
    # Check if exists
    existing = next((f for f in data['formats'] if f['id'] == format_id), None)
    if existing:
        # Update existing
        existing['name'] = name
        existing['description'] = description
        if structure:
            existing['structure'] = structure
        if remix_points:
            existing['remix_points'] = remix_points
        if examples:
            existing.setdefault('examples', []).extend(examples)
            existing['examples'] = list(set(existing['examples']))  # dedupe
        if source_url:
            existing['source_url'] = source_url
        if tags:
            existing['tags'] = tags
        if humor_mechanic:
            existing['humor_mechanic'] = humor_mechanic
        existing['updated_at'] = datetime.now(timezone.utc).isoformat()
        new_format = existing
    else:
        # Create new
        new_format = {
            'id': format_id,
            'name': name,
            'description': description,
            'structure': structure or {
                'visual': 'Describe the visual structure',
                'text': 'Describe text/caption placement',
                'timing': 'Describe pacing/timing'
            },
            'remix_points': remix_points or {
                'face': 'Can swap faces',
                'text': 'Can change text/caption',
                'context': 'Can change scenario'
            },
            'examples': examples or [],
            'source_url': source_url,
            'tags': tags or [],
            'humor_mechanic': humor_mechanic,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'use_count': 0,
            'viral_score': 0
        }
        data['formats'].append(new_format)
    
    save_formats(data)
    return new_format


def get_format(format_id: str) -> Optional[dict]:
    """Get a format by ID."""
    data = load_formats()
    return next((f for f in data['formats'] if f['id'] == format_id), None)


def list_formats(as_json: bool = False, tags: list = None) -> list:
    """List all formats, optionally filtered by tags."""
    data = load_formats()
    formats = data['formats']
    
    if tags:
        formats = [f for f in formats if any(t in f.get('tags', []) for t in tags)]
    
    if as_json:
        return formats
    
    return formats


def record_use(format_id: str):
    """Record that a format was used (for trending)."""
    data = load_formats()
    fmt = next((f for f in data['formats'] if f['id'] == format_id), None)
    if fmt:
        fmt['use_count'] = fmt.get('use_count', 0) + 1
        fmt['last_used'] = datetime.now(timezone.utc).isoformat()
        save_formats(data)
    
    # Also update trending
    trending = load_trending()
    entry = next((t for t in trending['trending'] if t['id'] == format_id), None)
    if entry:
        entry['uses_today'] = entry.get('uses_today', 0) + 1
    else:
        trending['trending'].append({
            'id': format_id,
            'uses_today': 1,
            'first_seen': datetime.now(timezone.utc).isoformat()
        })
    save_trending(trending)


def update_viral_score(format_id: str, score: int, source: str = None):
    """Update viral score based on external signals (views, shares, etc.)."""
    data = load_formats()
    fmt = next((f for f in data['formats'] if f['id'] == format_id), None)
    if fmt:
        fmt['viral_score'] = score
        if source:
            fmt.setdefault('viral_sources', []).append({
                'source': source,
                'score': score,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        save_formats(data)


def get_trending(limit: int = 10) -> list:
    """Get trending formats sorted by viral score and use count."""
    data = load_formats()
    formats = data['formats']
    
    # Sort by viral_score desc, then use_count desc
    sorted_formats = sorted(
        formats,
        key=lambda f: (f.get('viral_score', 0), f.get('use_count', 0)),
        reverse=True
    )
    
    return sorted_formats[:limit]


def export_for_webapp() -> dict:
    """Export formats in webapp-friendly structure."""
    data = load_formats()
    trending = get_trending(20)
    
    return {
        'formats': data['formats'],
        'trending': [f['id'] for f in trending],
        'total_count': len(data['formats']),
        'last_updated': data['metadata'].get('last_updated'),
        'api_version': '1.0'
    }


def main():
    parser = argparse.ArgumentParser(description='Manage meme formats')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new format')
    add_parser.add_argument('--name', '-n', required=True, help='Format name')
    add_parser.add_argument('--desc', '-d', required=True, help='Description')
    add_parser.add_argument('--example', '-e', action='append', help='Example URL (repeatable)')
    add_parser.add_argument('--source', '-s', help='Source/origin URL')
    add_parser.add_argument('--tag', '-t', action='append', help='Tag (repeatable)')
    add_parser.add_argument('--humor', help='Humor mechanic explanation')
    add_parser.add_argument('--visual', help='Visual structure description')
    add_parser.add_argument('--text-format', help='Text/caption format')
    add_parser.add_argument('--timing', help='Timing/pacing description')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List formats')
    list_parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')
    list_parser.add_argument('--tag', '-t', action='append', help='Filter by tag')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get format by ID')
    get_parser.add_argument('format_id', help='Format ID')
    get_parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')
    
    # Trending command
    trending_parser = subparsers.add_parser('trending', help='Get trending formats')
    trending_parser.add_argument('--limit', '-l', type=int, default=10, help='Number of results')
    trending_parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export for webapp')
    export_parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    
    # Use command (record usage)
    use_parser = subparsers.add_parser('use', help='Record format usage')
    use_parser.add_argument('format_id', help='Format ID')
    
    args = parser.parse_args()
    
    if args.command == 'add':
        structure = {}
        if args.visual:
            structure['visual'] = args.visual
        if args.text_format:
            structure['text'] = args.text_format
        if args.timing:
            structure['timing'] = args.timing
        
        fmt = add_format(
            name=args.name,
            description=args.desc,
            structure=structure if structure else None,
            examples=args.example,
            source_url=args.source,
            tags=args.tag,
            humor_mechanic=args.humor
        )
        print(f"✓ Added/updated format: {fmt['id']}")
        print(json.dumps(fmt, indent=2))
    
    elif args.command == 'list':
        formats = list_formats(as_json=True, tags=args.tag)
        if args.json:
            print(json.dumps(formats, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"MEME FORMATS ({len(formats)} total)")
            print(f"{'='*60}\n")
            for fmt in formats:
                tags = ' '.join(f'[{t}]' for t in fmt.get('tags', []))
                score = fmt.get('viral_score', 0)
                uses = fmt.get('use_count', 0)
                print(f"📌 {fmt['name']} ({fmt['id']}) {tags}")
                print(f"   {fmt['description']}")
                print(f"   Score: {score} | Uses: {uses}")
                print()
    
    elif args.command == 'get':
        fmt = get_format(args.format_id)
        if fmt:
            if args.json:
                print(json.dumps(fmt, indent=2))
            else:
                print(f"\n{fmt['name']} ({fmt['id']})")
                print(f"{'='*40}")
                print(f"Description: {fmt['description']}")
                print(f"Structure: {json.dumps(fmt.get('structure', {}), indent=2)}")
                print(f"Remix points: {', '.join(fmt.get('remix_points', {}).keys())}")
                if fmt.get('examples'):
                    print(f"Examples: {', '.join(fmt['examples'][:3])}")
                if fmt.get('humor_mechanic'):
                    print(f"Humor: {fmt['humor_mechanic']}")
        else:
            print(f"Format not found: {args.format_id}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'trending':
        formats = get_trending(args.limit)
        if args.json:
            print(json.dumps(formats, indent=2))
        else:
            print(f"\n🔥 TRENDING FORMATS\n")
            for i, fmt in enumerate(formats, 1):
                score = fmt.get('viral_score', 0)
                uses = fmt.get('use_count', 0)
                print(f"{i}. {fmt['name']} (score: {score}, uses: {uses})")
    
    elif args.command == 'export':
        data = export_for_webapp()
        output = json.dumps(data, indent=2)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"✓ Exported to {args.output}")
        else:
            print(output)
    
    elif args.command == 'use':
        record_use(args.format_id)
        print(f"✓ Recorded use of {args.format_id}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Fetch and extract content from a business website for profiling."""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
import urllib.request
import urllib.error
from html.parser import HTMLParser

class TextExtractor(HTMLParser):
    """Extract text content from HTML."""
    
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip_tags = {'script', 'style', 'nav', 'footer', 'header', 'noscript'}
        self.current_skip = 0
        
    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.current_skip += 1
            
    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.current_skip = max(0, self.current_skip - 1)
            
    def handle_data(self, data):
        if self.current_skip == 0:
            text = data.strip()
            if text:
                self.text.append(text)
                
    def get_text(self):
        return '\n'.join(self.text)

def fetch_page(url: str, timeout: int = 30) -> str:
    """Fetch a webpage and return HTML content."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or 'utf-8'
            return resp.read().decode(charset, errors='ignore')
    except Exception as e:
        print(f"  Failed to fetch {url}: {e}", file=sys.stderr)
        return ""

def extract_text(html: str) -> str:
    """Extract readable text from HTML."""
    parser = TextExtractor()
    try:
        parser.feed(html)
        return parser.get_text()
    except:
        return ""

def find_links(html: str, base_url: str) -> list:
    """Find internal links in HTML."""
    links = []
    pattern = r'href=["\']([^"\']+)["\']'
    
    for match in re.findall(pattern, html, re.IGNORECASE):
        if match.startswith('#') or match.startswith('mailto:') or match.startswith('tel:'):
            continue
        
        full_url = urljoin(base_url, match)
        parsed = urlparse(full_url)
        base_parsed = urlparse(base_url)
        
        # Only internal links
        if parsed.netloc == base_parsed.netloc:
            links.append(full_url)
    
    return list(set(links))

def find_key_pages(links: list, base_url: str) -> dict:
    """Identify key pages to analyze."""
    key_pages = {
        'about': None,
        'product': None,
        'pricing': None,
        'services': None,
        'features': None,
        'customers': None,
        'case-studies': None,
        'blog': None
    }
    
    patterns = {
        'about': r'/about|/company|/story|/team|/who-we-are',
        'product': r'/product|/solution|/platform|/how-it-works',
        'pricing': r'/pricing|/plans|/cost',
        'services': r'/service|/offering|/what-we-do',
        'features': r'/feature|/capability',
        'customers': r'/customer|/client|/testimonial|/review',
        'case-studies': r'/case-stud|/success-stor|/portfolio',
        'blog': r'/blog|/news|/resource|/article'
    }
    
    for link in links:
        lower_link = link.lower()
        for key, pattern in patterns.items():
            if key_pages[key] is None and re.search(pattern, lower_link):
                key_pages[key] = link
                break
    
    return key_pages

def main():
    parser = argparse.ArgumentParser(description="Profile a business website")
    parser.add_argument("url", help="Website URL to profile")
    parser.add_argument("--output", type=str, default="./output",
                       help="Output directory")
    parser.add_argument("--max-pages", type=int, default=6,
                       help="Maximum pages to fetch")
    
    args = parser.parse_args()
    
    # Normalize URL
    url = args.url
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace('www.', '')
    
    print(f"Profiling: {domain}")
    print(f"Output: {output_dir}")
    print()
    
    # Fetch homepage
    print("Fetching homepage...")
    homepage_html = fetch_page(url)
    if not homepage_html:
        print("Failed to fetch homepage", file=sys.stderr)
        sys.exit(1)
    
    homepage_text = extract_text(homepage_html)
    
    # Find key pages
    links = find_links(homepage_html, url)
    key_pages = find_key_pages(links, url)
    
    # Fetch key pages
    pages_content = {'homepage': homepage_text}
    pages_fetched = 1
    
    for page_type, page_url in key_pages.items():
        if page_url and pages_fetched < args.max_pages:
            print(f"Fetching {page_type}: {page_url}")
            html = fetch_page(page_url)
            if html:
                pages_content[page_type] = extract_text(html)
                pages_fetched += 1
    
    print(f"\nFetched {pages_fetched} pages")
    
    # Generate raw content file for analysis
    raw_output = output_dir / f"{domain.replace('.', '_')}_raw.md"
    
    with open(raw_output, 'w') as f:
        f.write(f"# Website Content: {domain}\n")
        f.write(f"Fetched: {datetime.now().isoformat()}\n")
        f.write(f"URL: {url}\n\n")
        
        for page_type, content in pages_content.items():
            if content:
                f.write(f"---\n\n## {page_type.upper()}\n\n")
                # Truncate very long content
                if len(content) > 8000:
                    content = content[:8000] + "\n\n[...truncated...]"
                f.write(content)
                f.write("\n\n")
    
    print(f"\nRaw content saved: {raw_output}")
    
    # Generate template for profile
    profile_output = output_dir / "BUSINESS_PROFILE.md"
    
    with open(profile_output, 'w') as f:
        f.write(f"""# Business Profile: {domain}

**URL:** {url}
**Profiled:** {datetime.now().strftime('%Y-%m-%d')}

---

## Company Overview
<!-- What they do, mission, founding story -->

[TO BE FILLED BY ANALYSIS]

## Target Market
<!-- Who they serve - demographics, psychographics, B2B/B2C, industry verticals -->

**Primary Audience:**
**Secondary Audience:**
**Market Segment:** B2B / B2C / Both

## Offering
<!-- Products/services, key features, pricing model -->

**Core Product/Service:**
**Key Features:**
**Pricing Model:**

## Use Cases
<!-- How customers use it, problems solved, outcomes -->

1. 
2. 
3. 

## Brand Persona
<!-- Voice, tone, personality, visual style -->

**Voice:** (e.g., professional, casual, playful, authoritative)
**Tone:** (e.g., friendly, serious, inspirational)
**Personality Traits:**
**Visual Style:**

## Content Angles
<!-- Suggested themes/hooks for viral content based on their niche -->

### Hook Ideas:
1. 
2. 
3. 

### Content Themes:
- 
- 
- 

## Competitors
<!-- Known or inferred competitors -->

- 

## Notes
<!-- Additional observations -->

---

*Raw content available at: {raw_output.name}*
""")
    
    print(f"Profile template saved: {profile_output}")
    print(f"\n✅ Ready for analysis. Review {raw_output.name} and fill in {profile_output.name}")

if __name__ == "__main__":
    main()

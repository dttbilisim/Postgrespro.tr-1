#!/usr/bin/env python3
"""
Blog Scraper for postgrespro.com/blog
Scrapes all blog posts and saves them as JSON files in wwwroot/content/blog/
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime
import time
from pathlib import Path

BASE_URL = "https://postgrespro.com/blog"
CONTENT_DIR = Path(__file__).parent.parent / "Postgrespro.tr" / "wwwroot" / "content" / "blog"
IMAGES_DIR = Path(__file__).parent.parent / "Postgrespro.tr" / "wwwroot" / "blog"

# Category mappings
CATEGORY_MAP = {
    "PostgreSQL": {"en": "PostgreSQL", "tr": "PostgreSQL"},
    "Company Updates": {"en": "Company Updates", "tr": "Şirket Güncellemeleri"}
}

def sanitize_filename(filename):
    """Sanitize filename for filesystem"""
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename.lower().strip('-')

def generate_slug(title):
    """Generate URL-friendly slug from title"""
    slug = title.lower()
    # Replace Turkish characters
    slug = slug.replace('ğ', 'g').replace('ü', 'u').replace('ş', 's')
    slug = slug.replace('ı', 'i').replace('ö', 'o').replace('ç', 'c')
    # Remove special characters
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    # Remove multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def calculate_reading_time(text):
    """Calculate reading time in minutes (average 200 words per minute)"""
    words = len(re.findall(r'\b\w+\b', text))
    return max(1, (words + 199) // 200)

def clean_html_content(html):
    """Clean HTML content, remove unwanted elements"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove unwanted elements
    unwanted_selectors = [
        'script', 'style', 'nav', 'footer', 'header',
        '.subscribe', '.social-share', '.newsletter',
        '.advertisement', '.ads', '[class*="ad-"]',
        '[class*="subscribe"]', '[class*="newsletter"]'
    ]
    
    for selector in unwanted_selectors:
        for element in soup.select(selector):
            element.decompose()
    
    # Remove empty paragraphs
    for p in soup.find_all('p'):
        if not p.get_text(strip=True):
            p.decompose()
    
    return str(soup)

def extract_images(html, base_url):
    """Extract image URLs from HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    images = []
    
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src')
        if src:
            # Convert relative URLs to absolute
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = urljoin(base_url, src)
            elif not src.startswith('http'):
                src = urljoin(base_url, src)
            images.append(src)
    
    return images

def download_image(img_url, slug):
    """Download image and return local path"""
    try:
        response = requests.get(img_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        # Get file extension
        parsed = urlparse(img_url)
        ext = os.path.splitext(parsed.path)[1] or '.jpg'
        
        # Create images directory for this post
        post_images_dir = IMAGES_DIR / slug
        post_images_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        filename = sanitize_filename(os.path.basename(parsed.path)) or 'image'
        if not filename.endswith(ext):
            filename += ext
        
        local_path = post_images_dir / filename
        local_path.write_bytes(response.content)
        
        # Return relative path
        return f"/blog/{slug}/{filename}"
    except Exception as e:
        print(f"Error downloading image {img_url}: {e}")
        return None

def scrape_blog_post(url):
    """Scrape a single blog post"""
    try:
        print(f"Scraping: {url}")
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title_elem = soup.find('h1') or soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else "Untitled"
        
        # Extract date
        date_str = None
        date_elem = soup.find('time') or soup.find(class_=re.compile(r'date|published'))
        if date_elem:
            date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
        
        # Try to parse date
        date = None
        if date_str:
            try:
                # Try various date formats
                for fmt in ['%Y-%m-%d', '%B %d, %Y', '%d %B %Y', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        date = datetime.strptime(date_str[:19], fmt)
                        break
                    except:
                        continue
            except:
                pass
        
        if not date:
            date = datetime.now()
        
        # Extract author
        author = "Postgres Pro"
        author_elem = soup.find(class_=re.compile(r'author|byline'))
        if author_elem:
            author = author_elem.get_text(strip=True)
        
        # Extract category
        category = "PostgreSQL"
        category_elem = soup.find(class_=re.compile(r'category|tag'))
        if category_elem:
            cat_text = category_elem.get_text(strip=True)
            if cat_text in CATEGORY_MAP:
                category = cat_text
        
        # Extract tags
        tags = []
        tag_elems = soup.find_all(class_=re.compile(r'tag|keyword'))
        for tag_elem in tag_elems:
            tag_text = tag_elem.get_text(strip=True)
            if tag_text and tag_text not in tags:
                tags.append(tag_text)
        
        # Extract content
        content_elem = soup.find('article') or soup.find('main') or soup.find(class_=re.compile(r'content|post-body'))
        if not content_elem:
            content_elem = soup.find('body')
        
        if content_elem:
            # Remove unwanted elements before extracting
            for unwanted in content_elem.find_all(['script', 'style', 'nav', 'footer']):
                unwanted.decompose()
            
            content_html = str(content_elem)
            content_html = clean_html_content(content_html)
            
            # Extract images
            images = extract_images(content_html, url)
            
            # Extract excerpt (first paragraph or meta description)
            excerpt = ""
            excerpt_elem = soup.find('meta', property='og:description') or soup.find('meta', attrs={'name': 'description'})
            if excerpt_elem:
                excerpt = excerpt_elem.get('content', '')
            
            if not excerpt:
                first_p = content_elem.find('p')
                if first_p:
                    excerpt = first_p.get_text(strip=True)[:200]
            
            # Generate slug
            slug = generate_slug(title)
            
            # Calculate reading time
            content_text = content_elem.get_text()
            reading_time = calculate_reading_time(content_text)
            
            # Create blog post object
            post = {
                "title": title,
                "titleTr": title,  # Will need translation later
                "slug": slug,
                "date": date.isoformat(),
                "author": author,
                "category": category,
                "categoryTr": CATEGORY_MAP.get(category, {}).get("tr", category),
                "tags": tags,
                "tagsTr": tags,  # Will need translation later
                "sourceUrl": url,
                "canonicalUrl": url,
                "excerpt": excerpt,
                "excerptTr": excerpt,  # Will need translation later
                "content": content_html,
                "contentTr": content_html,  # Will need translation later
                "readingTime": reading_time,
                "heroImage": None,
                "images": images,
                "published": True
            }
            
            return post
        else:
            print(f"Could not find content for {url}")
            return None
            
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def find_all_blog_links(base_url):
    """Find all blog post links from the blog listing pages"""
    links = set()
    page = 1
    
    while True:
        url = f"{base_url}" if page == 1 else f"{base_url}?page={page}"
        try:
            print(f"Fetching blog list page {page}...")
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all blog post links
            # Common patterns: article > a, .post > a, .blog-post > a, etc.
            post_links = soup.find_all('a', href=re.compile(r'/blog/'))
            
            found_new = False
            for link in post_links:
                href = link.get('href', '')
                if href and '/blog/' in href:
                    full_url = urljoin(base_url, href)
                    if full_url not in links:
                        links.add(full_url)
                        found_new = True
            
            # Check if there's a next page
            next_link = soup.find('a', class_=re.compile(r'next|pagination'))
            if not found_new or not next_link:
                break
            
            page += 1
            time.sleep(1)  # Be polite
            
        except Exception as e:
            print(f"Error fetching blog list page {page}: {e}")
            break
    
    return links

def main():
    """Main scraping function"""
    print("Starting blog scraping...")
    
    # Create directories
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all blog post URLs
    print("Finding all blog post URLs...")
    blog_urls = find_all_blog_links(BASE_URL)
    print(f"Found {len(blog_urls)} blog posts")
    
    # Scrape each post
    scraped_count = 0
    for url in blog_urls:
        post = scrape_blog_post(url)
        
        if post:
            # Save as JSON
            slug = post['slug']
            json_path = CONTENT_DIR / f"{slug}.json"
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(post, f, indent=2, ensure_ascii=False)
            
            scraped_count += 1
            print(f"Saved: {slug}.json")
        
        time.sleep(2)  # Be polite to the server
    
    print(f"\nScraping complete! Scraped {scraped_count} posts.")

if __name__ == "__main__":
    main()


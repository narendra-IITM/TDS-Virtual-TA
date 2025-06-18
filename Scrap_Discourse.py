import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin

BASE_URL = "https://discourse.onlinedegree.iitm.ac.in/c/courses/tds-kb/34"
OUTPUT_FILE = "discourse_data.json"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_page(url):
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {e}")
        return None

def get_topic_links(html):
    soup = BeautifulSoup(html, 'html.parser')
    topics = soup.select('tr.topic-list-item a.title')
    return [urljoin(BASE_URL, topic['href']) for topic in topics if topic.has_attr('href')]

def scrape_topic(url):
    html = get_page(url)
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    title = soup.find('h1', class_='fancy-title')
    content = soup.find('div', class_='post')
    
    if not title or not content:
        return None
    
    # Extract data
    links = []
    for link in content.select('a[href]'):
        href = link.get('href', '')
        if href:
            if not href.startswith('http'):
                href = urljoin(url, href)
            links.append({
                "url": href,
                "text": link.get_text(strip=True)[:100]
            })
    
    images = []
    for img in content.select('img'):
        src = img.get('src') or img.get('data-src')
        if src:
            if not src.startswith('http'):
                src = urljoin(url, src)
            images.append(src)
    
    return {
        "title": title.get_text(strip=True),
        "content": content.get_text(strip=True),
        "url": url,
        "links": links,
        "images": images
    }

def main():
    print("Starting scraping...")
    
    # Get main page
    main_page = get_page(BASE_URL)
    if not main_page:
        print("Failed to fetch main page")
        return
    
    # Get topic links
    topic_urls = get_topic_links(main_page)
    print(f"Found {len(topic_urls)} topics")
    
    # Scrape each topic
    scraped_data = []
    for i, url in enumerate(topic_urls, 1):
        print(f"\nProcessing topic {i}/{len(topic_urls)}: {url}")
        
        data = scrape_topic(url)
        if data:
            scraped_data.append(data)
            print(f"Success: {data['title']}")
        else:
            print(f"Failed to scrape topic")
        
        # Be gentle with the server
        time.sleep(1)
    
    # Save results
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nFinished. Saved {len(scraped_data)} topics to {OUTPUT_FILE}")

if __name__ == "__main__":
    import time
    main()

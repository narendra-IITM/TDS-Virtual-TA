from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import time
import os
import traceback

# Configuration
BASE_URL = "https://discourse.onlinedegree.iitm.ac.in/c/courses/tds-kb/34"
LOGIN_URL = "https://discourse.onlinedegree.iitm.ac.in/login"
OUTPUT_FILE = "discourse_tds_kb.json"
TIMEOUT = 20  # Increased timeout

# Get credentials from environment with fallback to empty string
USERNAME = os.getenv('DISCOURSE_USERNAME', '')
PASSWORD = os.getenv('DISCOURSE_PASSWORD', '')

def setup_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # Disabled for debugging
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.implicitly_wait(10)
    return driver

def login(driver, username, password):
    if not username or not password:
        print("No credentials provided, skipping login")
        return False
    
    print("Attempting login...")
    try:
        driver.get(LOGIN_URL)
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "login-account-name"))
        ).send_keys(username)
        
        driver.find_element(By.ID, "login-account-password").send_keys(password)
        driver.find_element(By.ID, "login-button").click()
        
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-notification-level='muted']"))
        )
        print("Login successful")
        return True
    except Exception as e:
        print(f"Login failed: {str(e)}")
        print(traceback.format_exc())
        return False

def scrape_topics(driver, base_url):
    print(f"Scraping topics from {base_url}")
    try:
        driver.get(base_url)
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".topic-list-body"))
        )
        
        # Scroll to load all topics
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        topics = soup.select('.topic-list-item')
        
        scraped_data = []
        topic_count = len(topics)
        print(f"Found {topic_count} topics to process")
        
        for i, topic in enumerate(topics, 1):
            try:
                title_link = topic.select_one('a.title')
                if not title_link:
                    continue
                    
                topic_url = title_link['href']
                if not topic_url.startswith('http'):
                    topic_url = f"https://discourse.onlinedegree.iitm.ac.in{topic_url}"
                
                print(f"\nProcessing topic {i}/{topic_count}: {title_link.get_text(strip=True)}")
                print(f"URL: {topic_url}")
                
                # Open topic in new tab
                driver.execute_script(f"window.open('{topic_url}');")
                driver.switch_to.window(driver.window_handles[1])
                
                try:
                    WebDriverWait(driver, TIMEOUT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".post"))
                    )
                    
                    topic_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    title = topic_soup.select_one('h1.fancy-title')
                    content = topic_soup.select_one('.cooked')
                    
                    if not title or not content:
                        print("Couldn't find title or content")
                        continue
                        
                    # Extract data
                    links = []
                    for link in content.select('a[href]'):
                        href = link.get('href', '')
                        if href and not href.startswith('http'):
                            href = f"https://discourse.onlinedegree.iitm.ac.in{href}"
                        links.append({
                            "url": href,
                            "text": link.get_text(strip=True)[:100]
                        })
                    
                    images = []
                    for img in content.select('img'):
                        src = img.get('src') or img.get('data-src')
                        if src and not src.startswith('http'):
                            src = f"https://discourse.onlinedegree.iitm.ac.in{src}"
                        if src:
                            images.append(src)
                    
                    scraped_data.append({
                        "title": title.get_text(strip=True),
                        "content": content.get_text(strip=True),
                        "url": topic_url,
                        "links": links,
                        "images": images
                    })
                    
                except Exception as e:
                    print(f"Error processing topic: {str(e)}")
                    print(traceback.format_exc())
                
                finally:
                    # Close tab and switch back
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Error with topic {i}: {str(e)}")
                print(traceback.format_exc())
        
        return scraped_data
    
    except Exception as e:
        print(f"Error in scrape_topics: {str(e)}")
        print(traceback.format_exc())
        return []

def main():
    driver = None
    try:
        driver = setup_driver()
        
        # Print credentials status for debugging
        print(f"Username provided: {'Yes' if USERNAME else 'No'}")
        print(f"Password provided: {'Yes' if PASSWORD else 'No'}")
        
        if USERNAME and PASSWORD:
            if not login(driver, USERNAME, PASSWORD):
                print("Proceeding without login")
        
        data = scrape_topics(driver, BASE_URL)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\nSuccessfully scraped {len(data)} topics. Saved to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print(traceback.format_exc())
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()

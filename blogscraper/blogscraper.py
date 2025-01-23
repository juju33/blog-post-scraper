import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
import threading
import queue
import os

app = Flask(__name__)
scraping_queue = queue.Queue()
scraping_status = {"status": "idle", "progress": 0, "total": 0, "current_url": ""}

class BlogScraper:
    def __init__(self, sitemap_url):
        self.sitemap_url = sitemap_url
        self.data = []
        self.status_callback = None

    def get_urls_from_sitemap(self):
        # Implementation of get_urls_from_sitemap method
        pass

    def scrape_blog_post(self, url):
        """Scrape individual blog post"""
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Modify these selectors based on the website's HTML structure
            title = soup.find('h1').text.strip() if soup.find('h1') else ''
            content = soup.find('article').text.strip() if soup.find('article') else ''
            
            # Find all images in the post (URLs only)
            images = []
            for img in soup.find_all('img'):
                if img.get('src'):
                    img_url = urljoin(url, img['src'])
                    images.append(img_url)
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'images': ','.join(images),  # Store URLs as comma-separated string
                'scraped_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return None

    def scrape_all_posts(self, status_callback=None):
        """Scrape all blog posts from sitemap with progress updates"""
        self.status_callback = status_callback
        urls = self.get_urls_from_sitemap()
        total_urls = len(urls)
        
        for index, url in enumerate(urls, 1):
            if self.status_callback:
                self.status_callback({
                    "status": "scraping",
                    "progress": index,
                    "total": total_urls,
                    "current_url": url
                })
            
            post_data = self.scrape_blog_post(url)
            if post_data:
                self.data.append(post_data)

        if self.status_callback:
            self.status_callback({
                "status": "completed",
                "progress": total_urls,
                "total": total_urls,
                "current_url": ""
            })

    def save_to_csv(self, filename='blog_posts.csv'):
        """Save scraped data to CSV file"""
        df = pd.DataFrame(self.data)
        df.to_csv(filename, index=False, encoding='utf-8')
        return filename

def update_status(status):
    global scraping_status
    scraping_status.update(status)

def scraping_worker(sitemap_url):
    scraper = BlogScraper(sitemap_url)
    scraper.scrape_all_posts(status_callback=update_status)
    scraper.save_to_csv('static/blog_posts.csv')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_scraping', methods=['POST'])
def start_scraping():
    sitemap_url = request.json.get('sitemap_url')
    if not sitemap_url:
        return jsonify({"error": "No sitemap URL provided"}), 400
    
    global scraping_status
    scraping_status = {"status": "starting", "progress": 0, "total": 0, "current_url": ""}
    
    # Start scraping in a background thread
    thread = threading.Thread(target=scraping_worker, args=(sitemap_url,))
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Scraping started"})

@app.route('/status')
def get_status():
    return jsonify(scraping_status)

@app.route('/download')
def download():
    if os.path.exists('static/blog_posts.csv'):
        return send_file('static/blog_posts.csv', as_attachment=True)
    return jsonify({"error": "No data available"}), 404

if __name__ == "__main__":
    os.makedirs('static', exist_ok=True)
    app.run(debug=True)

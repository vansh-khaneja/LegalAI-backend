import requests
from bs4 import BeautifulSoup
import os
import time
import logging
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Constants
BASE_URL = "https://cortesuprema.gov.co"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
DOWNLOAD_DIR = "supreme_court_pdfs"

# List of sitemaps to explore
SITEMAPS = [
    "https://cortesuprema.gov.co/wp-sitemap-posts-post-1.xml",
    "https://cortesuprema.gov.co/wp-sitemap-posts-page-1.xml",
    "https://cortesuprema.gov.co/wp-sitemap-posts-tribe_events-1.xml",
    "https://cortesuprema.gov.co/wp-sitemap-taxonomies-category-1.xml",
    "https://cortesuprema.gov.co/wp-sitemap-taxonomies-post_tag-1.xml",
    "https://cortesuprema.gov.co/wp-sitemap-taxonomies-tribe_events_cat-1.xml",
    "https://cortesuprema.gov.co/wp-sitemap-users-1.xml"
]

def get_urls_from_sitemap(sitemap_url):
    """Extract all URLs from a sitemap XML file."""
    try:
        logger.info(f"Fetching sitemap: {sitemap_url}")
        response = requests.get(sitemap_url, headers=HEADERS)
        if response.status_code != 200:
            logger.error(f"Failed to fetch sitemap: {sitemap_url}, Status: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'xml')
        urls = []
        
        # Extract all location URLs from the sitemap
        for loc in soup.find_all("loc"):
            urls.append(loc.text)
            
        logger.info(f"Found {len(urls)} URLs in sitemap")
        return urls
    except Exception as e:
        logger.error(f"Error parsing sitemap {sitemap_url}: {e}")
        return []

def get_pdf_from_iframe(page_url):
    """Find PDF iframe on the page and return the PDF URL."""
    try:
        response = requests.get(page_url, headers=HEADERS)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, "html.parser")
        iframe = soup.find("iframe", src=True)
        
        if iframe and iframe["src"].lower().endswith(".pdf"):
            pdf_url = iframe["src"]
            # Make URL absolute if it's relative
            if pdf_url.startswith("/"):
                pdf_url = BASE_URL + pdf_url
            return pdf_url
        
        return None
    except Exception as e:
        logger.error(f"Error parsing page {page_url}: {e}")
        return None

def create_folder_name(url):
    """Create an English-friendly folder name from URL path components."""
    # Parse the URL and get the path
    parsed_url = urlparse(url)
    path = parsed_url.path.strip("/")
    
    # Get content type from URL path
    if not path:
        return "homepage"
    
    # Map common Spanish terms to English
    spanish_to_english = {
        "categoria": "category",
        "categorias": "categories",
        "reiteraciones-relevantes": "relevant_reiterations",
        "eventos": "events",
        "usuario": "user",
        "usuarios": "users",
        "pagina": "page"
    }
    
    # Split path and translate known segments
    path_parts = path.split("/")
    for i, part in enumerate(path_parts):
        if part in spanish_to_english:
            path_parts[i] = spanish_to_english[part]
    
    # Join with underscores for a valid folder name
    folder_name = "_".join(path_parts)
    
    # Remove any unwanted characters
    folder_name = ''.join(c if c.isalnum() or c in ['_', '-'] else '_' for c in folder_name)
    
    return folder_name

def download_pdf(pdf_url, base_folder):
    """Download PDF and save to appropriate folder."""
    try:
        # Create folder name based on URL structure
        pdf_name = pdf_url.split("/")[-1]
        
        # Create the folder if it doesn't exist
        os.makedirs(base_folder, exist_ok=True)
        
        # Full path to save the PDF
        save_path = os.path.join(base_folder, pdf_name)
        
        # Check if already downloaded
        if os.path.exists(save_path):
            logger.info(f"PDF already exists: {save_path}")
            return False
        
        # Download the PDF
        logger.info(f"Downloading: {pdf_name} to {save_path}")
        pdf_response = requests.get(pdf_url, headers=HEADERS)
        
        with open(save_path, "wb") as f:
            f.write(pdf_response.content)
        
        logger.info(f"Successfully saved: {save_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading {pdf_url}: {e}")
        return False

def process_url(url):
    """Process a single URL to check for PDF and download if found."""
    logger.info(f"Processing URL: {url}")
    
    # Check if URL is a PDF directly
    if url.lower().endswith(".pdf"):
        folder_name = os.path.join(DOWNLOAD_DIR, "direct_pdfs")
        download_pdf(url, folder_name)
        return
    
    # Otherwise, check for PDF iframe on the page
    pdf_url = get_pdf_from_iframe(url)
    if pdf_url:
        # Create folder name based on URL structure
        folder_name = create_folder_name(url)
        full_folder_path = os.path.join(DOWNLOAD_DIR, folder_name)
        download_pdf(pdf_url, full_folder_path)
    else:
        logger.info(f"No PDF found at: {url}")

def process_paginated_category(category_url, max_pages=10):
    """Process a paginated category URL to find all posts and their PDFs."""
    base_category_url = category_url.rstrip('/')
    
    for page_num in range(1, max_pages + 1):
        if page_num == 1:
            page_url = base_category_url + "/"
        else:
            page_url = f"{base_category_url}/page/{page_num}/"
        
        logger.info(f"Checking category page: {page_url}")
        
        try:
            response = requests.get(page_url, headers=HEADERS)
            if response.status_code != 200:
                logger.info(f"No more pages at {page_url}")
                break
                
            soup = BeautifulSoup(response.content, "html.parser")
            post_links = []
            
            # Find all post links
            for h2 in soup.find_all("h2", class_="entry-title"):
                a_tag = h2.find("a", href=True)
                if a_tag:
                    post_links.append(a_tag["href"])
            
            # If no posts found, stop paginating
            if not post_links:
                logger.info(f"No posts found on page {page_num}")
                break
                
            logger.info(f"Found {len(post_links)} posts on page {page_num}")
            
            # Process each post link
            for post_link in post_links:
                folder_name = f"category_{create_folder_name(base_category_url)}_page_{page_num}"
                full_folder_path = os.path.join(DOWNLOAD_DIR, folder_name)
                
                pdf_url = get_pdf_from_iframe(post_link)
                if pdf_url:
                    download_pdf(pdf_url, full_folder_path)
                
                # Be polite to the server
                time.sleep(1)
        
        except Exception as e:
            logger.error(f"Error processing category page {page_url}: {e}")
            break
        
        # Be polite between page requests
        time.sleep(2)

def main():
    """Main function to orchestrate the scraping process."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Process known paginated categories first
    process_paginated_category("https://cortesuprema.gov.co/category/reiteraciones-relevantes")
    
    # Process all sitemaps
    all_urls = []
    for sitemap in SITEMAPS:
        urls = get_urls_from_sitemap(sitemap)
        all_urls.extend(urls)
    
    # Process each unique URL
    processed_urls = set()
    for url in all_urls:
        if url in processed_urls:
            continue
            
        process_url(url)
        processed_urls.add(url)
        
        # Be polite to the server
        time.sleep(1)
    
    logger.info(f"Scraping complete. Processed {len(processed_urls)} URLs.")

if __name__ == "__main__":
    main()

import os
import json
import re
import logging
import datetime
import time
from urllib.parse import urlparse
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from dotenv import load_dotenv
import requests
from docling.document_converter import DocumentConverter

# Returns a sanitized filename
def sanitize_filename(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9\-_\.]', '_', name)

# Extracts page title from markdown; returns "index" if none found
def get_page_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith('#'):
            title = line.strip('#').strip()
            if title:
                return sanitize_filename(title)
    return "index"

# Formats time into seconds, minutes, or hours
def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.2f} hours"

# Saves the converted files (Markdown and JSON) into the appropriate directory
def save_files(result, base_dir: str, source_url: str) -> None:
    parsed = urlparse(source_url)
    domain = parsed.netloc
    site_dir = os.path.join(base_dir, domain)
    os.makedirs(site_dir, exist_ok=True)
    
    md_content = result.document.export_to_markdown()
    page_title = get_page_title(md_content)
    
    md_file = os.path.join(site_dir, f"{page_title}.md")
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    json_data = {
        "title": page_title,
        "source_url": source_url,
        "processed_at": datetime.datetime.now().isoformat(),
        "content": None,
        "markdown": md_content
    }
    try:
        json_raw = result.document.export_to_json()
        json_data["content"] = json.loads(json_raw)
    except Exception:
        try:
            doc_dict = result.document.to_dict()
            json_data["content"] = doc_dict
        except Exception:
            json_data["content"] = {"error": "Failed to export the document."}
    
    json_file = os.path.join(site_dir, f"{page_title}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(json_data, indent=2, ensure_ascii=False))
    
    logging.info(f"Files saved in: {site_dir}")

# Processes a single URL and returns its result information
def process_url(url: str, base_dir: str) -> tuple:
    start_time = time.perf_counter()
    logging.info(f"Starting conversion for URL: {url}")
    try:
        converter = DocumentConverter()
        result = converter.convert(url)
        save_files(result, base_dir, url)
        status = "success"
        error_message = None
    except Exception as e:
        logging.error(f"Error processing URL: {url}. Details: {e}")
        status = "error"
        error_message = str(e)
    end_time = time.perf_counter()
    processing_time = round(end_time - start_time, 2)
    formatted_time = format_time(processing_time)
    domain = urlparse(url).netloc
    logging.info(f"Finished processing {url} in {formatted_time}")
    return domain, {
        "url": url,
        "status": status,
        "processing_time": processing_time,
        "processing_time_formatted": formatted_time,
        "error_message": error_message
    }

# Groups domains by primary domain; for this project, domains ending with "asimov.academy" are grouped together
def get_primary_domain(domain: str) -> str:
    if domain.endswith("asimov.academy"):
        return "asimov.academy"
    return domain

# Sends a webhook notification to the specified URL with the given payload
def send_webhook_notification(payload: list, webhook_url: str) -> None:
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("Webhook sent successfully.")
        else:
            logging.error(f"Webhook failed with status code: {response.status_code}")
    except Exception as e:
        logging.error(f"Error sending webhook: {e}")

# Clears the URLs file
def clear_urls_file(file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        f.truncate(0)
    logging.info(f"File '{file_path}' cleared after processing.")

def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, 
                        format="%(asctime)s - %(levelname)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    
    base_dir = os.getenv("dir_save", "scraping_data").strip()
    if base_dir.startswith("/"):
        base_dir = base_dir[1:]
    os.makedirs(base_dir, exist_ok=True)
    
    webhook_url = os.getenv("webhook_notification", "").strip()
    mode = os.getenv("mode", "development").strip().lower()
    urls_file = "urls.txt"
    
    if not os.path.exists(urls_file):
        logging.error(f"File '{urls_file}' not found. Exiting.")
        return

    with open(urls_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    if not urls:
        logging.error("No valid URLs found in 'urls.txt'. Exiting.")
        return
    
    # Sort URLs by primary domain and URL
    urls = sorted(urls, key=lambda u: (get_primary_domain(urlparse(u).netloc), u))
    
    total_urls = len(urls)
    logging.info(f"Starting processing of {total_urls} URL(s).")
    
    processed_data = {}
    for idx, url in enumerate(urls, start=1):
        logging.info(f"Processing URL {idx} of {total_urls}")
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(process_url, url, base_dir)
            try:
                domain, result_data = future.result(timeout=60)
            except TimeoutError:
                logging.error(f"Timeout after 1 minute for URL: {url}")
                domain = urlparse(url).netloc
                result_data = {
                    "url": url,
                    "status": "error",
                    "processing_time": None,
                    "processing_time_formatted": "Timeout after 1 minute",
                    "error_message": "Timeout after 1 minute"
                }
            except Exception as e:
                logging.error(f"Error processing URL: {url}. Details: {e}")
                domain = urlparse(url).netloc
                result_data = {
                    "url": url,
                    "status": "error",
                    "processing_time": None,
                    "processing_time_formatted": "Error occurred",
                    "error_message": str(e)
                }
        primary = get_primary_domain(domain)
        if primary in processed_data:
            processed_data[primary].append(result_data)
        else:
            processed_data[primary] = [result_data]

    logging.info("Processing completed for all URLs.")
    
    # Build sorted webhook payload based on primary domain
    webhook_payload = []
    for primary in sorted(processed_data.keys()):
        sorted_records = sorted(processed_data[primary], key=lambda r: r["url"])
        webhook_payload.append({
            "domain": primary,
            "urls": sorted_records
        })
    
    if webhook_url:
        logging.info("Sending webhook notification...")
        send_webhook_notification(webhook_payload, webhook_url)
    else:
        logging.info("Webhook not configured; notification not sent.")
    
    # Clear urls.txt only in production mode
    if mode == "production":
        clear_urls_file(urls_file)
    else:
        logging.info("Development mode; urls.txt not cleared.")

if __name__ == "__main__":
    main()
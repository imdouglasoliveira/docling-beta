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

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9\-_\.]', '_', name)

def get_page_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith('#'):
            title = line.strip('#').strip()
            if title:
                return sanitize_filename(title)
    return "index"

def save_files(result, base_dir: str, source_url: str) -> None:
    parsed = urlparse(source_url)
    site_name = parsed.netloc
    site_dir = os.path.join(base_dir, site_name)
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
        "content": None
    }
    try:
        json_raw = result.document.export_to_json()
        json_data["content"] = json.loads(json_raw)
    except Exception:
        try:
            doc_dict = result.document.to_dict()
            json_data["content"] = doc_dict
        except Exception:
            json_data["content"] = {"error": "não foi possível exportar o documento."}
    
    json_file = os.path.join(site_dir, f"{page_title}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(json_data, indent=2, ensure_ascii=False))
    
    logging.info(f"Arquivos salvos em: {site_dir}")

def process_url(url: str, base_dir: str) -> tuple:
    start_time = time.perf_counter()
    logging.info(f"Iniciando conversão da URL: {url}")
    try:
        converter = DocumentConverter()
        result = converter.convert(url)
        save_files(result, base_dir, url)
        status = "success"
        error_message = None
    except Exception as e:
        logging.error(f"Erro ao processar a URL: {url}. Detalhes: {e}")
        status = "error"
        error_message = str(e)
    end_time = time.perf_counter()
    processing_time = round(end_time - start_time, 2)
    domain = urlparse(url).netloc
    logging.info(f"Finalizado processamento de {url} em {processing_time} segundos")
    return domain, {
        "url": url,
        "status": status,
        "processing_time": processing_time,
        "error_message": error_message
    }

def send_webhook_notification(payload: list, webhook_url: str) -> None:
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("Webhook enviado com sucesso.")
        else:
            logging.error(f"Falha ao enviar webhook, status code: {response.status_code}")
    except Exception as e:
        logging.error(f"Erro ao enviar webhook: {e}")

def clear_urls_file(file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        f.truncate(0)
    logging.info(f"Arquivo '{file_path}' zerado após processamento.")

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
    urls_file = "urls.txt"
    if not os.path.exists(urls_file):
        logging.error(f"O arquivo '{urls_file}' não foi encontrado. A execução será encerrada.")
        return

    with open(urls_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    if not urls:
        logging.error("Nenhuma URL válida encontrada no arquivo 'urls.txt'. Execução encerrada.")
        return

    total_urls = len(urls)
    logging.info(f"Iniciando processamento de {total_urls} URL(s).")
    
    processed_data = {}
    for idx, url in enumerate(urls, start=1):
        logging.info(f"Processando URL {idx} de {total_urls}")
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(process_url, url, base_dir)
            try:
                domain, result_data = future.result(timeout=60)
            except TimeoutError:
                logging.error(f"Timeout de 1 min para a URL: {url}")
                domain = urlparse(url).netloc
                result_data = {
                    "url": url,
                    "status": "error",
                    "processing_time": None,
                    "error_message": "Timeout de 1 min"
                }
            except Exception as e:
                logging.error(f"Erro ao processar a URL: {url}. Detalhes: {e}")
                domain = urlparse(url).netloc
                result_data = {
                    "url": url,
                    "status": "error",
                    "processing_time": None,
                    "error_message": str(e)
                }
        if domain in processed_data:
            processed_data[domain].append(result_data)
        else:
            processed_data[domain] = [result_data]

    logging.info("Processamento concluído para todas as URLs.")

    # Monta payload para webhook: lista de objetos com domínio e registros
    webhook_payload = []
    for domain, records in processed_data.items():
        webhook_payload.append({
            "domain": domain,
            "urls": records
        })

    if webhook_url:
        logging.info("Enviando notificação para o webhook...")
        send_webhook_notification(webhook_payload, webhook_url)
    else:
        logging.info("Webhook não configurado; notificação não enviada.")

    clear_urls_file(urls_file)

if __name__ == "__main__":
    main()
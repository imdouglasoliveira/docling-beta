# docling-beta

docling-beta is a Python project that converts web pages using the Docling library. It reads a list of URLs from a file (`urls.txt`), processes each URL with a timeout of 1 minute, and saves the output in both Markdown and JSON formats in a structured directory format. The conversion results are organized by domain, and the filenames are based on the page's title.

## Features

- Reads URLs from `urls.txt` (one URL per line, ignoring empty lines).
- Converts each URL using the Docling library.
- Limits the processing time for each URL to 1 minute to avoid timeouts.
- Saves the results in Markdown (`.md`) and JSON (`.json`) formats in the `scraping_data/<domain>/` directory.
- Logs processing steps and errors (logs are output in Portuguese).
- Clears the `urls.txt` file after processing to prevent reprocessing the same URLs.
- Configurable webhook notifications: if the `webhook_notification` variable is set in the `.env` file, a POST request is sent with a JSON payload containing details about the processed URLs (grouped by domain).

## Requirements

- Python 3.13+
- [Poetry](https://python-poetry.org/)
- Dependencies:
  - `docling (>=2.29.0,<3.0.0)`
  - `python-dotenv (>=1.1.0,<2.0.0)`
  - `requests` (ensure it is installed)

## Installation

1. **Clone the repository:**
    ```bash
    git clone https://your-repository-url.git
    cd docling-beta
    ```

2. **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```

3. **Configure the environment:**

    Create a `.env` file in the project root with at least the following variables:
    ```
    dir_save = /scraping_data
    webhook_notification = https://your-webhook-url.com/notification
    ```
    Replace `https://your-webhook-url.com/notification` with your actual webhook URL. If `webhook_notification` is left empty, the notification will not be sent.

4. **Prepare the URLs file:**

    Create a file named `urls.txt` in the project root, containing one URL per line.

## Usage

Run the application using Poetry:
```bash
poetry run python html_converter.py
```
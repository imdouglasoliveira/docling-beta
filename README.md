# docling-beta

docling-beta is a Python project that converts web pages using the Docling library. It reads a list of URLs from a file (`urls.txt`), processes each URL with a timeout of 1 minute, and saves the output in both Markdown and JSON formats in a structured directory format. The conversion results are organized by domain, and the filenames are based on the page's title.

## Features

- Reads URLs from `urls.txt` (one URL per line, ignoring empty lines).
- Sorts the URLs by primary domain and URL for consistent processing. For example, **asimov.academy** and **hub.asimov.academy** are grouped together under **asimov.academy**.
- Converts each URL using the Docling library.
- Limits the processing time for each URL to 1 minute to avoid timeouts.
- Saves the results in Markdown (`.md`) and JSON (`.json`) formats in the `scraping_data/<domain>/` directory.
- Logs processing steps and errors (logs are output in Portuguese).
- Configurable webhook notifications: if the `webhook_notification` variable is set in the `.env` file, a POST request is sent with a JSON payload containing details about each processed URL (grouped by primary domain). Each URL entry includes the processing time (numeric and formatted).
- Conditional clearing of `urls.txt`: if `mode` is set to `production` in the `.env` file, the `urls.txt` file is cleared after processing; if set to `development`, the file remains unchanged.

## Requirements

- Python 3.13+
- [Poetry](https://python-poetry.org/)
- Dependencies:
  - `docling (>=2.29.0,<3.0.0)`
  - `python-dotenv (>=1.1.0,<2.0.0)`
  - `requests`

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

    Create a `.env` file in the project root using the provided example:
    ```env
    dir_save = /scraping_data
    save_in = [markdown, json]
    save_options = name.pages
    save_name = [name, name.json]
    webhook_notification = https://whk.a8z.com.br/webhook/docling
    mode = development  # Change to 'production' in production mode
    ```

4. **Prepare the URLs file:**

    Create a file named `urls.txt` in the project root, containing one URL per line. The URLs can be in any order; they will be sorted by the application.

## Usage

Run the application using Poetry:
```bash
poetry run python html_converter.py
```
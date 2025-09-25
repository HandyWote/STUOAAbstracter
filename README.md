# OAP - OA Portal Scraper

This project scrapes announcements from the OA portal, summarizes them with an AI API, and sends email notifications to subscribers.

## Project Structure

- `spider/OAP.py` - Scrapes the OA portal and generates daily JSON payloads
- `sender/Sender.py` - Sends email notifications to subscribers
- `config/config.py` - Centralized configuration management
- `events/` - Generated JSON files with daily announcements (not committed)
- `key/` - SMTP credentials (not committed)

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Configure environment:
   - Copy `env.example` to `env` and fill in your credentials
   - Add email addresses to `List.txt`

## Usage

### Collect announcements:
```bash
uv run python -m spider.OAP
```

### Send email notifications:
```bash
uv run python -m sender.Sender
```

Note: Use `-m` flag to run modules correctly due to Python path resolution.

## Configuration

- `API_KEY` - AI API key for summarizing announcements
- `SMTP_USER` - Email address for sending notifications
- `SMTP_PASSWORD` - Password or app-specific password for SMTP
- `EVENTS_DIR` - Directory for storing event files (default: `events/`)
- `RECIPIENT_LIST` - Path to recipient list file (default: `List.txt`)

## Dependencies

- Python 3.10+
- requests
- beautifulsoup4
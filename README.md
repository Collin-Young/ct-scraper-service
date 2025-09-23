
# CT Scraper Service

Minimal cloud-friendly packaging of the Connecticut civil case scraper so it can run scheduled jobs and email daily digests to subscribers. This folder is independent of the local research scripts.

## Components
- `ct_scraper/` - reusable scraping, data, API, and email helpers
- `scripts/` - CLI entrypoints invoked by cron/systemd/Celery beat
- `frontend/`

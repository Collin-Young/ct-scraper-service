# Deploying on DigitalOcean (Droplet)

These steps get the scraper API and daily jobs running on a cheap ($4/mo) Ubuntu 24.04 Droplet.

## 1. Provision the Droplet
1. Create a Basic Droplet (1 vCPU / 1GB RAM) using Ubuntu 24.04 LTS.
2. Add your SSH key so you can connect without a password.
3. After it boots, SSH in: `ssh root@your_droplet_ip`.

## 2. Install system dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3.11-dev build-essential git unzip \
    chromium-browser chromium-chromedriver xvfb
```
Chromium + chromedriver allow Selenium to run headless; `xvfb` provides a virtual display in case the site refuses pure headless.

## 3. Create a deploy user and project folder
```bash
sudo useradd -m -s /bin/bash scraper
sudo -u scraper mkdir -p /home/scraper/apps
sudo chown -R scraper:scraper /home/scraper/apps
```
Copy the project over using git (recommended) or `scp`:
```bash
sudo -u scraper git clone https://github.com/Collin-Young/ct-scraper-service.git /home/scraper/apps/ct-scraper-service
```
(Replace with your repo URL. If you are copying manually, upload the folder to `/home/scraper/apps/ct-scraper-service`.)

## 4. Set up Python environment
```bash
cd /home/scraper/apps/ct-scraper-service
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[email]
```
Copy `.env.example` to `.env` and fill in secrets (Stripe, SES, etc.). Example:
```bash
cp .env.example .env
nano .env
```
Ensure the SQLite file can be created:
```bash
mkdir -p data
chmod 750 data
```

## 5. Verify Selenium works
Run a limited scrape from the droplet to ensure Chromium launches:
```bash
source .venv/bin/activate
python scripts/scrape_daily.py run --limit 1
```
If you see Chromium sandbox errors, run chrome with `--no-sandbox` (already in the code) and confirm `chromedriver` is installed (`chromedriver --version`).

## 6. Configure systemd service for the API
Create `/etc/systemd/system/ct-scraper-api.service` (as root) using the template in this repo:
```bash
sudo cp /home/scraper/apps/ct-scraper-service/deploy/ct-scraper-api.service /etc/systemd/system/
sudo chown root:root /etc/systemd/system/ct-scraper-api.service
```
Update paths inside the file if your install path differs, then enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ct-scraper-api.service
sudo systemctl status ct-scraper-api.service
```
The API will be available on `http://droplet_ip:8000`. Put an Nginx reverse proxy + HTTPS in front if you need TLS (DigitalOcean Marketplace �Nginx� image can help).

## 7. Schedule daily scrape & digest
Two timers are provided:
- `ct-scraper-scrape.timer` runs the scraper daily at 19:30 UTC (3:30 pm ET).
- `ct-scraper-digest.timer` runs the email digest daily at 20:00 UTC (4:00 pm ET).

Install them:
```bash
sudo cp /home/scraper/apps/ct-scraper-service/deploy/ct-scraper-scrape.service /etc/systemd/system/
sudo cp /home/scraper/apps/ct-scraper-service/deploy/ct-scraper-scrape.timer /etc/systemd/system/
sudo cp /home/scraper/apps/ct-scraper-service/deploy/ct-scraper-digest.service /etc/systemd/system/
sudo cp /home/scraper/apps/ct-scraper-service/deploy/ct-scraper-digest.timer /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now ct-scraper-scrape.timer
sudo systemctl enable --now ct-scraper-digest.timer
```
Check upcoming runs:
```bash
systemctl list-timers | grep ct-scraper
```
Manual run for debugging:
```bash
sudo systemctl start ct-scraper-scrape.service
sudo journalctl -u ct-scraper-scrape.service -f
```

## 8. Optional: Nginx reverse proxy + TLS
Install Nginx and Certbot to expose the API over HTTPS:
```bash
sudo apt install -y nginx
sudo ufw allow 'Nginx Full'
```
Create `/etc/nginx/sites-available/ct-scraper` pointing to `http://127.0.0.1:8000`, enable it, and use `certbot --nginx` to fetch a Let�s Encrypt cert. This step is optional for private deployments.

## 9. Backups & monitoring
- SQLite DB lives in `/home/scraper/apps/ct-scraper-service/data/`. Use `doctl` or cron to `tar`/upload to Spaces nightly.
- Enable DigitalOcean Monitoring agent (`do-agent`) for CPU/RAM metrics.

## 10. Updating the app
Pull updates and restart services:
```bash
cd /home/scraper/apps/ct-scraper-service
source .venv/bin/activate
git pull
pip install -e .
sudo systemctl restart ct-scraper-api.service
```
Timers pick up changes automatically (they run scripts straight from the repo).


## 11. (Optional) Serve the static frontend
The simple UI in `frontend/` is pure HTML/JS. To serve it from the droplet, copy the folder to `/var/www/ct-scraper-frontend` and point Nginx at it:

```bash
sudo mkdir -p /var/www/ct-scraper-frontend
sudo cp -r /home/scraper/apps/ct-scraper-service/frontend/* /var/www/ct-scraper-frontend/
```

In your Nginx site config, add:
```nginx
location / {
    root /var/www/ct-scraper-frontend;
    index index.html;
}
```
Adjust the API base input on the page to point at the FastAPI host (e.g. `http://157.230.11.23:8000`).
\n## 12. (Optional) Populate latitude/longitude\nRun once after the first full scrape so the map has coordinates:\n`ash\nsu - scraper -c 'cd ~/apps/ct-scraper-service && source .venv/bin/activate && python scripts/backfill_geocode.py'\n`\nThe script respects Nominatim's rate limits (~1 request/sec) and caches results in ct_scraper/geocode_cache.json.\n

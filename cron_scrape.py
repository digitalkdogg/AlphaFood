#!/usr/bin/env python3
"""
AlphaFood scheduled scraper — run this from cron on your NAS.

Crontab example (scrape every 24 hours at 2am):
  0 2 * * * /usr/bin/python3 /opt/alphafood/cron_scrape.py >> /var/log/alphafood_scrape.log 2>&1

Requirements: pip3 install requests
"""

import os
import sys
import json
import logging
from datetime import datetime

import requests

# ── Config (edit these or set as environment variables) ──────────────────────

API_BASE   = os.getenv("ALPHAFOOD_API_URL", "http://localhost:8000")
ADMIN_EMAIL    = os.getenv("ALPHAFOOD_ADMIN_EMAIL", "admin@alphafood.local")
ADMIN_PASSWORD = os.getenv("ALPHAFOOD_ADMIN_PASSWORD", "admin123")

# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("alphafood-cron")


def get_token() -> str:
    r = requests.post(
        f"{API_BASE}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def trigger_scrape_all(token: str) -> dict:
    r = requests.post(
        f"{API_BASE}/api/admin/scrape/all",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def get_run_status(token: str, run_id: str) -> dict:
    r = requests.get(
        f"{API_BASE}/api/admin/scrape/runs/{run_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def main():
    log.info("AlphaFood scrape job starting")

    try:
        token = get_token()
        log.info("Authenticated successfully")
    except Exception as e:
        log.error(f"Authentication failed: {e}")
        sys.exit(1)

    try:
        result = trigger_scrape_all(token)
        run_id = result.get("run_id")
        log.info(f"Scrape triggered — run_id: {run_id}")
    except Exception as e:
        log.error(f"Failed to trigger scrape: {e}")
        sys.exit(1)

    # Poll until the global run is complete (max 2 hours)
    import time
    deadline = time.time() + 7200
    while time.time() < deadline:
        time.sleep(30)
        try:
            status = get_run_status(token, run_id)
            if status["status"] in ("success", "partial", "error"):
                log.info(
                    f"Run complete — status={status['status']} "
                    f"found={status['recipes_found']} "
                    f"added={status['recipes_added']} "
                    f"updated={status['recipes_updated']} "
                    f"skipped={status['recipes_skipped_non_recipe']}"
                )
                if status.get("error_message"):
                    log.warning(f"Error message: {status['error_message']}")
                sys.exit(0 if status["status"] != "error" else 1)
        except Exception as e:
            log.warning(f"Status poll failed: {e}")

    log.error("Scrape job timed out after 2 hours")
    sys.exit(1)


if __name__ == "__main__":
    main()

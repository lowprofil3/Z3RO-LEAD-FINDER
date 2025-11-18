"""Simple lead collector for publicly available business info.

This script scrapes public search results from Yellow Pages to gather
basic business contact details for a provided query and posts the
results to a Discord webhook.

Usage:
    python leadbot.py "barbers in Austin"
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

WEBHOOK_URL = (
    "https://discord.com/api/webhooks/1440082760491597985/"
    "lbuWATZLifqjRqqXqwFMEjI0C8_nb-5RKiJIP-GINAPpKweu7SLn4TpV44Vrvy0xqFy2"
)
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}


@dataclass
class Business:
    name: str
    phone: Optional[str]
    website: Optional[str]
    address: Optional[str]

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "name": self.name,
            "phone": self.phone,
            "website": self.website,
            "address": self.address,
        }


def split_query(query: str) -> Tuple[str, str]:
    """Split a free-form query into search term and location parts."""
    if " in " in query:
        term, location = query.split(" in ", 1)
        return term.strip(), location.strip()
    return query.strip(), ""


def fetch_business_listings(query: str) -> str:
    """Fetch Yellow Pages search results HTML for the provided query."""
    search_terms, location = split_query(query)
    params = {
        "search_terms": search_terms,
        "geo_location_terms": location,
    }

    try:
        response = requests.get(
            "https://www.yellowpages.com/search",
            params=params,
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch listings: {exc}") from exc


def clean_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    stripped = text.strip()
    return stripped or None


def parse_listings(html: str) -> List[Dict[str, Optional[str]]]:
    """Parse business listings from Yellow Pages HTML."""
    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, Optional[str]]] = []

    for listing in soup.select("div.search-results div.result"):
        name_tag = listing.select_one("a.business-name")
        phone_tag = listing.select_one("div.phones")
        website_tag = listing.select_one("a.track-visit-website")
        street_tag = listing.select_one("div.street-address")
        locality_tag = listing.select_one("div.locality")

        name = clean_text(name_tag.get_text()) if name_tag else None
        if not name:
            continue

        phone = clean_text(phone_tag.get_text()) if phone_tag else None
        website = website_tag.get("href") if website_tag else None
        address_parts = [
            clean_text(street_tag.get_text()) if street_tag else None,
            clean_text(locality_tag.get_text()) if locality_tag else None,
        ]
        address = ", ".join(part for part in address_parts if part)
        address = address or None

        results.append(Business(name, phone, website, address).as_dict())
        if len(results) >= 10:
            break

    return results


def send_to_webhook(data: Dict[str, object]) -> None:
    """Send the collected data to the configured Discord webhook."""
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to post to webhook: {exc}") from exc


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python leadbot.py \"barbers in Austin\"")

    query = sys.argv[1]
    html = fetch_business_listings(query)
    listings = parse_listings(html)

    payload = {"query": query, "results": listings}
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if listings:
        send_to_webhook(payload)
    else:
        print("No results found; skipping webhook notification.")


if __name__ == "__main__":
    main()

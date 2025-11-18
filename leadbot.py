"""Simple lead collector for publicly available business info.

This script queries OpenStreetMap's Nominatim API for public business
location data based on a free-form search query and posts the results to
a Discord webhook.

Usage:
    python leadbot.py "barbers in Austin"
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests

WEBHOOK_URL = (
    "https://discord.com/api/webhooks/1440082760491597985/"
    "lbuWATZLifqjRqqXqwFMEjI0C8_nb-5RKiJIP-GINAPpKweu7SLn4TpV44Vrvy0xqFy2"
)
HEADERS = {
    "User-Agent": "LeadFinderBot/1.0 (legal, non-abusive contact: your_email@example.com)",
}


@dataclass
class Business:
    name: str
    address: Optional[str]
    latitude: Optional[str]
    longitude: Optional[str]
    phone: Optional[str] = None
    website: Optional[str] = None

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "name": self.name,
            "address": self.address,
            "lat": self.latitude,
            "lon": self.longitude,
            "phone": self.phone,
            "website": self.website,
        }


def split_query(query: str) -> Tuple[str, str]:
    """Split a free-form query into search term and location parts."""
    if " in " in query:
        term, location = query.split(" in ", 1)
        return term.strip(), location.strip()
    return query.strip(), ""


def fetch_business_listings(query: str) -> List[Dict[str, object]]:
    """Fetch OpenStreetMap Nominatim search results for the provided query."""
    search_terms, location = split_query(query)
    q = " ".join(part for part in (search_terms, location) if part).strip()
    params = {
        "q": q,
        "format": "json",
        "addressdetails": 1,
        "limit": 15,
    }

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch listings: {exc}") from exc


def clean_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    stripped = text.strip()
    return stripped or None


def parse_listings(data: List[Dict[str, object]]) -> List[Dict[str, Optional[str]]]:
    """Parse business listings from Nominatim API data."""
    results: List[Dict[str, Optional[str]]] = []

    for item in data:
        name = clean_text(item.get("display_name") if isinstance(item, dict) else None)
        if not name:
            continue

        address_info = item.get("address", {}) if isinstance(item, dict) else {}
        address_parts = [
            clean_text(address_info.get("road")),
            clean_text(address_info.get("city") or address_info.get("town")),
            clean_text(address_info.get("state")),
            clean_text(address_info.get("postcode")),
        ]
        address = ", ".join(part for part in address_parts if part) or None

        latitude = clean_text(item.get("lat") if isinstance(item, dict) else None)
        longitude = clean_text(item.get("lon") if isinstance(item, dict) else None)

        results.append(Business(name, address, latitude, longitude).as_dict())

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
    search_results = fetch_business_listings(query)
    listings = parse_listings(search_results)

    payload = {"query": query, "results": listings}
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if listings:
        send_to_webhook(payload)
    else:
        print("No results found; skipping webhook notification.")


if __name__ == "__main__":
    main()

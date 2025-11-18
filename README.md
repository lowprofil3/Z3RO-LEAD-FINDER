# Z3RO-LEAD-FINDER

Simple CLI tool that searches OpenStreetMap's Nominatim API for public business listings and forwards the results to a Discord webhook.

## Usage
```
python leadbot.py "coffee shops in Belton"
```

The script prints the JSON payload it will post to the configured webhook. If no results are found, the webhook is skipped.

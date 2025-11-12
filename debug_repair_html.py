#!/usr/bin/env python
"""Quick script to fetch and save repair page HTML for inspection."""

import requests
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

headers = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.partselect.com',
}

urls = {
    'refrigerator': 'https://www.partselect.com/Repair/Refrigerator/',
    'dishwasher': 'https://www.partselect.com/Repair/Dishwasher/',
}

for name, url in urls.items():
    print(f"Fetching {name}...")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        output_file = Path(f'/Users/kenzaslaoui/Desktop/PartSelect/repair_{name}.html')
        output_file.write_text(response.text)
        print(f"  Saved to {output_file}")
        print(f"  File size: {len(response.text)} bytes")
    except Exception as e:
        print(f"  Error: {e}")

print("\nDone! Now inspect the HTML files in your IDE.")

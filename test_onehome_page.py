"""
Test fetching OneHome page directly
"""

import sys
import os
import io
import re

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from monitors.email_monitor import EmailMonitor
import requests
from bs4 import BeautifulSoup

def test_onehome_page():
    """Test fetching a OneHome page"""
    print("=" * 60)
    print("TEST: Fetch OneHome Page")
    print("=" * 60)

    # Create monitor to get link from email
    monitor = EmailMonitor('email_config.json')

    if not monitor.connect_to_email():
        print("Failed to connect")
        return

    # Get one email
    typ, data = monitor.imap.search(None, f'(FROM {monitor.config["email"]["sender"]})')
    email_ids = data[0].split()

    if not email_ids:
        print("No emails found")
        return

    # Get the last email
    msg_id = email_ids[-1]

    # Get the email
    import email as email_lib
    from email.header import decode_header

    typ, data = monitor.imap.fetch(msg_id, '(RFC822)')
    raw_email = data[0][1]
    msg = email_lib.message_from_bytes(raw_email)

    # Get HTML body
    html_body = None
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break

    # Extract link
    pattern = r'https://portal\.onehome\.com/[^\s<>"\']+properties[^\s<>"\']+'
    match = re.search(pattern, html_body)

    if not match:
        print("No link found")
        return

    url = match.group(0)
    print(f"\nLink: {url}")

    # Fetch the page
    print("\nFetching page...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {response.status_code}")

    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text()

    # Save to file for inspection
    with open('onehome_page.txt', 'w', encoding='utf-8') as f:
        f.write(text)

    print(f"\nPage text saved to: onehome_page.txt ({len(text)} chars)")

    # Look for key patterns
    print("\nLooking for patterns...")

    # Price
    price_matches = re.findall(r'\$([0-9,]+)', text)
    if price_matches:
        print(f"  Prices found: {price_matches[:5]}")

    # Acres
    acres_matches = re.findall(r'(\d+\.?\d*)\s*acres?', text, re.IGNORECASE)
    if acres_matches:
        print(f"  Acres found: {acres_matches[:5]}")

    # Address
    address_matches = re.findall(r'\d+\s+[\w\s]+(?:St|Street|Ave|Road|Dr|Lane)', text)
    if address_matches:
        print(f"  Addresses found: {address_matches[:3]}")

    monitor.imap.logout()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_onehome_page()

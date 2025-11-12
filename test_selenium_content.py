"""
Test Selenium page content
"""

import sys
import os
import io
import re
import time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from monitors.email_monitor import EmailMonitor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_selenium_content():
    """Test Selenium content"""
    print("=" * 60)
    print("TEST: Selenium Page Content")
    print("=" * 60)

    # Create monitor to get link
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
    print(f"\nLink: {url[:80]}...")

    # Set up Chrome
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=chrome_options)

    try:
        print("\nLoading page with Selenium...")
        driver.get(url)

        # Wait for body
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Wait for content
        time.sleep(5)

        # Get page source
        page_source = driver.page_source

        # Save to file
        with open('selenium_page.html', 'w', encoding='utf-8') as f:
            f.write(page_source)

        print(f"Page saved to: selenium_page.html ({len(page_source)} chars)")

        # Extract text
        text = driver.find_element(By.TAG_NAME, "body").text

        # Save text too
        with open('selenium_text.txt', 'w', encoding='utf-8') as f:
            f.write(text)

        print(f"Text saved to: selenium_text.txt ({len(text)} chars)")

        # Look for patterns in text
        print("\n" + "=" * 60)
        print("PATTERNS FOUND:")
        print("=" * 60)

        # Prices
        prices = re.findall(r'\$([0-9,]+)', text)
        print(f"\nPrices: {prices[:10]}")

        # Acres/Lot size
        acres = re.findall(r'(\d+\.?\d*)\s*(?:acres?|ac\b)', text, re.IGNORECASE)
        print(f"Acres: {acres}")

        # Lot Size
        lot_size = re.findall(r'Lot Size[:\s]+([^\n]+)', text, re.IGNORECASE)
        print(f"Lot Size: {lot_size}")

        # Address-like patterns
        addresses = re.findall(r'\d+\s+[\w\s]{3,30}(?:St|Street|Ave|Road|Dr|Lane|Way|Blvd)', text)
        print(f"Addresses: {addresses[:5]}")

        # MLS
        mls = re.findall(r'MLS[#\s:]+([A-Z0-9\-]+)', text, re.IGNORECASE)
        print(f"MLS: {mls}")

        print("\nFirst 1000 chars of text:")
        print(text[:1000])

    finally:
        driver.quit()
        monitor.imap.logout()

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_selenium_content()

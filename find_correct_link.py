"""
Find the correct link in email
"""

import sys
import os
import io
import re

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from monitors.email_monitor import EmailMonitor
import email as email_lib

def find_correct_link():
    """Find the correct property link"""
    print("=" * 60)
    print("Find Correct Link in Email")
    print("=" * 60)

    # Create monitor
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
    print(f"\nProcessing email ID: {msg_id.decode()}")

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

    if not html_body:
        print("No HTML body")
        return

    # Save HTML to file
    with open('email_html.html', 'w', encoding='utf-8') as f:
        f.write(html_body)

    print(f"Saved HTML to: email_html.html ({len(html_body)} chars)")

    # Find ALL links to portal.onehome.com
    all_links = re.findall(r'https://portal\.onehome\.com/[^\s<>"\']+', html_body)

    print(f"\n{len(all_links)} links found:")
    for i, link in enumerate(all_links, 1):
        print(f"\n[{i}] {link[:100]}...")

        # Check if it contains "properties" (plural = list)
        if 'properties?' in link:
            print("    -> This is PROPERTIES LIST (plural)")
        elif 'property/' in link or 'listing/' in link:
            print("    -> This might be SINGLE PROPERTY")

        # Check for MLS-like ID in URL
        mls_in_url = re.search(r'/(\d{6,8})', link)
        if mls_in_url:
            print(f"    -> Contains ID: {mls_in_url.group(1)}")

    monitor.imap.logout()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    find_correct_link()

"""
Test parsing one email from CML
"""

import sys
import os
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from monitors.email_monitor import EmailMonitor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_one_email():
    """Test parsing one email"""
    print("=" * 60)
    print("TEST: Parse One Email from CML")
    print("=" * 60)

    # Create monitor
    monitor = EmailMonitor('email_config.json')

    # Connect to email
    if not monitor.connect_to_email():
        print("Failed to connect")
        return

    # Search for one email from CML
    typ, data = monitor.imap.search(None, f'(FROM {monitor.config["email"]["sender"]})')
    email_ids = data[0].split()

    if not email_ids:
        print("No emails found")
        return

    # Get the last email (most recent)
    msg_id = email_ids[-1]
    print(f"\nProcessing email ID: {msg_id.decode()}")

    # Process the email - returns list of listings
    listings = monitor.process_email(msg_id)

    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)

    if listings:
        print(f"\nParsed {len(listings)} listing(s) successfully!")

        for i, listing in enumerate(listings, 1):
            print(f"\n[Listing {i}]")
            print(f"  Address: {listing.get('address', 'N/A')}")
            print(f"  City: {listing.get('city', 'N/A')}")
            print(f"  Price: ${listing.get('price', 0):,.0f}")
            print(f"  Acres: {listing.get('acres', 0):.2f}")
            print(f"  MLS: {listing.get('mls', 'N/A')}")
            if listing.get('lat') and listing.get('lng'):
                print(f"  Coordinates: {listing['lat']:.4f}, {listing['lng']:.4f}")
            print(f"  Source: {listing.get('source_url', 'N/A')[:80]}...")

            # Check if it passes filters
            should_alert, reason = monitor.should_alert(listing)
            print(f"  Passes filters: {should_alert}")
            print(f"  Reason: {reason}")
    else:
        print("\nNo listings found in email")

    monitor.imap.logout()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_one_email()

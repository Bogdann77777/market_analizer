"""
Test email connection and show recent emails
"""

import imaplib
import email
from email.header import decode_header
import json
from datetime import datetime

def test_connection():
    """Test IMAP connection to Gmail"""

    # Load config
    with open('email_config.json', 'r') as f:
        config = json.load(f)

    print("=" * 60)
    print("TESTING EMAIL CONNECTION")
    print("=" * 60)
    print(f"Server: {config['email']['server']}")
    print(f"Username: {config['email']['username']}")
    print("=" * 60)

    try:
        # Connect to server
        print("\n1. Connecting to IMAP server...")
        imap = imaplib.IMAP4_SSL(
            config['email']['server'],
            config['email']['port']
        )
        print("   [OK] Connected to server")

        # Login
        print("\n2. Logging in...")
        imap.login(
            config['email']['username'],
            config['email']['password']
        )
        print("   [OK] Login successful!")

        # Select folder
        print(f"\n3. Selecting folder: {config['email']['folder']}...")
        imap.select(config['email']['folder'])
        print("   [OK] Folder selected")

        # Search for emails from CML
        print("\n4. Searching for emails from CML@canopylistings.com...")
        search_criteria = '(FROM "CML@canopylistings.com")'
        typ, data = imap.search(None, search_criteria)

        email_ids = data[0].split()
        print(f"   [OK] Found {len(email_ids)} emails from CML@canopylistings.com")

        # Show recent emails with land keywords
        print("\n5. Searching for land-related emails...")
        land_search = '(OR SUBJECT "land" SUBJECT "lot" SUBJECT "acre" BODY "land" BODY "acre")'
        typ, data = imap.search(None, land_search)

        land_ids = data[0].split()
        print(f"   [OK] Found {len(land_ids)} land-related emails")

        # Show last 5 land emails
        if land_ids:
            print("\n6. Recent land emails (last 5):")
            print("-" * 60)

            for msg_id in land_ids[-5:]:
                # Fetch email
                typ, data = imap.fetch(msg_id, '(RFC822)')
                raw_email = data[0][1]

                # Parse email
                msg = email.message_from_bytes(raw_email)

                # Get subject
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()

                # Get from
                from_addr = msg["From"]

                # Get date
                date = msg["Date"]

                print(f"\n   Subject: {subject}")
                print(f"   From: {from_addr}")
                print(f"   Date: {date}")

        # Show unread count
        print("\n7. Checking unread emails...")
        typ, data = imap.search(None, 'UNSEEN')
        unread_ids = data[0].split()
        print(f"   [OK] {len(unread_ids)} unread emails")

        # Logout
        imap.logout()

        print("\n" + "=" * 60)
        print("[SUCCESS] EMAIL CONNECTION TEST SUCCESSFUL!")
        print("=" * 60)
        print("\nYour email is properly configured for monitoring.")
        print("The system can now:")
        print("  - Connect to your Gmail")
        print("  - Search for land emails")
        print("  - Parse email content")
        print("  - Monitor for new opportunities")

        return True

    except imaplib.IMAP4.error as e:
        print(f"\n[ERROR] IMAP Error: {e}")
        print("\nPossible solutions:")
        print("1. Check if you're using an App Password (not regular password)")
        print("2. Make sure 2-factor authentication is enabled")
        print("3. Generate new App Password at:")
        print("   https://myaccount.google.com/apppasswords")
        return False

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        print("\nPlease check your configuration in email_config.json")
        return False


if __name__ == "__main__":
    test_connection()
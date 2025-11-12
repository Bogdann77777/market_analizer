"""
Test Email Monitor - check monitoring system
"""

import sys
import os
import io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from monitors.email_monitor import EmailMonitor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_monitor():
    """Test the email monitor"""
    print("=" * 60)
    print("EMAIL MONITOR TEST")
    print("=" * 60)

    # Create monitor
    monitor = EmailMonitor('email_config.json')

    print("\nConfiguration:")
    print(f"  Email: {monitor.config['email']['username']}")
    print(f"  Sender: {monitor.config['email']['sender']}")
    print(f"  Max Price: ${monitor.config['filters']['max_price']:,}")
    print(f"  Min Lot Size: {monitor.config['filters']['min_lot_size_acres']} acres")
    print(f"  Telegram: {'Enabled' if monitor.config['telegram']['enabled'] else 'Disabled'}")

    print("\n" + "=" * 60)
    print("Checking for new emails...")
    print("=" * 60)

    # Check for new emails (one time)
    alerts = monitor.check_new_emails()

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nAlerts found: {len(alerts)}")

    for i, alert in enumerate(alerts, 1):
        print(f"\n[{i}] {alert.get('address', 'Unknown')}")
        print(f"    Price: ${alert.get('price', 0):,.0f}")
        print(f"    Size: {alert.get('acres', 0):.2f} acres")
        print(f"    Reason: {alert.get('alert_reason', 'N/A')}")
        if alert.get('lat') and alert.get('lng'):
            print(f"    Coordinates: {alert['lat']:.4f}, {alert['lng']:.4f}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_monitor()

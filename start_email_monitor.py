"""
Land Email Monitor - Main Entry Point

This script monitors your email for land opportunities and sends
Telegram alerts for promising properties based on zone analysis.
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from monitors.email_monitor import EmailMonitor
from notifications.telegram_bot import TelegramNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def validate_config():
    """Validate configuration file"""
    config_path = 'email_config.json'

    if not os.path.exists(config_path):
        logger.error(f"Configuration file {config_path} not found!")
        return False

    with open(config_path, 'r') as f:
        config = json.load(f)

    # Check required email settings
    if config['email']['username'] == "YOUR_EMAIL@gmail.com":
        logger.error("Please configure your email settings in email_config.json")
        print("\n" + "=" * 60)
        print("EMAIL CONFIGURATION REQUIRED")
        print("=" * 60)
        print("\n1. Edit email_config.json")
        print("2. Set your Gmail address in 'username'")
        print("3. Generate an App Password:")
        print("   - Go to https://myaccount.google.com/apppasswords")
        print("   - Create a new app password for 'Mail'")
        print("   - Use this password in the config file")
        print("\n" + "=" * 60)
        return False

    # Check Telegram settings if enabled
    if config['telegram']['enabled']:
        if config['telegram']['bot_token'] == "YOUR_BOT_TOKEN":
            logger.warning("Telegram not configured - alerts will be logged only")
            print("\n" + "=" * 60)
            print("TELEGRAM CONFIGURATION (OPTIONAL)")
            print("=" * 60)
            print("\nTo enable Telegram alerts:")
            print("1. Message @BotFather on Telegram")
            print("2. Create a new bot with /newbot")
            print("3. Copy the bot token to email_config.json")
            print("4. Message your bot to start a chat")
            print("5. Get your chat ID:")
            print("   - Message @userinfobot")
            print("   - Or check https://api.telegram.org/bot<TOKEN>/getUpdates")
            print("6. Add chat_id to email_config.json")
            print("\n" + "=" * 60)

    return True


def test_zone_analyzer():
    """Test the zone analyzer with sample data"""
    logger.info("Testing zone analyzer...")

    from analyzers.zone_analyzer import analyze_nearby_zones

    # Test with Asheville center
    analysis = analyze_nearby_zones(35.5951, -82.5515, radius_miles=1.0)

    if analysis['properties_analyzed'] > 0:
        logger.info(f"Zone analyzer working: {analysis['properties_analyzed']} properties analyzed")
        return True
    else:
        logger.warning("No properties found for zone analysis")
        return False


def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("ASHEVILLE LAND EMAIL MONITOR")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    # Validate configuration
    if not validate_config():
        sys.exit(1)

    # Test zone analyzer
    test_zone_analyzer()

    # Create and run monitor
    try:
        monitor = EmailMonitor('email_config.json')

        print("\nMonitor Configuration:")
        print(f"  Email: {monitor.config['email']['username']}")
        print(f"  Max Price: ${monitor.config['filters']['max_price']:,}")
        print(f"  Min Lot Size: {monitor.config['filters']['min_lot_size_acres']} acres")
        print(f"  Check Interval: {monitor.config['monitoring']['check_interval_minutes']} minutes")
        print(f"  Telegram: {'Enabled' if monitor.config['telegram']['enabled'] else 'Disabled'}")
        print("\n" + "=" * 60)
        print("Monitor is running. Press Ctrl+C to stop.")
        print("=" * 60 + "\n")

        # Run the monitor
        monitor.run_monitor()

    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("Monitor stopped by user")
        print("=" * 60)
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    main()
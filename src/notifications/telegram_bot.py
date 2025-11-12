"""
Telegram Bot for sending land opportunity alerts
"""

import requests
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications via Telegram Bot API"""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """
        Send text message to Telegram

        Args:
            text: Message text (supports Markdown)
            parse_mode: Parse mode (Markdown or HTML)

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }

            response = requests.post(url, json=payload)

            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def send_location(self, lat: float, lng: float) -> bool:
        """
        Send location pin to Telegram

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.api_url}/sendLocation"
            payload = {
                "chat_id": self.chat_id,
                "latitude": lat,
                "longitude": lng
            }

            response = requests.post(url, json=payload)

            if response.status_code == 200:
                logger.info("Location sent successfully")
                return True
            else:
                logger.error(f"Failed to send location: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending location: {e}")
            return False

    def send_land_alert(self, listing: Dict, zone_analysis: Dict = None) -> bool:
        """
        Send formatted land opportunity alert

        Args:
            listing: Land listing details
            zone_analysis: Optional zone analysis results

        Returns:
            True if successful, False otherwise
        """
        # Format message
        lines = [
            "🚨 *NEW LAND OPPORTUNITY* 🚨",
            "",
            f"📍 *Location:* {listing.get('address', 'Unknown')}, {listing.get('city', 'Unknown')}",
            f"💰 *Price:* ${listing.get('price', 0):,.0f}",
            f"📏 *Size:* {listing.get('acres', 0):.2f} acres ({listing.get('sqft', 0):,.0f} sqft)",
        ]

        # Add price per acre if available
        if listing.get('price_per_acre'):
            lines.append(f"💵 *Price/Acre:* ${listing['price_per_acre']:,.0f}")

        # Add MLS number if available
        if listing.get('mls'):
            lines.append(f"🏠 *MLS:* {listing['mls']}")

        # Add URL if available
        if listing.get('source_url'):
            lines.append(f"🔗 *Link:* {listing['source_url']}")

        # Add zone analysis if available
        if zone_analysis and 'score' in zone_analysis:
            lines.extend([
                "",
                f"📊 *Zone Analysis:*",
                f"Score: {zone_analysis['score']}/100",
                f"Green Zones: {zone_analysis['statistics'].get('green_zones_percent', 0):.0f}%",
                f"Properties Analyzed: {zone_analysis['properties_analyzed']}",
                "",
                f"📈 *Recommendation:* {zone_analysis['recommendation']}"
            ])

        # Add alert reason if available
        if listing.get('alert_reason'):
            lines.extend([
                "",
                f"✅ *Alert Triggered:* {listing['alert_reason']}"
            ])

        # Add MLS if available
        if listing.get('mls'):
            lines.append(f"🏠 *MLS:* {listing['mls']}")

        # Add source info
        if listing.get('email_subject'):
            lines.extend([
                "",
                f"📧 *Source:* {listing['email_subject']}"
            ])

        message = "\n".join(lines)

        # Send text message
        success = self.send_message(message)

        # Send location if coordinates available
        if success and listing.get('lat') and listing.get('lng'):
            self.send_location(listing['lat'], listing['lng'])

        return success


def send_telegram_alert(message: str, config: Dict) -> bool:
    """
    Simple function to send alert via Telegram

    Args:
        message: Alert message
        config: Telegram configuration with bot_token and chat_id

    Returns:
        True if successful, False otherwise
    """
    if not config.get('bot_token') or not config.get('chat_id'):
        logger.warning("Telegram not configured")
        return False

    notifier = TelegramNotifier(config['bot_token'], config['chat_id'])
    return notifier.send_message(message)


if __name__ == "__main__":
    # Test the Telegram bot
    import os

    # Load test configuration
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

    if not bot_token or not chat_id:
        print("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        print("\nTo get these:")
        print("1. Create a bot with @BotFather on Telegram")
        print("2. Get your chat ID by messaging @userinfobot")
        exit(1)

    # Create notifier
    notifier = TelegramNotifier(bot_token, chat_id)

    # Test message
    test_listing = {
        'address': '123 Test Lane',
        'city': 'Asheville',
        'price': 75000,
        'acres': 1.5,
        'sqft': 65340,
        'price_per_acre': 50000,
        'alert_reason': 'Great location with 80% green zones nearby',
        'mls': 'TEST123'
    }

    test_zone_analysis = {
        'score': 85,
        'properties_analyzed': 42,
        'statistics': {
            'green_zones_percent': 80
        },
        'recommendation': '🟢 EXCELLENT OPPORTUNITY! Strong appreciation potential.'
    }

    print("Sending test alert to Telegram...")
    success = notifier.send_land_alert(test_listing, test_zone_analysis)

    if success:
        print("✅ Test alert sent successfully!")
    else:
        print("❌ Failed to send test alert")
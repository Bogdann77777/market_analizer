"""
Email Monitor for Land Listings
Monitors email inbox for new land listings and analyzes their potential
"""

import imaplib
import email
from email.header import decode_header
import re
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import get_session, Property
from analyzers.zone_analyzer import analyze_nearby_zones
from notifications.telegram_bot import send_telegram_alert

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmailMonitor:
    """Monitor email for land listings and analyze opportunities"""

    def __init__(self, config_path: str = 'email_config.json'):
        """Initialize email monitor with configuration"""
        self.config = self.load_config(config_path)
        self.imap = None
        self.processed_emails = set()  # Track processed email IDs
        self.load_processed_emails()

    def load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found. Using defaults.")
            return self.get_default_config()

    def get_default_config(self) -> dict:
        """Get default configuration"""
        return {
            "email": {
                "server": "imap.gmail.com",
                "port": 993,
                "username": "",  # Set in config file
                "password": "",  # Set in config file or use app password
                "folder": "INBOX",
                "search_criteria": 'SUBJECT "land" OR SUBJECT "lot" OR SUBJECT "acre"'
            },
            "filters": {
                "max_price": 150000,
                "min_lot_size_acres": 0.25,
                "max_price_per_acre": 50000,
                "search_radius_miles": 1.0,
                "min_green_zone_ratio": 0.5  # 50% of nearby properties should be green/light-green
            },
            "telegram": {
                "bot_token": "",  # Set in config file
                "chat_id": ""     # Set in config file
            },
            "monitoring": {
                "check_interval_minutes": 30,
                "enabled": True
            }
        }

    def connect_to_email(self) -> bool:
        """Connect to email server via IMAP"""
        try:
            # Connect to server
            self.imap = imaplib.IMAP4_SSL(
                self.config['email']['server'],
                self.config['email']['port']
            )

            # Login
            self.imap.login(
                self.config['email']['username'],
                self.config['email']['password']
            )

            # Select folder
            self.imap.select(self.config['email']['folder'])

            logger.info("Successfully connected to email server")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to email: {e}")
            return False

    def parse_land_listing(self, email_body: str) -> Optional[Dict]:
        """Extract land listing information from email body"""
        listing = {}

        # Common patterns in land listing emails
        patterns = {
            'price': [
                r'\$([0-9,]+)',
                r'Price:\s*\$([0-9,]+)',
                r'Asking:\s*\$([0-9,]+)',
                r'Listed at:\s*\$([0-9,]+)'
            ],
            'acres': [
                r'(\d+\.?\d*)\s*acres?',
                r'(\d+\.?\d*)\s*ac\b',
                r'Lot Size:\s*(\d+\.?\d*)\s*acres?'
            ],
            'sqft': [
                r'(\d+,?\d*)\s*sq\.?\s*ft',
                r'(\d+,?\d*)\s*square feet',
                r'Lot Size:\s*(\d+,?\d*)\s*sq'
            ],
            'address': [
                r'(?:Address|Location|Property):\s*(.+?)(?:\n|$)',
                r'(\d+\s+[\w\s]+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|Way|Circle|Ct|Court))',
            ],
            'city': [
                r'(?:City|Location):\s*(\w+)',
                r',\s*(\w+)\s*,?\s*NC',
                r'in\s+(\w+),?\s*NC'
            ],
            'mls': [
                r'MLS\s*#?\s*(\w+)',
                r'Listing\s*#?\s*(\w+)',
                r'ID:\s*(\w+)'
            ]
        }

        # Extract information using patterns
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, email_body, re.IGNORECASE)
                if match:
                    value = match.group(1)

                    # Clean up the value
                    if field in ['price', 'sqft']:
                        value = value.replace(',', '')
                        listing[field] = float(value)
                    elif field == 'acres':
                        listing[field] = float(value)
                        # Convert to sqft if not already present
                        if 'sqft' not in listing:
                            listing['sqft'] = listing[field] * 43560
                    else:
                        listing[field] = value.strip()
                    break

        # Validate required fields
        if 'price' in listing and ('acres' in listing or 'sqft' in listing):
            # Add default city if not found
            if 'city' not in listing:
                listing['city'] = 'Asheville'  # Default

            # Calculate price per acre if possible
            if 'acres' in listing:
                listing['price_per_acre'] = listing['price'] / listing['acres']
            elif 'sqft' in listing:
                acres = listing['sqft'] / 43560
                listing['acres'] = acres
                listing['price_per_acre'] = listing['price'] / acres

            return listing

        return None

    def check_nearby_zones(self, lat: float, lng: float, radius_miles: float = 1.0) -> Dict:
        """Analyze nearby property zones"""
        session = get_session()
        try:
            # Calculate radius in degrees (rough approximation)
            # 1 mile ≈ 0.0145 degrees at this latitude
            radius_deg = radius_miles * 0.0145

            # Get nearby properties
            nearby = session.query(Property).filter(
                Property.latitude.between(lat - radius_deg, lat + radius_deg),
                Property.longitude.between(lng - radius_deg, lng + radius_deg),
                Property.price_per_sqft.isnot(None)
            ).all()

            # Categorize by zone color
            zones = {
                'green': 0,      # $350+/sqft
                'light_green': 0, # $300-350/sqft
                'yellow': 0,     # $220-300/sqft
                'red': 0         # <$220/sqft
            }

            for prop in nearby:
                if prop.price_per_sqft >= 350:
                    zones['green'] += 1
                elif prop.price_per_sqft >= 300:
                    zones['light_green'] += 1
                elif prop.price_per_sqft >= 220:
                    zones['yellow'] += 1
                else:
                    zones['red'] += 1

            total = sum(zones.values())
            if total > 0:
                green_ratio = (zones['green'] + zones['light_green']) / total
            else:
                green_ratio = 0

            return {
                'zones': zones,
                'total_nearby': total,
                'green_ratio': green_ratio,
                'is_promising': green_ratio >= self.config['filters']['min_green_zone_ratio']
            }

        finally:
            session.close()

    def geocode_address(self, address: str, city: str = None) -> Optional[Tuple[float, float]]:
        """Get coordinates for an address using Nominatim"""
        try:
            import requests
            from urllib.parse import quote

            # Build full address
            full_address = f"{address}, {city}" if city else address

            # Add default location if not present
            if 'NC' not in full_address and 'North Carolina' not in full_address:
                full_address += ', NC, USA'

            # Use Nominatim (OpenStreetMap)
            url = f"https://nominatim.openstreetmap.org/search?q={quote(full_address)}&format=json&limit=1"
            headers = {'User-Agent': 'AshevilleLandAnalyzer/1.0'}

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            results = response.json()

            if results:
                lat = float(results[0]['lat'])
                lon = float(results[0]['lon'])
                logger.info(f"Geocoded: {address} -> ({lat}, {lon})")
                return (lat, lon)
            else:
                logger.warning(f"No results for: {address}")
                return None

        except Exception as e:
            logger.error(f"Geocoding error for {address}: {e}")
            return None

    def extract_onehome_links(self, html_body: str) -> List[str]:
        """Extract OneHome listing links from HTML email"""
        try:
            # Look for /listing? links (single property, not properties list)
            pattern = r'https://portal\.onehome\.com/[^\s<>"\']+/listing\?[^\s<>"\']+'
            matches = re.findall(pattern, html_body)

            # Remove duplicates while preserving order
            seen = set()
            unique_links = []
            for link in matches:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)

            return unique_links
        except Exception as e:
            logger.error(f"Error extracting links: {e}")
            return []

    def parse_onehome_page(self, url: str) -> Optional[Dict]:
        """Parse OneHome property page to extract: acres, price, address"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from bs4 import BeautifulSoup

            # Set up Chrome options for headless mode
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            # Create driver
            driver = webdriver.Chrome(options=chrome_options)

            try:
                # Load page
                driver.get(url)

                # Wait for page to load (wait up to 10 seconds for body content)
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                # Give extra time for JavaScript to populate content
                time.sleep(3)

                # Get page source
                page_source = driver.page_source

            finally:
                driver.quit()

            soup = BeautifulSoup(page_source, 'html.parser')

            listing = {}

            # Extract price - look for dollar amounts
            price_patterns = [
                r'\$([0-9,]+)',
                r'Price:\s*\$([0-9,]+)',
                r'List Price:\s*\$([0-9,]+)'
            ]

            page_text = soup.get_text()
            for pattern in price_patterns:
                match = re.search(pattern, page_text)
                if match:
                    price_str = match.group(1).replace(',', '')
                    listing['price'] = float(price_str)
                    break

            # Extract acres
            acres_patterns = [
                r'(\d+\.?\d*)\s*acres?',
                r'(\d+\.?\d*)\s*ac\b',
                r'Lot Size:\s*(\d+\.?\d*)\s*acres?',
                r'Acres:\s*(\d+\.?\d*)'
            ]

            for pattern in acres_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    listing['acres'] = float(match.group(1))
                    listing['sqft'] = listing['acres'] * 43560
                    break

            # Extract address - look for structured data or common patterns
            address_patterns = [
                r'(?:Address|Location|Property):\s*(.+?)(?:\n|,\s*NC)',
                r'(\d+\s+[\w\s]+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|Way|Circle|Ct|Court|Blvd|Boulevard)[,\s]+[\w\s]+,\s*NC)',
            ]

            for pattern in address_patterns:
                match = re.search(pattern, page_text)
                if match:
                    address = match.group(1).strip()

                    # Clean up address - remove excessive whitespace and newlines
                    address = re.sub(r'\s+', ' ', address)  # Replace multiple spaces/newlines with single space
                    listing['address'] = address

                    # Extract city from address
                    city_match = re.search(r',\s*(\w+)\s*,?\s*NC', address)
                    if city_match:
                        listing['city'] = city_match.group(1)
                    break

            # Extract MLS number
            mls_patterns = [
                r'MLS\s*#?\s*[:.]?\s*([A-Z0-9\-]+)',
                r'MLS Number:\s*([A-Z0-9\-]+)',
                r'Listing\s*#?\s*[:.]?\s*([A-Z0-9\-]+)',
                r'ID:\s*([A-Z0-9\-]+)'
            ]

            for pattern in mls_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    listing['mls'] = match.group(1)
                    break

            # If we got the minimum required fields
            if 'price' in listing and 'acres' in listing:
                # Calculate price per acre
                listing['price_per_acre'] = listing['price'] / listing['acres']

                logger.info(f"Parsed OneHome page: ${listing.get('price', 0):,.0f}, {listing.get('acres', 0):.2f} acres, ${listing['price_per_acre']:,.0f}/acre, MLS: {listing.get('mls', 'N/A')}")
                return listing
            else:
                logger.warning(f"Missing required fields from OneHome page")
                return None

        except Exception as e:
            logger.error(f"Error parsing OneHome page: {e}")
            return None

    def process_email(self, msg_id: str) -> List[Dict]:
        """Process a single email message - returns list of listings"""
        listings = []

        try:
            # Fetch email
            typ, data = self.imap.fetch(msg_id, '(RFC822)')
            raw_email = data[0][1]

            # Parse email
            msg = email.message_from_bytes(raw_email)

            # Get subject
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()

            # Get date
            date = msg["Date"]

            # Get HTML body
            html_body = None
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        html_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                html_body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

            if not html_body:
                logger.debug(f"No HTML body in email {msg_id}")
                return listings

            # Extract OneHome listing links
            onehome_links = self.extract_onehome_links(html_body)

            if not onehome_links:
                logger.debug(f"No OneHome listing links found in email {msg_id}")
                return listings

            logger.info(f"Found {len(onehome_links)} listing link(s) in email")

            # Parse each listing
            for link in onehome_links:
                logger.info(f"Processing listing: {link[:80]}...")

                # Parse the OneHome page
                listing = self.parse_onehome_page(link)

                if listing:
                    listing['email_subject'] = subject
                    listing['email_date'] = date
                    listing['email_id'] = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                    listing['source_url'] = link

                    # Try to geocode address
                    if listing.get('address'):
                        coords = self.geocode_address(
                            listing['address'],
                            listing.get('city', 'Asheville')
                        )
                        if coords:
                            listing['lat'], listing['lng'] = coords
                            # Add slight delay to respect Nominatim rate limits
                            time.sleep(1)

                    logger.info(f"Parsed listing: {listing.get('address', 'Unknown')}")
                    listings.append(listing)
                else:
                    logger.debug(f"Could not parse listing from OneHome page")

        except Exception as e:
            logger.error(f"Error processing email {msg_id}: {e}")

        return listings

    def should_alert(self, listing: Dict) -> Tuple[bool, str]:
        """Determine if listing should trigger an alert"""
        reasons = []

        # ONLY PRICE FILTER
        price = listing.get('price', float('inf'))
        max_price = self.config['filters']['max_price']

        if price > max_price:
            return False, f"Price too high: ${price:,.0f} > ${max_price:,.0f}"

        # Price passed - SEND ALERT with info
        reasons.append(f"✓ Price: ${price:,.0f}")

        # Add size info (not a filter)
        acres = listing.get('acres', 0)
        if acres > 0:
            reasons.append(f"ℹ️ Size: {acres:.2f} acres")

        # Add Green Zone info (NOT a filter, just information)
        if listing.get('lat') and listing.get('lng'):
            zone_analysis = self.check_nearby_zones(
                listing['lat'],
                listing['lng'],
                self.config['filters']['search_radius_miles']
            )

            green_ratio = zone_analysis.get('green_ratio', 0)
            total_nearby = zone_analysis.get('total_nearby', 0)

            if total_nearby > 0:
                # Determine zone category
                if green_ratio >= 0.6:
                    zone_label = "🟢 Excellent Location"
                elif green_ratio >= 0.4:
                    zone_label = "🟡 Good Location"
                elif green_ratio >= 0.2:
                    zone_label = "🟠 Moderate Location"
                else:
                    zone_label = "🔴 Low Value Area"

                reasons.append(f"ℹ️ {zone_label}: {green_ratio:.0%} green zones ({total_nearby} properties nearby)")
            else:
                reasons.append("ℹ️ 🏜️ Remote area - no nearby properties in database")
        else:
            reasons.append("ℹ️ ⚠️ Location not geocoded")

        return True, "\n".join(reasons)

    def load_processed_emails(self):
        """Load list of already processed email IDs"""
        try:
            with open('processed_emails.json', 'r') as f:
                self.processed_emails = set(json.load(f))
        except FileNotFoundError:
            self.processed_emails = set()

    def save_processed_emails(self):
        """Save list of processed email IDs"""
        with open('processed_emails.json', 'w') as f:
            json.dump(list(self.processed_emails), f)

    def save_to_database(self, listing: Dict) -> bool:
        """Save listing to database"""
        try:
            session = get_session()

            # Check if already exists by MLS number
            mls = listing.get('mls')
            if mls:
                existing = session.query(Property).filter_by(mls_number=mls).first()
                if existing:
                    logger.info(f"Property {mls} already in database")
                    session.close()
                    return False

            # Create property object
            prop = Property(
                mls_number=mls or f"EMAIL_{datetime.now().timestamp()}",
                address=listing.get('address', 'Unknown'),
                city=listing.get('city', self.config['geocoding']['fallback_city']),
                state='NC',
                zip='',
                latitude=listing.get('lat'),
                longitude=listing.get('lng'),
                list_price=listing.get('price'),
                sqft=listing.get('sqft', 0),
                lot_size=listing.get('acres'),
                status='active',
                archived=False
            )

            session.add(prop)
            session.commit()
            logger.info(f"Saved to database: {listing.get('address')}")
            session.close()
            return True

        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            return False

    def check_new_emails(self) -> List[Dict]:
        """Check for new land listing emails"""
        alerts = []

        if not self.connect_to_email():
            return alerts

        try:
            # Search for emails matching criteria
            search_criteria = self.config['email'].get('search_criteria', 'ALL')

            # Search for unread emails
            typ, data = self.imap.search(None, f'(UNSEEN {search_criteria})')

            email_ids = data[0].split()
            logger.info(f"Found {len(email_ids)} unread emails matching criteria")

            for msg_id in email_ids:
                # Skip if already processed
                msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                if msg_id_str in self.processed_emails:
                    continue

                # Process email - returns list of listings
                listings = self.process_email(msg_id)

                # Process each listing from the email
                for listing in listings:
                    # Save ALL listings to database (even if they don't pass filters)
                    self.save_to_database(listing)

                    # Check if should alert
                    should_alert, reason = self.should_alert(listing)

                    if should_alert:
                        listing['alert_reason'] = reason
                        alerts.append(listing)
                        logger.info(f"✓ Alert triggered: {listing.get('address', 'Unknown')} - {reason}")
                    else:
                        logger.info(f"○ Saved to DB (no alert): {listing.get('address', 'Unknown')} - {reason}")

                # Mark email as processed
                self.processed_emails.add(msg_id_str)

            # Save processed emails
            self.save_processed_emails()

        except Exception as e:
            logger.error(f"Error checking emails: {e}")

        finally:
            if self.imap:
                self.imap.logout()

        return alerts

    def run_monitor(self):
        """Run continuous email monitoring"""
        logger.info("Starting email monitor...")

        # Initialize Telegram notifier if enabled
        telegram_notifier = None
        if self.config['telegram'].get('enabled'):
            from notifications.telegram_bot import TelegramNotifier
            telegram_notifier = TelegramNotifier(
                self.config['telegram']['bot_token'],
                self.config['telegram']['chat_id']
            )
            logger.info("Telegram notifications enabled")

        while self.config['monitoring']['enabled']:
            try:
                # Check for new emails
                alerts = self.check_new_emails()

                # Send alerts
                for alert in alerts:
                    logger.info(f"Processing alert for: {alert.get('address')}")

                    # Send to Telegram if configured
                    if telegram_notifier:
                        success = telegram_notifier.send_land_alert(alert)
                        if success:
                            logger.info(f"✅ Telegram alert sent for: {alert.get('address')}")
                        else:
                            logger.error(f"❌ Failed to send Telegram alert")
                    else:
                        # Just log the alert
                        message = self.format_alert_message(alert)
                        logger.info(f"ALERT: {message}")

                # Wait before next check
                interval = self.config['monitoring']['check_interval_minutes']
                logger.info(f"Waiting {interval} minutes before next check...")
                time.sleep(interval * 60)

            except KeyboardInterrupt:
                logger.info("Stopping email monitor...")
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

    def format_alert_message(self, listing: Dict) -> str:
        """Format listing for alert message"""
        lines = [
            "🚨 *NEW LAND OPPORTUNITY* 🚨",
            "",
            f"📍 *Location:* {listing.get('address', 'Unknown')}, {listing.get('city', 'Unknown')}",
            f"💰 *Price:* ${listing.get('price', 0):,.0f}",
            f"📏 *Size:* {listing.get('acres', 0):.2f} acres",
            f"💵 *Price/Acre:* ${listing.get('price_per_acre', 0):,.0f}",
            "",
            f"✅ *Alert Reason:* {listing.get('alert_reason', 'Meets criteria')}",
            "",
            f"📧 *Source:* {listing.get('email_subject', 'Email')}",
            f"📅 *Date:* {listing.get('email_date', 'Unknown')}"
        ]

        if listing.get('mls'):
            lines.append(f"🏠 *MLS:* {listing['mls']}")

        return "\n".join(lines)


if __name__ == "__main__":
    # Test the email monitor
    monitor = EmailMonitor()

    # Check configuration
    if not monitor.config['email']['username']:
        print("Please configure email settings in email_config.json")
        sys.exit(1)

    # Run monitor
    monitor.run_monitor()
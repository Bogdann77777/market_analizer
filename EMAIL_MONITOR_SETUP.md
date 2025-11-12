# 📧 Email Monitor Setup Guide

## 🚀 Quick Start

The email monitor automatically checks your inbox for land opportunities and sends Telegram alerts when it finds promising properties near green zones.

## 📋 Setup Steps

### 1. Configure Gmail Access

1. Open `email_config.json`
2. Set your Gmail address in `"username"`
3. Generate an App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Sign in to your Google account
   - Select "Mail" as the app
   - Copy the generated 16-character password
   - Paste it in `"password"` field (remove spaces)

**Example:**
```json
"email": {
    "username": "yourname@gmail.com",
    "password": "abcd efgh ijkl mnop"  // Remove spaces
}
```

### 2. Configure Telegram Bot (Optional but Recommended)

1. **Create a Telegram Bot:**
   - Open Telegram and search for `@BotFather`
   - Send `/newbot`
   - Choose a name (e.g., "My Land Alert Bot")
   - Choose a username (e.g., "mylandalert_bot")
   - Copy the token (looks like: `123456789:ABCdef...`)

2. **Get Your Chat ID:**
   - Start a chat with your new bot
   - Send any message to the bot
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find your chat ID in the response

3. **Update Config:**
```json
"telegram": {
    "bot_token": "123456789:ABCdef...",
    "chat_id": "987654321"
}
```

### 3. Set Your Filters

Customize in `email_config.json`:

```json
"filters": {
    "max_price": 150000,              // Maximum land price
    "min_lot_size_acres": 0.25,       // Minimum lot size
    "max_price_per_acre": 50000,      // Max $/acre
    "search_radius_miles": 1.0,       // Zone analysis radius
    "min_green_zone_ratio": 0.6       // 60% green zones required
}
```

### 4. Run the Monitor

Double-click `start_monitor.bat` or run:
```
python start_email_monitor.py
```

## 🎯 How It Works

1. **Email Scanning:** Checks inbox every 30 minutes for emails with "land", "lot", "acre" in subject
2. **Data Extraction:** Parses price, acreage, location from email body
3. **Zone Analysis:** Analyzes properties within 1 mile radius:
   - 🟢 Green zones: $350+/sqft (excellent)
   - 💚 Light green: $300-350/sqft (very good)
   - 🟡 Yellow: $220-300/sqft (moderate)
   - 🔴 Red: <$220/sqft (poor)

4. **Alert Triggers:** Sends Telegram alert if:
   - Price is under your max
   - Lot size meets minimum
   - 60%+ properties nearby are in green zones
   - Investment score > 65/100

## 📊 Alert Information

Each alert includes:
- 📍 Location and address
- 💰 Price and price per acre
- 📏 Lot size in acres
- 📊 Zone analysis score (0-100)
- 🟢 Percentage of green zones nearby
- 📈 Investment recommendation

## 🔧 Troubleshooting

### Gmail Not Connecting
- Enable 2-factor authentication on your Google account
- Use App Password, not your regular password
- Check if "Less secure app access" is needed (not recommended)

### No Emails Found
- Check spam folder settings
- Verify search criteria in config
- Test with broader search terms

### Telegram Not Working
- Verify bot token is correct
- Make sure you've messaged the bot first
- Check chat_id is your personal ID

### Zone Analysis Issues
- Ensure database has property data loaded
- Check coordinates are being extracted correctly
- Verify radius setting (default 1 mile)

## 📝 Email Formats Supported

The monitor can parse these common formats:

- **Price:** $75,000, Price: $75000, Asking: $75,000
- **Size:** 1.5 acres, 2.5 ac, Lot Size: 65,340 sq ft
- **Address:** Standard US addresses with street names
- **MLS:** MLS# 123456, Listing ID: ABC123

## 🔄 Advanced Configuration

### Business Hours Only
```json
"monitoring": {
    "business_hours_only": true,
    "start_hour": 8,
    "end_hour": 22
}
```

### Custom Search Terms
```json
"search_criteria": "(OR SUBJECT \"land\" SUBJECT \"vacant\" BODY \"for sale\")"
```

### Multiple Price Tiers
```json
"price_alerts": {
    "under_50k": true,
    "under_75k": true,
    "under_100k": true
}
```

## 📱 Sample Telegram Alert

```
🚨 NEW LAND OPPORTUNITY 🚨

📍 Location: 123 Mountain View Rd, Asheville
💰 Price: $75,000
📏 Size: 1.50 acres (65,340 sqft)
💵 Price/Acre: $50,000

📊 Zone Analysis:
Score: 85/100
Green Zones: 75%
Properties Analyzed: 42

📈 Recommendation: 🟢 EXCELLENT OPPORTUNITY! Strong appreciation potential.

✅ Alert Triggered: Great location! 75% green zones nearby

📧 Source: New Listing: Prime Land in Asheville
```

## 🛡️ Security Notes

- Never commit `email_config.json` with real credentials
- Use environment variables for production
- App passwords are safer than regular passwords
- Monitor logs are saved to `email_monitor.log`

## 📞 Support

- Check `email_monitor.log` for detailed errors
- Test zone analyzer: `python src/analyzers/zone_analyzer.py`
- Test Telegram: `python src/notifications/telegram_bot.py`

---
*Happy land hunting! 🏞️*
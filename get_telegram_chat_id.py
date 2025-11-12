"""
Get your Telegram Chat ID
"""

import requests
import json

# Your bot token
BOT_TOKEN = "8522601631:AAHTowScesNCgfQg4VPmXiFzr7XqKpAwXp0"

print("=" * 60)
print("TELEGRAM CHAT ID FINDER")
print("=" * 60)
print("\nMake sure you have:")
print("1. Opened Telegram")
print("2. Found your bot")
print("3. Sent at least one message to the bot")
print("\nChecking for messages...")

# Get updates from Telegram
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

try:
    print(f"\nConnecting to Telegram API...")
    response = requests.get(url)
    data = response.json()

    print(f"API Response: {data.get('ok', False)}")

    if not data.get('ok'):
        print(f"Error from Telegram: {data.get('description', 'Unknown error')}")

    if data.get('ok'):
        print(f"Found {len(data.get('result', []))} messages")

    if data.get('ok') and data.get('result'):
        # Get the most recent message
        latest = data['result'][-1]

        if 'message' in latest:
            chat_id = latest['message']['chat']['id']
            username = latest['message']['chat'].get('username', 'Unknown')
            first_name = latest['message']['chat'].get('first_name', '')

            print("\n" + "=" * 60)
            print("FOUND YOUR CHAT ID!")
            print("=" * 60)
            print(f"\nChat ID: {chat_id}")
            print(f"Username: @{username}")
            print(f"Name: {first_name}")

            print("\n" + "=" * 60)
            print("NEXT STEPS:")
            print("=" * 60)
            print(f"\n1. Your Chat ID is: {chat_id}")
            print("2. I will update the config file automatically")

            # Update config file
            with open('email_config.json', 'r') as f:
                config = json.load(f)

            config['telegram']['chat_id'] = str(chat_id)

            with open('email_config.json', 'w') as f:
                json.dump(config, f, indent=4)

            print("3. Config file updated successfully!")

            # Send test message
            print("\n4. Sending test message to Telegram...")
            test_msg = "Hello! Land Monitor is now connected to your Telegram!"
            send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            params = {
                'chat_id': chat_id,
                'text': test_msg,
                'parse_mode': 'Markdown'
            }

            send_response = requests.post(send_url, json=params)

            if send_response.status_code == 200:
                print("   [OK] Test message sent! Check your Telegram.")
            else:
                print("   [ERROR] Could not send test message")

        else:
            print("\n[ERROR] No messages found. Please send a message to the bot first.")
    else:
        print("\n[ERROR] Could not get updates from Telegram")
        print("Make sure you have sent at least one message to your bot")

except Exception as e:
    print(f"\n[ERROR] {e}")
    print("\nTroubleshooting:")
    print("1. Make sure you've created the bot with @BotFather")
    print("2. Make sure you've started a chat with your bot")
    print("3. Send any message to your bot before running this script")
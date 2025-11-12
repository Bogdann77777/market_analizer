"""
Simple UI to update email monitor filters
"""

import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CONFIG_FILE = 'email_config.json'


def load_config():
    """Load current configuration"""
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def save_config(config):
    """Save configuration"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)


def show_current_filters(config):
    """Display current filter settings"""
    print("\n" + "=" * 60)
    print("CURRENT FILTER SETTINGS")
    print("=" * 60)
    print(f"\n  Max Price: ${config['filters']['max_price']:,}")
    print("\nINFORMATION (not filters):")
    print(f"  - Lot size shown in alerts")
    print(f"  - Green zone status shown in alerts")
    print("\n" + "=" * 60)


def update_filter():
    """Main function to update filters"""
    print("\n" + "=" * 60)
    print("ASHEVILLE LAND ANALYZER - UPDATE FILTERS")
    print("=" * 60)

    # Load current config
    config = load_config()

    # Show current settings
    show_current_filters(config)

    print("\nUpdate Max Price Filter:")
    print(f"Current: ${config['filters']['max_price']:,}")
    print("\nExamples:")
    print("  30000  - for $30k budget")
    print("  75000  - for $75k budget")
    print("  100000 - for $100k budget")
    print("\nEnter 0 to cancel")

    choice = input("\nEnter new Max Price ($): ").strip()

    if choice == '0':
        print("\nNo changes made. Exiting...")
        return

    try:
        new_price = int(choice)
        if new_price < 1000:
            print("\n✗ Price too low. Please enter a realistic value.")
            return

        config['filters']['max_price'] = new_price
        print(f"\n✓ Max Price updated to: ${config['filters']['max_price']:,}")

        # Save updated config
        save_config(config)

        print("\n" + "=" * 60)
        print("CONFIGURATION SAVED SUCCESSFULLY")
        print("=" * 60)

        # Show updated settings
        show_current_filters(config)

        print("\nChanges will take effect on next monitor run.")
        print("If monitor is running, restart it to apply changes.")

    except ValueError:
        print("\n✗ Invalid input. Please enter a valid number.")
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    try:
        update_filter()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n✗ Error: {e}")

    input("\nPress Enter to exit...")

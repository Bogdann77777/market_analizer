from src.data.database import get_session, Property

session = get_session()

print('=' * 60)
print('TESTING VACANT LAND PRICE FILTERS')
print('=' * 60)

# Get all vacant land (sqft <= 100)
vacant_land = session.query(Property).filter(
    Property.sqft <= 100,
    Property.archived == False
).all()

print(f'\nTotal vacant land properties: {len(vacant_land)}')

# Count by price ranges
price_ranges = [
    (50000, 'Under $50k'),
    (75000, 'Under $75k'),
    (100000, 'Under $100k'),
    (150000, 'Under $150k'),
    (200000, 'Under $200k'),
    (float('inf'), 'All prices')
]

for max_price, label in price_ranges:
    count = 0
    for prop in vacant_land:
        price = prop.list_price or prop.sale_price
        if price and price <= max_price:
            count += 1
    print(f'{label}: {count} properties')

print('\n' + '=' * 60)
print('TESTING VACANT LAND SIZE FILTERS')
print('=' * 60)

# Count by size ranges (in acres)
size_ranges = [
    (0.25, 'Over 0.25 acres'),
    (0.5, 'Over 0.5 acres'),
    (1, 'Over 1 acre'),
    (2, 'Over 2 acres'),
    (5, 'Over 5 acres'),
]

for min_acres, label in size_ranges:
    count = 0
    min_sqft = min_acres * 43560  # Convert acres to sqft
    for prop in vacant_land:
        if prop.lot_size and prop.lot_size >= min_sqft:
            count += 1
    print(f'{label}: {count} properties')

# Sample some properties
print('\n' + '=' * 60)
print('SAMPLE VACANT LAND UNDER $100K')
print('=' * 60)

samples = [p for p in vacant_land if (p.list_price or p.sale_price) and (p.list_price or p.sale_price) <= 100000][:5]
for prop in samples:
    price = prop.list_price or prop.sale_price
    acres = prop.lot_size / 43560 if prop.lot_size else 0
    print(f'\nAddress: {prop.address}, {prop.city}')
    print(f'  Price: ${price:,.0f}')
    print(f'  Lot size: {acres:.2f} acres ({prop.lot_size:,.0f} sqft)' if prop.lot_size else '  Lot size: N/A')

session.close()
import pandas as pd

df = pd.read_csv('redfin_2025-11-11-16-19-42.csv')

# Remove warning row
if 'accordance' in str(df.iloc[0, 0]).lower() if len(df) > 0 else False:
    df = df.iloc[1:].reset_index(drop=True)

# Look at Vacant Land properties
vacant_land = df[df['PROPERTY TYPE'] == 'Vacant Land']
print(f'Total Vacant Land properties: {len(vacant_land)}')
print(f'Vacant Land with SQUARE FEET: {vacant_land["SQUARE FEET"].notna().sum()}')
print(f'Vacant Land without SQUARE FEET: {vacant_land["SQUARE FEET"].isna().sum()}')

print('\n=== Sample Vacant Land properties ===')
print('Columns available:', list(vacant_land.columns))
print('\nFirst 3 Vacant Land records:')
for idx, row in vacant_land.head(3).iterrows():
    print(f'\nAddress: {row["ADDRESS"]}')
    print(f'Price: ${row["PRICE"]:,.0f}' if pd.notna(row["PRICE"]) else 'Price: N/A')
    print(f'LOT SIZE: {row["LOT SIZE"]}' if pd.notna(row["LOT SIZE"]) else 'LOT SIZE: N/A')
    print(f'SQUARE FEET: {row["SQUARE FEET"]}')
    print(f'PROPERTY TYPE: {row["PROPERTY TYPE"]}')

# Check if LOT SIZE can be used instead
print('\n=== LOT SIZE Analysis ===')
print(f'Records with LOT SIZE: {df["LOT SIZE"].notna().sum()}')
print(f'Vacant Land with LOT SIZE: {vacant_land["LOT SIZE"].notna().sum()}')

# Check all properties without SQUARE FEET
no_sqft = df[df['SQUARE FEET'].isna()]
print(f'\n=== Properties without SQUARE FEET ===')
print(f'Total: {len(no_sqft)}')
print('By property type:')
print(no_sqft['PROPERTY TYPE'].value_counts())
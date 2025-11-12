"""
Flask Web Application - UI Interface for Asheville Land Analyzer
"""

from flask import Flask, render_template, jsonify, request, flash, redirect
from flask_cors import CORS
from werkzeug.utils import secure_filename
import sys
import os
import pandas as pd
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import get_session, Property, StreetAnalysis, LandOpportunity, MarketHeatZone
from config import CITY_CENTER
from analyzers.price_calculator import calculate_price_per_sqft, extract_street_name

# Configuration for file upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
app.config['SECRET_KEY'] = 'asheville-land-analyzer-2024'

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    """Main page with Google Maps"""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    session = get_session()
    try:
        properties_with_url = session.query(Property).filter(
            Property.url != None,
            Property.url != ''
        ).count()

        active_properties = session.query(Property).filter(
            Property.status.in_(['active', 'Active', 'ACTIVE'])
        ).count()

        stats = {
            'properties': session.query(Property).count(),
            'active_properties': active_properties,
            'properties_with_url': properties_with_url,
            'streets': session.query(StreetAnalysis).count(),
            'opportunities': session.query(LandOpportunity).count(),
            'market_zones': session.query(MarketHeatZone).count()
        }
        return jsonify(stats)
    finally:
        session.close()

@app.route('/api/properties')
def get_properties():
    """Get all properties with coordinates"""
    session = get_session()
    try:
        # Get query parameters
        city = request.args.get('city', None)
        limit = request.args.get('limit', 15000, type=int)  # Increased to include all properties

        # Build query - get all properties (filtering will be done on frontend)
        query = session.query(Property).filter(
            Property.latitude != None,
            Property.longitude != None,
            Property.archived == False
        )

        # Filter by city if specified
        if city:
            query = query.filter(Property.city == city)

        # Apply limit
        properties = query.limit(limit).all()

        data = []
        for prop in properties:
            data.append({
                'id': prop.id,
                'address': prop.address,
                'city': prop.city,
                'lat': prop.latitude,
                'lng': prop.longitude,
                'price': prop.sale_price or prop.list_price,
                'price_sqft': prop.price_per_sqft,
                'status': prop.status,
                'sqft': prop.sqft,
                'lot_size': prop.lot_size,
                'url': prop.url
            })

        return jsonify(data)
    finally:
        session.close()

@app.route('/api/streets')
def get_streets():
    """Get street analysis data"""
    session = get_session()
    try:
        streets = session.query(StreetAnalysis).all()

        data = []
        for street in streets:
            data.append({
                'street_name': street.street_name,
                'city': street.city,
                'color': street.color,
                'median_price_sqft': street.median_price_sqft,
                'sample_size': street.sample_size,
                'confidence': street.confidence_score
            })

        return jsonify(data)
    finally:
        session.close()

@app.route('/api/opportunities')
def get_opportunities():
    """Get land opportunities"""
    session = get_session()
    try:
        opportunities = session.query(LandOpportunity).all()

        data = []
        for opp in opportunities:
            prop = session.query(Property).filter_by(id=opp.property_id).first()
            if prop and prop.latitude and prop.longitude:
                data.append({
                    'id': opp.id,
                    'address': prop.address,
                    'lat': prop.latitude,
                    'lng': prop.longitude,
                    'urgency_score': opp.urgency_score,
                    'urgency_level': opp.urgency_level,
                    'zone_color': opp.zone_color,
                    'market_status': opp.market_status,
                    'price': prop.list_price or prop.sale_price,
                    'lot_size': prop.lot_size,
                    'notes': opp.notes
                })

        return jsonify(data)
    finally:
        session.close()

@app.route('/api/config')
def get_config():
    """Get map configuration"""
    return jsonify({
        'center': {
            'lat': CITY_CENTER['lat'],
            'lng': CITY_CENTER['lon']
        },
        'name': CITY_CENTER['name']
    })

@app.route('/api/cities')
def get_cities():
    """Get list of cities with property counts"""
    session = get_session()
    try:
        from sqlalchemy import func
        cities = session.query(
            Property.city,
            func.count(Property.id).label('count')
        ).filter(
            Property.archived == False
        ).group_by(Property.city).order_by(func.count(Property.id).desc()).all()

        return jsonify([{
            'city': city,
            'count': count
        } for city, count in cities])
    finally:
        session.close()

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_redfin_csv(filepath):
    """Parse Redfin CSV format and return processed data"""
    # Read CSV - the warning is on row 2, not row 1
    df = pd.read_csv(filepath)

    # Remove the warning row if it exists (check if first column contains warning text)
    if len(df) > 0 and 'accordance' in str(df.iloc[0, 0]).lower():
        df = df.iloc[1:].reset_index(drop=True)

    # Remove any completely empty rows
    df = df.dropna(how='all')

    # Map Redfin columns to our database columns
    column_mapping = {
        'ADDRESS': 'address',
        'CITY': 'city',
        'STATE OR PROVINCE': 'state',
        'ZIP OR POSTAL CODE': 'zip',
        'PRICE': 'price',
        'BEDS': 'bedrooms',
        'BATHS': 'bathrooms',
        'SQUARE FEET': 'sqft',
        'LOT SIZE': 'lot_size',
        'YEAR BUILT': 'year_built',
        'DAYS ON MARKET': 'days_on_market',
        '$/SQUARE FEET': 'price_per_sqft',
        'STATUS': 'status',
        'MLS#': 'mls_number',
        'LATITUDE': 'latitude',
        'LONGITUDE': 'longitude',
        'PROPERTY TYPE': 'property_type',
        'SOLD DATE': 'sold_date'
    }

    # Find and map URL column (it has a long name in Redfin CSV)
    for col in df.columns:
        if 'URL' in col.upper():
            column_mapping[col] = 'url'
            break

    # Rename columns
    df = df.rename(columns=column_mapping)

    # Clean and convert data
    if 'price' in df.columns:
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
    if 'sqft' in df.columns:
        df['sqft'] = pd.to_numeric(df['sqft'], errors='coerce')
    if 'lot_size' in df.columns:
        df['lot_size'] = pd.to_numeric(df['lot_size'], errors='coerce')
    if 'days_on_market' in df.columns:
        df['days_on_market'] = pd.to_numeric(df['days_on_market'], errors='coerce')

    # Convert status to lowercase and handle NaN values
    if 'status' in df.columns:
        df['status'] = df['status'].fillna('active')  # Default to 'active' if missing
        df['status'] = df['status'].astype(str).str.lower()
        # Replace 'nan' string with 'active'
        df['status'] = df['status'].replace('nan', 'active')
        # Map common status values
        status_mapping = {
            'for sale': 'active',
            'pending': 'pending',
            'sold': 'sold',
            'under contract': 'under_contract',
            'coming soon': 'active',
            'contingent': 'pending'
        }
        df['status'] = df['status'].replace(status_mapping)

    # Handle Vacant Land - use LOT SIZE as sqft if no SQUARE FEET
    if 'property_type' in df.columns:
        # For vacant land without sqft, use lot_size if available
        vacant_mask = (df['property_type'].str.lower() == 'vacant land') & df['sqft'].isna()
        if 'lot_size' in df.columns:
            # Use 1 sqft as placeholder for vacant land (we have lot_size separately)
            df.loc[vacant_mask & df['lot_size'].notna(), 'sqft'] = 1

    # Filter out invalid rows - only require address
    df = df.dropna(subset=['address'])

    # For properties that aren't vacant land, they need valid sqft
    if 'property_type' in df.columns:
        non_vacant_mask = df['property_type'].str.lower() != 'vacant land'
        df = df[~(non_vacant_mask & (df['sqft'].isna() | (df['sqft'] <= 0)))]
    else:
        # If no property type column, apply old filter
        df = df.dropna(subset=['sqft'])
        df = df[df['sqft'] > 0]

    return df

@app.route('/api/import', methods=['POST'])
def import_csv():
    """Import CSV file with property data"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        # Check if file has a filename
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Check if file is allowed
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only CSV files are allowed'}), 400

        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Parse CSV based on format
        df = parse_redfin_csv(filepath)

        # Import to database
        session = get_session()
        imported_count = 0
        updated_count = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                # Check if property already exists
                existing = None
                mls_num = row.get('mls_number')
                if pd.notna(mls_num) and str(mls_num).lower() != 'nan':
                    existing = session.query(Property).filter_by(
                        mls_number=str(mls_num)
                    ).first()

                if existing:
                    # Update existing property
                    if pd.notna(row.get('price')):
                        if row.get('status') == 'sold':
                            existing.sale_price = row['price']
                        else:
                            existing.list_price = row['price']

                    existing.status = row.get('status', 'active')

                    # Update URL if available and not already set
                    if pd.notna(row.get('url')) and not existing.url:
                        existing.url = str(row['url'])

                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new property
                    # Generate unique MLS number if missing or invalid
                    mls_number = None
                    if pd.notna(mls_num) and str(mls_num).lower() != 'nan':
                        mls_number = str(mls_num)
                    else:
                        # Generate unique ID based on timestamp and index
                        import time
                        mls_number = f'IMP_{int(time.time())}_{idx}'

                    # Handle city field - use default if missing or nan
                    city = row.get('city', 'Asheville')
                    if pd.isna(city) or str(city).lower() == 'nan' or not city:
                        # Try to determine city from ZIP code if available
                        zip_code_temp = row.get('zip', '')
                        if pd.notna(zip_code_temp) and str(zip_code_temp).startswith('287'):
                            # Common ZIP prefixes for cities near Asheville
                            zip_prefix = str(zip_code_temp)[:5]
                            zip_to_city = {
                                '28801': 'Asheville', '28802': 'Asheville', '28803': 'Asheville',
                                '28804': 'Asheville', '28805': 'Asheville', '28806': 'Asheville',
                                '28704': 'Arden', '28711': 'Black Mountain', '28715': 'Candler',
                                '28716': 'Canton', '28732': 'Fletcher', '28739': 'Flat Rock',
                                '28748': 'Leicester', '28753': 'Marshall', '28754': 'Mars Hill',
                                '28778': 'Swannanoa', '28787': 'Weaverville',
                                '28791': 'Hendersonville', '28792': 'Hendersonville',
                                '28785': 'Waynesville', '28786': 'Waynesville'
                            }
                            city = zip_to_city.get(zip_prefix, 'Asheville')
                        else:
                            city = 'Asheville'  # Default city

                    # Handle state field
                    state = row.get('state', 'NC')
                    if pd.isna(state) or str(state).lower() == 'nan' or not state:
                        state = 'NC'

                    # Handle zip code
                    zip_code = row.get('zip', '')
                    if pd.notna(zip_code) and str(zip_code).lower() != 'nan':
                        zip_code = str(zip_code)[:10]
                    else:
                        zip_code = ''

                    # Handle sqft - use 1 for vacant land if needed
                    sqft = row['sqft']
                    if pd.isna(sqft) or sqft <= 0:
                        sqft = 1  # Default for vacant land or missing data

                    property_data = {
                        'mls_number': mls_number,
                        'address': row['address'],
                        'city': city,
                        'state': state,
                        'zip': zip_code,
                        'sqft': sqft,
                        'status': row.get('status', 'active'),
                        'archived': False
                    }

                    # Add optional fields
                    if pd.notna(row.get('price')):
                        if row.get('status') == 'sold':
                            property_data['sale_price'] = row['price']
                        else:
                            property_data['list_price'] = row['price']

                        # Calculate price per sqft
                        property_data['price_per_sqft'] = calculate_price_per_sqft(
                            row['price'], row['sqft']
                        )

                    if pd.notna(row.get('latitude')):
                        property_data['latitude'] = row['latitude']
                    if pd.notna(row.get('longitude')):
                        property_data['longitude'] = row['longitude']
                    if pd.notna(row.get('bedrooms')):
                        property_data['bedrooms'] = int(row['bedrooms'])
                    if pd.notna(row.get('bathrooms')):
                        property_data['bathrooms'] = float(row['bathrooms'])
                    if pd.notna(row.get('lot_size')):
                        property_data['lot_size'] = row['lot_size']
                    if pd.notna(row.get('days_on_market')):
                        property_data['days_on_market'] = int(row['days_on_market'])
                    if pd.notna(row.get('url')):
                        property_data['url'] = str(row['url'])

                    # Extract street name
                    property_data['street_name'] = extract_street_name(row['address'])

                    new_property = Property(**property_data)
                    session.add(new_property)
                    imported_count += 1

            except Exception as e:
                error_msg = f"Row {idx} ({row.get('address', 'Unknown')}): {str(e)}"
                errors.append(error_msg)
                print(f"Import error: {error_msg}")
                continue

        # Commit changes
        session.commit()
        session.close()

        # Clean up uploaded file
        os.remove(filepath)

        return jsonify({
            'success': True,
            'imported': imported_count,
            'updated': updated_count,
            'total_processed': len(df),
            'errors': errors[:10]  # Return first 10 errors only
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/import/status')
def import_status():
    """Get current import status and statistics"""
    session = get_session()
    try:
        total_properties = session.query(Property).count()
        active_properties = session.query(Property).filter_by(status='active').count()
        sold_properties = session.query(Property).filter_by(status='sold').count()

        return jsonify({
            'total': total_properties,
            'active': active_properties,
            'sold': sold_properties
        })
    finally:
        session.close()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("   ASHEVILLE LAND ANALYZER - Web UI")
    print("="*60)
    print("\n  Starting web server...")
    print(f"  Open: http://localhost:5001")
    print("\n" + "="*60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5001)

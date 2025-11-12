"""
Zone Analyzer - Analyzes property zones around a given location
"""

import math
from typing import Dict, List, Tuple, Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import get_session, Property


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates in miles using Haversine formula
    """
    # Radius of Earth in miles
    R = 3959.0

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


def get_zone_color(price_per_sqft: float) -> str:
    """Get zone color based on price per square foot"""
    if price_per_sqft >= 350:
        return 'green'
    elif price_per_sqft >= 300:
        return 'light_green'
    elif price_per_sqft >= 220:
        return 'yellow'
    else:
        return 'red'


def analyze_nearby_zones(lat: float, lng: float, radius_miles: float = 1.0,
                         min_properties: int = 5) -> Dict:
    """
    Analyze property zones within radius of given coordinates

    Args:
        lat: Latitude of target location
        lng: Longitude of target location
        radius_miles: Search radius in miles (default 1.0)
        min_properties: Minimum properties needed for valid analysis

    Returns:
        Dictionary with zone analysis results
    """
    session = get_session()
    analysis = {
        'target_lat': lat,
        'target_lng': lng,
        'radius_miles': radius_miles,
        'properties_analyzed': 0,
        'zones': {
            'green': {'count': 0, 'properties': []},
            'light_green': {'count': 0, 'properties': []},
            'yellow': {'count': 0, 'properties': []},
            'red': {'count': 0, 'properties': []}
        },
        'statistics': {},
        'recommendation': '',
        'score': 0
    }

    try:
        # Get rough bounding box (approximate)
        # 1 degree latitude ≈ 69 miles
        # 1 degree longitude ≈ 55 miles at this latitude
        lat_delta = radius_miles / 69
        lng_delta = radius_miles / 55

        # Query properties in bounding box
        properties = session.query(Property).filter(
            Property.latitude.between(lat - lat_delta, lat + lat_delta),
            Property.longitude.between(lng - lng_delta, lng + lng_delta),
            Property.price_per_sqft.isnot(None),
            Property.archived == False
        ).all()

        # Filter by actual distance and analyze
        nearby_properties = []
        for prop in properties:
            distance = calculate_distance(lat, lng, prop.latitude, prop.longitude)
            if distance <= radius_miles:
                zone_color = get_zone_color(prop.price_per_sqft)

                prop_info = {
                    'address': prop.address,
                    'city': prop.city,
                    'price_per_sqft': prop.price_per_sqft,
                    'distance_miles': round(distance, 2)
                }

                analysis['zones'][zone_color]['count'] += 1
                analysis['zones'][zone_color]['properties'].append(prop_info)
                nearby_properties.append(prop)

        analysis['properties_analyzed'] = len(nearby_properties)

        # Calculate statistics if enough properties
        if len(nearby_properties) >= min_properties:
            # Calculate zone percentages
            total = len(nearby_properties)
            green_count = analysis['zones']['green']['count']
            light_green_count = analysis['zones']['light_green']['count']
            yellow_count = analysis['zones']['yellow']['count']
            red_count = analysis['zones']['red']['count']

            analysis['statistics'] = {
                'green_percent': (green_count / total) * 100,
                'light_green_percent': (light_green_count / total) * 100,
                'yellow_percent': (yellow_count / total) * 100,
                'red_percent': (red_count / total) * 100,
                'green_zones_total': green_count + light_green_count,
                'green_zones_percent': ((green_count + light_green_count) / total) * 100
            }

            # Calculate investment score (0-100)
            score = calculate_investment_score(analysis['statistics'])
            analysis['score'] = score

            # Generate recommendation
            analysis['recommendation'] = generate_recommendation(score, analysis['statistics'])

        else:
            analysis['statistics'] = {
                'message': f'Not enough data. Found only {len(nearby_properties)} properties.'
            }
            analysis['recommendation'] = 'Insufficient data for analysis'

    finally:
        session.close()

    return analysis


def calculate_investment_score(stats: Dict) -> int:
    """
    Calculate investment score based on zone distribution (0-100)

    Scoring logic:
    - Green zones: +40 points per 25%
    - Light green zones: +30 points per 25%
    - Yellow zones: +10 points per 25%
    - Red zones: -20 points per 25%
    """
    score = 40  # Base score

    # Positive factors
    score += (stats['green_percent'] / 25) * 35
    score += (stats['light_green_percent'] / 25) * 25
    score += (stats['yellow_percent'] / 25) * 10

    # Negative factors
    score -= (stats['red_percent'] / 25) * 25

    # Bonus for high concentration of green zones
    if stats['green_zones_percent'] >= 75:
        score += 25  # Excellent area
    elif stats['green_zones_percent'] >= 60:
        score += 15  # Very good area
    elif stats['green_zones_percent'] >= 50:
        score += 10  # Good area - threshold for alerts
    elif stats['green_zones_percent'] >= 40:
        score += 5   # Moderate area

    # Cap between 0-100
    return max(0, min(100, int(score)))


def generate_recommendation(score: int, stats: Dict) -> str:
    """Generate investment recommendation based on score and statistics"""
    green_percent = stats['green_zones_percent']

    if score >= 85:
        return f"EXCELLENT OPPORTUNITY! {green_percent:.0f}% green zones. Premium location with strong appreciation."
    elif score >= 70:
        return f"VERY GOOD location. {green_percent:.0f}% green zones. Above 50% threshold - good investment."
    elif score >= 55:
        return f"GOOD opportunity. {green_percent:.0f}% green zones. Meets 50% threshold for alerts."
    elif score >= 40:
        return f"MODERATE area. {green_percent:.0f}% green zones. Just below 50% threshold - review carefully."
    elif score >= 25:
        return f"BELOW AVERAGE area. Only {green_percent:.0f}% green zones. Under 50% threshold - caution advised."
    else:
        return f"POOR location. Only {green_percent:.0f}% green zones. Well below 50% threshold - high risk."


def find_best_zones(city: str = None, min_score: int = 65,
                    sample_size: int = 100) -> List[Dict]:
    """
    Find areas with the best zone distributions

    Args:
        city: Filter by city (optional)
        min_score: Minimum investment score
        sample_size: Number of random points to sample

    Returns:
        List of high-scoring locations
    """
    session = get_session()
    best_zones = []

    try:
        # Get sample properties to use as test points
        query = session.query(Property).filter(
            Property.latitude.isnot(None),
            Property.longitude.isnot(None),
            Property.archived == False
        )

        if city:
            query = query.filter(Property.city == city)

        # Get random sample
        sample_properties = query.limit(sample_size).all()

        for prop in sample_properties:
            # Analyze zone around this property
            analysis = analyze_nearby_zones(
                prop.latitude,
                prop.longitude,
                radius_miles=1.0
            )

            if analysis['score'] >= min_score:
                best_zones.append({
                    'center_address': prop.address,
                    'city': prop.city,
                    'lat': prop.latitude,
                    'lng': prop.longitude,
                    'score': analysis['score'],
                    'green_zones_percent': analysis['statistics'].get('green_zones_percent', 0),
                    'properties_analyzed': analysis['properties_analyzed'],
                    'recommendation': analysis['recommendation']
                })

        # Sort by score
        best_zones.sort(key=lambda x: x['score'], reverse=True)

    finally:
        session.close()

    return best_zones


if __name__ == "__main__":
    # Test the zone analyzer
    # Using Asheville city center as test
    test_lat = 35.5951
    test_lng = -82.5515

    print("=" * 60)
    print("ZONE ANALYSIS TEST")
    print("=" * 60)
    print(f"Analyzing zones around: {test_lat}, {test_lng}")
    print()

    analysis = analyze_nearby_zones(test_lat, test_lng, radius_miles=1.0)

    print(f"Properties analyzed: {analysis['properties_analyzed']}")
    print()

    if 'green_zones_percent' in analysis['statistics']:
        print("Zone Distribution:")
        print(f"  Green zones: {analysis['statistics']['green_percent']:.1f}%")
        print(f"  Light green zones: {analysis['statistics']['light_green_percent']:.1f}%")
        print(f"  Yellow zones: {analysis['statistics']['yellow_percent']:.1f}%")
        print(f"  Red zones: {analysis['statistics']['red_percent']:.1f}%")
        print()
        print(f"Investment Score: {analysis['score']}/100")
        print(f"Recommendation: {analysis['recommendation']}")
    else:
        print(analysis['statistics'].get('message', 'No analysis available'))

    # Find best zones
    print("\n" + "=" * 60)
    print("FINDING BEST ZONES IN ASHEVILLE")
    print("=" * 60)

    best = find_best_zones(city='Asheville', min_score=65, sample_size=20)

    if best:
        print(f"\nFound {len(best)} high-scoring zones:\n")
        for i, zone in enumerate(best[:5], 1):
            print(f"{i}. {zone['center_address']}")
            print(f"   Score: {zone['score']}/100")
            print(f"   Green zones: {zone['green_zones_percent']:.0f}%")
            print(f"   {zone['recommendation']}")
            print()
    else:
        print("No high-scoring zones found")
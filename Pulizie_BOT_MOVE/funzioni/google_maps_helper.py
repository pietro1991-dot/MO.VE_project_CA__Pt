"""
Google Maps API Helper
Geocoding e calcolo distanze utilizzando Google Maps Platform
"""

import requests
from typing import Optional, Tuple
from .config import GOOGLE_MAPS_API_KEY


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Converte un indirizzo in coordinate GPS usando Google Geocoding API
    Returns: (lat, lon) oppure None
    """
    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ Google Maps API key non configurata")
        return None
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'address': address,
        'key': GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if data['status'] == 'OK' and len(data['results']) > 0:
            location = data['results'][0]['geometry']['location']
            return (location['lat'], location['lng'])
        else:
            print(f"⚠️ Geocoding fallito per '{address}': {data['status']}")
            return None
    except Exception as e:
        print(f"❌ Errore geocoding: {e}")
        return None


def get_distance_matrix(origins: list, destinations: list) -> dict:
    """
    Calcola distanze e tempi di percorrenza tra più origini e destinazioni
    usando Google Distance Matrix API
    
    Args:
        origins: lista di tuple (lat, lon) o indirizzi
        destinations: lista di tuple (lat, lon) o indirizzi
    
    Returns:
        dict con distanze in metri e durate in secondi
    """
    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ Google Maps API key non configurata")
        return {}
    
    # Converti coordinate in formato "lat,lon"
    def format_location(loc):
        if isinstance(loc, tuple):
            return f"{loc[0]},{loc[1]}"
        return str(loc)
    
    origins_str = "|".join([format_location(o) for o in origins])
    destinations_str = "|".join([format_location(d) for d in destinations])
    
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        'origins': origins_str,
        'destinations': destinations_str,
        'mode': 'driving',  # driving, walking, bicycling, transit
        'language': 'it',
        'key': GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data['status'] == 'OK':
            results = []
            for row in data['rows']:
                for element in row['elements']:
                    if element['status'] == 'OK':
                        results.append({
                            'distance_meters': element['distance']['value'],
                            'distance_text': element['distance']['text'],
                            'duration_seconds': element['duration']['value'],
                            'duration_text': element['duration']['text']
                        })
                    else:
                        results.append(None)
            return {'results': results, 'raw': data}
        else:
            print(f"⚠️ Distance Matrix fallito: {data['status']}")
            return {}
    except Exception as e:
        print(f"❌ Errore Distance Matrix: {e}")
        return {}


def get_nearby_places(lat: float, lon: float, radius: int = 500, place_type: str = 'point_of_interest') -> list:
    """
    Trova luoghi nelle vicinanze usando Google Places API
    
    Args:
        lat, lon: coordinate GPS
        radius: raggio di ricerca in metri
        place_type: tipo di luogo (restaurant, cafe, store, etc.)
    
    Returns:
        lista di luoghi con nome, indirizzo, coordinate
    """
    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ Google Maps API key non configurata")
        return []
    
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        'location': f"{lat},{lon}",
        'radius': radius,
        'type': place_type,
        'language': 'it',
        'key': GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data['status'] == 'OK':
            places = []
            for place in data['results']:
                places.append({
                    'name': place.get('name'),
                    'address': place.get('vicinity'),
                    'lat': place['geometry']['location']['lat'],
                    'lon': place['geometry']['location']['lng'],
                    'rating': place.get('rating'),
                    'place_id': place.get('place_id')
                })
            return places
        else:
            print(f"⚠️ Nearby search fallito: {data['status']}")
            return []
    except Exception as e:
        print(f"❌ Errore nearby search: {e}")
        return []


def enrich_appartamenti_with_geocoding(appartamenti: list) -> list:
    """
    Arricchisce lista appartamenti con coordinate GPS ottenute da indirizzi
    Se un appartamento ha già coordinate, le mantiene.
    """
    if not GOOGLE_MAPS_API_KEY:
        return appartamenti
    
    enriched = []
    for app in appartamenti:
        app_copy = dict(app)
        
        # Se non ha coordinate o sono vuote, prova geocoding
        if not app.get('coordinate') or app['coordinate'] == '':
            if app.get('indirizzo'):
                print(f"🔍 Geocoding: {app['nome']} - {app['indirizzo']}")
                coords = geocode_address(app['indirizzo'])
                if coords:
                    app_copy['coordinate'] = f"{coords[0]},{coords[1]}"
                    app_copy['geocoded'] = True
                    print(f"✅ Coordinate trovate: {coords}")
        
        enriched.append(app_copy)
    
    return enriched


if __name__ == '__main__':
    # Test API
    print("🗺️  Test Google Maps API\n")
    
    # Test Geocoding
    print("1️⃣ Geocoding indirizzo...")
    coords = geocode_address("Via Roma 1, Milano")
    if coords:
        print(f"   ✅ Coordinate: {coords}")
    
    # Test Distance Matrix
    if coords:
        print("\n2️⃣ Calcolo distanza...")
        origins = [coords]
        destinations = [(45.4642, 9.1900)]  # Duomo Milano
        result = get_distance_matrix(origins, destinations)
        if result.get('results'):
            print(f"   ✅ Distanza: {result['results'][0]['distance_text']}")
            print(f"   ⏱️  Durata: {result['results'][0]['duration_text']}")
    
    print("\n✅ Test completato")

import requests
from supabase import create_client, Client
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import time
import hashlib
import math

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Missing Supabase credentials")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

seen_events = set()

def get_event_hash(event):
    unique_str = f"{event.get('event_type')}_{event.get('latitude')}_{event.get('longitude')}_{event.get('event_time')}"
    return hashlib.md5(unique_str.encode()).hexdigest()

def is_in_ocean(lat, lon):
    if -60 < lat < 60:
        if (lon > -180 and lon < -30) or (lon > 20 and lon < 150) or (lon > 150 and lon < 180):
            return True
        if (lat > -60 and lat < -30 and lon > -180 and lon < 180):
            return True
    return False

def generate_tsunami(earthquake):
    mag = earthquake.get('magnitude', 0)
    lat = earthquake.get('latitude', 0)
    lon = earthquake.get('longitude', 0)
    
    if mag > 6.5 and is_in_ocean(lat, lon):
        return {
            "title": f"Tsunami warning - {earthquake.get('title', 'Undersea earthquake')}",
            "event_type": "tsunami",
            "source": "Generated",
            "category": "marine",
            "severity": "high" if mag > 7.5 else "medium",
            "latitude": lat,
            "longitude": lon,
            "magnitude": mag,
            "event_time": earthquake.get('event_time'),
            "external_url": earthquake.get('external_url', '')
        }
    return None

def fetch_earthquakes():
    """Fetch earthquakes from last 24 hours (not just last few minutes)"""
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    start_time = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    params = {
        "format": "geojson",
        "starttime": start_time,
        "minmagnitude": 2.5,
        "orderby": "time",
        "limit": 100
    }
    
    print(f"  📡 Fetching earthquakes from {start_time}...")
    response = requests.get(url, params=params)
    print(f"  📡 Response status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"  ❌ API Error: {response.status_code}")
        return []
    
    data = response.json()
    features = data.get('features', [])
    print(f"  📡 Found {len(features)} earthquake features")
    
    events = []
    for feature in features:
        props = feature['properties']
        coords = feature['geometry']['coordinates']
        
        mag = props.get('mag', 0)
        if mag >= 6:
            severity = "high"
        elif mag >= 4:
            severity = "medium"
        else:
            severity = "low"
        
        event_time = datetime.fromtimestamp(props['time'] / 1000).isoformat()
        
        event = {
            "title": props.get('title', 'Unknown earthquake'),
            "event_type": "earthquake",
            "source": "USGS",
            "category": "seismic",
            "severity": severity,
            "latitude": coords[1],
            "longitude": coords[0],
            "magnitude": mag,
            "event_time": event_time,
            "external_url": props.get('url', '')
        }
        events.append(event)
        
        tsunami = generate_tsunami(event)
        if tsunami:
            events.append(tsunami)
    
    earthquake_count = len([e for e in events if e['event_type'] == 'earthquake'])
    tsunami_count = len([e for e in events if e['event_type'] == 'tsunami'])
    print(f"  📊 Earthquakes: {earthquake_count}, Tsunamis: {tsunami_count}")
    return events

def fetch_nasa_events():
    """Fetch NASA events from last 24 hours"""
    url = "https://eonet.gsfc.nasa.gov/api/v3/events"
    params = {"status": "open", "limit": 100}
    
    print(f"  📡 Fetching NASA events...")
    response = requests.get(url, params=params)
    print(f"  📡 Response status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"  ❌ API Error: {response.status_code}")
        return []
    
    data = response.json()
    items = data.get('events', [])
    print(f"  📡 Found {len(items)} NASA events")
    
    events = []
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    
    for item in items:
        categories = [c.get('title', '').lower() for c in item.get('categories', [])]
        
        event_type = None
        severity = "medium"
        
        if any('wildfire' in c or 'fire' in c for c in categories):
            event_type = "wildfire"
            severity = "high"
        elif any('volcano' in c for c in categories):
            event_type = "volcano"
            severity = "high"
        elif any('flood' in c for c in categories):
            event_type = "flood"
            severity = "medium"
        elif any('storm' in c or 'cyclone' in c for c in categories):
            event_type = "storm"
            severity = "high"
        else:
            continue
        
        geometries = item.get('geometry', [])
        if not geometries:
            continue
        
        coords = geometries[0].get('coordinates', [])
        if len(coords) < 2:
            continue
        
        event_time = geometries[0].get('date', datetime.now(timezone.utc).isoformat())
        
        if event_time.endswith('Z'):
            event_time = event_time.replace('Z', '+00:00')
        event_dt = datetime.fromisoformat(event_time)
        
        if event_dt < one_day_ago:
            continue
        
        events.append({
            "title": item.get('title', 'Unknown')[:200],
            "event_type": event_type,
            "source": "NASA",
            "category": "natural",
            "severity": severity,
            "latitude": coords[1],
            "longitude": coords[0],
            "magnitude": None,
            "event_time": event_time,
            "external_url": item.get('link', '')
        })
    
    print(f"  🔥 NASA Events (last 24h): {len(events)}")
    return events

def fetch_weather_alerts():
    """Fetch severe weather alerts"""
    regions = [
        {"name": "US Central", "lat": 39.83, "lon": -98.58},
        {"name": "Europe", "lat": 50.11, "lon": 8.68},
        {"name": "East Asia", "lat": 35.68, "lon": 139.76},
        {"name": "Southeast Asia", "lat": 13.41, "lon": 103.87},
        {"name": "Australia", "lat": -25.27, "lon": 133.78}
    ]
    
    events = []
    for region in regions:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": region["lat"],
            "longitude": region["lon"],
            "current_weather": True,
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            weather = data.get('current_weather', {})
            windspeed = weather.get('windspeed', 0)
            
            if windspeed > 50:
                severity = "high" if windspeed > 80 else "medium"
                events.append({
                    "title": f"High wind alert - {region['name']}: {windspeed} km/h",
                    "event_type": "storm",
                    "source": "Open-Meteo",
                    "category": "weather",
                    "severity": severity,
                    "latitude": region["lat"],
                    "longitude": region["lon"],
                    "magnitude": windspeed,
                    "event_time": datetime.now(timezone.utc).isoformat(),
                    "external_url": ""
                })
        except Exception as e:
            print(f"  ⚠️ Weather fetch failed for {region['name']}: {e}")
    
    print(f"  🌪️ Weather Alerts: {len(events)}")
    return events

def insert_new_events(events):
    if not events:
        return 0
    
    # First, clear old events (older than 2 days)
    cutoff_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    supabase.table('events').delete().lt('event_time', cutoff_time).execute()
    
    inserted = 0
    for event in events:
        event_hash = get_event_hash(event)
        if event_hash in seen_events:
            continue
        
        try:
            supabase.table('events').insert(event).execute()
            seen_events.add(event_hash)
            inserted += 1
            print(f"  ✅ Inserted: {event.get('event_type', 'event')} - {event.get('title', '')[:40]}")
        except Exception as e:
            print(f"  ❌ Error inserting: {e}")
    
    return inserted

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🌍 EVENTHORIZON ETL - ONE TIME RUN")
    print("="*60)
    print(f"Time: {datetime.now(timezone.utc).isoformat()}\n")
    
    # Fetch all events
    print("1. Fetching earthquakes...")
    earthquakes = fetch_earthquakes()
    
    print("\n2. Fetching NASA events...")
    nasa_events = fetch_nasa_events()
    
    print("\n3. Fetching weather alerts...")
    weather_events = fetch_weather_alerts()
    
    # Merge all events
    all_events = earthquakes + nasa_events + weather_events
    print(f"\n📦 Total events fetched: {len(all_events)}")
    
    # Insert into database
    print("\n4. Inserting into Supabase...")
    inserted = insert_new_events(all_events)
    print(f"\n✅ Done! Inserted {inserted} new events.")
    
    # Show current event count in database
    result = supabase.table('events').select('count', count='exact').execute()
    print(f"📊 Total events in database: {result.count}")
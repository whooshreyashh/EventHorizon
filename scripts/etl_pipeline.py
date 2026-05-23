import requests
from supabase import create_client, Client
import os
from datetime import datetime, timedelta
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
    """Simple ocean check: basic lat/lon bounds for major oceans"""
    # Rough approximation - avoids major landmasses
    if -60 < lat < 60:
        # Pacific, Atlantic, Indian ocean areas
        if (lon > -180 and lon < -30) or (lon > 20 and lon < 150) or (lon > 150 and lon < 180):
            return True
        # Specific ocean areas
        if (lat > -60 and lat < -30 and lon > -180 and lon < 180):
            return True
    return False

def generate_tsunami(earthquake):
    """Generate tsunami event from undersea earthquake > 6.5 magnitude"""
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

def fetch_earthquakes(since_time=None):
    if since_time is None:
        since_time = datetime.now() - timedelta(hours=6)
    
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": since_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "minmagnitude": 2.5,
        "orderby": "time"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    events = []
    for feature in data.get('features', []):
        props = feature['properties']
        coords = feature['geometry']['coordinates']
        
        mag = props.get('mag', 0)
        if mag >= 6:
            severity = "high"
        elif mag >= 4:
            severity = "medium"
        else:
            severity = "low"
        
        event = {
            "title": props.get('title', 'Unknown earthquake'),
            "event_type": "earthquake",
            "source": "USGS",
            "category": "seismic",
            "severity": severity,
            "latitude": coords[1],
            "longitude": coords[0],
            "magnitude": mag,
            "event_time": datetime.fromtimestamp(props['time'] / 1000).isoformat(),
            "external_url": props.get('url', '')
        }
        events.append(event)
        
        # Generate tsunami if conditions met
        tsunami = generate_tsunami(event)
        if tsunami:
            events.append(tsunami)
    
    return events

def fetch_nasa_events():
    url = "https://eonet.gsfc.nasa.gov/api/v3/events"
    params = {"status": "open", "limit": 50}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    events = []
    one_hour_ago = datetime.now() - timedelta(hours=1)
    
    for item in data.get('events', []):
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
        
        event_time = geometries[0].get('date', datetime.now().isoformat())
        event_dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
        
        if event_dt < one_hour_ago:
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
    
    return events

def fetch_weather_alerts():
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
            "hourly": "windspeed_10m"
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
                    "event_time": datetime.now().isoformat(),
                    "external_url": ""
                })
        except Exception as e:
            print(f"  ⚠️ Weather fetch failed for {region['name']}: {e}")
    
    return events

def insert_new_events(events):
    if not events:
        return 0
    
    inserted = 0
    for event in events:
        event_hash = get_event_hash(event)
        if event_hash in seen_events:
            continue
        
        try:
            supabase.table('events').insert(event).execute()
            seen_events.add(event_hash)
            inserted += 1
            print(f"  🔴 LIVE: {event.get('event_type')} - {event.get('title', '')[:50]}")
        except Exception as e:
            print(f"  Error inserting: {e}")
    
    return inserted

def cleanup_old_events():
    cutoff_time = (datetime.now() - timedelta(days=2)).isoformat()
    result = supabase.table('events').delete().lt('event_time', cutoff_time).execute()
    if result.data:
        print(f"  🧹 Cleaned up {len(result.data)} old events")

if __name__ == "__main__":
    print("\n🌍 LIVE ETL STARTING (with Tsunami detection)")
    print("=" * 60)
    print("Checking for earthquakes and generating tsunamis when applicable...\n")
    
    existing = supabase.table('events').select('event_type, latitude, longitude, event_time').execute()
    for e in existing.data:
        seen_events.add(get_event_hash(e))
    
    last_nasa_fetch = datetime.now() - timedelta(hours=1)
    last_cleanup = datetime.now()
    
    try:
        while True:
            now = datetime.now()
            
            # Fetch earthquakes every 30 seconds
            earthquakes = fetch_earthquakes(now - timedelta(minutes=5))
            inserted = insert_new_events(earthquakes)
            
            if inserted > 0:
                print(f"  ✅ {inserted} new events (earthquakes + tsunamis)")
            
            # Fetch NASA events every hour
            if now - last_nasa_fetch >= timedelta(hours=1):
                nasa_events = fetch_nasa_events()
                insert_new_events(nasa_events)
                last_nasa_fetch = now
            
            # Cleanup old events every 6 hours
            if now - last_cleanup >= timedelta(hours=6):
                cleanup_old_events()
                last_cleanup = now
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\n✅ Live ETL stopped.")
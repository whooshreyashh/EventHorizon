import requests
from supabase import create_client, Client
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Missing Supabase credentials")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_earthquakes():
    """Fetch earthquakes from USGS API (last 24 hours, magnitude > 2.5)"""
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
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
        
        events.append({
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
        })
    
    print(f"  📊 Earthquakes: {len(events)}")
    return events

def fetch_nasa_events():
    """Fetch wildfires, volcanoes, floods from NASA EONET"""
    url = "https://eonet.gsfc.nasa.gov/api/v3/events"
    params = {"status": "open", "limit": 100}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    events = []
    for item in data.get('events', []):
        title = item.get('title', '')
        categories = [c.get('title', '').lower() for c in item.get('categories', [])]
        
        # Determine event type and severity
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
            continue  # Skip uncategorized
        
        # Get coordinates
        geometries = item.get('geometry', [])
        if not geometries:
            continue
        
        coords = geometries[0].get('coordinates', [])
        if len(coords) >= 2:
            lat = coords[1]
            lon = coords[0]
        else:
            continue
        
        event_time = geometries[0].get('date', datetime.now().isoformat())
        
        events.append({
            "title": title[:200],
            "event_type": event_type,
            "source": "NASA",
            "category": "natural",
            "severity": severity,
            "latitude": lat,
            "longitude": lon,
            "magnitude": None,
            "event_time": event_time,
            "external_url": item.get('link', '')
        })
    
    print(f"  🔥 NASA Events: {len(events)}")
    return events

def fetch_weather_alerts():
    """Fetch severe weather alerts from Open-Meteo"""
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
    
    print(f"  🌪️ Weather Alerts: {len(events)}")
    return events

def insert_events(events):
    """Insert events into Supabase, avoiding duplicates"""
    if not events:
        return 0
    
    # Delete events older than 2 days
    cutoff_time = (datetime.now() - timedelta(days=2)).isoformat()
    supabase.table('events').delete().lt('event_time', cutoff_time).execute()
    
    inserted = 0
    for event in events:
        try:
            # Check for duplicate in last 6 hours (same type and location)
            existing = supabase.table('events')\
                .select('id')\
                .eq('event_type', event['event_type'])\
                .eq('latitude', event['latitude'])\
                .eq('longitude', event['longitude'])\
                .gte('event_time', (datetime.now() - timedelta(hours=6)).isoformat())\
                .execute()
            
            if not existing.data:
                supabase.table('events').insert(event).execute()
                inserted += 1
        except Exception as e:
            print(f"  Error inserting: {e}")
    
    print(f"  ✅ Inserted {inserted} new events")
    return inserted

if __name__ == "__main__":
    print(f"\n🌍 FETCHING EVENTS at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    all_events = []
    
    print("1. Fetching earthquakes...")
    all_events.extend(fetch_earthquakes())
    
    print("2. Fetching NASA events...")
    all_events.extend(fetch_nasa_events())
    
    print("3. Fetching weather alerts...")
    all_events.extend(fetch_weather_alerts())
    
    print("-" * 50)
    print(f"Total events fetched: {len(all_events)}")
    
    inserted = insert_events(all_events)
    print(f"✅ ETL Complete. {inserted} new events added.\n")
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
    """Simple ocean check for tsunami generation"""
    if -60 < lat < 60:
        if (lon > -180 and lon < -30) or (lon > 20 and lon < 150) or (lon > 150 and lon < 180):
            return True
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
        since_time = datetime.now(timezone.utc) - timedelta(hours=6)
    
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": since_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "minmagnitude": 2.5,
        "orderby": "time",
        "limit": 100
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
    """Fetch NASA events - last 7 days (not just 1 hour)"""
    url = "https://eonet.gsfc.nasa.gov/api/v3/events"
    params = {"status": "open", "limit": 100}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    events = []
    # Look back 7 days instead of 1 hour
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
    
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
        
        event_time = geometries[0].get('date', datetime.now(timezone.utc).isoformat())
        
        # Handle timezone
        if event_time.endswith('Z'):
            event_time = event_time.replace('Z', '+00:00')
        event_dt = datetime.fromisoformat(event_time)
        
        # Include events from last 7 days
        if event_dt < cutoff_time:
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
    
    print(f"  🔥 NASA Events (last 7 days): {len(events)}")
    return events

def fetch_weather_alerts():
    """Fetch severe weather alerts from Open-Meteo with enhanced detection"""
    
    # Expanded list of storm-prone locations
    locations = [
        # North America
        {"name": "Miami, FL", "lat": 25.7617, "lon": -80.1918},
        {"name": "Houston, TX", "lat": 29.7604, "lon": -95.3698},
        {"name": "New Orleans, LA", "lat": 29.9511, "lon": -90.0715},
        {"name": "Charleston, SC", "lat": 32.7765, "lon": -79.9311},
        {"name": "Norfolk, VA", "lat": 36.8508, "lon": -76.2859},
        {"name": "San Francisco, CA", "lat": 37.7749, "lon": -122.4194},
        {"name": "Seattle, WA", "lat": 47.6062, "lon": -122.3321},
        {"name": "Chicago, IL", "lat": 41.8781, "lon": -87.6298},
        
        # Caribbean & Central America
        {"name": "San Juan, PR", "lat": 18.4663, "lon": -66.1057},
        {"name": "Nassau, Bahamas", "lat": 25.0443, "lon": -77.3504},
        {"name": "Cancun, Mexico", "lat": 21.1619, "lon": -86.8515},
        
        # Europe
        {"name": "London, UK", "lat": 51.5074, "lon": -0.1278},
        {"name": "Dublin, Ireland", "lat": 53.3498, "lon": -6.2603},
        {"name": "Bordeaux, France", "lat": 44.8378, "lon": -0.5792},
        {"name": "Hamburg, Germany", "lat": 53.5511, "lon": 9.9937},
        
        # Asia
        {"name": "Tokyo, Japan", "lat": 35.6762, "lon": 139.6503},
        {"name": "Shanghai, China", "lat": 31.2304, "lon": 121.4737},
        {"name": "Hong Kong", "lat": 22.3193, "lon": 114.1694},
        {"name": "Manila, Philippines", "lat": 14.5995, "lon": 120.9842},
        {"name": "Mumbai, India", "lat": 19.0760, "lon": 72.8777},
        
        # Pacific
        {"name": "Honolulu, HI", "lat": 21.3069, "lon": -157.8583},
        {"name": "Suva, Fiji", "lat": -18.1416, "lon": 178.4419},
        {"name": "Auckland, NZ", "lat": -36.8485, "lon": 174.7633},
        
        # Australia
        {"name": "Sydney, Australia", "lat": -33.8688, "lon": 151.2093},
        {"name": "Brisbane, Australia", "lat": -27.4698, "lon": 153.0251},
    ]
    
    events = []
    
    # Weather code meanings for Open-Meteo
    # https://open-meteo.com/en/docs
    severe_codes = {
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Severe thunderstorm"
    }
    
    for loc in locations:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": loc["lat"],
            "longitude": loc["lon"],
            "current_weather": True,
            "hourly": "windspeed_10m",
            "timezone": "auto"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            weather = data.get('current_weather', {})
            windspeed = weather.get('windspeed', 0)
            weather_code = weather.get('weathercode', 0)
            
            is_severe = False
            alert_title = None
            severity = "medium"
            
            # Check for severe weather codes
            if weather_code in severe_codes:
                is_severe = True
                alert_title = f"{severe_codes[weather_code]} detected - {loc['name']}"
                severity = "high"
            
            # Check for high winds (lowered threshold to 40 km/h)
            elif windspeed > 40:
                is_severe = True
                wind_class = "Strong" if windspeed > 50 else "Moderate"
                alert_title = f"{wind_class} winds ({windspeed} km/h) - {loc['name']}"
                severity = "high" if windspeed > 60 else "medium"
            
            if is_severe and alert_title:
                events.append({
                    "title": alert_title,
                    "event_type": "storm",
                    "source": "Open-Meteo",
                    "category": "weather",
                    "severity": severity,
                    "latitude": loc["lat"],
                    "longitude": loc["lon"],
                    "magnitude": windspeed if windspeed > 0 else None,
                    "event_time": datetime.now(timezone.utc).isoformat(),
                    "external_url": f"https://open-meteo.com/en/location/{loc['lat']}/{loc['lon']}"
                })
                
        except Exception as e:
            print(f"  ⚠️ Weather fetch failed for {loc['name']}: {e}")
    
    # If no real-time alerts found, add sample recent historical alerts for demo
    if len(events) == 0:
        print("  ℹ️ No active storms detected. Adding sample historical alerts for demonstration.")
        
        # Sample historical storms (real events from past year)
        sample_storms = [
            {"name": "Hurricane Milton (Florida, Oct 2024)", "lat": 27.0, "lon": -82.0, "severity": "high", "wind": 195},
            {"name": "Typhoon Krathon (Taiwan, Oct 2024)", "lat": 22.5, "lon": 120.5, "severity": "high", "wind": 175},
            {"name": "Storm Boris (Central Europe, Sep 2024)", "lat": 50.0, "lon": 15.0, "severity": "medium", "wind": 85},
            {"name": "Cyclone Remal (Bay of Bengal, May 2024)", "lat": 21.0, "lon": 89.0, "severity": "high", "wind": 110},
        ]
        
        for storm in sample_storms:
            events.append({
                "title": storm["name"],
                "event_type": "storm",
                "source": "Historical",
                "category": "weather",
                "severity": storm["severity"],
                "latitude": storm["lat"],
                "longitude": storm["lon"],
                "magnitude": storm["wind"],
                "event_time": (datetime.now(timezone.utc) - timedelta(days=180)).isoformat(),
                "external_url": ""
            })
    
    print(f"  🌪️ Weather Alerts: {len(events)}")
    return events

def insert_new_events(events):
    """Insert only new events not seen before"""
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
            print(f"  ✅ Inserted: {event.get('event_type')} - {event.get('title', '')[:50]}")
        except Exception as e:
            print(f"  ❌ Error inserting: {e}")
    
    return inserted

def cleanup_old_events():
    """Delete events older than 2 days"""
    cutoff_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    result = supabase.table('events').delete().lt('event_time', cutoff_time).execute()
    if result.data:
        print(f"  🧹 Cleaned up {len(result.data)} old events")

if __name__ == "__main__":
    print("\n🌍 LIVE ETL STARTING (with Tsunami detection)")
    print("=" * 60)
    print("Fetching earthquakes, NASA events, and weather alerts...\n")
    
    # Load existing event hashes
    existing = supabase.table('events').select('event_type, latitude, longitude, event_time').execute()
    for e in existing.data:
        seen_events.add(get_event_hash(e))
    
    last_nasa_fetch = datetime.now(timezone.utc) - timedelta(hours=1)
    last_weather_fetch = datetime.now(timezone.utc) - timedelta(minutes=30)
    last_cleanup = datetime.now(timezone.utc)
    
    try:
        while True:
            now = datetime.now(timezone.utc)
            
            # Fetch earthquakes every 30 seconds
            earthquakes = fetch_earthquakes(now - timedelta(minutes=5))
            inserted = insert_new_events(earthquakes)
            
            if inserted > 0:
                print(f"  📊 {inserted} new earthquake/tsunami events")
            
            # Fetch NASA events every hour
            if now - last_nasa_fetch >= timedelta(hours=1):
                print("\n  📡 Checking NASA...")
                nasa_events = fetch_nasa_events()
                insert_new_events(nasa_events)
                last_nasa_fetch = now
            
            # Fetch weather alerts every 30 minutes
            if now - last_weather_fetch >= timedelta(minutes=30):
                print("\n  📡 Checking weather...")
                weather_events = fetch_weather_alerts()
                insert_new_events(weather_events)
                last_weather_fetch = now
            
            # Cleanup old events every 6 hours
            if now - last_cleanup >= timedelta(hours=6):
                cleanup_old_events()
                last_cleanup = now
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\n✅ Live ETL stopped.")
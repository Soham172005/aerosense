import requests
from django.core.management.base import BaseCommand
from aqi_app.models import City, Station, AQIReading
from datetime import datetime
import pytz

WAQI_TOKEN = "37d9b44a6027c30946a2dbff7bf7facc25e91ff5"
INDIA_BOUNDS = [68.0, 8.0, 97.0, 37.0]  # minLon, minLat, maxLon, maxLat


# ------------------------------------------------------------
#  CLEAN CITY NAME (handles string or dict)
# ------------------------------------------------------------
def clean_city_name(raw):
    """
    Accepts raw which may be:
      - a string: "Delhi"
      - a dict: {"name": "Delhi", ...}
    Returns cleaned city name or None if invalid.
    """
    # handle dict case (WAQI sometimes returns dict)
    if isinstance(raw, dict):
        raw = raw.get("name") or raw.get("station") or ""

    # now raw should be string or falsy
    if not raw:
        return None

    if not isinstance(raw, str):
        raw = str(raw)

    city = raw.strip().replace(" ,", ",")
    city = city.split("(")[0].strip()
    # remove country codes words commonly appended
    city = city.replace("India", "").replace("IN", "").strip()

    # Remove obvious numeric garbage (e.g., codes)
    if any(char.isdigit() for char in city):
        # attempt a looser cleanup: keep parts without digits
        parts = [p.strip() for p in city.split(",") if p and not any(ch.isdigit() for ch in p)]
        if parts:
            city = parts[0]
        else:
            return None

    if len(city) < 2:
        return None

    return city.title()


# ------------------------------------------------------------
#  FETCH INDIA AQI FROM WAQI MAP API
# ------------------------------------------------------------
def fetch_india_aqi():
    print("Fetching India AQI from WAQI...")

    # WAQI expects latlng as minLat,minLng,maxLat,maxLng or similar; keep previous ordering
    url = (
        f"https://api.waqi.info/map/bounds/?"
        f"token={WAQI_TOKEN}&"
        f"latlng={INDIA_BOUNDS[1]},{INDIA_BOUNDS[0]},{INDIA_BOUNDS[3]},{INDIA_BOUNDS[2]}"
    )

    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok":
        print("WAQI API returned error:", data)
        return []

    results = data.get("data", [])
    clean_results = []

    for station in results:
        # station['station'] can be string OR dict
        raw_station = station.get("station")
        city_name = clean_city_name(raw_station)

        # as a fallback, WAQI sometimes includes top-level city field - try that
        if not city_name:
            top_city = station.get("city")  # sometimes present
            city_name = clean_city_name(top_city)

        if not city_name:
            continue

        # AQI validation
        aqi_raw = station.get("aqi")
        try:
            aqi_value = int(aqi_raw)
        except Exception:
            continue

        # ignore extremely low/junk values
        if aqi_value < 5:
            continue  # likely invalid station

        lat = station.get("lat")
        lon = station.get("lon")
        if lat is None or lon is None:
            continue

        clean_results.append({
            "city": city_name,
            "aqi": aqi_value,
            "lat": lat,
            "lon": lon,
            "timestamp": datetime.now(pytz.UTC),
            "raw": station,
        })

    return clean_results


# ------------------------------------------------------------
#  STORE INTO DATABASE
# ------------------------------------------------------------
def store_data(clean_data):
    created = 0
    updated = 0

    for entry in clean_data:
        city, _ = City.objects.get_or_create(
            name=entry["city"],
            defaults={"country": "India"}
        )

        # create a reasonably unique station code using city and lat/lon
        code = f"{entry['city'].replace(' ', '_')}_{round(entry['lat'], 3)}_{round(entry['lon'], 3)}"
        station, _ = Station.objects.get_or_create(
            code=code[:50],
            defaults={
                "city": city,
                "name": f"{city.name} Station",
                "latitude": entry["lat"],
                "longitude": entry["lon"],
                "data_source": "WAQI"
            }
        )

        obj, flag = AQIReading.objects.update_or_create(
            station=station,
            timestamp=entry["timestamp"],
            defaults={
                "city": city,
                "aqi": entry["aqi"],
                "pm25": None,
                "pm10": None,
                "no2": None,
                "so2": None,
                "o3": None,
                "co": None,
                "nh3": None,
                "raw_data": entry["raw"]
            }
        )

        if flag:
            created += 1
        else:
            updated += 1

    return created, updated


# ------------------------------------------------------------
#  DJANGO COMMAND
# ------------------------------------------------------------
class Command(BaseCommand):
    help = "Fetches live AQI for India from WAQI and stores clean results."

    def handle(self, *args, **options):

        data = fetch_india_aqi()
        if not data:
            print("No valid AQI data received.")
            return

        created, updated = store_data(data)
        print(f"Done! Created: {created}, Updated: {updated}")

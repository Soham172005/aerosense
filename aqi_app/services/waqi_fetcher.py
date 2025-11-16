import requests
from django.utils import timezone

WAQI_TOKEN = "37d9b44a6027c30946a2dbff7bf7facc25e91ff5"

BOUNDS_URL = (
    f"https://api.waqi.info/map/bounds/"
    f"?token={WAQI_TOKEN}&latlng=6,68,36,97"
)


def fetch_all_india_wAQI():
    """
    Fetch AQI for entire India using WAQI bounding box API.
    Returns list of station dictionaries.
    """
    resp = requests.get(BOUNDS_URL, timeout=30)
    resp.raise_for_status()

    data = resp.json()

    if data.get("status") != "ok":
        raise Exception(f"WAQI Error: {data}")

    stations = data.get("data", [])

    final = []
    now = timezone.now()

    for st in stations:

        station_raw = st.get("station")
        city_raw = st.get("city")

        # Station may be dict or string
        if isinstance(station_raw, dict):
            station_name = station_raw.get("name", "Unknown Station")
        else:
            station_name = station_raw or "Unknown Station"

        # City may be dict or string
        if isinstance(city_raw, dict):
            city_name = city_raw.get("name", "Unknown City")
        else:
            city_name = city_raw or "Unknown City"

        # AQI may be "-" or number → convert to int or None
        raw_aqi = st.get("aqi")
        try:
            aqi_value = int(raw_aqi)
        except:
            aqi_value = None

        final.append({
            "aqi": aqi_value,
            "lat": st.get("lat"),
            "lon": st.get("lon"),
            "station_name": station_name,
            "city": city_name,
            "time": now,
            "raw": st,
        })




    return final

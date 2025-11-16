import requests
from datetime import datetime
from django.utils import timezone

API_URL = "https://api.openaq.org/v3/latest?country=IN&limit=1000"

# -------------------------
# AQI Calculation (EPA PM2.5/PM10)
# -------------------------
PM25_BREAKPOINTS = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]

PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 504, 301, 400),
    (505, 604, 401, 500),
]


def _linear(C, Clow, Chigh, Ilow, Ihigh):
    return int(round(((Ihigh - Ilow) / (Chigh - Clow)) * (C - Clow) + Ilow))


def compute_aqi(C, breakpoints):
    if C is None:
        return None
    C = float(C)
    for Clow, Chigh, Ilow, Ihigh in breakpoints:
        if Clow <= C <= Chigh:
            return _linear(C, Clow, Chigh, Ilow, Ihigh)
    return None


def compute_overall_aqi(pm25, pm10):
    aqi_pm25 = compute_aqi(pm25, PM25_BREAKPOINTS)
    aqi_pm10 = compute_aqi(pm10, PM10_BREAKPOINTS)

    values = [v for v in [aqi_pm25, aqi_pm10] if v is not None]
    return max(values) if values else None


# -------------------------
# Fetcher
# -------------------------
def fetch_openaq_v3():
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def collect_and_prepare_readings():
    data = fetch_openaq_v3()
    results = data.get("results", [])

    final = []
    now = timezone.now()

    for item in results:
        city = item.get("city") or "Unknown"
        location = item.get("location") or "Unknown"

        coordinates = item.get("coordinates", {})
        lat = coordinates.get("latitude")
        lon = coordinates.get("longitude")

        # Collect pollutants
        pm25 = None
        pm10 = None
        values_dict = {}

        for m in item.get("measurements", []):
            param = m.get("parameter")
            value = m.get("value")
            if param == "pm25":
                pm25 = value
            if param == "pm10":
                pm10 = value
            values_dict[param] = value

        # compute AQI
        overall_aqi = compute_overall_aqi(pm25, pm10)

        final.append({
            "city": city,
            "location": location,
            "lat": lat,
            "lon": lon,
            "aqi": overall_aqi,
            "measurements": values_dict,
            "timestamp": now,
            "raw": item,
        })

    return final

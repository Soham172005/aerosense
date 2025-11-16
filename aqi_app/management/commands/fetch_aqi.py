from django.core.management.base import BaseCommand
from django.utils import timezone
from aqi_app.services.live_aqi_fetcher import collect_and_prepare_readings
from aqi_app.models import City, Station, AQIReading


class Command(BaseCommand):
    help = "Fetch AQI data from OpenAQ v3"

    def handle(self, *args, **options):
        self.stdout.write("Fetching AQI from OpenAQ v3...")

        try:
            records = collect_and_prepare_readings()
        except Exception as e:
            self.stderr.write(f"Fetch failed: {e}")
            return

        created, updated = 0, 0

        for r in records:
            city, _ = City.objects.get_or_create(
                name=r["city"],
                defaults={"latitude": r["lat"], "longitude": r["lon"]},
            )

            station_code = r["location"].replace(" ", "_")[:50]

            station, _ = Station.objects.get_or_create(
                code=station_code,
                defaults={
                    "city": city,
                    "name": r["location"],
                    "latitude": r["lat"],
                    "longitude": r["lon"],
                    "data_source": "OpenAQ",
                },
            )

            obj, flag = AQIReading.objects.update_or_create(
                station=station,
                timestamp=r["timestamp"],
                defaults={
                    "city": city,
                    "aqi": r["aqi"],
                    "pm25": r["measurements"].get("pm25"),
                    "pm10": r["measurements"].get("pm10"),
                    "no2": r["measurements"].get("no2"),
                    "so2": r["measurements"].get("so2"),
                    "o3": r["measurements"].get("o3"),
                    "co": r["measurements"].get("co"),
                    "nh3": r["measurements"].get("nh3"),
                    "raw_data": r["raw"],
                }
            )

            if flag:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done! Created: {created}, Updated: {updated}"
        ))

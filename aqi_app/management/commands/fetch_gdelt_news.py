# aqi_app/management/commands/fetch_gdelt_news.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.cache import cache
from aqi_app.utils.gdelt import fetch_gdelt_articles
from aqi_app.models import NewsArticle
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Fetch latest GDELT environmental articles and store in NewsArticle model (dedup by url)."

    def add_arguments(self, parser):
        parser.add_argument("--query", type=str, default=None, help="GDELT query string")
        parser.add_argument("--max", type=int, default=50, help="Max number of articles to fetch")

    def handle(self, *args, **options):
        query = options.get("query") or ("air pollution OR air quality OR wildfire OR smoke OR environment")
        max_items = options.get("max") or 50

        self.stdout.write(f"Fetching GDELT articles (query={query}) ...")
        articles = fetch_gdelt_articles(query="(air pollution OR air quality OR wildfire OR smoke OR environment)",max_items=50)
        saved = 0
        updated = 0

        for a in articles:
            url = a.get("url")
            if not url:
                continue

            # dedupe by unique URL
            obj, created = NewsArticle.objects.get_or_create(
                url=url,
                defaults={
                    "title": a.get("title", "")[:512],
                    "summary": a.get("summary", ""),
                    "source": a.get("source", "")[:256],
                    "published_at": a.get("published_at") or timezone.now(),
                }
            )
            if not created:
                # optionally update metadata if changed
                updated_fields = []
                if a.get("title") and obj.title != a.get("title")[:512]:
                    obj.title = a.get("title")[:512]; updated_fields.append("title")
                if a.get("summary") and obj.summary != a.get("summary"):
                    obj.summary = a.get("summary"); updated_fields.append("summary")
                if a.get("source") and obj.source != a.get("source")[:256]:
                    obj.source = a.get("source")[:256]; updated_fields.append("source")
                if updated_fields:
                    obj.save(update_fields=updated_fields)
                    updated += 1
            else:
                saved += 1

        # Refresh cache (simple approach)
        latest = list(NewsArticle.objects.all().order_by("-published_at")[:100])
        cache.set("gdelt_news", latest, 60 * 15)  # cache 15 minutes

        self.stdout.write(self.style.SUCCESS(f"Done. saved={saved}, updated={updated}, cached={len(latest)}"))

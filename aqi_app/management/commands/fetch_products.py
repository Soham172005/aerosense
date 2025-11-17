from django.core.management.base import BaseCommand
from django.utils import timezone
from aqi_app.models import Product
from aqi_app.services.product_fetcher import ProductFetcher
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch air quality products from SerpAPI and populate database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            type=str,
            help="Fetch only specific category (mask/purifier/room_purifier/monitor/car-filter/plant)",
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Update existing products (prices, ratings, etc.)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing products before fetching",
        )
        parser.add_argument(
            "--max-per-query",
            type=int,
            default=10,
            help="Maximum products per search query (default: 10)",
        )

    def handle(self, *args, **options):
        category = options.get("category")
        refresh = options.get("refresh")
        clear = options.get("clear")
        max_per_query = options.get("max_per_query")

        self.stdout.write(self.style.SUCCESS("=== Product Fetcher Started ==="))

        # Clear existing products if requested
        if clear:
            count = Product.objects.count()
            Product.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Cleared {count} existing products")
            )

        # Initialize fetcher
        fetcher = ProductFetcher()

        # Define AQI ranges for each product type
        aqi_ranges = {
            "mask": (50, 300),
            "purifier": (100, 500),
            "room_purifier": (50, 500),
            "monitor": (0, 500),
            "car-filter": (100, 300),
            "plant": (0, 150),
        }

        # Define effectiveness ratings by type
        effectiveness_by_type = {
            "mask": 85,
            "purifier": 95,
            "room_purifier": 90,
            "monitor": 70,
            "car-filter": 80,
            "plant": 60,
        }

        # Fetch products
        if category:
            # Single category
            self.stdout.write(f"Fetching products for category: {category}")
            all_products = {category: []}
            
            queries = self._get_queries_for_category(category)
            for query in queries:
                products = fetcher.fetch_products(query, max_results=max_per_query)
                all_products[category].extend(products)
        else:
            # All categories
            self.stdout.write("Fetching products for all categories...")
            all_products = fetcher.fetch_all_categories()

        # Process and save products
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for product_type, products in all_products.items():
            self.stdout.write(
                self.style.HTTP_INFO(
                    f"\nProcessing {len(products)} products for '{product_type}'..."
                )
            )

            aqi_min, aqi_max = aqi_ranges.get(product_type, (0, 500))
            default_effectiveness = effectiveness_by_type.get(product_type, 75)

            for item in products:
                try:
                    # Skip if no name or price
                    if not item.get("name") or not item.get("price"):
                        skipped_count += 1
                        continue

                    # Check if product already exists (by name)
                    existing = Product.objects.filter(
                        name__iexact=item["name"]
                    ).first()

                    if existing and not refresh:
                        skipped_count += 1
                        continue

                    # Prepare product data
                    product_data = {
                        "name": item["name"][:256],
                        "product_type": product_type,
                        "description": item.get("description", "")[:500],
                        "price": item.get("price", 0),
                        "image_url": item.get("image_url", ""),
                        "product_url": item.get("product_url", ""),
                        "aqi_min": aqi_min,
                        "aqi_max": aqi_max,
                        "effectiveness": self._calculate_effectiveness(
                            item, default_effectiveness
                        ),
                        "rating": item.get("rating", 0),
                        "reviews": item.get("reviews", 0),
                        "features": self._extract_features(item),
                        "recommended_for": self._get_recommended_for(
                            product_type, aqi_min, aqi_max
                        ),
                    }

                    if existing:
                        # Update existing product
                        for key, value in product_data.items():
                            setattr(existing, key, value)
                        existing.updated_at = timezone.now()
                        existing.save()
                        updated_count += 1
                        self.stdout.write(f"  ✓ Updated: {item['name'][:50]}")
                    else:
                        # Create new product
                        Product.objects.create(**product_data)
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✓ Created: {item['name'][:50]}")
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ Error processing {item.get('name', 'Unknown')}: {e}"
                        )
                    )
                    continue

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("=== Fetch Complete ==="))
        self.stdout.write(f"Created: {created_count}")
        self.stdout.write(f"Updated: {updated_count}")
        self.stdout.write(f"Skipped: {skipped_count}")
        self.stdout.write(f"Total in DB: {Product.objects.count()}")
        self.stdout.write("=" * 50)

    def _get_queries_for_category(self, category: str):
        """Get search queries for a specific category."""
        queries_map = {
            "mask": [
                "n95 mask india",
                "n99 anti pollution mask india",
                "reusable pollution mask india",
            ],
            "purifier": [
                "air purifier india hepa",
                "best air purifier india 2024",
                "air purifier under 20000",
            ],
            "room_purifier": [
                "room air purifier india",
                "bedroom air purifier best",
                "portable air purifier india",
            ],
            "monitor": [
                "air quality monitor india pm2.5",
                "aqi meter india",
                "indoor air quality monitor",
            ],
            "car-filter": [
                "car air purifier india best",
                "vehicle cabin air filter",
                "car ionizer air purifier",
            ],
            "plant": [
                "air purifying indoor plants india",
                "snake plant india online",
                "money plant for home india",
            ],
        }
        return queries_map.get(category, [])

    def _calculate_effectiveness(self, item: dict, default: int) -> int:
        """
        Calculate product effectiveness based on available data.
        Higher rating/reviews = higher effectiveness.
        """
        base = default
        rating = item.get("rating", 0)
        reviews = item.get("reviews", 0)

        # Boost for high ratings
        if rating >= 4.5:
            base += 5
        elif rating >= 4.0:
            base += 3

        # Boost for many reviews (social proof)
        if reviews >= 5000:
            base += 5
        elif reviews >= 1000:
            base += 3

        # Cap at 100
        return min(base, 100)

    def _extract_features(self, item: dict) -> list:
        """Extract product features from available data."""
        features = []

        # Add delivery info as feature
        delivery = item.get("delivery", "")
        if delivery:
            features.append(delivery)

        # Add source as feature
        source = item.get("source", "")
        if source:
            features.append(f"Available at {source}")

        # Add rating as feature if available
        rating = item.get("rating", 0)
        reviews = item.get("reviews", 0)
        if rating > 0:
            features.append(f"Rated {rating}/5")
        if reviews > 0:
            features.append(f"{reviews} reviews")

        return features[:5]  # Limit to 5 features

    def _get_recommended_for(self, product_type: str, aqi_min: int, aqi_max: int) -> list:
        """Get recommended use cases based on product type and AQI range."""
        recommendations = []

        # Type-specific recommendations
        type_recommendations = {
            "mask": ["Daily commute", "Outdoor activities", "Cycling"],
            "purifier": ["Bedrooms", "Living rooms", "Offices"],
            "room_purifier": ["Small rooms", "Bedrooms", "Study rooms"],
            "monitor": ["Home monitoring", "Office spaces", "Schools"],
            "car-filter": ["Daily commuters", "Long drives", "City traffic"],
            "plant": ["Home decor", "Natural purification", "Low pollution areas"],
        }

        recommendations.extend(type_recommendations.get(product_type, []))

        # AQI-specific recommendations
        if aqi_max >= 200:
            recommendations.append("High pollution areas")
        if aqi_min <= 50:
            recommendations.append("Preventive care")

        # Health-specific recommendations
        if product_type in ["mask", "purifier", "room_purifier"]:
            recommendations.extend(["Asthma patients", "Elderly", "Children"])

        return list(set(recommendations))[:5]  # Unique, max 5
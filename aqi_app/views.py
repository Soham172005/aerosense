from django.shortcuts import render
from aqi_app.models import AQIReading, City, Product
from django.shortcuts import render
from django.db.models import OuterRef, Subquery, Max
from aqi_app.models import AQIReading, Station
from django.utils.timezone import now
from aqi_app.utils.city_map import CITY_PATTERNS
from django.utils import timezone
import random
from datetime import datetime, timedelta
import json
import re
from aqi_app.models import NewsArticle
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Product
from .serializers import ProductSerializer
from rest_framework import viewsets
from rest_framework.response import Response
from django.shortcuts import render
from .models import Product, City, AQIReading
from .serializers import ProductSerializer
from aqi_app.utils.product_recommender import (
    get_recommendations, 
    get_recommendation_message,
    get_aqi_category
)

# ---------------- PRODUCT API ----------------
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


# ---------------- HTML PAGE ----------------
def products_page(request):
    cities = City.objects.all()
    selected_city = request.GET.get("city")

    aqi_value = None
    recommendations = []

    if selected_city:
        latest = AQIReading.objects.filter(city_id=selected_city).order_by("-timestamp").first()

        if latest:
            aqi_value = latest.aqi

            recommendations = Product.objects.filter(
                aqi_min__lte=aqi_value,
                aqi_max__gte=aqi_value
            ).order_by("-effectiveness")

    return render(request, "products.html", {
        "cities": cities,
        "aqi_value": aqi_value,
        "recommendations": recommendations
    })

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


@api_view(['GET'])
def product_recommendations(request):
    aqi = int(request.GET.get("aqi", 0))

    # basic filtering logic
    recommended = []
    products = Product.objects.all()

    for p in products:
        # aqiRange = "100-200" OR "150+"
        if "+" in p.aqiRange:
            if aqi >= int(p.aqiRange.replace("+", "")):
                recommended.append(p)
        elif "-" in p.aqiRange:
            low, high = map(int, p.aqiRange.split("-"))
            if low <= aqi <= high:
                recommended.append(p)
        else:
            recommended.append(p)

    serializer = ProductSerializer(recommended, many=True)
    return Response(serializer.data)

def categorize_news(article):
    text = f"{article.title} {article.summary}".lower()

    categories = {
        "breaking": ["breaking", "alert", "warning", "emergency", "wildfire", "smoke", "fire", "disaster"],
        "research": ["study", "report", "analysis", "research", "scientist", "university"],
        "policy": ["government", "policy", "regulation", "bill", "law", "environmental agency"],
        "health": ["health", "respiratory", "asthma", "disease", "hospital", "impact"],
        "technology": ["technology", "ai", "sensor", "innovation", "data", "machine learning"],
    }

    for cat, keywords in categories.items():
        if any(k in text for k in keywords):
            return cat

    return "general"


def news_view(request):
    search = request.GET.get("search", "").strip().lower()
    category = request.GET.get("category", "all")
    articles = NewsArticle.objects.all().order_by('-published_at')

# categorize dynamically
    for a in articles:
        a.category = categorize_news(a)

    # FILTER
    if category != "all":
        articles = [a for a in articles if a.category == category]


    # Base queryset
    qs = NewsArticle.objects.all()

    # Apply search filter
    if search:
        qs = qs.filter(
            title__icontains=search
        ) | qs.filter(summary__icontains=search)

    # Apply category filter (breaking, research, policy, health, technology)
    if category != "all":
        qs = qs.filter(source__icontains=category)

    qs = qs.order_by("-published_at")[:100]  # last 100 articles

    return render(request, "aqi_app/news.html", {
        "articles": qs,
        "search": search,
        "category": category,
    })

def home_view(request):
    """Homepage UI with hero section + features + live AQI list."""

    # pick first 6 cities for homepage display
    cities = City.objects.all()[:6]

    aqi_data = []
    for c in cities:
        latest = AQIReading.objects.filter(city=c).order_by("-timestamp").first()
        if latest:
            aqi_data.append({
                "city": c,
                "aqi": latest.aqi,
                "primary_pollutant": "PM2.5",
                "category": get_aqi_category(latest.aqi),
                "updated": latest.timestamp,
            })

    return render(request, "aqi_app/home_vibe.html", {"aqi_data": aqi_data})

def _clean_city_name(name: str) -> str:
    if not name:
        return name
    # replace multiple commas/spaces with single comma + trim leading/trailing spaces/commas
    s = re.sub(r',\s*,+', ',', name)           # collapse consecutive commas
    s = re.sub(r'\s*,\s*', ', ', s).strip()     # normalize spacing around commas
    s = s.strip(', ')                            # remove leading/trailing commas/spaces

def live_monitoring_view(request):

    # 1. Get ALL known cities (sorted)
    known_cities = list(City.objects.all().order_by("name"))

    # 2. Select first 9 (most popular / most available)
    popular_cities = known_cities[:9]

    # 3. Fetch latest AQI reading for each city
    live_data = []

    for city in popular_cities:
        reading = AQIReading.objects.filter(city=city).order_by("-timestamp").first()

        if reading:
            # Determine AQI category
            aqi = reading.aqi or 0

            if aqi <= 50:
                label = "Good"
            elif aqi <= 100:
                label = "Moderate"
            elif aqi <= 150:
                label = "Unhealthy for Sensitive Groups"
            elif aqi <= 200:
                label = "Unhealthy"
            elif aqi <= 300:
                label = "Very Unhealthy"
            else:
                label = "Hazardous"

            live_data.append({
                "city": city.name,
                "aqi": aqi,
                "primary_pollutant": reading.pm25 or reading.pm10 or "PM2.5",
                "category": label,
                "timestamp": reading.timestamp,
            })

    context = {
        "live_data": live_data,
        "last_refresh": timezone.now(),
    }

    return render(request, "aqi_app/live_monitoring.html", context)

from django.shortcuts import render
from .models import City, AQIReading


def get_aqi_category(aqi):
    if aqi is None:
        return "Unknown"
    if aqi <= 50: return "Good"
    if aqi <= 100: return "Moderate"
    if aqi <= 150: return "Unhealthy for Sensitive Groups"
    if aqi <= 200: return "Unhealthy"
    if aqi <= 300: return "Very Unhealthy"
    return "Hazardous"



def get_latest_aqi(city):
    """Return latest AQI reading for that city."""
    return AQIReading.objects.filter(city=city).order_by("-timestamp").first()


def generate_forecast(aqi):
    """Generate artificial 24-hour forecast ±10 variation."""
    forecast = []
    for i in range(1, 25):
        variation = random.randint(-12, 12)
        value = max(0, min(500, aqi + variation))

        forecast.append({
            "hour": f"{i:02d}:00",
            "aqi": value,
            "label": get_aqi_status(value),
            "color": get_aqi_color(value),
        })

    return forecast


def get_aqi_status(aqi):
    if aqi <= 50: return "Good"
    if aqi <= 100: return "Moderate"
    if aqi <= 150: return "Unhealthy for Sensitive Groups"
    if aqi <= 200: return "Unhealthy"
    if aqi <= 300: return "Very Unhealthy"
    return "Hazardous"


def get_aqi_color(aqi):
    if aqi <= 50: return "aqi-good"
    if aqi <= 100: return "aqi-moderate"
    if aqi <= 150: return "aqi-sensitive"
    if aqi <= 200: return "aqi-unhealthy"
    if aqi <= 300: return "aqi-very-unhealthy"
    return "aqi-hazardous"


def forecasting_view(request):

    # all known cities
    known_cities = list(City.objects.values_list("name", flat=True))

    selected_city = request.GET.get("city")

    selected_data = None
    latest_aqi = None
    forecast = None

    # Validate only known cities
    if selected_city in known_cities:
        city_obj = City.objects.get(name=selected_city)
        latest_aqi = get_latest_aqi(city_obj)

        if latest_aqi:
            forecast = generate_forecast(latest_aqi.aqi)

            selected_data = {
                "city": selected_city,
                "aqi": latest_aqi.aqi,
                "timestamp": latest_aqi.timestamp,
            }

    context = {
        "known_cities_json": json.dumps(known_cities),
        "selected_city": selected_city,
        "selected_data": selected_data,
        "forecast": forecast,
    }

    return render(request, "aqi_app/forecasting.html", context)


def trends_view(request):
    """
    Basic Trends view that loads all known cities.
    You can later replace with real historical AQI logic.
    """
    cities = City.objects.all().order_by("name")

    context = {
        "cities": cities,
    }
    return render(request, "aqi_app/trends.html", context)


def products_page(request):
    """
    Smart Product Recommender page.
    Shows products based on selected city's AQI level.
    """
    
    # Get all cities for dropdown (sorted alphabetically)
    cities = City.objects.all().order_by('name')
    
    # Get selected city from query parameter
    selected_city_name = request.GET.get('city')
    selected_city = None
    current_aqi = None
    aqi_info = None
    recommended_products = []
    all_products = []
    
    if selected_city_name:
        try:
            # Get city object
            selected_city = City.objects.get(name=selected_city_name)
            
            # Get latest AQI reading for this city
            latest_reading = AQIReading.objects.filter(
                city=selected_city
            ).order_by('-timestamp').first()
            
            if latest_reading and latest_reading.aqi:
                current_aqi = latest_reading.aqi
                
                # Get AQI category and recommendation message
                aqi_info = get_recommendation_message(current_aqi)
                aqi_info['value'] = current_aqi
                aqi_info['category_key'] = get_aqi_category(current_aqi)
                aqi_info['timestamp'] = latest_reading.timestamp
                
                # Get recommended products based on AQI
                recommended_products = get_recommendations(
                    aqi=current_aqi,
                    max_results=50
                )
                
        except City.DoesNotExist:
            pass
    
    # Get all products for category filtering (even if no city selected)
    all_products = Product.objects.all().order_by('-effectiveness', '-rating')
    
    # Count products by category
    product_counts = {
        'all': all_products.count(),
        'mask': all_products.filter(product_type='mask').count(),
        'purifier': all_products.filter(product_type='purifier').count(),
        'room_purifier': all_products.filter(product_type='room_purifier').count(),
        'monitor': all_products.filter(product_type='monitor').count(),
        'car_filter': all_products.filter(product_type='car-filter').count(),  # ✅ Fixed
        'plant': all_products.filter(product_type='plant').count(),
    }
    
    context = {
        'cities': cities,
        'selected_city': selected_city,
        'current_aqi': current_aqi,
        'aqi_info': aqi_info,
        'recommended_products': recommended_products,
        'all_products': all_products,
        'product_counts': product_counts,
    }
    
    return render(request, 'aqi_app/products.html', context)

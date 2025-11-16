from django.db import models
from django.contrib.auth.models import User


# ----------------------------------------------------------
# 1. CITY MODEL
# ----------------------------------------------------------
class City(models.Model):
    name = models.CharField(max_length=128, db_index=True)
    state = models.CharField(max_length=128, blank=True, null=True)
    country = models.CharField(max_length=128, default="India")
    
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    population = models.IntegerField(null=True, blank=True)     # optional analytics
    station_count = models.IntegerField(default=1)               # number of AQI stations
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["state"]),
        ]

    def __str__(self):
        return self.name


# ----------------------------------------------------------
# 2. STATION MODEL (Each City Can Have Multiple AQI Stations)
# ----------------------------------------------------------
class Station(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="stations")

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=50, blank=True, null=True, unique=True)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    data_source = models.CharField(
        max_length=128,
        default="OpenAQ",
        help_text="API or dataset used to fetch data",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["city", "name"]

    def __str__(self):
        return f"{self.name} ({self.city.name})"


# ----------------------------------------------------------
# 3. AQI READING MODEL (Every 5–15 Minutes)
# ----------------------------------------------------------
class AQIReading(models.Model):
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="readings")
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="readings")

    timestamp = models.DateTimeField(db_index=True)

    aqi = models.IntegerField(null=True, blank=True)

    pm25 = models.FloatField(null=True, blank=True)
    pm10 = models.FloatField(null=True, blank=True)
    no2 = models.FloatField(null=True, blank=True)
    so2 = models.FloatField(null=True, blank=True)
    o3 = models.FloatField(null=True, blank=True)
    co = models.FloatField(null=True, blank=True)
    nh3 = models.FloatField(null=True, blank=True)

    raw_data = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ("station", "timestamp")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["aqi"]),
            models.Index(fields=["pm25"]),
        ]

    def __str__(self):
        return f"{self.city} @ {self.timestamp} — AQI: {self.aqi}"


# ----------------------------------------------------------
# 4. FORECAST MODEL (ML/DL Outputs)
# ----------------------------------------------------------
class Forecast(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="forecasts")
    
    timestamp = models.DateTimeField(db_index=True)     # prediction time
    target_time = models.DateTimeField(db_index=True)   # time for which prediction is valid

    predicted_aqi = models.FloatField()
    model_name = models.CharField(max_length=64)        # Prophet, LSTM, RF, SARIMA
    model_version = models.CharField(max_length=32, default="v1")

    confidence_low = models.FloatField(null=True, blank=True)
    confidence_high = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("city", "target_time", "model_name")
        ordering = ["target_time"]

    def __str__(self):
        return f"{self.city} → {self.target_time} : {self.predicted_aqi}"


# ----------------------------------------------------------
# 5. HEALTH ADVISORY BASED ON AQI BANDS
# ----------------------------------------------------------
class HealthBand(models.Model):
    """Static rules for health advisories: Good, Moderate, Poor, etc."""
    name = models.CharField(max_length=64)
    min_aqi = models.IntegerField()
    max_aqi = models.IntegerField()
    message = models.TextField()
    recommendations = models.TextField()

    class Meta:
        ordering = ["min_aqi"]

    def __str__(self):
        return f"{self.name} ({self.min_aqi}-{self.max_aqi})"


# ----------------------------------------------------------
# 6. PRODUCT RECOMMENDER MODEL
# ----------------------------------------------------------
class Product(models.Model):
    PRODUCT_TYPES = [
        ("mask", "Mask"),
        ("purifier", "Air Purifier"),
        ("health", "Health Supplement"),
    ]

    name = models.CharField(max_length=256)
    product_type = models.CharField(max_length=32, choices=PRODUCT_TYPES)
    price = models.FloatField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    product_url = models.URLField(null=True, blank=True)

    min_aqi = models.IntegerField(default=50)
    max_aqi = models.IntegerField(default=500)

    rating = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["product_type"]

    def __str__(self):
        return self.name


# ----------------------------------------------------------
# 7. AI-SUMMARIZED NEWS MODEL
# ----------------------------------------------------------
class NewsArticle(models.Model):
    title = models.CharField(max_length=512)
    source = models.CharField(max_length=256)
    url = models.URLField(unique=True)

    published_at = models.DateTimeField(null=True, blank=True)

    summary = models.TextField()
    raw_content = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title


# ----------------------------------------------------------
# 8. TRAVEL ROUTE MODEL (Stores Low-Pollution Routes)
# ----------------------------------------------------------
class TravelRoute(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="routes")

    source_name = models.CharField(max_length=256)
    source_lat = models.FloatField()
    source_lon = models.FloatField()

    dest_name = models.CharField(max_length=256)
    dest_lat = models.FloatField()
    dest_lon = models.FloatField()

    route_geometry = models.JSONField()        # list of coordinates
    pollution_score = models.FloatField()      # ML based score
    average_aqi = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source_name} → {self.dest_name} ({self.city.name})"


# ----------------------------------------------------------
# 9. USER PROFILE (PERSONALIZED ADVICE)
# ----------------------------------------------------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    age = models.IntegerField(null=True, blank=True)
    conditions = models.JSONField(default=list)     # ["asthma","elderly"]

    preferred_city = models.ForeignKey(
        City,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

class Product(models.Model):
    PRODUCT_TYPES = [
        ("mask", "Mask"),
        ("purifier", "Air Purifier"),
        ("monitor", "Air Quality Monitor"),
        ("car-filter", "Car Filter"),
        ("plant", "Plant"),
    ]

    name = models.CharField(max_length=256)
    product_type = models.CharField(max_length=32, choices=PRODUCT_TYPES)
    description = models.TextField(blank=True)
    price = models.FloatField(null=True, blank=True)
    image_url = models.URLField(blank=True, null=True)
    product_url = models.URLField(blank=True, null=True)

    # inclusive aqiRange stored as "min-max" or "All"
    aqi_min = models.IntegerField(default=0)
    aqi_max = models.IntegerField(default=500)

    effectiveness = models.IntegerField(default=0)   # 0-100
    rating = models.FloatField(null=True, blank=True)
    reviews = models.IntegerField(null=True, blank=True)
    features = models.JSONField(default=list, blank=True)  # list of strings
    recommended_for = models.JSONField(default=list, blank=True)  # list of strings

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_type", "-effectiveness"]

    def __str__(self):
        return self.name
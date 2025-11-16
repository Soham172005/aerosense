from rest_framework import serializers
from .models import Product, City, AQIReading

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = "__all__"


class AQIReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AQIReading
        fields = "__all__"

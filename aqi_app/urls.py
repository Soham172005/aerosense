from django.urls import path
from . import views
from .views import ProductViewSet, product_recommendations
from rest_framework import routers
from django.urls import path, include
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, products_page

router = DefaultRouter()
router.register("products-api", ProductViewSet)

router = routers.DefaultRouter()
router.register(r'products', ProductViewSet)

urlpatterns = [
    path("", views.home_view, name="home"),

    path("live-monitoring/", views.live_monitoring_view, name="live_monitoring"),

    path("forecasting/", views.forecasting_view, name="forecasting"),
    
    path("trends/", views.trends_view, name="trends"),

    # aqi_app/urls.py
    path("news/", views.news_view, name="news"),

    path("api/recommendations/", product_recommendations),
    path("", include(router.urls)),

    path("", include(router.urls)),
    path("products-page/", products_page, name="products_page"),




]


from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),

    path("live-monitoring/", views.live_monitoring_view, name="live_monitoring"),

    path("forecasting/", views.forecasting_view, name="forecasting"),
    
    path("trends/", views.trends_view, name="trends"),

    # aqi_app/urls.py
    path("news/", views.news_view, name="news"),



]


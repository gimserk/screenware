# bulletin_board/slideshow/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # A list of all available slide decks
    path('', views.SlideDeckListView.as_view(), name='slidedeck_list'),

    # The main display view for a single slide deck
    path('deck/<slug:slidedeck_slug>/', views.slidedeck_view, name='slidedeck_detail'),
    
    # The API endpoint to check for slide deck updates
    path('api/status/<slug:slidedeck_slug>/', views.slidedeck_status_view, name='slidedeck_status'),
    
    # The API endpoint for devices to send their heartbeat
    path('api/heartbeat/', views.device_heartbeat_view, name='device_heartbeat'),
    path('api/status/<int:deck_pk>/', views.slidedeck_api_status, name='slidedeck_api_status'),
]
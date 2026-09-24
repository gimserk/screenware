from django.urls import path
from . import views

urlpatterns = [
    path('show/<int:pk>/', views.slidedeck_detail, name='slidedeck_show'),
    path('api/status/<int:pk>/', views.slidedeck_status, name='slidedeck_status'),
    path('api/heartbeat/', views.device_heartbeat, name='device_heartbeat'),
]

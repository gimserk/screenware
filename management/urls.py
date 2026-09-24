from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Devices
    path('devices/', views.device_list, name='device_list'),
    path('devices/add/', views.device_create, name='device_create'),
    path('devices/<int:pk>/edit/', views.device_update, name='device_update'),
    path('devices/<int:pk>/delete/', views.device_delete, name='device_delete'),

    # Slide Decks
    path('decks/', views.slidedeck_list, name='slidedeck_list'),
    path('decks/add/', views.slidedeck_create, name='slidedeck_create'),
    path('decks/<int:pk>/edit/', views.slidedeck_update, name='slidedeck_update'),
    path('decks/<int:pk>/delete/', views.slidedeck_delete, name='slidedeck_delete'),

    # Slide Management
    path('decks/<int:pk>/slides/', views.manage_slides, name='manage_slides'),
    path('slides/add/<int:deck_pk>/', views.slide_create, name='slide_create'),
    path('slides/<int:pk>/edit/', views.slide_update, name='slide_update'),
    path('slides/<int:pk>/delete/', views.slide_delete, name='slide_delete'),

    # Hardware Manifest Sync Endpoint
    path('api/device/<str:identifier>/manifest/', views.device_manifest, name='device_manifest'),
]

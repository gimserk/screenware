# management/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Device Management
    path('devices/', views.DeviceListView.as_view(), name='manage_device_list'),
    path('slidedecks/<int:deck_pk>/reorder/', views.reorder_slides_view, name='manage_slides_reorder'),
    path('devices/<str:pk>/edit/', views.DeviceUpdateView.as_view(), name='manage_device_edit'),
    path('devices/<str:pk>/delete/', views.DeviceDeleteView.as_view(), name='manage_device_delete'),

    # Slide Deck Management
    path('slidedecks/', views.SlideDeckListView.as_view(), name='manage_slidedeck_list'),
    path('slidedecks/new/', views.SlideDeckCreateView.as_view(), name='manage_slidedeck_new'),
    path('slidedecks/<int:pk>/edit/', views.SlideDeckUpdateView.as_view(), name='manage_slidedeck_edit'),
    path('slidedecks/<int:pk>/delete/', views.SlideDeckDeleteView.as_view(), name='manage_slidedeck_delete'),

    # Individual Slide Management
    path('slidedecks/<int:deck_pk>/slides/', views.manage_slides_view, name='manage_slides'),
    path('slides/<int:pk>/edit/', views.SlideUpdateView.as_view(), name='manage_slide_edit'),
    path('slides/<int:pk>/delete/', views.SlideDeleteView.as_view(), name='manage_slide_delete'),
    path('download-script/', views.download_setup_script_view, name='download_setup_script'),
]
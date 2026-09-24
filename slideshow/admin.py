from django.contrib import admin
from .models import SlideDeck, Slide, Device

@admin.register(SlideDeck)
class SlideDeckAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'last_updated')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'deck', 'content_type', 'duration', 'order', 'active')
    list_filter = ('deck', 'content_type', 'active')
    ordering = ('deck', 'order')

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'device_id', 'mac_address', 'assigned_slidedeck', 'last_seen', 'is_online')
    list_filter = ('assigned_slidedeck',)

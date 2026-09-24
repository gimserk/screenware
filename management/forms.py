from django import forms
from slideshow.models import SlideDeck, Slide, Device

class SlideDeckForm(forms.ModelForm):
    class Meta:
        model = SlideDeck
        fields = ['name', 'slug', 'description']

class SlideForm(forms.ModelForm):
    class Meta:
        model = Slide
        fields = [
            'title', 'duration', 'content_type', 'order', 'active',
            'image', 'video', 'text_content', 'youtube_video_id',
            'calendar_url', 'calendar_display_style', 'latitude', 'longitude',
            'api_key', 'rss_feed_url'
        ]

class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['name', 'device_id', 'mac_address', 'assigned_slidedeck']

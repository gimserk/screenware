# bulletin_board/slideshow/models.py

from django.db import models
from django.utils import timezone

class SlideDeck(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, help_text="A short, URL-friendly version of the name.")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Slide(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('youtube', 'YouTube Video'),
        ('calendar', 'ICS Calendar'),
        ('weather', 'Weather'),
        ('rss', 'RSS Feed'),
    ]

    CALENDAR_VIEW_CHOICES = [
        ('ics_week', 'ICS Weekly Agenda'), 
        ('html_embed', 'HTML Full Page Embed'),
        ('ics_today', "ICS Today's Agenda"),
    ]

    slide_deck = models.ForeignKey(SlideDeck, on_delete=models.CASCADE, related_name='slides')
    title = models.CharField(max_length=200)
    content_type = models.CharField(max_length=15, choices=CONTENT_TYPE_CHOICES)
    
    # Content fields
    text_content = models.TextField(blank=True, help_text="Enter text content for the slide.")
    image_content = models.ImageField(upload_to='images/', blank=True, help_text="Upload an image for the slide.")
    video_content = models.FileField(upload_to='videos/', blank=True, help_text="Upload a video for the slide.")
    youtube_video_id = models.CharField(max_length=50, blank=True, help_text="Enter the YouTube Video ID (e.g., 'dQw4w9WgXcQ').")
    calendar_url = models.URLField(blank=True, help_text="Enter the URL for an ICS calendar or the HTML calendar link.")
    calendar_display_style = models.CharField(
        max_length=20,
        choices=CALENDAR_VIEW_CHOICES,
        default='ics_week',
        help_text="Choose how to display the calendar."
    )
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text="e.g., 41.139981")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text="e.g., -104.820244")
    api_key = models.CharField(max_length=100, blank=True, null=True, help_text="OpenWeatherMap API Key")
    rss_feed_url = models.URLField(max_length=500, blank=True, null=True, help_text="Enter the URL for an RSS news feed.")

    duration = models.PositiveIntegerField(default=10, help_text="Duration to display the slide in seconds.")
    order = models.PositiveIntegerField(default=0, help_text="Order of the slide in the slideshow.")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

class Device(models.Model):
    """Represents a physical display device like a Raspberry Pi."""
    device_id = models.CharField(
        max_length=255, 
        unique=True, 
        primary_key=True, 
        help_text="A unique identifier for the device, e.g., a MAC address."
    )
    name = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="A friendly name for the device, e.g., 'Lobby Display'"
    )
    last_seen = models.DateTimeField(
        default=timezone.now, 
        help_text="The last time this device sent a heartbeat."
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    assigned_slidedeck = models.ForeignKey(
        SlideDeck, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        related_name='devices'
    )
    
    def __str__(self):
        return self.name or self.device_id
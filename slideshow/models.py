from django.db import models
from django.utils import timezone

class SlideDeck(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Slide(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('image', 'Image Asset'),
        ('text', 'Text Announcement'),
        ('video', 'Video File (MP4)'),
        ('youtube', 'YouTube Video'),
        ('calendar', 'Calendar Feed (ICS/Embed)'),
        ('weather', 'Weather Forecast'),
        ('rss', 'RSS News Feed'),
    ]

    deck = models.ForeignKey(SlideDeck, on_delete=models.CASCADE, related_name='slides')
    title = models.CharField(max_length=200)
    duration = models.IntegerField(default=10, help_text="Display duration in seconds")
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='image')
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    # Content fields
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    video = models.FileField(upload_to='videos/', blank=True, null=True)
    text_content = models.TextField(blank=True, help_text="Body text for announcement slides")
    youtube_video_id = models.CharField(max_length=50, blank=True, help_text="e.g. dQw4w9WgXcQ")
    calendar_url = models.URLField(max_length=500, blank=True, help_text="Public iCal (.ics) or embed URL")
    calendar_display_style = models.CharField(max_length=50, default='agenda', blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    api_key = models.CharField(max_length=200, blank=True)
    rss_feed_url = models.URLField(max_length=500, blank=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.deck.name} - [{self.order}] {self.title} ({self.get_content_type_display()})"

class Device(models.Model):
    name = models.CharField(max_length=100, default='TV Display')
    device_id = models.CharField(max_length=100, unique=True, db_index=True)
    mac_address = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    assigned_slidedeck = models.ForeignKey(
        SlideDeck, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices'
    )
    last_seen = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='Offline')

    @property
    def is_online(self):
        if not self.last_seen:
            return False
        return (timezone.now() - self.last_seen).total_seconds() < 300

    def __str__(self):
        return f"{self.name} ({self.mac_address or self.device_id})"

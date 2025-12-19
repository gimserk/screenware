# management/forms.py

from django import forms
from slideshow.models import Slide

class SlideForm(forms.ModelForm):
    class Meta:
        model = Slide
        fields = [
            'title', 
            'content_type', 
            'duration', 
            'order', 
            'text_content', 
            'image_content',
            'video_content',
            'youtube_video_id',
            'calendar_url',
            'calendar_display_style',
            'latitude',
            'longitude',
            'api_key', 
            'rss_feed_url',
        ]
        widgets = {
            'text_content': forms.Textarea(attrs={'rows': 4}),
        }
       
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields not required by default, we'll control this with JavaScript later
        for field_name in self.fields:
            if field_name not in ['title', 'content_type', 'duration', 'order']:
                self.fields[field_name].required = False
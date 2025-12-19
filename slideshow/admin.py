# bulletin_board/slideshow/admin.py

from django.contrib import admin
from .models import SlideDeck, Slide

class SlideInline(admin.TabularInline):
    model = Slide
    extra = 1
    # The 'youtube_video_id' field is now included here
    fields = ('title', 'content_type', 'text_content', 'image_content', 'video_content', 'youtube_video_id', 'calendar_url', 'duration', 'order')


class SlideDeckAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SlideInline]
    list_display = ('name', 'slug')

admin.site.register(SlideDeck, SlideDeckAdmin)

@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'slide_deck', 'content_type', 'order', 'duration')
    list_filter = ('slide_deck', 'content_type')
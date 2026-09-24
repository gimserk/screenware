from django import forms
from slideshow.models import SlideDeck, Slide, Device

class SlideDeckForm(forms.ModelForm):
    class Meta:
        model = SlideDeck
        fields = ['name', 'slug', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white focus:border-indigo-500 outline-none'}),
            'slug': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white font-mono text-sm focus:border-indigo-500 outline-none'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-indigo-500 outline-none'}),
        }

class SlideForm(forms.ModelForm):
    class Meta:
        model = Slide
        fields = [
            'title', 'duration', 'content_type', 'order', 'active',
            'image', 'video', 'text_content', 'youtube_video_id',
            'calendar_url', 'calendar_display_style', 'latitude', 'longitude',
            'api_key', 'rss_feed_url'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
            'duration': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
            'content_type': forms.Select(attrs={'id': 'id_content_type', 'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
            'order': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
            'active': forms.CheckboxInput(attrs={'class': 'rounded bg-slate-900'}),
            'text_content': forms.Textarea(attrs={'rows': 3, 'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
            'youtube_video_id': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
            'calendar_url': forms.URLInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
            'calendar_display_style': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
            'latitude': forms.NumberInput(attrs={'step': 'any', 'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
            'longitude': forms.NumberInput(attrs={'step': 'any', 'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
            'api_key': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
            'rss_feed_url': forms.URLInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-sm focus:border-cyan-500 outline-none'}),
        }

class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['name', 'device_id', 'mac_address', 'assigned_slidedeck']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white focus:border-cyan-500 outline-none'}),
            'device_id': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white font-mono text-sm focus:border-cyan-500 outline-none'}),
            'mac_address': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white font-mono text-sm focus:border-cyan-500 outline-none'}),
            'assigned_slidedeck': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white focus:border-cyan-500 outline-none'}),
        }

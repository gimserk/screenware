# bulletin_board/slideshow/views.py

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import requests
from icalendar import Calendar, Event
from datetime import datetime, timedelta, time, date
import pytz
import math
import json
import feedparser
from collections import Counter
from dateutil.rrule import rrulestr, rrule

from .models import SlideDeck, Device

class SlideDeckListView(ListView):
    """
    A view to display a list of all available slide decks.
    """
    model = SlideDeck
    template_name = 'slideshow/slidedeck_list.html'
    context_object_name = 'slidedecks'

def slidedeck_view(request, slidedeck_slug):
    slidedeck = get_object_or_404(SlideDeck, slug=slidedeck_slug)
    slides = slidedeck.slides.all().order_by('order', 'id')
    browser_header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'}

    for slide in slides:
        duration_in_seconds = slide.duration if slide.duration > 0 else 10
        slide.duration_ms = duration_in_seconds * 1000

        if slide.content_type == 'calendar' and slide.calendar_url:
            if slide.calendar_display_style in ['ics_today', 'ics_week']:
                try:
                    response = requests.get(slide.calendar_url, headers=browser_header)
                    response.raise_for_status()
                    gcal = Calendar.from_ical(response.text)
                    server_tz = pytz.timezone(settings.TIME_ZONE)
                    today = timezone.now().astimezone(server_tz)

                    # ▼▼▼ RESTORED 'ics_today' LOGIC ▼▼▼
                    if slide.calendar_display_style == 'ics_today':
                        todays_events = []
                        for component in gcal.walk('VEVENT'):
                            dtstart = component.get('dtstart').dt
                            
                            if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                                dtstart = server_tz.localize(datetime.combine(dtstart, time.min))
                            if dtstart.tzinfo is None:
                                dtstart = server_tz.localize(dtstart)
                            
                            if component.get('rrule'):
                                rules = rrulestr(component.get('rrule').to_ical().decode(), dtstart=dtstart)
                                start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
                                end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)
                                
                                for occ_start in rules.between(start_of_day, end_of_day):
                                    duration = component.get('dtend').dt - component.get('dtstart').dt
                                    occ_end = occ_start + duration
                                    todays_events.append({
                                        'summary': component.get('summary'),
                                        'begin': occ_start,
                                        'end': occ_end,
                                        'all_day': False
                                    })
                            else:
                                if dtstart.date() == today.date():
                                    all_day = isinstance(component.get('dtstart').dt, date) and not isinstance(component.get('dtstart').dt, datetime)
                                    todays_events.append({
                                        'summary': component.get('summary'),
                                        'begin': dtstart,
                                        'end': component.get('dtend').dt,
                                        'all_day': all_day
                                    })
                        
                        slide.todays_events = sorted(todays_events, key=lambda e: e['begin'])
                    
                    elif slide.calendar_display_style == 'ics_week':
                        slide.weekly_calendar_data = []
                        start_of_week_date = today.date() - timedelta(days=today.weekday())
                        
                        for i in range(5):
                            current_day_date = start_of_week_date + timedelta(days=i)
                            day_data = {'date': current_day_date, 'time_slots': []}
                            
                            for hour in range(8, 20):
                                slot_start = server_tz.localize(datetime.combine(current_day_date, time(hour=hour)))
                                day_data['time_slots'].append({'time': slot_start, 'event': None, 'is_continuation': False})
                            
                            events_on_day = []
                            for component in gcal.walk('VEVENT'):
                                dtstart = component.get('dtstart').dt
                                
                                if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                                    dtstart = server_tz.localize(datetime.combine(dtstart, time.min))
                                if dtstart.tzinfo is None:
                                    dtstart = server_tz.localize(dtstart)
                                
                                if component.get('rrule'):
                                    rules = rrulestr(component.get('rrule').to_ical().decode(), dtstart=dtstart)
                                    day_start_dt = server_tz.localize(datetime.combine(current_day_date, time.min))
                                    day_end_dt = server_tz.localize(datetime.combine(current_day_date, time.max))

                                    for occ_start in rules.between(day_start_dt, day_end_dt, inc=True):
                                        duration = component.get('dtend').dt - component.get('dtstart').dt
                                        events_on_day.append({
                                            'summary': component.get('summary'),
                                            'begin': occ_start,
                                            'end': occ_start + duration
                                        })
                                else:
                                    if dtstart.date() == current_day_date:
                                        events_on_day.append({
                                            'summary': component.get('summary'),
                                            'begin': dtstart,
                                            'end': component.get('dtend').dt
                                        })

                            day_start_dt_grid = server_tz.localize(datetime.combine(current_day_date, time(hour=8)))
                            day_end_dt_grid = server_tz.localize(datetime.combine(current_day_date, time(hour=20)))

                            for event in sorted(events_on_day, key=lambda e: e['begin']):
                                event_start_local = event['begin'].astimezone(server_tz)
                                
                                start_hour = 8 if event_start_local.hour < 8 else event_start_local.hour
                                slot_index = start_hour - 8
                                
                                if 0 <= slot_index < 12 and not day_data['time_slots'][slot_index]['event']:
                                    visible_start = max(event['begin'].astimezone(server_tz), day_start_dt_grid)
                                    visible_end = min(event['end'].astimezone(server_tz), day_end_dt_grid)
                                    
                                    duration_hours = math.ceil((visible_end - visible_start).total_seconds() / 3600)
                                    if duration_hours < 1: duration_hours = 1
                                    
                                    day_data['time_slots'][slot_index]['event'] = {'name': event['summary'], 'duration': duration_hours}
                                    
                                    for j in range(1, int(duration_hours)):
                                        if slot_index + j < 12:
                                            day_data['time_slots'][slot_index + j]['is_continuation'] = True
                            
                            slide.weekly_calendar_data.append(day_data)
                
                except Exception as e:
                    print(f"Error parsing calendar for url {slide.calendar_url}: {e}")
        
        

        elif slide.content_type == 'weather' and slide.latitude and slide.longitude:
            api_key = getattr(settings, 'OPENWEATHERMAP_API_KEY', None)
            if not api_key:
                print("Error: OPENWEATHERMAP_API_KEY not set in settings.py")
                continue
            
            url_current = f"https://api.openweathermap.org/data/2.5/weather?lat={slide.latitude}&lon={slide.longitude}&appid={api_key}&units=imperial"
            url_forecast = f"https://api.openweathermap.org/data/2.5/forecast?lat={slide.latitude}&lon={slide.longitude}&appid={api_key}&units=imperial"

            try:
                response_current = requests.get(url_current)
                response_current.raise_for_status()
                data_current = response_current.json()

                response_forecast = requests.get(url_forecast)
                response_forecast.raise_for_status()
                data_forecast = response_forecast.json()

                hourly_forecast = data_forecast['list'][:5]

                daily_data = {}
                for item in data_forecast['list']:
                    item_date = datetime.fromtimestamp(item['dt'], tz=pytz.UTC).date()
                    if item_date not in daily_data:
                        daily_data[item_date] = {'temps': [], 'icons': []}
                    daily_data[item_date]['temps'].append(item['main']['temp'])
                    daily_data[item_date]['icons'].append(item['weather'][0]['icon'][:-1])

                daily_forecast = []
                server_tz = pytz.timezone(settings.TIME_ZONE)
                today = timezone.now().astimezone(server_tz).date()

                for forecast_date, values in sorted(daily_data.items()):
                    if forecast_date <= today or len(daily_forecast) >= 5:
                        continue
                    
                    most_common_icon = Counter(values['icons']).most_common(1)[0][0]
                    daily_forecast.append({
                        'dt': datetime.combine(forecast_date, time()).timestamp(),
                        'temp': {
                            'min': min(values['temps']),
                            'max': max(values['temps'])
                        },
                        'weather': [{'icon': most_common_icon}]
                    })
                
                background_map = {
                    'Thunderstorm': 'thunderstorm', 'Drizzle': 'drizzle', 'Rain': 'rain',
                    'Snow': 'snow', 'Clear': 'clear sky', 'Clouds': 'cloudy'
                }
                main_condition = data_current['weather'][0]['main']
                background_keyword = background_map.get(main_condition, 'weather')
                
                slide.weather_data = {
                    'current': data_current,
                    'hourly': hourly_forecast,
                    'daily': daily_forecast,
                    'background_keyword': background_keyword,
                    'timezone': settings.TIME_ZONE 
                }

            except requests.exceptions.RequestException as e:
                print(f"Error fetching free tier weather data: {e}")
                slide.weather_data = None
        
        elif slide.content_type == 'rss' and slide.rss_feed_url:
            try:
                feed = feedparser.parse(slide.rss_feed_url)
                slide.rss_data = {
                    'title': feed.feed.title,
                    'entries': feed.entries[:5]
                }
            except Exception as e:
                print(f"Error fetching RSS feed {slide.rss_feed_url}: {e}")
                slide.rss_data = None

    return render(request, 'slideshow/slidedeck_detail.html', {'slidedeck': slidedeck, 'slides': slides})

def slidedeck_status_view(request, slidedeck_slug):
    """
    A view that returns the last updated timestamp for a slide deck as JSON.
    """
    slidedeck = get_object_or_404(SlideDeck, slug=slidedeck_slug)
    return JsonResponse({'last_updated': slidedeck.last_updated})

@csrf_exempt
@require_POST
def device_heartbeat_view(request):
    """
    API endpoint for devices to report their status.
    It now returns the currently assigned slidedeck slug.
    """
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        if not device_id:
            return JsonResponse({'status': 'error', 'message': 'Device ID is required.'}, status=400)

        ip_address = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')

        device, created = Device.objects.update_or_create(
            device_id=device_id,
            defaults={'last_seen': timezone.now(), 'ip_address': ip_address}
        )
        
        # Prepare the response payload with the slug
        response_data = {
            'status': 'success',
            'message': 'Heartbeat received.',
            'assigned_slidedeck_pk': device.assigned_slidedeck_id,
            # IMPORTANT: Add the slug to the response
            'assigned_slidedeck_slug': device.assigned_slidedeck.slug if device.assigned_slidedeck else None
        }
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def slidedeck_api_status(request, deck_slug):
    """
    API endpoint to check the last_updated timestamp of a SlideDeck by its slug.
    """
    slidedeck = get_object_or_404(SlideDeck, slug=deck_slug)
    return JsonResponse({
        'name': slidedeck.name,
        'last_updated': slidedeck.last_updated.isoformat(),
    })
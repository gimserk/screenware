import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import SlideDeck, Device

def slidedeck_detail(request, pk):
    deck = get_object_or_404(SlideDeck, pk=pk)
    slides = deck.slides.filter(active=True).order_by('order')
    return render(request, 'slideshow/slidedeck_detail.html', {
        'deck': deck,
        'slides': slides
    })

def slidedeck_status(request, pk):
    deck = get_object_or_404(SlideDeck, pk=pk)
    return JsonResponse({'last_updated': deck.last_updated.isoformat()})

@csrf_exempt
def device_heartbeat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            dev_id = data.get('device_id')
            if dev_id:
                device, _ = Device.objects.get_or_create(device_id=dev_id)
                device.last_seen = timezone.now()
                ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
                if ip:
                    device.ip_address = ip.split(',')[0].strip()
                device.save()
                return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'invalid request'}, status=405)

import json
import hashlib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.utils import timezone
from slideshow.models import SlideDeck, Slide, Device
from .forms import SlideDeckForm, SlideForm, DeviceForm

@login_required
def dashboard(request):
    devices = Device.objects.all()
    decks = SlideDeck.objects.all()
    return render(request, 'management/dashboard.html', {
        'devices': devices,
        'decks': decks
    })

@login_required
def device_list(request):
    devices = Device.objects.all()
    return render(request, 'management/device_list.html', {'devices': devices})

@login_required
def device_create(request):
    if request.method == 'POST':
        form = DeviceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('device_list')
    else:
        form = DeviceForm()
    return render(request, 'management/device_form.html', {'form': form, 'title': 'Add Device'})

@login_required
def device_update(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            form.save()
            return redirect('device_list')
    else:
        form = DeviceForm(instance=device)
    return render(request, 'management/device_form.html', {'form': form, 'title': 'Edit Device'})

@login_required
def device_delete(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        device.delete()
        return redirect('device_list')
    return render(request, 'management/device_confirm_delete.html', {'device': device})

@login_required
def slidedeck_list(request):
    decks = SlideDeck.objects.all()
    return render(request, 'management/slidedeck_list.html', {'decks': decks})

@login_required
def slidedeck_create(request):
    if request.method == 'POST':
        form = SlideDeckForm(request.POST)
        if form.is_valid():
            deck = form.save()
            return redirect('manage_slides', pk=deck.pk)
    else:
        form = SlideDeckForm()
    return render(request, 'management/slidedeck_form.html', {'form': form, 'title': 'New Slide Deck'})

@login_required
def slidedeck_update(request, pk):
    deck = get_object_or_404(SlideDeck, pk=pk)
    if request.method == 'POST':
        form = SlideDeckForm(request.POST, instance=deck)
        if form.is_valid():
            form.save()
            return redirect('slidedeck_list')
    else:
        form = SlideDeckForm(instance=deck)
    return render(request, 'management/slidedeck_form.html', {'form': form, 'title': 'Edit Slide Deck'})

@login_required
def slidedeck_delete(request, pk):
    deck = get_object_or_404(SlideDeck, pk=pk)
    if request.method == 'POST':
        deck.delete()
        return redirect('slidedeck_list')
    return render(request, 'management/slidedeck_confirm_delete.html', {'deck': deck})

@login_required
def manage_slides(request, pk):
    deck = get_object_or_404(SlideDeck, pk=pk)
    slides = deck.slides.all().order_by('order')
    form = SlideForm()
    return render(request, 'management/manage_slides.html', {
        'deck': deck,
        'slides': slides,
        'form': form
    })

@login_required
def slide_create(request, deck_pk):
    deck = get_object_or_404(SlideDeck, pk=deck_pk)
    if request.method == 'POST':
        form = SlideForm(request.POST, request.FILES)
        if form.is_valid():
            slide = form.save(commit=False)
            slide.deck = deck
            # Set order to next available if not provided
            if not slide.order:
                max_order = deck.slides.count()
                slide.order = max_order + 1
            slide.save()
            deck.save() # triggers last_updated
            return redirect('manage_slides', pk=deck.pk)
    return redirect('manage_slides', pk=deck.pk)

@login_required
def slide_update(request, pk):
    slide = get_object_or_404(Slide, pk=pk)
    if request.method == 'POST':
        form = SlideForm(request.POST, request.FILES, instance=slide)
        if form.is_valid():
            form.save()
            slide.deck.save()
            return redirect('manage_slides', pk=slide.deck.pk)
    else:
        form = SlideForm(instance=slide)
    return render(request, 'management/slide_form.html', {'form': form, 'slide': slide})

@login_required
def slide_delete(request, pk):
    slide = get_object_or_404(Slide, pk=pk)
    deck_pk = slide.deck.pk
    if request.method == 'POST':
        slide.delete()
        SlideDeck.objects.filter(pk=deck_pk).update(last_updated=timezone.now())
        return redirect('manage_slides', pk=deck_pk)
    return render(request, 'management/slide_confirm_delete.html', {'slide': slide})

@login_required
@csrf_exempt
def reorder_slides(request):
    """
    AJAX endpoint to update slide ordering dynamically from UI drag-and-drop or reordering buttons.
    Expects JSON: {'order': [slide_id_1, slide_id_2, ...]}
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            order_list = data.get('order', [])
            for index, slide_id in enumerate(order_list):
                Slide.objects.filter(id=slide_id).update(order=index + 1)
            if order_list:
                first_slide = Slide.objects.filter(id=order_list[0]).first()
                if first_slide and first_slide.deck:
                    first_slide.deck.save() # bump timestamp
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return HttpResponseBadRequest('POST required')

def device_manifest(request, identifier):
    """
    Delivers a deterministic JSON manifest containing active slide metadata,
    duration specifications, wall-clock epoch anchor, and an atomic SHA-256 version hash.
    Accepts MAC address (colon or hyphen delimited) or hardware device ID.
    Auto-registers newly discovered displays for seamless onboarding.
    """
    norm_id = identifier.replace('-', ':').upper()

    device = Device.objects.filter(
        Q(mac_address__iexact=norm_id) |
        Q(mac_address__iexact=identifier) |
        Q(device_id__iexact=norm_id) |
        Q(device_id__iexact=identifier)
    ).first()

    if not device and identifier.isdigit():
        device = Device.objects.filter(pk=int(identifier)).first()

    # Auto-register newly discovered display if it does not exist
    if not device:
        client_ip = request.META.get('HTTP_X_CLIENT_IP') or request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()
        device = Device.objects.create(
            name=f"New Display ({identifier[-8:] if len(identifier) >= 8 else identifier})",
            device_id=identifier,
            mac_address=norm_id if ':' in norm_id else None,
            ip_address=client_ip,
            last_seen=timezone.now(),
            status="Online"
        )

    # Update heartbeat and IP address
    if hasattr(device, 'last_seen'):
        client_ip = request.META.get('HTTP_X_CLIENT_IP') or request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
        if client_ip:
            device.ip_address = client_ip.split(',')[0].strip()
        device.last_seen = timezone.now()
        device.status = "Online"
        device.save(update_fields=['last_seen', 'ip_address', 'status'])

    deck = getattr(device, 'assigned_slidedeck', None) or getattr(device, 'slide_deck', None)
    if not deck:
        return JsonResponse({
            "version_hash": "",
            "deck_start_epoch": 0,
            "total_duration": 0,
            "slides": [],
            "server_time": timezone.now().timestamp(),
            "device_name": device.name,
            "status": "unassigned"
        })

    slides_qs = deck.slides.filter(active=True).order_by('order')

    slide_data = []
    total_duration = 0

    for slide in slides_qs:
        duration = getattr(slide, 'duration', 10) or 10
        total_duration += duration

        image_field = getattr(slide, 'image', None)
        media_url = ""
        filename = ""
        if image_field and bool(image_field):
            media_url = request.build_absolute_uri(image_field.url)
            filename = image_field.name.split('/')[-1]

        # Video asset if content_type is video
        video_field = getattr(slide, 'video', None)
        video_url = ""
        if video_field and bool(video_field):
            video_url = request.build_absolute_uri(video_field.url)
            if not filename:
                filename = video_field.name.split('/')[-1]

        slide_data.append({
            "id": slide.id,
            "title": slide.title,
            "url": media_url or video_url,
            "filename": filename,
            "duration": duration,
            "order": getattr(slide, 'order', 0),
            "content_type": getattr(slide, 'content_type', 'image'),
            "text_content": getattr(slide, 'text_content', ''),
            "youtube_video_id": getattr(slide, 'youtube_video_id', ''),
            "calendar_url": getattr(slide, 'calendar_url', ''),
            "calendar_display_style": getattr(slide, 'calendar_display_style', 'agenda'),
            "latitude": getattr(slide, 'latitude', None),
            "longitude": getattr(slide, 'longitude', None),
            "rss_feed_url": getattr(slide, 'rss_feed_url', '')
        })

    # Atomic version hash includes all slide data & order
    hash_payload = json.dumps(slide_data, sort_keys=True)
    version_hash = hashlib.sha256(hash_payload.encode('utf-8')).hexdigest()

    response_data = {
        "version_hash": version_hash,
        "deck_start_epoch": 0,  # Unix epoch 0 (1970-01-01 UTC) anchor for deterministic modulo time sync
        "total_duration": total_duration,
        "slides": slide_data,
        "server_time": timezone.now().timestamp(),
        "device_name": device.name,
        "deck_name": deck.name,
        "status": "active"
    }
    return JsonResponse(response_data)

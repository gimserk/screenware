import json
import hashlib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
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
            slide.save()
            deck.save()
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

def device_manifest(request, identifier):
    """
    Delivers a deterministic JSON manifest containing active slide metadata,
    duration specifications, wall-clock epoch anchor, and an atomic SHA-256 version hash.
    Accepts MAC address (colon/hyphen delimited) or hardware device ID.
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

    if not device:
        return JsonResponse({"error": "Device not found"}, status=404)

    # Touch device last_seen timestamp as a passive heartbeat
    if hasattr(device, 'last_seen'):
        device.last_seen = timezone.now()
        device.save(update_fields=['last_seen'])

    deck = getattr(device, 'assigned_slidedeck', None) or getattr(device, 'slide_deck', None)
    if not deck:
        return JsonResponse({
            "version_hash": "",
            "deck_start_epoch": 0,
            "total_duration": 0,
            "slides": [],
            "server_time": timezone.now().timestamp()
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

        slide_data.append({
            "id": slide.id,
            "url": media_url,
            "filename": filename,
            "duration": duration,
            "order": getattr(slide, 'order', 0),
            "content_type": getattr(slide, 'content_type', 'image')
        })

    hash_payload = json.dumps(slide_data, sort_keys=True)
    version_hash = hashlib.sha256(hash_payload.encode('utf-8')).hexdigest()

    response_data = {
        "version_hash": version_hash,
        "deck_start_epoch": 0,
        "total_duration": total_duration,
        "slides": slide_data,
        "server_time": timezone.now().timestamp()
    }
    return JsonResponse(response_data)

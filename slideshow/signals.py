from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Slide, SlideDeck

@receiver([post_save, post_delete], sender=Slide)
def update_slidedeck_timestamp(sender, instance, **kwargs):
    if instance.deck:
        instance.deck.save()  # Triggers auto_now update on last_updated

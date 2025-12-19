from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Slide

@receiver([post_save, post_delete], sender=Slide)
def update_slidedeck_timestamp(sender, instance, **kwargs):
    """
    Whenever a Slide is saved or deleted, update its parent SlideDeck's
    last_updated timestamp.
    """
    # By calling .save() on the parent, the 'auto_now=True' field
    # on SlideDeck will automatically update the timestamp.
    instance.slide_deck.save()
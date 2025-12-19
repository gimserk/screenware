from django.apps import AppConfig

class SlideshowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'slideshow'

    def ready(self):
        # This line is crucial for registering your signals.
        import slideshow.signals
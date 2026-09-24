from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='SlideDeck',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='TV Display', max_length=100)),
                ('device_id', models.CharField(db_index=True, max_length=100, unique=True)),
                ('mac_address', models.CharField(blank=True, db_index=True, max_length=50, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('last_seen', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(default='Offline', max_length=20)),
                ('assigned_slidedeck', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='devices', to='slideshow.slidedeck')),
            ],
        ),
        migrations.CreateModel(
            name='Slide',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('duration', models.IntegerField(default=10, help_text='Display duration in seconds')),
                ('content_type', models.CharField(choices=[('text', 'Text'), ('image', 'Image'), ('video', 'Video'), ('youtube', 'YouTube'), ('calendar', 'Calendar'), ('weather', 'Weather'), ('rss', 'RSS Feed')], default='image', max_length=20)),
                ('order', models.PositiveIntegerField(default=0)),
                ('active', models.BooleanField(default=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='images/')),
                ('video', models.FileField(blank=True, null=True, upload_to='videos/')),
                ('text_content', models.TextField(blank=True)),
                ('youtube_video_id', models.CharField(blank=True, max_length=50)),
                ('calendar_url', models.URLField(blank=True, max_length=500)),
                ('calendar_display_style', models.CharField(blank=True, default='agenda', max_length=50)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('api_key', models.CharField(blank=True, max_length=200)),
                ('rss_feed_url', models.URLField(blank=True, max_length=500)),
                ('deck', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='slides', to='slideshow.slidedeck')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
    ]

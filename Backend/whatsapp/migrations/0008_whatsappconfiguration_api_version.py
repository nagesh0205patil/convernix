from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('whatsapp', '0007_notification_delivery_audit')]

    operations = [
        migrations.AddField(
            model_name='whatsappconfiguration',
            name='api_version',
            field=models.CharField(default='v23.0', max_length=20, verbose_name='WHATSAPP_API_VERSION'),
        ),
    ]

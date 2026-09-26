from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('whatsapp', '0008_whatsappconfiguration_api_version')]

    operations = [
        migrations.AddField(
            model_name='whatsappmessage',
            name='seen_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]

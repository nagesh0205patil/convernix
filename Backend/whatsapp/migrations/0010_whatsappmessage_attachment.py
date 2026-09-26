from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('whatsapp', '0009_whatsappmessage_seen_at')]

    operations = [
        migrations.AddField(
            model_name='whatsappmessage',
            name='attachment',
            field=models.FileField(blank=True, upload_to='conversation_attachments/%Y/%m/%d/'),
        ),
        migrations.AddField(
            model_name='whatsappmessage',
            name='attachment_content_type',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='whatsappmessage',
            name='attachment_name',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]

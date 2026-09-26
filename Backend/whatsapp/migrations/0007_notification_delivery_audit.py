from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('whatsapp', '0006_businessnumber_forwarding_number')]

    operations = [
        migrations.AddField(
            model_name='departmentmember', name='notification_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='whatsappconfiguration', name='notification_template',
            field=models.CharField(default='new_lead_notification', max_length=150, verbose_name='WHATSAPP_TEMPLATE_NAME'),
        ),
        migrations.AddField(
            model_name='whatsappconfiguration', name='template_language',
            field=models.CharField(default='en', max_length=20, verbose_name='WHATSAPP_TEMPLATE_LANGUAGE'),
        ),
        migrations.AlterField(
            model_name='whatsappconfiguration', name='meta_access_token',
            field=models.TextField(blank=True, default='', verbose_name='WHATSAPP_ACCESS_TOKEN'),
        ),
        migrations.AddField(model_name='notification', name='recipient_number', field=models.CharField(blank=True, max_length=20)),
        migrations.AddField(model_name='notification', name='template_name', field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name='notification', name='request_payload', field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name='notification', name='response_payload', field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name='notification', name='http_status_code', field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name='notification', name='error_code', field=models.CharField(blank=True, max_length=50)),
        migrations.AddField(model_name='notification', name='error_subcode', field=models.CharField(blank=True, max_length=50)),
        migrations.AddField(model_name='notification', name='fbtrace_id', field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='notification', name='retry_count', field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='notification', name='sent_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AlterField(
            model_name='notification', name='status',
            field=models.CharField(choices=[
                ('queued', 'Queued'), ('processing', 'Processing'), ('sent', 'Sent'),
                ('delivered', 'Delivered'), ('read', 'Read'), ('failed', 'Failed'),
                ('permanently_failed', 'Permanently failed'),
            ], default='queued', max_length=20),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('whatsapp', '0004_multiple_whatsapp_configurations'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappconfiguration',
            name='meta_app_id',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='META_APP_ID'),
        ),
        migrations.AlterField(
            model_name='whatsappconfiguration',
            name='business_account_id',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='WABA_ID'),
        ),
        migrations.AlterField(
            model_name='whatsappconfiguration',
            name='business_number',
            field=models.CharField(max_length=20, unique=True, verbose_name='WHATSAPP_BUSINESS_NUMBER'),
        ),
        migrations.AlterField(
            model_name='whatsappconfiguration',
            name='default_team',
            field=models.CharField(default='Support', max_length=50, verbose_name='DEFAULT_TEAM'),
        ),
        migrations.AlterField(
            model_name='whatsappconfiguration',
            name='meta_access_token',
            field=models.TextField(blank=True, default='', verbose_name='META_ACCESS_TOKEN'),
        ),
        migrations.AlterField(
            model_name='whatsappconfiguration',
            name='phone_number_id',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='WHATSAPP_PHONE_NUMBER_ID'),
        ),
        migrations.AlterField(
            model_name='whatsappconfiguration',
            name='verify_token',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='WHATSAPP_VERIFY_TOKEN'),
        ),
        migrations.AlterField(
            model_name='whatsappconfiguration',
            name='webhook_secret',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='META_APP_SECRET'),
        ),
    ]

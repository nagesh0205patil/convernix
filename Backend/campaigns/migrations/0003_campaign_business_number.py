import django.db.models.deletion
from django.db import migrations, models


def assign_existing_campaigns(apps, schema_editor):
    Campaign = apps.get_model('campaigns', 'Campaign')
    BusinessNumber = apps.get_model('whatsapp', 'BusinessNumber')
    first_number = BusinessNumber.objects.order_by('pk').first()
    if first_number:
        Campaign.objects.filter(business_number__isnull=True).update(business_number=first_number)


class Migration(migrations.Migration):
    dependencies = [
        ('campaigns', '0002_initial'),
        ('whatsapp', '0010_whatsappmessage_attachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='business_number',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='campaigns', to='whatsapp.businessnumber',
            ),
        ),
        migrations.RunPython(assign_existing_campaigns, migrations.RunPython.noop),
    ]

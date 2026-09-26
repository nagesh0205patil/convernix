from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('users', '0003_platform_access_roles')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='number_access',
            field=models.CharField(
                choices=[('india', 'India number'), ('us', 'US number'), ('both', 'Both numbers')],
                default='both',
                max_length=10,
            ),
        ),
    ]
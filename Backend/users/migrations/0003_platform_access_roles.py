from django.db import migrations, models


def migrate_roles(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(is_superuser=True).update(role='owner')
    User.objects.filter(is_staff=True, is_superuser=False).update(role='admin')
    User.objects.exclude(role__in=('viewer', 'editor', 'admin', 'owner')).update(role='viewer')


class Migration(migrations.Migration):
    dependencies = [('users', '0002_user_role_user_team_name_user_whatsapp_number')]
    operations = [
        migrations.AlterField(
            model_name='user', name='role',
            field=models.CharField(choices=[('viewer', 'Viewer'), ('editor', 'Editor'), ('admin', 'Administrator'), ('owner', 'Owner')], default='viewer', max_length=30),
        ),
        migrations.RunPython(migrate_roles, migrations.RunPython.noop),
    ]

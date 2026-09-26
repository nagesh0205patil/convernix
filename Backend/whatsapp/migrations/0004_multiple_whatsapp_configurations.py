from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('whatsapp', '0003_whatsappconfiguration'),
    ]

    operations = [
        migrations.RunPython(
            code=lambda apps, schema_editor: (
                schema_editor.execute("""
                    SELECT setval(
                        pg_get_serial_sequence('whatsapp_whatsappconfiguration', 'id'),
                        COALESCE((SELECT MAX(id) FROM whatsapp_whatsappconfiguration), 1),
                        true
                    );
                """) if schema_editor.connection.vendor == 'postgresql' else None
            ),
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='whatsappconfiguration',
            name='business_number',
            field=models.CharField(max_length=20, unique=True),
        ),
    ]

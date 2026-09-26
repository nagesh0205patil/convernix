import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create the initial platform administrator from environment variables when it does not exist.'

    def handle(self, *args, **options):
        email = os.environ.get('PLATFORM_ADMIN_EMAIL', '').strip().lower()
        password = os.environ.get('PLATFORM_ADMIN_PASSWORD', '')
        username = os.environ.get('PLATFORM_ADMIN_USERNAME', 'platform-admin').strip()

        if not email and not password:
            self.stdout.write('Platform administrator initialization skipped (credentials not configured).')
            return
        if not email or not password:
            raise CommandError('PLATFORM_ADMIN_EMAIL and PLATFORM_ADMIN_PASSWORD must both be configured.')
        if len(password) < 8:
            raise CommandError('PLATFORM_ADMIN_PASSWORD must contain at least 8 characters.')

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if user:
            changed_fields = []
            for field in ('is_staff', 'is_superuser', 'is_active'):
                if not getattr(user, field):
                    setattr(user, field, True)
                    changed_fields.append(field)
            if changed_fields:
                user.save(update_fields=changed_fields)
            self.stdout.write(self.style.SUCCESS(f'Platform administrator already exists: {email}'))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Platform administrator created: {email}'))

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from campaigns.models import Campaign
from users.models import Tenant
from whatsapp.models import BusinessNumber, Customer, Department, Enquiry, WhatsAppConfiguration

User = get_user_model()


class Command(BaseCommand):
    help = 'Ensure a default tenant exists and link unassigned legacy records to it.'

    def handle(self, *args, **options):
        tenant, created = Tenant.objects.get_or_create(
            slug='convernix-demo',
            defaults={
                'name': 'Convernix Demo',
                'tier': 'mid',
                'status': 'active',
                'max_numbers': 5,
                'max_users': 15,
                'max_campaigns_monthly': 50,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created default tenant: {tenant.name}'))
        else:
            self.stdout.write(f'Using existing default tenant: {tenant.name}')

        # Link users (leave superuser/platform admin unbound)
        updated_users = User.objects.filter(tenant__isnull=True, is_superuser=False).update(tenant=tenant)
        self.stdout.write(f'Updated {updated_users} unassigned user(s).')

        # Link whatsapp resources
        updated_numbers = BusinessNumber.objects.filter(tenant__isnull=True).update(tenant=tenant)
        updated_configs = WhatsAppConfiguration.objects.filter(tenant__isnull=True).update(tenant=tenant)
        updated_depts = Department.objects.filter(tenant__isnull=True).update(tenant=tenant)
        updated_customers = Customer.objects.filter(tenant__isnull=True).update(tenant=tenant)
        updated_enquiries = Enquiry.objects.filter(tenant__isnull=True).update(tenant=tenant)
        updated_campaigns = Campaign.objects.filter(tenant__isnull=True).update(tenant=tenant)

        self.stdout.write(self.style.SUCCESS(
            f'Linked to tenant {tenant.name}: {updated_numbers} numbers, {updated_configs} configs, '
            f'{updated_depts} departments, {updated_customers} customers, {updated_enquiries} enquiries, '
            f'{updated_campaigns} campaigns.'
        ))


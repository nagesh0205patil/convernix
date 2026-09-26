from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from campaigns.models import Campaign
from analytics.models import CampaignMetric
from whatsapp.models import BusinessNumber, Department, DepartmentMember, RoutingRule
from django.utils import timezone
from datetime import datetime, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed demo data for the WhatsApp marketing dashboard.'

    def handle(self, *args, **options):
        team_members = {
            'Sales': [
                ('User A', 'sales.a@whatsapp.local', '+15550000001'),
                ('User B', 'sales.b@whatsapp.local', '+15550000002'),
            ],
            'Support': [
                ('User C', 'support.c@whatsapp.local', '+15550000003'),
                ('User D', 'support.d@whatsapp.local', '+15550000004'),
            ],
            'HR': [
                ('User E', 'hr.e@whatsapp.local', '+15550000005'),
                ('User F', 'hr.f@whatsapp.local', '+15550000006'),
            ],
        }

        for team_name, members in team_members.items():
            for full_name, email, whatsapp_number in members:
                first_name, last_name = full_name.split(' ', 1) if ' ' in full_name else (full_name, '')
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': email.split('@')[0],
                        'first_name': first_name,
                        'last_name': last_name,
                        'phone_number': whatsapp_number,
                        'whatsapp_number': whatsapp_number,
                        'team_name': team_name,
                        'role': team_name.lower(),
                        'organization': 'WhatsApp Team',
                        'is_staff': False,
                        'is_superuser': False,
                    },
                )
                if not created:
                    user.team_name = team_name
                    user.role = team_name.lower()
                    user.whatsapp_number = whatsapp_number
                    user.phone_number = whatsapp_number
                    user.save()

                if created:
                    user.set_password('demo12345')
                    user.save()

                department, _ = Department.objects.get_or_create(name=team_name, defaults={'slug': team_name.lower()})
                DepartmentMember.objects.update_or_create(
                    department=department,
                    whatsapp_number=whatsapp_number,
                    defaults={'name': full_name, 'user': user, 'active': True},
                )

        user, created = User.objects.get_or_create(
            email='demo@whatsapp.local',
            defaults={
                'username': 'demo-user',
                'first_name': 'Demo',
                'last_name': 'User',
                'phone_number': '+1234567890',
                'organization': 'Marketing Team',
                'is_staff': True,
                'is_superuser': True,
                'team_name': 'Support',
                'role': 'support',
                'whatsapp_number': '+1234567890',
            },
        )
        if created:
            user.set_password('demo12345')
            user.save()

        business_number, _ = BusinessNumber.objects.get_or_create(
            number='+15550009999', defaults={'default_team': 'Support'},
        )
        for keyword, team in [('pricing', 'Sales'), ('sales', 'Sales'), ('support', 'Support'), ('billing', 'Support'), ('career', 'HR'), ('job', 'HR')]:
            RoutingRule.objects.get_or_create(business_number=business_number, keyword=keyword, defaults={'team_name': team})

        if not Campaign.objects.filter(created_by=user).exists():
            campaigns = [
                Campaign.objects.create(
                    name='Spring Promo',
                    message='Enjoy 20% off on curated products this week.',
                    status='running',
                    target_audience='VIP customers',
                    sent_count=2500,
                    delivered_count=2340,
                    opened_count=1500,
                    clicked_count=420,
                    created_by=user,
                ),
                Campaign.objects.create(
                    name='Launch Reminder',
                    message='The launch is live. Tap to see the latest updates.',
                    status='scheduled',
                    target_audience='All customers',
                    scheduled_at=timezone.now() + timedelta(days=2),
                    sent_count=1800,
                    delivered_count=1700,
                    opened_count=980,
                    clicked_count=310,
                    created_by=user,
                ),
            ]

            for campaign in campaigns:
                CampaignMetric.objects.get_or_create(
                    campaign=campaign,
                    date=timezone.now().date(),
                    defaults={
                        'sent': campaign.sent_count,
                        'delivered': campaign.delivered_count,
                        'opened': campaign.opened_count,
                        'clicked': campaign.clicked_count,
                        'created_by': user,
                    },
                )

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))

from django.core.management.base import BaseCommand
from accounts.permissions import create_user_groups


class Command(BaseCommand):
    help = 'Create user groups and assign permissions'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Creating user groups and permissions...')
        )
        
        try:
            create_user_groups()
            self.stdout.write(
                self.style.SUCCESS('Successfully created user groups and permissions')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating groups: {e}')
            )

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from accounts.models import User


class Command(BaseCommand):
    help = 'Assign existing users to appropriate groups based on their user_type'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-type',
            type=str,
            help='Assign only users of specific type (e.g., admin, doctor, patient)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Assigning users to groups based on user_type...')
        )
        
        # Filter users by type if specified
        users_queryset = User.objects.all()
        if options['user_type']:
            users_queryset = users_queryset.filter(user_type=options['user_type'])
        
        group_mapping = {
            'admin': 'Administrators',
            'doctor': 'Doctors',
            'nurse': 'Nurses',
            'receptionist': 'Receptionists',
            'patient': 'Patients',
            'lab_technician': 'Lab Technicians',
            'pharmacist': 'Pharmacists',
        }
        
        # Check if all groups exist
        missing_groups = []
        for group_name in group_mapping.values():
            if not Group.objects.filter(name=group_name).exists():
                missing_groups.append(group_name)
        
        if missing_groups:
            self.stdout.write(
                self.style.WARNING(
                    f'Missing groups: {", ".join(missing_groups)}. '
                    'Run "python manage.py setup_groups" first.'
                )
            )
            return
        
        updated_count = 0
        skipped_count = 0
        
        for user in users_queryset:
            group_name = group_mapping.get(user.user_type)
            
            if not group_name:
                self.stdout.write(
                    self.style.WARNING(
                        f'No group mapping for user {user.username} with type "{user.user_type}"'
                    )
                )
                skipped_count += 1
                continue
            
            try:
                group = Group.objects.get(name=group_name)
                
                # Check if user is already in the correct group
                current_groups = list(user.groups.values_list('name', flat=True))
                
                if options['dry_run']:
                    if group_name not in current_groups:
                        self.stdout.write(
                            f'Would assign {user.username} ({user.user_type}) to group "{group_name}"'
                        )
                        updated_count += 1
                    else:
                        self.stdout.write(
                            f'User {user.username} already in correct group "{group_name}"'
                        )
                        skipped_count += 1
                else:
                    if group_name not in current_groups:
                        # Remove user from all groups first
                        user.groups.clear()
                        # Add user to correct group
                        user.groups.add(group)
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Assigned {user.username} ({user.user_type}) to group "{group_name}"'
                            )
                        )
                        updated_count += 1
                    else:
                        self.stdout.write(
                            f'User {user.username} already in correct group "{group_name}"'
                        )
                        skipped_count += 1
                        
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Group "{group_name}" does not exist')
                )
                skipped_count += 1
        
        # Summary
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nDry run completed. Would update {updated_count} users, '
                    f'skipped {skipped_count} users.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nCompleted. Updated {updated_count} users, skipped {skipped_count} users.'
                )
            )
        
        # Show group statistics
        self.stdout.write('\nGroup membership statistics:')
        for user_type, group_name in group_mapping.items():
            try:
                group = Group.objects.get(name=group_name)
                user_count = group.user_set.count()
                self.stdout.write(f'  {group_name}: {user_count} users')
            except Group.DoesNotExist:
                self.stdout.write(f'  {group_name}: Group not found')

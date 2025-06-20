from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Migrate from SQLite to Neon PostgreSQL database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup-data',
            action='store_true',
            help='Create a data backup before migration',
        )
        parser.add_argument(
            '--load-data',
            action='store_true',
            help='Load data from backup after migration',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting migration to Neon PostgreSQL...')
        )
        
        # Check current database engine
        current_engine = settings.DATABASES['default']['ENGINE']
        
        if 'postgresql' in current_engine:
            self.stdout.write(
                self.style.SUCCESS('Already using PostgreSQL database!')
            )
            return
        
        # Step 1: Backup data if requested
        if options['backup_data']:
            self.stdout.write('Creating data backup...')
            try:
                call_command('dumpdata', 
                           '--natural-foreign', 
                           '--natural-primary',
                           '--exclude=contenttypes',
                           '--exclude=auth.permission',
                           '--exclude=sessions.session',
                           '--output=data_backup.json')
                self.stdout.write(
                    self.style.SUCCESS('Data backup created: data_backup.json')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating backup: {e}')
                )
                return
        
        # Step 2: Instructions for user
        self.stdout.write(
            self.style.WARNING('\n' + '='*60)
        )
        self.stdout.write(
            self.style.WARNING('MANUAL STEPS REQUIRED:')
        )
        self.stdout.write(
            self.style.WARNING('='*60)
        )
        self.stdout.write(
            '1. Update your .env file with Neon PostgreSQL credentials:'
        )
        self.stdout.write(
            '   DB_ENGINE=django.db.backends.postgresql'
        )
        self.stdout.write(
            '   DB_NAME=your_neon_database_name'
        )
        self.stdout.write(
            '   DB_USER=your_neon_username'
        )
        self.stdout.write(
            '   DB_PASSWORD=your_neon_password'
        )
        self.stdout.write(
            '   DB_HOST=your_neon_host.neon.tech'
        )
        self.stdout.write(
            '   DB_PORT=5432'
        )
        self.stdout.write('')
        self.stdout.write(
            '2. After updating .env, run:'
        )
        self.stdout.write(
            '   python manage.py migrate'
        )
        self.stdout.write('')
        self.stdout.write(
            '3. Create a new superuser:'
        )
        self.stdout.write(
            '   python manage.py createsuperuser'
        )
        self.stdout.write('')
        self.stdout.write(
            '4. Set up groups and permissions:'
        )
        self.stdout.write(
            '   python manage.py setup_groups'
        )
        
        if options['backup_data']:
            self.stdout.write('')
            self.stdout.write(
                '5. Load your data backup:'
            )
            self.stdout.write(
                '   python manage.py loaddata data_backup.json'
            )
        
        self.stdout.write(
            self.style.WARNING('='*60)
        )
        
        # Step 3: Load data if requested and PostgreSQL is configured
        if options['load_data']:
            if os.path.exists('data_backup.json'):
                self.stdout.write('Loading data from backup...')
                try:
                    call_command('loaddata', 'data_backup.json')
                    self.stdout.write(
                        self.style.SUCCESS('Data loaded successfully!')
                    )
                    
                    # Reassign users to groups
                    self.stdout.write('Reassigning users to groups...')
                    call_command('assign_user_groups')
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading data: {e}')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR('No backup file found: data_backup.json')
                )
        
        self.stdout.write(
            self.style.SUCCESS('\nMigration preparation complete!')
        )

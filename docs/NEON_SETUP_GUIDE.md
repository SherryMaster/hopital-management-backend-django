# Neon PostgreSQL Setup Guide

This guide will help you migrate from SQLite to Neon PostgreSQL for the Hospital Management System.

## Prerequisites

- ✅ PostgreSQL adapter already installed (`psycopg2-binary`)
- ✅ Database models and migrations ready
- ✅ Current SQLite database with data

## Step 1: Create Neon Database

1. **Go to Neon Console**: Visit [https://neon.tech](https://neon.tech)
2. **Create Account/Login**: Sign up or log in to your Neon account
3. **Create New Project**: 
   - Click "Create Project"
   - Choose a project name (e.g., "Hospital Management System")
   - Select your preferred region
4. **Create Database**:
   - Database name: `hospital_management_db` (or your preferred name)
   - Note down the connection details

## Step 2: Get Connection Details

From your Neon dashboard, copy the connection details:

```
Host: your-project-name.neon.tech
Database: hospital_management_db
Username: your_username
Password: your_password
Port: 5432
```

## Step 3: Update Environment Configuration

1. **Backup Current Data** (if you have important data):
   ```bash
   python manage.py migrate_to_neon --backup-data
   ```

2. **Update .env file** with your Neon credentials:
   ```env
   # Database Configuration (Neon PostgreSQL)
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=hospital_management_db
   DB_USER=your_neon_username
   DB_PASSWORD=your_neon_password
   DB_HOST=your-project-name.neon.tech
   DB_PORT=5432
   ```

## Step 4: Run Migrations

1. **Test Connection**:
   ```bash
   python manage.py check --database default
   ```

2. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

3. **Create Superuser**:
   ```bash
   python manage.py createsuperuser
   ```

4. **Setup Groups and Permissions**:
   ```bash
   python manage.py setup_groups
   ```

5. **Assign User to Groups**:
   ```bash
   python manage.py assign_user_groups
   ```

## Step 5: Load Data (if you have backup)

If you created a backup in Step 3:

```bash
python manage.py migrate_to_neon --load-data
```

## Step 6: Verify Setup

1. **Start Server**:
   ```bash
   python manage.py runserver
   ```

2. **Test Login**:
   ```bash
   curl -X POST http://localhost:8000/api/accounts/auth/login/ \
        -H "Content-Type: application/json" \
        -d '{"email": "your_admin_email", "password": "your_password"}'
   ```

3. **Check Database**:
   ```bash
   python manage.py shell -c "from django.db import connection; print('Connected to:', connection.settings_dict['NAME'])"
   ```

## Benefits of Using Neon PostgreSQL

- ✅ **Production-Ready**: Scalable PostgreSQL database
- ✅ **Automatic Backups**: Built-in backup and recovery
- ✅ **Branching**: Database branching for development
- ✅ **Monitoring**: Built-in monitoring and analytics
- ✅ **Security**: SSL connections and security features

## Troubleshooting

### Connection Issues
- Verify your Neon credentials are correct
- Check if your IP is whitelisted (Neon usually allows all IPs by default)
- Ensure the database name exists in your Neon project

### Migration Issues
- Make sure all migrations are applied: `python manage.py showmigrations`
- If you get permission errors, check your Neon user permissions

### Data Issues
- If data is missing, restore from backup: `python manage.py loaddata data_backup.json`
- Reassign users to groups: `python manage.py assign_user_groups`

## Current Status

- 🔄 **Currently using**: SQLite (development)
- 🎯 **Target**: Neon PostgreSQL (production-ready)
- 📋 **Action needed**: Update .env with your Neon credentials

## Quick Commands Reference

```bash
# Backup current data
python manage.py migrate_to_neon --backup-data

# After updating .env with Neon credentials:
python manage.py migrate
python manage.py createsuperuser
python manage.py setup_groups
python manage.py assign_user_groups

# Load backup data (if needed)
python manage.py migrate_to_neon --load-data

# Test connection
python manage.py shell -c "from django.db import connection; print('Database:', connection.settings_dict['NAME'])"
```

---

**Note**: The system is currently configured to work with both SQLite and PostgreSQL. Simply update the .env file with your Neon credentials to switch to PostgreSQL.

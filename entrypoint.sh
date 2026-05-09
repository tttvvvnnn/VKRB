#!/bin/sh
set -e

echo "==> Applying migrations..."
python manage.py migrate

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Checking superuser..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'Admin123!')
    print('Superuser created: admin / Admin123!')
else:
    print('Superuser already exists, skipping.')
"

echo "==> Seeding skills..."
python manage.py seed_skills

echo "==> Checking demo data..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(email='ivan.petrov@example.com').exists():
    from django.core.management import call_command
    call_command('seed_demo_data')
else:
    print('Demo data already exists, skipping.')
"

echo "==> Starting gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
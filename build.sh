#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

cd backend
python manage.py collectstatic --no-input
python manage.py migrate

# Create the initial admin only when credentials are configured and it is absent.
python manage.py shell -c "
from django.contrib.auth.models import User
import os
u = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
e = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
p = os.getenv('DJANGO_SUPERUSER_PASSWORD', '')
if p and not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u, e, p)
    print('Superuser created')
else:
    print('Superuser skipped (exists or no password)')
"

python manage.py seed_plans

cd ..

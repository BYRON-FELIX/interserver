#!/usr/bin/env bash
# Render build script — runs on every deploy.

set -o errexit

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cd backend
python manage.py collectstatic --no-input

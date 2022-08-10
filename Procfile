web: gunicorn UAMSAPI.wsgi --log-level debug

celeryworker: celery -A celeryconfig worker --loglevel INFO


celerybeatworker: celery -A celeryconfig beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

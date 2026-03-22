web: gunicorn index:server --workers 4 --timeout 60
worker: celery -A index:celery_instance worker --loglevel=INFO --concurrency=2 --max-tasks-per-child=1
scheduler: celery -A index:celery_instance beat --loglevel=INFO
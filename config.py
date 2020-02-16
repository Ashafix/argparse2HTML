import os

CELERY_BROKER_URL = 'redis://localhost:6379/0'
RESULT_BACKEND = 'redis://localhost:6379/0'
USE_CELERY = True
SERVER_PORT = 5000

JOB_FOLDER = os.path.join(os.getcwd(), 'jobs')

os.makedirs(JOB_FOLDER, exist_ok=True)

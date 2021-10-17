import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(os.path.join(BASE_DIR, 'mysite.sqlite3')),
    },
}

SECRET_KEY = "wow I'm a really bad default secret key"

ROOT_URLCONF = 'tests.urls'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'esi',
]

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# esi
ESI_API_URL = 'https://esi.evetech.net/'
ESI_SSO_CLIENT_ID = 'test-dummy'
ESI_SSO_CLIENT_SECRET = 'test-dummy'
ESI_SSO_CALLBACK_URL = 'http://localhost:8000'

# timezone.now() needs to be tz_aware
USE_TZ = True

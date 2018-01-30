import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'k028&n4$%6-r%+uro-go5i=9%ye)25-72j)_+k9$(#p(zd1k8v'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'db',
    }
}

SERVER_EMAIL = 'alert@communityasap.com'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = 'alert@communityasap.com'
EMAIL_HOST_PASSWORD = 'zarfpsvxlhwdrlcd'
DEFAULT_EMAIL_FROM = 'alert@communityasap.com'

TWILIO_SID = "ACf1f6f136d8234792eb2c2872d5dd850c"
TWILIO_AUTH_TOKEN = "554096e942d0d8382bfe034c1ed44bf1"
TWILIO_NUMBER = "+15874094405"

# This will have to change when added to production server
DOMAIN = "http://127.0.0.1:8000"
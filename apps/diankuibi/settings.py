import os
from pathlib import Path

from settings.database import DATABASE_SETTING
from settings.logging import LOGGING_SETTING

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = 'django-insecure-8el_o9*+bzonht%md+3rdh9y9zqx6@uow=sbhf!1o75$kgtm(j'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
]

# Automatically register all apps
INSTALLED_APPS += [
    f'{app.name}'
    for app in BASE_DIR.iterdir()
    if app.is_dir() and (app / "apps.py").exists()
]

CORS_ALLOW_ALL_ORIGINS = True

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(TEMPLATE_BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'diankuibi.wsgi.application'

DATABASES = DATABASE_SETTING

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'zh-hans'

USE_L10N = True

USE_TZ = True

TIME_ZONE = 'Asia/Shanghai'

STATIC_URL = 'static/'

STATICFILES_DIRS = [
    os.path.join(TEMPLATE_BASE_DIR, 'templates/static')
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ROOT_URLCONF = 'diankuibi.urls'

# Output log settings
LOGGING = LOGGING_SETTING

# Completely disable memory caching
FILE_UPLOAD_MAX_MEMORY_SIZE = 0

# Maximum volume of POST request
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024 * 10

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ]
}

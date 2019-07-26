INSTALLED_APPS = (
    'wagtailcsvimport',
    'tests',

    # third party apps
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'wagtail.admin',
    'wagtail.core',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.users',
    # wagtail dependencies
    'modelcluster',
    'taggit',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

SECRET_KEY = 'dummy'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

ROOT_URLCONF = 'tests.urls'

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'wagtail.core.middleware.SiteMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
    }
]

USE_TZ = True
TIME_ZONE = 'UTC'

WAGTAIL_SITE_NAME = 'wagtailcsvimport tests'

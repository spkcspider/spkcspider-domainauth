# flake8: noqa

from spkcspider.settings import *  # noqa: F403, F401

INSTALLED_APPS += [
    'spkcspider.apps.spider_keys',
    'spkcspider.apps.spider_tags',
    'spider_domainauth'

]
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

RATELIMIT_ENABLE = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'pleasechangeme124354'

# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
# specify fixtures directory for tests
FIXTURE_DIRS = [
     "tests/fixtures/"
]
DOMAINAUTH_URL = 'spider_domainauth:domainauth-db'

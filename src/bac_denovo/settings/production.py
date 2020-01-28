from .base import *
import sys
import logging.config

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Must mention ALLOWED_HOSTS in production!
ALLOWED_HOSTS = ['127.0.0.1']

# Turn off debug while imported by Celery with a workaround
# See http://stackoverflow.com/a/4806384
if 'celery' in sys.argv[0]:
    DEBUG = False

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env.str('EMAIL_HOST')
EMAIL_HOST_USER = env.str('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD')
EMAIL_PORT = env.int('EMAIL_PORT')
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS')
DEFAULT_FROM_EMAIL = 'MiDSystem <NO_REPLY@localhost>'


#db settings
#fix this for production
DATABASES = {
    # Raises ImproperlyConfigured exception if DATABASE_URL not in
    # os.environ
    #'default': env.db()
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'MiDSystem',                       # Or path to database file if using sqlite3.
        'USER': 'midsystem',                       # Not used with sqlite3.
        'PASSWORD': '***MiDSystem!Awesome$$$',               # Not used with sqlite3.
        'HOST': 'localhost',                           # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '3306',                           # Set to empty string for default. Not used with sqlite3.
    }
    
}

# Log everything to the logs directory at the top
LOGFILE_ROOT = join(dirname(BASE_DIR), 'logs')
INTERNAL_IPS=('127.0.0.1')

# Reset logging
# http://www.caktusgroup.com/blog/2015/01/27/
# Django-Logging-Configuration-logging_config-default-settings-logger/
LOGGING_CONFIG = None
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': (
                '[%(asctime)s] %(levelname)s '
                '[%(pathname)s:%(lineno)s] %(message)s'
            ),
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'django_log_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': join(LOGFILE_ROOT, 'django.log'),
            'formatter': 'verbose'
        },
        'proj_log_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': join(LOGFILE_ROOT, 'project.log'),
            'formatter': 'verbose'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['django_log_file', ],
            'propagate': True,
            'level': 'DEBUG',
        },
        # 'project': {
        #     'handlers': ['proj_log_file', 'console', ],
        #     'level': 'DEBUG',
        # },
    }
}

for app in LOCAL_APPS:
    LOGGING['loggers'][app] = {
        'handlers': ['proj_log_file', 'console', ],
        'level': 'DEBUG',
    }

logging.config.dictConfig(LOGGING)

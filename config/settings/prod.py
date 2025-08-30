# settings/prod.py
from .base import *

# PROD-specific overrides (예: DEBUG=False)
DEBUG = False
ALLOWED_HOSTS = ['15.164.219.24', 'localhost', '127.0.0.1']

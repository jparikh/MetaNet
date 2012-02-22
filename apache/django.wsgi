import os
import sys

root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, root)

os.environ['DJANGO_SETTINGS_MODULE'] = 'metanet.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
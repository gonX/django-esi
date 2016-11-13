from __future__ import unicode_literals
from django.conf import settings

# These are required in your project's settings.
ESI_SSO_CLIENT_ID = getattr(settings, 'ESI_SSO_CLIENT_ID')
ESI_SSO_CLIENT_SECRET = getattr(settings, 'ESI_SSO_CLIENT_SECRET')
ESI_SSO_CALLBACK_URL = getattr(settings, 'ESI_SSO_CALLBACK_URL')

# Change these to switch to Singularity
ESI_API_DATASOURCE = getattr(settings, 'ESI_API_DATASOURCE', 'tranquility')
ESI_OAUTH_URL = getattr(settings, 'ESI_SSO_BASE_URL', 'https://login.eveonline.com/oauth')

# Change this to access different revisions of the ESI API
ESI_API_VERSION = getattr(settings, 'ESI_API_VERSION', 'latest')

# These probably won't ever change. Override if needed.
ESI_API_URL = getattr(settings, 'ESI_API_URL', 'https://esi.tech.ccp.is/')
ESI_SWAGGER_URL = getattr(settings, 'ESI_SWAGGER_URL', ESI_API_URL + ESI_API_VERSION + '/swagger.json')
ESI_OAUTH_LOGIN_URL = getattr(settings, 'ESI_SSO_LOGIN_URL', ESI_OAUTH_URL + "/authorize/")
ESI_TOKEN_URL = getattr(settings, 'ESI_CODE_EXCHANGE_URL', ESI_OAUTH_URL + "/token")
ESI_TOKEN_VERIFY_URL = getattr(settings, 'ESI_TOKEN_EXCHANGE_URL', ESI_OAUTH_URL + "/verify")
ESI_TOKEN_VALID_DURATION = int(getattr(settings, 'ESI_TOKEN_VALID_DURATION', 1200))
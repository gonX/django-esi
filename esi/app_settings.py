from django.conf import settings

# These are required for SSO to function. 
# Can be left blank if settings.DEBUG is set to True
ESI_SSO_CLIENT_ID = getattr(settings, 'ESI_SSO_CLIENT_ID', None)
ESI_SSO_CLIENT_SECRET = getattr(settings, 'ESI_SSO_CLIENT_SECRET', None)
ESI_SSO_CALLBACK_URL = getattr(settings, 'ESI_SSO_CALLBACK_URL', None)

# Change these to switch to Singularity
ESI_API_DATASOURCE = getattr(settings, 'ESI_API_DATASOURCE', 'tranquility')
ESI_OAUTH_URL = getattr(
    settings, 'ESI_SSO_BASE_URL', 'https://login.eveonline.com/oauth'
)

# Change this to access different revisions of the ESI API by default
ESI_API_VERSION = getattr(settings, 'ESI_API_VERSION', 'latest')

# Enable to force new token creation every callback
ESI_ALWAYS_CREATE_TOKEN = getattr(settings, 'ESI_ALWAYS_CREATE_TOKEN', False)

# Disable to stop caching endpoint responses
ESI_CACHE_RESPONSE = getattr(settings, 'ESI_CACHE_RESPONSE', True)

# Enable/disable verbose info logging
ESI_INFO_LOGGING_ENABLED = getattr(settings, 'ESI_INFO_LOGGING_ENABLED', False)

# Set log level for libraries like bravado and urlib3
ESI_LOG_LEVEL_LIBRARIES = str(getattr(settings, 'ESI_LOG_LEVEL_LIBRARIES', 'INFO'))

# Max size of the connection pool. Increase this setting if you hav more parallel
# threads connected to ESI at the same time.
ESI_CONNECTION_POOL_MAXSIZE = getattr(settings, 'ESI_CONNECTION_POOL_MAXSIZE', 10)

# Max retries on failed connections
ESI_CONNECTION_ERROR_MAX_RETRIES = getattr(
    settings, 'ESI_CONNECTION_ERROR_MAX_RETRIES', 3
)

# Max retries on server errors
ESI_SERVER_ERROR_MAX_RETRIES = getattr(settings, 'ESI_SERVER_ERROR_MAX_RETRIES', 3)

# Backoff factor for retries on server error
ESI_SERVER_ERROR_BACKOFF_FACTOR = getattr(
    settings, 'ESI_SERVER_ERROR_BACKOFF_FACTOR', 0.2
)

# Default timeouts for all requests to ESI. 
# Can be overwritten by passing "timeout" with result()
ESI_REQUESTS_CONNECT_TIMEOUT = getattr(settings, 'ESI_REQUESTS_CONNECT_TIMEOUT', 5)
ESI_REQUESTS_READ_TIMEOUT = getattr(settings, 'ESI_REQUESTS_READ_TIMEOUT', 30)

# These probably won't ever change. Override if needed.
ESI_API_URL = getattr(settings, 'ESI_API_URL', 'https://esi.evetech.net/')
ESI_OAUTH_LOGIN_URL = getattr(
    settings, 'ESI_SSO_LOGIN_URL', ESI_OAUTH_URL + "/authorize/"
)
ESI_TOKEN_URL = getattr(settings, 'ESI_CODE_EXCHANGE_URL', ESI_OAUTH_URL + "/token")
ESI_TOKEN_VERIFY_URL = getattr(
    settings, 'ESI_TOKEN_EXCHANGE_URL', ESI_OAUTH_URL + "/verify"
)
ESI_TOKEN_VALID_DURATION = int(getattr(settings, 'ESI_TOKEN_VALID_DURATION', 1170))
ESI_SPEC_CACHE_DURATION = int(getattr(settings, 'ESI_SPEC_CACHE_DURATION', 3600))

# list of all official language codes supported by ESI
ESI_LANGUAGES = getattr(settings, 'ESI_LANGUAGES', [
    'de', 'en-us', 'fr', 'ja', 'ru', 'zh', 'ko'
])

from datetime import datetime
from hashlib import md5
import json
import logging
from time import sleep
from urllib import parse as urlparse

from bravado.client import SwaggerClient
from bravado import requests_client
from bravado.exception import (
    HTTPBadGateway, HTTPGatewayTimeout, HTTPServiceUnavailable
)
from bravado.swagger_model import Loader
from bravado.http_future import HttpFuture
from bravado_core.spec import Spec, CONFIG_DEFAULTS
from requests.adapters import HTTPAdapter

from django.core.cache import cache

from .errors import TokenExpiredError
from . import app_settings


logger = logging.getLogger(__name__)

_LIBRARIES_LOG_LEVEL = logging.getLevelName(app_settings.ESI_LOG_LEVEL_LIBRARIES)
logging.getLogger('swagger_spec_validator').setLevel(_LIBRARIES_LOG_LEVEL)
logging.getLogger('bravado_core').setLevel(_LIBRARIES_LOG_LEVEL)
logging.getLogger('urllib3').setLevel(_LIBRARIES_LOG_LEVEL)
logging.getLogger('bravado').setLevel(_LIBRARIES_LOG_LEVEL)

SPEC_CONFIG = {'use_models': False}
RETRY_SLEEP_SECS = 1


class CachingHttpFuture(HttpFuture):
    """
    Used to add caching to certain HTTP requests according to "Expires" header
    """    
    def _cache_key(self):
        """
        Generated the key name used to cache responses        
        :return: formatted cache name
        """
        request = self.future.request
        str_hash = md5(
            (
                request.method 
                + request.url 
                + str(request.params) 
                + str(request.data) 
                + str(request.json)
            ).encode('utf-8')
        ).hexdigest()
        return 'esi_%s' % str_hash

    @staticmethod
    def _time_to_expiry(expires):
        """
        Determines the seconds until a HTTP header "Expires" timestamp
        :param expires: HTTP response "Expires" header
        :return: seconds until "Expires" time
        """
        try:
            expires_dt = datetime.strptime(str(expires), '%a, %d %b %Y %H:%M:%S %Z')
            delta = expires_dt - datetime.utcnow()
            return delta.total_seconds()
        except ValueError:
            return 0

    def results(self, **kwargs):
        """Executes the request and returns the response from ESI for the current 
        route. Response will include all pages if there are more available.

        Optional parameters:
        - timeout: timeout for request to ESI in seconds, overwrites default
        """
        results = list()
        headers = None
        # preserve original value
        _also_return_response = self.request_config.also_return_response
        # override to always get the raw response for expiry header
        self.request_config.also_return_response = True  
        
        if "page" in self.operation.params:
            current_page = 1
            total_pages = 1
           
            # loop all pages and add data to output array
            while current_page <= total_pages:  
                self.future.request.params["page"] = current_page                
                # will use cache if applicable
                result, headers = self.result(**kwargs)
                total_pages = int(headers.headers['X-Pages'])  
                # append to results list to be seamless to the client
                results += result  
                current_page += 1
        else:  # it doesn't so just return
            results, headers = self.result(**kwargs)

        # restore original value
        self.request_config.also_return_response = _also_return_response  

        # obey the output 
        if self.request_config.also_return_response:  
            return results, headers
        else:
            return results

    def results_localized(self, languages: list = None, **kwargs) -> dict:
        """Executes the request and returns the response from ESI for all default
        languages and pages (if any). This method returns a dict of all responses 
        with the language code as keys.

        Optional parameters:
        - languages: list of languages to return instead of all default languages
        - timeout: timeout for request to ESI in seconds, overwrites default
        """
        if not languages:
            my_languages = list(app_settings.ESI_LANGUAGES)
        else:
            my_languages = []
            for lang in dict.fromkeys(languages):
                if lang not in app_settings.ESI_LANGUAGES:
                    raise ValueError('Invalid language code: %s' % lang)
                my_languages.append(lang)
        
        return {
            language: self.results(language=language, **kwargs) 
            for language in my_languages
        }

    def result(self, **kwargs):
        """Executes the request and returns the response from ESI. Response will
        include the requested / first page only if there are more pages available.

        Optional parameters:
        - timeout: timeout for request to ESI in seconds, overwrites default
        - retries: max number of retries, overwrites default
        """
        if 'language' in kwargs.keys():
            # this parameter is not supported by bravado, so we can't pass it on
            self.future.request.params['language'] = str(kwargs.pop('language'))

        if 'retries' in kwargs.keys():            
            max_retries = int(kwargs.pop('retries'))
        else:
            max_retries = int(app_settings.ESI_SERVER_ERROR_MAX_RETRIES)
        
        max_retries = max(0, max_retries)

        if 'timeout' not in kwargs:
            kwargs['timeout'] = (
                app_settings.ESI_REQUESTS_CONNECT_TIMEOUT,
                app_settings.ESI_REQUESTS_READ_TIMEOUT
            )
        
        if (
            app_settings.ESI_CACHE_RESPONSE 
            and self.future.request.method == 'GET' 
            and self.operation is not None
        ):           
            result = None
            response = None
            cache_key = self._cache_key()
            try:
                cached = cache.get(cache_key)
            except Exception:
                cached = None
                logger.warning(
                    "Attempt to read ESI results from cache failed", exc_info=True
                )

            if cached:
                result, response = cached
                expiry = self._time_to_expiry(str(response.headers.get('Expires')))
                if expiry < 0:
                    logger.warning(
                        "cache expired by %d seconds, Forcing expiry", expiry
                    )
                    cached = False

            if not cached:
                # preserve original value
                _also_return_response = self.request_config.also_return_response  
                # override to always get the raw response for expiry header
                self.request_config.also_return_response = True
                
                retries = 0
                while retries <= max_retries:
                    try:
                        if app_settings.ESI_INFO_LOGGING_ENABLED:
                            params = self.future.request.params
                            logger.info(
                                'Fetching from ESI: %s%s%s',
                                self.future.request.url,
                                f' - language {params["language"]}' 
                                if 'language' in params else '',
                                f' - page {params["page"]}' 
                                if 'page' in params else ''
                            )
                        logger.debug(
                            'ESI request: %s - %s',
                            self.future.request.url,
                            self.future.request.params
                        )
                        logger.debug(
                            'ESI request headers: %s', self.future.request.headers
                        )
                        result, response = super().result(**kwargs)
                        logger.debug(
                            'ESI response status code: %s', response.status_code
                        )
                        logger.debug('ESI response headers: %s', response.headers)
                        logger.debug('ESI response content: %s', response.text)
                        break
                    except (
                        HTTPBadGateway, HTTPGatewayTimeout, HTTPServiceUnavailable
                    ) as ex:
                        if retries < max_retries:
                            logger.warning(
                                "ESI error (Retry: %d/%d)", 
                                retries, 
                                max_retries,
                                exc_info=True
                            )
                            if retries > 0:
                                wait_secs = (
                                    app_settings.ESI_SERVER_ERROR_BACKOFF_FACTOR 
                                    * (2 ** (retries - 1))
                                )
                                sleep(wait_secs)
                            retries += 1
                        else:
                            raise ex
                
                # restore original value
                self.request_config.also_return_response = _also_return_response  

                if response and 'Expires' in response.headers:
                    expires = self._time_to_expiry(response.headers['Expires'])
                    if expires > 0:
                        try:
                            cache.set(cache_key, (result, response), expires)
                        except Exception:
                            logger.warning(
                                "Failed to write ESI result to cache", exc_info=True
                            )

            if self.request_config.also_return_response:
                return result, response
            else:
                return result
        else:
            return super().result(**kwargs)


requests_client.HttpFuture = CachingHttpFuture


class TokenAuthenticator(requests_client.Authenticator):
    """
    Adds the authorization header containing access token, if specified.
    Sets ESI datasource to tranquility or singularity.
    """

    def __init__(self, token=None, datasource=None):
        host = urlparse.urlsplit(app_settings.ESI_API_URL).hostname
        super().__init__(host)
        self.token = token
        self.datasource = datasource

    def apply(self, request):
        if self.token and self.token.expired:
            if self.token.can_refresh:
                self.token.refresh()
            else:
                raise TokenExpiredError()
        request.headers['Authorization'] = \
            'Bearer ' + self.token.access_token if self.token else None
        request.params['datasource'] = \
            self.datasource or app_settings.ESI_API_DATASOURCE
        return request


def build_cache_name(name):
    """
    Cache key name formatter
    :param name: Name of the spec dict to cache, usually version
    :return: String name for cache key
    :rtype: str
    """
    return 'esi_swaggerspec_%s' % name


def cache_spec(name, spec):
    """
    Cache the spec dict
    :param name: Version name
    :param spec: Spec dict
    :return: True if cached
    """
    return cache.set(
        build_cache_name(name), spec, app_settings.ESI_SPEC_CACHE_DURATION
    )


def build_spec_url(spec_version):
    """
    Generates the URL to swagger.json for the ESI version
    :param spec_version: Name of the swagger spec version, like latest or v4
    :return: URL to swagger.json for the requested spec version
    """
    return urlparse.urljoin(app_settings.ESI_API_URL, spec_version + '/swagger.json')


def get_spec(name, http_client=None, config=None):
    """
    :param name: Name of the revision of spec, eg latest or v4
    :param http_client: Requests client used for retrieving specs
    :param config: Spec configuration - see Spec.CONFIG_DEFAULTS
    :return: :class:`bravado_core.spec.Spec`
    """
    http_client = http_client or requests_client.RequestsClient()

    def load_spec():
        loader = Loader(http_client)
        return loader.load_spec(build_spec_url(name))

    spec_dict = cache.get_or_set(
        build_cache_name(name), load_spec, app_settings.ESI_SPEC_CACHE_DURATION
    )
    config = dict(CONFIG_DEFAULTS, **(config or {}))
    return Spec.from_dict(spec_dict, build_spec_url(name), http_client, config)


def build_spec(base_version, http_client=None, **kwargs):
    """
    Generates the Spec used to initialize a SwaggerClient, 
    supporting mixed resource versions
    :param http_client: :class:`bravado.requests_client.RequestsClient`
    :param base_version: Version to base the spec on. 
    Any resource without an explicit version will be this.
    :param kwargs: Explicit resource versions, by name (eg Character='v4')
    :return: :class:`bravado_core.spec.Spec`
    """
    base_spec = get_spec(base_version, http_client=http_client, config=SPEC_CONFIG)
    if kwargs:
        for resource, resource_version in kwargs.items():
            versioned_spec = get_spec(
                resource_version, http_client=http_client, config=SPEC_CONFIG
            )
            try:
                spec_resource = versioned_spec.resources[resource.capitalize()]
            except KeyError:
                raise AttributeError(
                    'Resource {0} not found on API revision {1}'.format(
                        resource, resource_version
                    )
                )
            base_spec.resources[resource.capitalize()] = spec_resource
    return base_spec


def read_spec(path, http_client=None):
    """
    Reads in a swagger spec file used to initialize a SwaggerClient
    :param path: String path to local swagger spec file.
    :param http_client: :class:`bravado.requests_client.RequestsClient`
    :return: :class:`bravado_core.spec.Spec`
    """
    with open(path, 'r', encoding='utf-8') as f:
        spec_dict = json.loads(f.read())

    return SwaggerClient.from_spec(
        spec_dict, http_client=http_client, config=SPEC_CONFIG
    )


def esi_client_factory(
    token=None, datasource=None, spec_file=None, version=None, **kwargs
):
    """
    Generates an ESI client.
    :param token: :class:`esi.Token` used to access authenticated endpoints.
    :param datasource: Name of the ESI datasource to access.
    :param spec_file: Absolute path to a swagger spec file to load.
    :param version: Base ESI API version. Accepted values are 'legacy', 'latest', 
    'dev', or 'vX' where X is a number.
    :param kwargs: Explicit resource versions to build, in the form Character='v4'. 
    Same values accepted as version.
    :return: :class:`bravado.client.SwaggerClient`

    If a spec_file is specified, specific versioning is not available. 
    Meaning the version and resource version kwargs
    are ignored in favour of the versions available in the spec_file.
    """    
    if app_settings.ESI_INFO_LOGGING_ENABLED:
        logger.info('Generating an ESI client...')
    client = requests_client.RequestsClient()
    my_http_adapter = HTTPAdapter(
        pool_maxsize=app_settings.ESI_CONNECTION_POOL_MAXSIZE, 
        max_retries=app_settings.ESI_CONNECTION_ERROR_MAX_RETRIES
    )
    client.session.mount('https://', my_http_adapter)
    
    if token or datasource:
        client.authenticator = TokenAuthenticator(token=token, datasource=datasource)

    api_version = version or app_settings.ESI_API_VERSION

    if spec_file:
        return read_spec(spec_file, http_client=client)
    else:
        spec = build_spec(api_version, http_client=client, **kwargs)
        return SwaggerClient(spec)


def minimize_spec(spec_dict, operations=None, resources=None):
    """
    Trims down a source spec dict to only the operations or resources indicated.
    :param spec_dict: The source spec dict to minimize.
    :type spec_dict: dict
    :param operations: A list of operation IDs to retain.
    :type operations: list of str
    :param resources: A list of resource names to retain.
    :type resources: list of str
    :return: Minimized swagger spec dict
    :rtype: dict
    """
    operations = operations or []
    resources = resources or []

    # keep the ugly overhead for now but only add paths we need
    minimized = {key: value for key, value in spec_dict.items() if key != 'paths'}
    minimized['paths'] = {}

    for path_name, path in spec_dict['paths'].items():
        for method, data in path.items():
            if (
                data['operationId'] in operations 
                or any(tag in resources for tag in data['tags'])
            ):
                if path_name not in minimized['paths']:
                    minimized['paths'][path_name] = {}
                minimized['paths'][path_name][method] = data

    return minimized


class EsiClientProvider:
    """Class for providing a single ESI client instance for the whole app"""

    _client = None
    
    def __init__(self, datasource=None, spec_file=None, version=None, **kwargs):
        """        
        :param datasource: Name of the ESI datasource to access.
        :param spec_file: Absolute path to a swagger spec file to load.
        :param version: Base ESI API version. 
        Accepted values are 'legacy', 'latest', 'dev', or 'vX' where X is a number.
        :param kwargs: Explicit resource versions to build, 
        in the form Character='v4'. Same values accepted as version.        

        If a spec_file is specified, specific versioning is not available. 
        Meaning the version and resource version kwargs
        are ignored in favour of the versions available in the spec_file.
        """
        self._datasource = datasource
        self._spec_file = spec_file
        self._version = version
        self._kwargs = kwargs

    @property
    def client(self):
        if self._client is None:
            self._client = esi_client_factory(
                datasource=self._datasource,                
                spec_file=self._spec_file,
                version=self._version,
                **self._kwargs,
            )
        return self._client

    def __str__(self):
        return 'EsiClientProvider'

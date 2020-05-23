from datetime import datetime, timedelta
import logging
import os
from unittest.mock import patch, Mock
import json

import bravado
from bravado_core.spec import Spec
from bravado.requests_client import RequestsClient
from requests.exceptions import ConnectionError

import django
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from . import _generate_token, _store_as_Token, _set_logger
from ..clients import (
    MAX_RETRIES, 
    EsiClientProvider, 
    esi_client_factory, 
    TokenAuthenticator, 
    build_cache_name,
    build_spec,
    build_spec_url,    
    cache_spec,
    get_spec,
    read_spec,
    minimize_spec,
    SwaggerClient,
    CachingHttpFuture
)
from ..errors import TokenExpiredError

SWAGGER_SPEC_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    'test_swagger.json'
) 

_set_logger(logging.getLogger('esi.clients'), __file__)


class TestClientCache(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.c = esi_client_factory(spec_file=SWAGGER_SPEC_PATH)

    @patch.object(django.core.cache.cache, 'set')
    @patch.object(django.core.cache.cache, 'get')
    @patch.object(bravado.http_future.HttpFuture, 'result')
    def test_cache_expire(self, result_hit, cache_hit, cache_set):
        cache.clear()

        class MockResultFuture:
            def __init__(self):
                dt = datetime.utcnow().replace(tzinfo=timezone.utc) \
                    + timedelta(seconds=60)
                self.headers = {'Expires': dt.strftime('%a, %d %b %Y %H:%M:%S %Z')}

        class MockResultPast:
            def __init__(self):
                dt = datetime.utcnow().replace(tzinfo=timezone.utc) \
                    - timedelta(seconds=60)
                self.headers = {'Expires': dt.strftime('%a, %d %b %Y %H:%M:%S %Z')}

        result_hit.return_value = ({'players': 500}, MockResultFuture())
        cache_hit.return_value = False

        # hit api
        r = self.c.Status.get_status().result()
        self.assertEquals(r['players'], 500)

        cache_hit.return_value = ({'players': 50}, MockResultFuture())
        # hit cache and pass
        r = self.c.Status.get_status().result()
        self.assertEquals(r['players'], 50)

        cache_hit.return_value = ({'players': 50}, MockResultPast())
        # hit cache fail, re-hit api
        r = self.c.Status.get_status().result()
        self.assertEquals(r['players'], 500)


@patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 3)
class TestTokenAuthenticator(TestCase):

    def setUp(self):        
        self.user = User.objects.create_user(
            'Bruce Wayne',
            'abc@example.com',
            'password'
        )
        self.token = _store_as_Token(
            _generate_token(
                character_id=101,
                character_name=self.user.username,
                scopes=['abc'],
                access_token='my_access_token'
            ), 
            self.user
        )        

    @patch(
        'esi.clients.app_settings.ESI_API_URL', 
        'https://www.example.com/esi/'
    )
    @patch('esi.clients.app_settings.ESI_API_DATASOURCE', 'dummy')
    def test_apply_defaults(self):
        request = Mock()
        request.headers = dict()
        request.params = dict()

        x = TokenAuthenticator()
        request2 = x.apply(request)
        self.assertEqual(
            request2.headers['Authorization'],
            None
        )
        self.assertEqual(
            request2.params['datasource'],
            'dummy'
        )

    @patch(
        'esi.clients.app_settings.ESI_API_URL', 
        'https://www.example.com/esi/'
    )
    @patch('esi.clients.app_settings.ESI_API_DATASOURCE', 'dummy')
    def test_apply_token(self):
        request = Mock()
        request.headers = dict()
        request.params = dict()

        x = TokenAuthenticator(token=self.token)
        request2 = x.apply(request)
        self.assertEqual(
            request2.headers['Authorization'],
            'Bearer my_access_token'
        )
        self.assertEqual(
            request2.params['datasource'],
            'dummy'
        )

    @patch(
        'esi.clients.app_settings.ESI_API_URL', 
        'https://www.example.com/esi/'
    )
    @patch('esi.clients.app_settings.ESI_API_DATASOURCE', 'dummy')
    def test_apply_token_datasource(self):
        request = Mock()
        request.headers = dict()
        request.params = dict()

        x = TokenAuthenticator(token=self.token, datasource='dummy2')
        request2 = x.apply(request)
        self.assertEqual(
            request2.headers['Authorization'],
            'Bearer my_access_token'
        )
        self.assertEqual(
            request2.params['datasource'],
            'dummy2'
        )

    @patch(
        'esi.clients.app_settings.ESI_API_URL', 
        'https://www.example.com/esi/'
    )
    @patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    @patch('esi.clients.app_settings.ESI_API_DATASOURCE', 'dummy')
    @patch('esi.models.Token.refresh', autospec=True)
    def test_apply_token_expired_success(self, mock_Token_refresh):
        request = Mock()
        request.headers = dict()
        request.params = dict()

        self.token.created -= timedelta(121)
        
        x = TokenAuthenticator(token=self.token)
        request2 = x.apply(request)
        self.assertEqual(
            request2.headers['Authorization'],
            'Bearer my_access_token'
        )
        self.assertEqual(
            request2.params['datasource'],
            'dummy'
        )
        self.assertEqual(mock_Token_refresh.call_count, 1)

    @patch(
        'esi.clients.app_settings.ESI_API_URL', 
        'https://www.example.com/esi/'
    )
    @patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    @patch('esi.clients.app_settings.ESI_API_DATASOURCE', 'dummy')
    @patch('esi.models.Token.refresh', autospec=True)
    def test_apply_token_expired_failed(self, mock_Token_refresh):
        
        request = Mock()
        request.headers = dict()
        request.params = dict()

        self.token.created -= timedelta(121)
        self.token.refresh_token = None
        
        x = TokenAuthenticator(token=self.token)
        with self.assertRaises(TokenExpiredError):
            x.apply(request)
        
        self.assertEqual(mock_Token_refresh.call_count, 0)


class TestModuleFunctions(TestCase):
    
    @classmethod
    def setUpClass(cls):        
        super(TestModuleFunctions, cls).setUpClass()        
        with open(SWAGGER_SPEC_PATH, 'r', encoding='utf-8') as f:
            cls.test_spec_dict = json.load(f)

    def test_build_cache_name(self):
        self.assertEqual(
            build_cache_name('abc'),
            'esi_swaggerspec_abc'
        )

    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 3)
    def test_cache_spec(self):
        spec = {
            'dummy_spec': True
        }
        cache_spec('abc', spec)
        self.assertDictEqual(
            cache.get('esi_swaggerspec_abc'),
            spec
        )

    @patch('esi.clients.app_settings.ESI_API_URL', 'https://www.example.com/esi/')
    def test_build_spec_url(self):
        self.assertEqual(
            build_spec_url('v2'), 'https://www.example.com/esi/v2/swagger.json'
        )

    @patch('esi.clients.requests_client.RequestsClient', autospec=True)
    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)
    def test_get_spec_defaults(self, mock_RequestsClient):        
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        spec = get_spec('latest')
        self.assertIsInstance(spec, Spec)

    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)                
    def test_get_spec_with_http_client(self):        
        mock_http_client = Mock(spec=RequestsClient)
        mock_http_client.request.return_value.result.return_value.json.return_value = \
            self.test_spec_dict
        spec = get_spec('latest', http_client=mock_http_client)
        self.assertIsInstance(spec, Spec)

    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)                
    def test_get_spec_with_config(self):        
        mock_http_client = Mock(spec=RequestsClient)
        mock_http_client.request.return_value.result.return_value.json.return_value = \
            self.test_spec_dict
        spec = get_spec(
            'latest', 
            http_client=mock_http_client, 
            config={'dummy_config': True}
        )
        self.assertIsInstance(spec, Spec)
        self.assertIn('dummy_config', spec.config)

    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)    
    def test_build_spec_defaults(self):        
        mock_http_client = Mock(spec=RequestsClient)
        mock_http_client.request.return_value.result.return_value\
            .json.return_value = self.test_spec_dict
        spec = build_spec('v1', http_client=mock_http_client)
        self.assertIsInstance(spec, Spec)

    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)    
    def test_build_spec_explicit_resource_found(self):        
        mock_http_client = Mock(spec=RequestsClient)
        mock_http_client.request.return_value.result.return_value\
            .json.return_value = self.test_spec_dict
        spec = build_spec('v1', http_client=mock_http_client, Status='v1')
        self.assertIsInstance(spec, Spec)
    
    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)    
    def test_build_spec_explicit_resource_not_found(self):        
        mock_http_client = Mock(spec=RequestsClient)
        mock_http_client.request.return_value.result.return_value\
            .json.return_value = self.test_spec_dict
        with self.assertRaises(AttributeError):
            build_spec('v1', http_client=mock_http_client, Character='v4')

    def test_read_spec(self):
        mock_http_client = Mock(spec=RequestsClient)
        mock_http_client.request.return_value.result.return_value\
            .json.return_value = self.test_spec_dict

        client = read_spec(SWAGGER_SPEC_PATH)
        self.assertIsInstance(client, SwaggerClient)

    def test_minimize_spec_defaults(self):
        spec_dict = minimize_spec(self.test_spec_dict)
        self.assertIsInstance(spec_dict, dict)
        # todo: add better verification of functionality
    
    def test_minimize_spec_resources(self):
        spec_dict = minimize_spec(self.test_spec_dict, resources=['Status'])
        self.assertIsInstance(spec_dict, dict)
        # todo: add better verification of functionality


class TestEsiClientFactory(TestCase):
    
    @classmethod
    def setUpClass(cls):        
        super(TestEsiClientFactory, cls).setUpClass()        
        with open(SWAGGER_SPEC_PATH, 'r', encoding='utf-8') as f:
            cls.test_spec_dict = json.load(f)

    def setUp(self):        
        self.user = User.objects.create_user(
            'Bruce Wayne',
            'abc@example.com',
            'password'
        )
        self.token = _store_as_Token(
            _generate_token(
                character_id=101,
                character_name=self.user.username,
                scopes=['abc'],
                access_token='my_access_token'
            ), 
            self.user
        )        

    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)
    @patch('esi.clients.requests_client.RequestsClient', autospec=True)
    def test_minimal_client(self, mock_RequestsClient):
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory()
        self.assertIsInstance(client, SwaggerClient)

    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)
    @patch('esi.clients.requests_client.RequestsClient', autospec=True)
    def test_client_with_token(self, mock_RequestsClient):
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory(token=self.token)
        self.assertIsInstance(client, SwaggerClient)

    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)
    @patch('esi.clients.requests_client.RequestsClient', autospec=True)
    def test_client_with_datasource(self, mock_RequestsClient):
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory(datasource='singularity')
        self.assertIsInstance(client, SwaggerClient)

    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)
    @patch('esi.clients.requests_client.RequestsClient', autospec=True)
    def test_client_with_version(self, mock_RequestsClient):
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory(version='v1')
        self.assertIsInstance(client, SwaggerClient)

    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)
    @patch('esi.clients.requests_client.RequestsClient', autospec=True)
    def test_client_with_spec_file(self, mock_RequestsClient):
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory(spec_file=SWAGGER_SPEC_PATH)
        self.assertIsInstance(client, SwaggerClient)

    @patch('esi.clients.app_settings.ESI_SPEC_CACHE_DURATION', 1)
    @patch('esi.clients.requests_client.RequestsClient', autospec=True)
    def test_client_with_explicit_resource(self, mock_RequestsClient):
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory(Status='v1')
        self.assertIsInstance(client, SwaggerClient)

    def test__time_to_expiry_failure(self):
        seconds = CachingHttpFuture._time_to_expiry("fail")
        self.assertEqual(seconds, 0)


class TestClientResults(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.c = esi_client_factory()

    @patch.object(bravado.http_future.HttpFuture, 'result')
    def test_retry(self, request_hit):
        request_hit.side_effect = ConnectionError()
        try:
            self.c.Status.get_status().result()
        except ConnectionError as e:
            # requests error thrown
            self.assertIsInstance(e, ConnectionError)  
            # we tried # times before raising
            self.assertEqual(request_hit.call_count, MAX_RETRIES)  
    
    @patch.object(bravado.http_future.HttpFuture, 'result')
    def test_pages(self, request_hit):
        class MockResultHeaders:
            def __init__(self):
                self.headers = {'X-Pages': 10}

        request_hit.return_value = ({"contract_test": 1}, MockResultHeaders())
        self.c.Contracts.get_contracts_public_region_id(region_id=1).result_all_pages()
        self.assertEqual(request_hit.call_count, 10)  # we got 10 pages of data

    @patch.object(bravado.http_future.HttpFuture, 'result')
    def test_pages_response(self, request_hit):
        class MockResultHeaders:
            def __init__(self):
                self.headers = {'X-Pages': 10}

        request_hit.return_value = ({"contract_test": 1}, MockResultHeaders())
        o = self.c.Contracts.get_contracts_public_region_id(region_id=1)
        o.request_config.also_return_response = True
        result, response = o.result_all_pages()
        self.assertEqual(request_hit.call_count, 10)  # we got 10 pages of data
        self.assertEqual(len(result), 10)   # we got 10 lots of data
        self.assertEqual(response.headers, {'X-Pages': 10})  # we got header of data

    @patch.object(bravado.http_future.HttpFuture, 'result')
    def test_pages_on_non_paged_endpoint(self, request_hit):
        class MockResultHeaders:
            def __init__(self):
                self.headers = {'header_test': "ok"}

        request_hit.return_value = ({"status_test": 1}, MockResultHeaders())

        self.c.Status.get_status().result_all_pages()
        self.assertEqual(request_hit.call_count, 1)     # we got no pages of data


class TestEsiClientProvider(TestCase):    
    
    @patch('esi.clients.esi_client_factory')
    def test_client_loads_on_demand(
        self, mock_esi_client_factory
    ):
        mock_esi_client_factory.return_value = 'my_client'
        
        # create client on demand when called the first time
        my_provider = EsiClientProvider()
        self.assertFalse(mock_esi_client_factory.called)
        self.assertIsNone(my_provider._client)
        my_client = my_provider.client
        self.assertTrue(mock_esi_client_factory.call_count, 1)
        self.assertIsNotNone(my_provider._client)
        self.assertEqual(my_client, 'my_client')

        # re-use same client when called again
        new_client = my_provider.client
        self.assertTrue(mock_esi_client_factory.call_count, 1)
        self.assertEqual(my_client, new_client)
        
    @patch('esi.clients.esi_client_factory')
    def test_str(self, mock_esi_client_factory):        
        my_provider = EsiClientProvider()
        self.assertEqual(str(my_provider), 'EsiClientProvider')

    @patch('esi.clients.esi_client_factory')
    def test_with_datasource(self, mock_esi_client_factory):
        my_provider = EsiClientProvider(datasource='dummy')
        my_provider.client()
        self.assertTrue(mock_esi_client_factory.called)        
        args, kwargs = mock_esi_client_factory.call_args
        self.assertEqual(kwargs['datasource'], 'dummy')

    @patch('esi.clients.esi_client_factory')
    def test_with_spec_file(self, mock_esi_client_factory):
        my_provider = EsiClientProvider(spec_file='dummy')
        my_provider.client()
        self.assertTrue(mock_esi_client_factory.called)        
        args, kwargs = mock_esi_client_factory.call_args
        self.assertEqual(kwargs['spec_file'], 'dummy')

    @patch('esi.clients.esi_client_factory')
    def test_with_version(self, mock_esi_client_factory):
        my_provider = EsiClientProvider(version='dummy')
        my_provider.client()
        self.assertTrue(mock_esi_client_factory.called)        
        args, kwargs = mock_esi_client_factory.call_args
        self.assertEqual(kwargs['version'], 'dummy')

    @patch('esi.clients.esi_client_factory')
    def test_with_kwargs(self, mock_esi_client_factory):
        my_provider = EsiClientProvider(alpha='yes', bravo='no')
        my_provider.client()
        self.assertTrue(mock_esi_client_factory.called)        
        args, kwargs = mock_esi_client_factory.call_args
        self.assertEqual(kwargs['alpha'], 'yes')
        self.assertEqual(kwargs['bravo'], 'no')

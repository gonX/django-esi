from datetime import datetime, timedelta
import logging
import os
from unittest.mock import patch, Mock
import json

import bravado
from bravado_core.spec import Spec
from bravado.requests_client import RequestsClient
from bravado.exception import HTTPBadGateway

import django
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from . import _generate_token, _store_as_Token, _set_logger
from ..clients import (    
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

SWAGGER_SPEC_PATH_MINIMAL = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'test_swagger.json'
)
SWAGGER_SPEC_PATH_FULL = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'test_swagger_full.json'
)

MODULE_PATH = 'esi.clients'
_set_logger(logging.getLogger(MODULE_PATH), __file__)


def my_sleep(value):
    """mock function for sleep that also checks for valid values"""
    if value < 0:
        raise ValueError('sleep length must be non-negative')


class MockResultFuture:
    def __init__(self):
        dt = datetime.utcnow().replace(tzinfo=timezone.utc) \
            + timedelta(seconds=60)
        self.headers = {'Expires': dt.strftime('%a, %d %b %Y %H:%M:%S %Z')}
        self.status_code = 200
        self.text = 'dummy'


class MockResultPast:
    def __init__(self):
        dt = datetime.utcnow().replace(tzinfo=timezone.utc) \
            - timedelta(seconds=60)
        self.headers = {'Expires': dt.strftime('%a, %d %b %Y %H:%M:%S %Z')}


@patch.object(django.core.cache.cache, 'set')
@patch.object(django.core.cache.cache, 'get')
@patch.object(bravado.http_future.HttpFuture, 'result')
class TestClientCache(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.c = esi_client_factory(spec_file=SWAGGER_SPEC_PATH_MINIMAL)

    def test_cache_expire(self, mock_future_result, mock_cache_get, mock_cache_set):
        cache.clear()
        mock_future_result.return_value = ({'players': 500}, MockResultFuture())
        mock_cache_get.return_value = False

        # hit api
        r = self.c.Status.get_status().result()
        self.assertEquals(r['players'], 500)

        mock_cache_get.return_value = ({'players': 50}, MockResultFuture())
        # hit cache and pass
        r = self.c.Status.get_status().result()
        self.assertEquals(r['players'], 50)

        mock_cache_get.return_value = ({'players': 50}, MockResultPast())
        # hit cache fail, re-hit api
        r = self.c.Status.get_status().result()
        self.assertEquals(r['players'], 500)

    def test_can_handle_exception_from_cache_set(
        self, mock_future_result, mock_cache_get, mock_cache_set
    ):
        cache.clear()
        mock_future_result.return_value = ({'players': 500}, MockResultFuture())
        mock_cache_get.return_value = False
        mock_cache_set.side_effect = RuntimeError("TEST: Could not write to cache")

        # hit api
        r = self.c.Status.get_status().result()
        self.assertEquals(r['players'], 500)

    def test_can_handle_exception_from_cache_get(
        self, mock_future_result, mock_cache_get, mock_cache_set
    ):
        cache.clear()
        mock_future_result.return_value = ({'players': 500}, MockResultFuture())        
        mock_cache_get.side_effect = RuntimeError("TEST: Could not read from cache")

        # hit api
        r = self.c.Status.get_status().result()
        self.assertEquals(r['players'], 500)
    

@patch(MODULE_PATH + '.app_settings.ESI_SPEC_CACHE_DURATION', 3)
@patch(MODULE_PATH + '.app_settings.ESI_API_URL', 'https://www.example.com/esi/')
@patch(MODULE_PATH + '.app_settings.ESI_API_DATASOURCE', 'dummy')
@patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
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
    
    def test_apply_defaults(self):
        request = Mock()
        request.headers = dict()
        request.params = dict()

        x = TokenAuthenticator()
        request2 = x.apply(request)
        self.assertEqual(request2.headers['Authorization'], None)
        self.assertEqual(request2.params['datasource'], 'dummy')
    
    def test_apply_token(self):
        request = Mock()
        request.headers = dict()
        request.params = dict()

        x = TokenAuthenticator(token=self.token)
        request2 = x.apply(request)
        self.assertEqual(request2.headers['Authorization'], 'Bearer my_access_token')
        self.assertEqual(request2.params['datasource'], 'dummy')
    
    def test_apply_token_datasource(self):
        request = Mock()
        request.headers = dict()
        request.params = dict()

        x = TokenAuthenticator(token=self.token, datasource='dummy2')
        request2 = x.apply(request)
        self.assertEqual(request2.headers['Authorization'], 'Bearer my_access_token')
        self.assertEqual(request2.params['datasource'], 'dummy2')
        
    @patch('esi.models.Token.refresh', spec=True)
    def test_apply_token_expired_success(self, mock_Token_refresh):
        request = Mock()
        request.headers = dict()
        request.params = dict()

        self.token.created -= timedelta(121)
        
        x = TokenAuthenticator(token=self.token)
        request2 = x.apply(request)
        self.assertEqual(request2.headers['Authorization'], 'Bearer my_access_token')
        self.assertEqual(request2.params['datasource'], 'dummy')
        self.assertEqual(mock_Token_refresh.call_count, 1)
        
    @patch('esi.models.Token.refresh', spec=True)
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
        super().setUpClass()        
        with open(SWAGGER_SPEC_PATH_MINIMAL, 'r', encoding='utf-8') as f:
            cls.test_spec_dict = json.load(f)

    def test_build_cache_name(self):
        self.assertEqual(build_cache_name('abc'), 'esi_swaggerspec_abc')

    @patch(MODULE_PATH + '.app_settings.ESI_SPEC_CACHE_DURATION', 3)
    def test_cache_spec(self):
        spec = {
            'dummy_spec': True
        }
        cache_spec('abc', spec)
        self.assertDictEqual(cache.get('esi_swaggerspec_abc'), spec)

    @patch(MODULE_PATH + '.app_settings.ESI_API_URL', 'https://www.example.com/esi/')
    def test_build_spec_url(self):
        self.assertEqual(
            build_spec_url('v2'), 'https://www.example.com/esi/v2/swagger.json'
        )

    @patch(MODULE_PATH + '.requests_client.RequestsClient', spec=True)
    @patch(MODULE_PATH + '.app_settings.ESI_SPEC_CACHE_DURATION', 1)
    def test_get_spec_defaults(self, mock_RequestsClient):        
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        spec = get_spec('latest')
        self.assertIsInstance(spec, Spec)

    @patch(MODULE_PATH + '.app_settings.ESI_SPEC_CACHE_DURATION', 1)                
    def test_get_spec_with_http_client(self):        
        mock_http_client = Mock(spec=RequestsClient)
        mock_http_client.request.return_value.result.return_value.json.return_value = \
            self.test_spec_dict
        spec = get_spec('latest', http_client=mock_http_client)
        self.assertIsInstance(spec, Spec)

    @patch(MODULE_PATH + '.app_settings.ESI_SPEC_CACHE_DURATION', 1)                
    def test_get_spec_with_config(self):        
        mock_http_client = Mock(spec=RequestsClient)
        mock_http_client.request.return_value.result.return_value.json.return_value = \
            self.test_spec_dict
        spec = get_spec(
            'latest', http_client=mock_http_client, config={'dummy_config': True}
        )
        self.assertIsInstance(spec, Spec)
        self.assertIn('dummy_config', spec.config)

    @patch(MODULE_PATH + '.app_settings.ESI_SPEC_CACHE_DURATION', 1)    
    def test_build_spec_defaults(self):        
        mock_http_client = Mock(spec=RequestsClient)
        mock_http_client.request.return_value.result.return_value\
            .json.return_value = self.test_spec_dict
        spec = build_spec('v1', http_client=mock_http_client)
        self.assertIsInstance(spec, Spec)

    @patch(MODULE_PATH + '.app_settings.ESI_SPEC_CACHE_DURATION', 1)    
    def test_build_spec_explicit_resource_found(self):        
        mock_http_client = Mock(spec=RequestsClient)
        mock_http_client.request.return_value.result.return_value\
            .json.return_value = self.test_spec_dict
        spec = build_spec('v1', http_client=mock_http_client, Status='v1')
        self.assertIsInstance(spec, Spec)
    
    @patch(MODULE_PATH + '.app_settings.ESI_SPEC_CACHE_DURATION', 1)    
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

        client = read_spec(SWAGGER_SPEC_PATH_MINIMAL)
        self.assertIsInstance(client, SwaggerClient)

    def test_minimize_spec_defaults(self):
        spec_dict = minimize_spec(self.test_spec_dict)
        self.assertIsInstance(spec_dict, dict)
        # todo: add better verification of functionality
    
    def test_minimize_spec_resources(self):
        spec_dict = minimize_spec(self.test_spec_dict, resources=['Status'])
        self.assertIsInstance(spec_dict, dict)
        # todo: add better verification of functionality


@patch(MODULE_PATH + '.app_settings.ESI_SPEC_CACHE_DURATION', 1)
@patch(MODULE_PATH + '.requests_client.RequestsClient')
class TestEsiClientFactory(TestCase):
    
    @classmethod
    def setUpClass(cls):        
        super().setUpClass()        
        with open(SWAGGER_SPEC_PATH_MINIMAL, 'r', encoding='utf-8') as f:
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
    
    def test_minimal_client(self, mock_RequestsClient):        
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory()
        self.assertIsInstance(client, SwaggerClient)
    
    def test_client_with_token(self, mock_RequestsClient):
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory(token=self.token)
        self.assertIsInstance(client, SwaggerClient)

    def test_client_with_datasource(self, mock_RequestsClient):
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory(datasource='singularity')
        self.assertIsInstance(client, SwaggerClient)

    def test_client_with_version(self, mock_RequestsClient):
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory(version='v1')
        self.assertIsInstance(client, SwaggerClient)

    def test_client_with_spec_file(self, mock_RequestsClient):
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory(spec_file=SWAGGER_SPEC_PATH_MINIMAL)
        self.assertIsInstance(client, SwaggerClient)

    def test_client_with_explicit_resource(self, mock_RequestsClient):
        mock_RequestsClient.return_value.request.return_value.\
            result.return_value.json.return_value = self.test_spec_dict
        client = esi_client_factory(Status='v1')
        self.assertIsInstance(client, SwaggerClient)

    def test__time_to_expiry_failure(self, mock_RequestsClient):
        seconds = CachingHttpFuture._time_to_expiry("fail")
        self.assertEqual(seconds, 0)


@patch(MODULE_PATH + '.HttpFuture.result')
class TestClientResult(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.c = esi_client_factory(spec_file=SWAGGER_SPEC_PATH_MINIMAL)

    @patch(MODULE_PATH + '.app_settings.ESI_REQUESTS_CONNECT_TIMEOUT', 10)
    @patch(MODULE_PATH + '.app_settings.ESI_REQUESTS_READ_TIMEOUT', 60)
    def test_use_default_timeout(self, mock_future_result):
        mock_future_result.return_value = (None, Mock(**{'headers': {}}))
        self.c.Status.get_status().result()
        self.assertTrue(mock_future_result.called)
        args, kwargs = mock_future_result.call_args
        self.assertEqual(kwargs['timeout'], (10, 60))

    @patch(MODULE_PATH + '.app_settings.ESI_REQUESTS_CONNECT_TIMEOUT', 10)
    @patch(MODULE_PATH + '.app_settings.ESI_REQUESTS_READ_TIMEOUT', 60)
    def test_use_custom_timeout(self, mock_future_result):
        mock_future_result.return_value = (None, Mock(**{'headers': {}}))
        self.c.Status.get_status().result(timeout=42)
        self.assertTrue(mock_future_result.called)
        args, kwargs = mock_future_result.call_args
        self.assertEqual(kwargs['timeout'], 42)
    
    def test_support_language_parameter(self, mock_future_result):
        mock_future_result.return_value = (None, Mock(**{'headers': {}}))        
        my_language = 'de'
        operation = self.c.Status.get_status()
        operation.result(language=my_language)
        self.assertTrue(mock_future_result.called)        
        self.assertEqual(operation.future.request.params['language'], my_language)
        args, kwargs = mock_future_result.call_args
        self.assertNotIn('language', kwargs)
    
    @patch(MODULE_PATH + '.app_settings.ESI_SERVER_ERROR_BACKOFF_FACTOR', 0.5)
    @patch(MODULE_PATH + '.app_settings.ESI_SERVER_ERROR_MAX_RETRIES', 4)
    @patch(MODULE_PATH + '.sleep')
    def test_retries_1(self, mock_sleep, mock_future_result):
        mock_sleep.side_effect = my_sleep
        mock_future_result.side_effect = HTTPBadGateway(response=Mock())        
        try:
            self.c.Status.get_status().result()
        except HTTPBadGateway as e:
            # requests error thrown
            self.assertIsInstance(e, HTTPBadGateway)  
            # we tried # times before raising
            self.assertEqual(mock_future_result.call_count, 5)
            call_list = mock_sleep.call_args_list
            result = [args[0] for args, _ in [x for x in call_list]]
            expected = [0.5, 1.0, 2.0]
            self.assertListEqual(expected, result)
            
    @patch(MODULE_PATH + '.app_settings.ESI_SERVER_ERROR_BACKOFF_FACTOR', 0.5)
    @patch(MODULE_PATH + '.app_settings.ESI_SERVER_ERROR_MAX_RETRIES', 1)
    @patch(MODULE_PATH + '.sleep')
    def test_retries_2(self, mock_sleep, mock_future_result):
        mock_sleep.side_effect = my_sleep
        mock_future_result.side_effect = HTTPBadGateway(response=Mock())        
        try:
            self.c.Status.get_status().result()
        except HTTPBadGateway as e:
            # requests error thrown
            self.assertIsInstance(e, HTTPBadGateway)  
            # we tried # times before raising
            self.assertEqual(mock_future_result.call_count, 2)

    @patch(MODULE_PATH + '.app_settings.ESI_SERVER_ERROR_BACKOFF_FACTOR', 0.5)
    @patch(MODULE_PATH + '.app_settings.ESI_SERVER_ERROR_MAX_RETRIES', 0)
    @patch(MODULE_PATH + '.sleep')
    def test_retries_3(self, mock_sleep, mock_future_result):
        mock_sleep.side_effect = my_sleep
        mock_future_result.side_effect = HTTPBadGateway(response=Mock())        
        try:
            self.c.Status.get_status().result()
        except HTTPBadGateway as e:
            # requests error thrown
            self.assertIsInstance(e, HTTPBadGateway)  
            # we tried # times before raising
            self.assertEqual(mock_future_result.call_count, 1)
           
    @patch(MODULE_PATH + '.app_settings.ESI_SERVER_ERROR_BACKOFF_FACTOR', 0.5)
    @patch(MODULE_PATH + '.app_settings.ESI_SERVER_ERROR_MAX_RETRIES', 4)
    @patch(MODULE_PATH + '.sleep')
    def test_retry_with_custom_retries(self, mock_sleep, mock_future_result):
        mock_sleep.side_effect = my_sleep
        mock_future_result.side_effect = HTTPBadGateway(response=Mock())        
        try:
            self.c.Status.get_status().result(retries=1)
        except HTTPBadGateway as e:
            # requests error thrown
            self.assertIsInstance(e, HTTPBadGateway)  
            # we tried # times before raising
            self.assertEqual(mock_future_result.call_count, 2)
            

@patch(MODULE_PATH + '.HttpFuture.result')
class TestClientResultAllPages(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.c = esi_client_factory(spec_file=SWAGGER_SPEC_PATH_FULL)

    def test_pages(self, mock_future_result):

        class MockResultHeaders:
            def __init__(self):
                self.headers = {'X-Pages': 10}
                self.status_code = 200
                self.text = 'dummy'

        mock_future_result.return_value = ({"contract_test": 1}, MockResultHeaders())
        self.c.Contracts.get_contracts_public_region_id(region_id=1).results()
        self.assertEqual(mock_future_result.call_count, 10)  # we got 10 pages of data
    
    def test_pages_response(self, mock_future_result):

        class MockResultHeaders:
            def __init__(self):
                self.headers = {'X-Pages': 10}
                self.status_code = 200
                self.text = 'dummy'

        mock_future_result.return_value = ({"contract_test": 1}, MockResultHeaders())
        o = self.c.Contracts.get_contracts_public_region_id(region_id=1)
        o.request_config.also_return_response = True
        result, response = o.results()
        self.assertEqual(mock_future_result.call_count, 10)  # we got 10 pages of data
        self.assertEqual(len(result), 10)   # we got 10 lots of data
        self.assertEqual(response.headers, {'X-Pages': 10})  # we got header of data

    def test_pages_on_non_paged_endpoint(self, mock_future_result):

        class MockResultHeaders:
            def __init__(self):
                self.headers = {'header_test': "ok"}
                self.status_code = 200
                self.text = 'dummy'

        mock_future_result.return_value = ({"status_test": 1}, MockResultHeaders())

        self.c.Status.get_status().results()
        self.assertEqual(mock_future_result.call_count, 1)     # we got no pages of data


@patch(MODULE_PATH + '.app_settings.ESI_LANGUAGES', ['lang1', 'lang2', 'lang3'])
@patch(MODULE_PATH + '.CachingHttpFuture.results')
class TestClientResultsLocalized(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.c = esi_client_factory(spec_file=SWAGGER_SPEC_PATH_MINIMAL)
    
    @staticmethod
    def my_results(**kwargs):
        if 'language' in kwargs:
            return 'response_' + kwargs['language']
        else:
            return ''

    def test_default(self, mock_future_results):
        mock_future_results.side_effect = self.my_results
        result = self.c.Status.get_status().results_localized()
        expected = {
            'lang1': 'response_lang1',
            'lang2': 'response_lang2',
            'lang3': 'response_lang3',
        }
        self.assertDictEqual(result, expected)

    def test_custom_languages(self, mock_future_results):
        mock_future_results.side_effect = self.my_results
        result = (
            self.c.Status.get_status().results_localized(languages=['lang2', 'lang3'])
        )
        expected = {
            'lang2': 'response_lang2',
            'lang3': 'response_lang3',
        }
        self.assertDictEqual(result, expected)

    def test_raise_on_invalid_language(self, mock_future_results):
        mock_future_results.side_effect = self.my_results
        
        with self.assertRaises(ValueError):
            self.c.Status.get_status().results_localized(languages=['lang2', 'xxx'])
        

@patch(MODULE_PATH + '.esi_client_factory')
class TestEsiClientProvider(TestCase):    
      
    def test_client_loads_on_demand(self, mock_esi_client_factory):
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
            
    def test_str(self, mock_esi_client_factory):        
        my_provider = EsiClientProvider()
        self.assertEqual(str(my_provider), 'EsiClientProvider')
    
    def test_with_datasource(self, mock_esi_client_factory):
        my_provider = EsiClientProvider(datasource='dummy')
        my_provider.client()
        self.assertTrue(mock_esi_client_factory.called)        
        args, kwargs = mock_esi_client_factory.call_args
        self.assertEqual(kwargs['datasource'], 'dummy')
    
    def test_with_spec_file(self, mock_esi_client_factory):
        my_provider = EsiClientProvider(spec_file='dummy')
        my_provider.client()
        self.assertTrue(mock_esi_client_factory.called)        
        args, kwargs = mock_esi_client_factory.call_args
        self.assertEqual(kwargs['spec_file'], 'dummy')
    
    def test_with_version(self, mock_esi_client_factory):
        my_provider = EsiClientProvider(version='dummy')
        my_provider.client()
        self.assertTrue(mock_esi_client_factory.called)        
        args, kwargs = mock_esi_client_factory.call_args
        self.assertEqual(kwargs['version'], 'dummy')

    def test_with_kwargs(self, mock_esi_client_factory):
        my_provider = EsiClientProvider(alpha='yes', bravo='no')
        my_provider.client()
        self.assertTrue(mock_esi_client_factory.called)        
        args, kwargs = mock_esi_client_factory.call_args
        self.assertEqual(kwargs['alpha'], 'yes')
        self.assertEqual(kwargs['bravo'], 'no')

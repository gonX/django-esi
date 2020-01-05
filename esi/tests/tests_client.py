import bravado
import datetime
import django
import os
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from esi.clients import esi_client_factory
from unittest import mock

SWAGGER_SPEC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_swagger.json') 

class TestClientCache(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.c = esi_client_factory(spec_file=SWAGGER_SPEC_PATH)

    @mock.patch.object(django.core.cache.cache, 'set')
    @mock.patch.object(django.core.cache.cache, 'get')
    @mock.patch.object(bravado.http_future.HttpFuture, 'result')
    def test_cache_expire(self, result_hit, cache_hit, cache_set):
        cache.clear()

        class MockResultFuture:
            def __init__(self):
                dt = datetime.datetime.utcnow().replace(tzinfo=timezone.utc) + datetime.timedelta(seconds=60)
                self.headers = {'Expires':dt.strftime('%a, %d %b %Y %H:%M:%S %Z')}

        class MockResultPast:
            def __init__(self):
                dt = datetime.datetime.utcnow().replace(tzinfo=timezone.utc) - datetime.timedelta(seconds=60)
                self.headers = {'Expires':dt.strftime('%a, %d %b %Y %H:%M:%S %Z')}

        result_hit.return_value = ({'players':500},MockResultFuture())
        cache_hit.return_value = False

        #hit api
        r = self.c.Status.get_status().result()
        self.assertEquals(r['players'], 500)

        cache_hit.return_value = ({'players':50},MockResultFuture())
        #hit cache and pass
        r = self.c.Status.get_status().result()
        self.assertEquals(r['players'], 50)

        cache_hit.return_value = ({'players':50},MockResultPast())
        #hit cache fail, rehit api
        r = self.c.Status.get_status().result()
        self.assertEquals(r['players'], 500)


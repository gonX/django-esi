from datetime import timedelta
import logging
from unittest.mock import patch, Mock

from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase, RequestFactory
from django.utils import timezone

from . import _dt_eveformat, _generate_token, _store_as_Token, _set_logger
from ..errors import TokenError, IncompleteResponseError
from ..managers import _process_scopes, TokenQueryset, TokenManager
from ..models import Token
   

_set_logger(logging.getLogger('esi.managers'), __file__)


class TestProcessScopes(TestCase):

    def test_none(self):
        self.assertSetEqual(
            _process_scopes(None),
            set()
        )

    def test_empty_list(self):
        self.assertSetEqual(
            _process_scopes([]),
            set()
        )

    def test_single_string_1(self):
        self.assertSetEqual(
            _process_scopes(['one']),
            {'one'}
        )

    def test_single_string_2(self):
        self.assertSetEqual(
            _process_scopes(['one two three']),
            {'one', 'two', 'three'}
        )

    def test_list(self):
        self.assertSetEqual(
            _process_scopes(['one', 'two', 'three']),
            {'one', 'two', 'three'}
        )

    def test_tuple(self):
        self.assertSetEqual(
            _process_scopes(('one', 'two', 'three')),
            {'one', 'two', 'three'}
        )


class TestTokenQuerySet(TestCase):

    def setUp(self):        
        self.user1 = User.objects.create_user(
            'Bruce Wayne',
            'abc@example.com',
            'password'
        )
        self.user2 = User.objects.create_user(
            'Peter Parker',
            'abc@example.com',
            'password'
        )
        Token.objects.all().delete()


    @patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    def test_get_expired(self):        
        t1 = _store_as_Token(
            _generate_token(
                character_id=101,
                character_name=self.user1.username,
                scopes=['abc']
            ), 
            self.user1
        )
        t2 = _store_as_Token(
            _generate_token(
                character_id=102,
                character_name=self.user2.username,
                scopes=['xyz']
            ), 
            self.user2
        )        
        self.assertEqual(list(
            Token.objects.get_queryset().get_expired()), 
            []
        )
        
        t2.created -= timedelta(121)
        t2.save()        
        self.assertEqual(list(Token.objects.get_queryset().get_expired()),
            [t2]
        )


    @patch('esi.managers.app_settings.ESI_SSO_CLIENT_ID', 'abc')
    @patch('esi.managers.app_settings.ESI_SSO_CLIENT_SECRET', 'xyz')    
    @patch('esi.models.Token.delete', autospec=True)
    @patch('esi.models.Token.refresh', autospec=True)
    @patch('esi.managers.requests.auth.HTTPBasicAuth', autospec=True)
    @patch('esi.managers.OAuth2Session', autospec=True)
    def test_bulk_refresh_normal(
        self,
        mock_OAuth2Session,
        mock_HTTPBasicAuth,
        mock_Token_refresh,
        mock_Token_delete
    ):        
        character_id = 99
        character_name = 'Bruce Wayne'
        t1 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc']
            ), 
            self.user1
        )
        t2 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['xyz']
            ), 
            self.user1
        )        
        incomplete_qs = Token.objects.get_queryset().bulk_refresh()
        self.assertEqual(mock_Token_refresh.call_count, 2)
        self.assertEqual(mock_Token_delete.call_count, 0)
        self.assertSetEqual(
            set(incomplete_qs),
            {t1, t2}
        )
        
        # Note
        # looks like a bug in bulk_refresh():
        # this filter can never find anything, because refresh_token 
        # can not be null:
        #   self.filter(refresh_token__isnull=True).get_expired().delete()


    @patch('esi.managers.app_settings.ESI_SSO_CLIENT_ID', 'abc')
    @patch('esi.managers.app_settings.ESI_SSO_CLIENT_SECRET', 'xyz')    
    @patch('esi.models.Token.delete', autospec=True)
    @patch('esi.models.Token.refresh', autospec=True)
    @patch('esi.managers.requests.auth.HTTPBasicAuth', autospec=True)
    @patch('esi.managers.OAuth2Session', autospec=True)
    def test_bulk_refresh_token_error(
        self,
        mock_OAuth2Session,
        mock_HTTPBasicAuth,
        mock_Token_refresh,
        mock_Token_delete
    ):        
        mock_Token_refresh.side_effect = TokenError
        
        character_id = 99
        character_name = 'Bruce Wayne'
        t1 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc']
            ), 
            self.user1
        )
        t2 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['xyz']
            ), 
            self.user1
        )        
        incomplete_qs = Token.objects.get_queryset().bulk_refresh()
        self.assertEqual(mock_Token_refresh.call_count, 2)
        self.assertEqual(mock_Token_delete.call_count, 2)
        self.assertSetEqual(
            set(incomplete_qs),
            {t1, t2}
        )

    @patch('esi.managers.app_settings.ESI_SSO_CLIENT_ID', 'abc')
    @patch('esi.managers.app_settings.ESI_SSO_CLIENT_SECRET', 'xyz')    
    @patch('esi.models.Token.delete', autospec=True)
    @patch('esi.models.Token.refresh', autospec=True)
    @patch('esi.managers.requests.auth.HTTPBasicAuth', autospec=True)
    @patch('esi.managers.OAuth2Session', autospec=True)
    def test_bulk_refresh_incomplete_response_error(
        self,
        mock_OAuth2Session,
        mock_HTTPBasicAuth,
        mock_Token_refresh,
        mock_Token_delete
    ):        
        mock_Token_refresh.side_effect = IncompleteResponseError
        
        character_id = 99
        character_name = 'Bruce Wayne'
        t1 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc']
            ), 
            self.user1
        )
        t2 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['xyz']
            ), 
            self.user1
        )        
        incomplete_qs = Token.objects.get_queryset().bulk_refresh()
        self.assertEqual(mock_Token_refresh.call_count, 2)
        self.assertEqual(mock_Token_delete.call_count, 0)
        self.assertSetEqual(
            set(incomplete_qs),
            set()
        )
    
    @patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    @patch('esi.managers.TokenQueryset.bulk_refresh', autospec=True)    
    def test_require_valid_none_expired(
        self,        
        mock_bulk_refresh
    ):                        
        character_id = 99
        character_name = 'Bruce Wayne'
        t1 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc']
            ), 
            self.user1
        )
        t2 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['xyz']
            ), 
            self.user1
        )     
        mock_bulk_refresh.return_value = Token.objects.none()
                
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_valid()),
            {t1, t2}
        )        
        

    @patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    @patch('esi.managers.TokenQueryset.bulk_refresh', autospec=True)    
    def test_require_valid_some_expired(
        self,        
        mock_bulk_refresh
    ):                        
        character_id = 99
        character_name = 'Bruce Wayne'
        t1 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc']
            ), 
            self.user1
        )
        t2 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['xyz']
            ), 
            self.user1
        )
        t2.created -= timedelta(121)
        t2.save()
        mock_bulk_refresh.return_value = Token.objects\
            .filter(pk__in=[t2.pk])
                
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_valid()),
            {t1, t2}
        )        

    @patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    @patch('esi.managers.TokenQueryset.bulk_refresh', autospec=True)    
    def test_require_valid_one_refresh_error(
        self,        
        mock_bulk_refresh
    ):                        
        character_id = 99
        character_name = 'Bruce Wayne'
        t1 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc']
            ), 
            self.user1
        )
        t2 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['xyz']
            ), 
            self.user1
        )
        t2.created -= timedelta(121)
        t2.save()
        mock_bulk_refresh.return_value = Token.objects.none()
                
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_valid()),
            {t1}
        )        

    def test_require_scopes_normal(self):
        character_id = 99
        character_name = 'Bruce Wayne'
        t1 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc', 'xyz', '123']
            ), 
            self.user1
        )
        t2 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc', 'xyz']
            ), 
            self.user1
        )
        t3 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc', '123']
            ), 
            self.user1
        )
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_scopes('abc')),
        	{t1, t2, t3}
        )
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_scopes('xyz')),
        	{t1, t2}
        )
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_scopes('123')),
        	{t1, t3}
        )
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_scopes('555')),
        	set()
        )
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_scopes('abc xyz 123')),
        	{t1}
        )

    def test_require_scopes_empty(self):
        character_id = 99
        character_name = 'Bruce Wayne'
        t1 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc', 'xyz', '123']
            ), 
            self.user1
        )
        t2 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name
            ), 
            self.user1
        )
        t2.scopes.all().delete()
        t3 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc', '123']
            ), 
            self.user1
        )
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_scopes('')),
        	{t2}
        )        

    def test_require_scopes_exact(self):
        character_id = 99
        character_name = 'Bruce Wayne'
        t1 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc', 'xyz', '123']
            ), 
            self.user1
        )
        t2 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc', 'xyz']
            ), 
            self.user1
        )
        t3 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc', '123']
            ), 
            self.user1
        )
        t4 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc', '123']
            ), 
            self.user1
        )
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_scopes_exact('abc')),
        	set()
        )
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_scopes_exact('abc xyz')),
        	{t2}
        )
        self.assertSetEqual(
            set(Token.objects.get_queryset().require_scopes_exact('abc 123')),
        	{t3, t4}
        )

    def test_require_scopes_exact(self):
        character_id = 99
        character_name = 'Bruce Wayne'
        t1 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc', 'xyz', '123']
            ), 
            self.user1
        )
        t2 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['abc', 'xyz']
            ), 
            self.user1
        )
        t3 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['xyz', '123']
            ), 
            self.user1
        )
        t4 = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['xyz', '123']
            ), 
            self.user1
        )
        self.assertSetEqual(
            set(Token.objects.get_queryset().equivalent_to(t3)),
        	{t4}
        )        
       

class TestTokenManager(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.user1 = User.objects.create_user(
            'Bruce Wayne',
            'abc@example.com',
            'password'
        )

    
    @patch('esi.managers.app_settings.ESI_SSO_CLIENT_ID', 'abc')
    @patch('esi.managers.app_settings.ESI_SSO_CLIENT_SECRET', 'xyz')
    @patch('esi.managers.app_settings.ESI_SSO_CALLBACK_URL', 'localhost')
    @patch('esi.managers.app_settings.ESI_TOKEN_URL', 'localhost')
    @patch('esi.managers.app_settings.ESI_TOKEN_VERIFY_URL', 'localhost')
    @patch('esi.managers.app_settings.ESI_ALWAYS_CREATE_TOKEN', False)
    @patch('esi.managers.OAuth2Session', autospec=True)
    def test_create_from_code(self, mock_OAuth2Session):
        mock_oauth = Mock()
        mock_oauth.request.return_value.json.return_value = \
            _generate_token(
                99, 'Bruce Wayne', scopes=[
                    'esi-calendar.read_calendar_events.v1',
                    'esi-location.read_location.v1', 
                    'esi-location.read_ship_type.v1',
                    'esi-unknown-scope'
                ]
            )
        mock_oauth.fetch_token.return_value = {
            'access_token': 'access_token',
            'refresh_token': 'refresh_token',
            'token_type': 'Bearer',
            'expires_in': 1200,
        }
        mock_OAuth2Session.return_value = mock_oauth

        # create new token from code
        token1 = Token.objects.create_from_code('abc123xyz')
        self.assertEqual(
            token1.character_id,
            99
        )
        self.assertEqual(
            token1.character_name,
            'Bruce Wayne'
        )

        # should return existing token instead of creating a new one
        # since ESI_ALWAYS_CREATE_TOKEN is False
        token2 = Token.objects.create_from_code('11abc123xyz')
        self.assertEqual(token1, token2)


    @patch('esi.managers.TokenManager.create_from_code', autospec=True)
    def test_create_from_request(self, mock_create_from_code):
        mock_create_from_code.return_value = 'we got you'
        
        request = self.factory.get('https://www.example.com?code=abc123')
        request.user = self.user1

        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()

        x = Token.objects.create_from_request(request)
        self.assertEqual(x, 'we got you')
        self.assertEqual(mock_create_from_code.call_args[0][1], 'abc123')


        
from datetime import timedelta
import logging
from unittest.mock import patch, Mock

from django.contrib.auth.models import User
from django.test import TestCase

from . import _generate_token, _store_as_Token, _set_logger
from ..clients import *
from ..models import CallbackRedirect, Token
from ..tasks import cleanup_callbackredirect, cleanup_token


_set_logger(logging.getLogger('esi.tasks'), __file__)


class TestTasks(TestCase):

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
    

    def test_cleanup_callbackredirect_default(self):
        CallbackRedirect.objects.all().delete()
        callback_url = 'https://www.example.com/redirect/'
        c1_valid = CallbackRedirect.objects.create(
            session_key='abc1',
            state='xyz1',
            url=callback_url
        )
        c2_expired = CallbackRedirect.objects.create(
            session_key='abc2',
            state='xyz2',
            url=callback_url
        )
        c3_valid = CallbackRedirect.objects.create(
            session_key='abc3',
            state='xyz3',
            url=callback_url
        )
        c2_expired.created -= timedelta(seconds=301)
        c2_expired.save()
        cleanup_callbackredirect()

        self.assertSetEqual(
            set(CallbackRedirect.objects.all()),
            {c1_valid, c3_valid}
        )

    def test_cleanup_callbackredirect_custom_age(self):
        CallbackRedirect.objects.all().delete()
        callback_url = 'https://www.example.com/redirect/'
        c1_valid = CallbackRedirect.objects.create(
            session_key='abc1',
            state='xyz1',
            url=callback_url
        )
        c2_expired = CallbackRedirect.objects.create(
            session_key='abc2',
            state='xyz2',
            url=callback_url
        )
        c3_valid = CallbackRedirect.objects.create(
            session_key='abc3',
            state='xyz3',
            url=callback_url
        )
        c2_expired.created -= timedelta(seconds=601)
        c2_expired.save()
        c3_valid.created -= timedelta(seconds=301)
        c3_valid.save()
        cleanup_callbackredirect(max_age=600)

        self.assertSetEqual(
            set(CallbackRedirect.objects.all()),
            {c1_valid, c3_valid}
        )


    @patch('esi.models.Token.refresh', autospec=True)
    @patch('esi.managers.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    def test_cleanup_token(self, mock_token_refresh):
        t_valid_1 = _store_as_Token(
            _generate_token(
                character_id=101,
                character_name=self.user1.username,
                scopes=['abc', 'xyz']
            ), 
            self.user1
        )
        t_expired_1 = _store_as_Token(
            _generate_token(
                character_id=102,
                character_name=self.user2.username,
                scopes=['xyz']
            ), 
            self.user2
        )   
        t_valid_2 = _store_as_Token(
            _generate_token(
                character_id=101,
                character_name=self.user1.username,
                scopes=['abc', '123']
            ), 
            self.user1
        )
        t_expired_2 = _store_as_Token(
            _generate_token(
                character_id=102,
                character_name=self.user2.username,
                scopes=['123']
            ), 
            self.user2
        ) 
        t_no_user_1 = _store_as_Token(
            _generate_token(
                character_id=1234,
                character_name="No User",
                scopes=['123']
            ), 
            None
        ) 

        t_expired_1.created -= timedelta(121)
        t_expired_1.save()        
        t_expired_2.created -= timedelta(121)
        t_expired_2.save()        

        cleanup_token()
        self.assertEqual(mock_token_refresh.call_count, 2)
        
        all_tokens = Token.objects.all()
        self.assertNotIn(t_no_user_1, all_tokens)
        
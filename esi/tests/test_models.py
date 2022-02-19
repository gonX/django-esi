"""unit tests for esi"""

from datetime import timedelta
import logging
from unittest.mock import patch, Mock

from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.models import User
from django.utils import timezone
from django.test import TestCase

from oauthlib.oauth2.rfc6749.errors import InvalidGrantError, \
    MissingTokenError, InvalidClientError, InvalidTokenError, \
    InvalidClientIdError

from . import _generate_token, _store_as_Token, _set_logger
from ..errors import TokenInvalidError, NotRefreshableTokenError, \
    TokenExpiredError, IncompleteResponseError
from ..models import Scope, Token, CallbackRedirect

logger = _set_logger(logging.getLogger('esi.models'), __file__)


class TestScope(TestCase):
    """tests for model Scope"""

    def test_str(self):
        x = Scope(name='dummy_scope')
        self.assertEqual(
            "dummy_scope",
            str(x)
        )

    def test_friendly_name_fail(self):
        x = Scope(name='dummy_scope')
        self.assertEqual(
            "dummy_scope",
            x.friendly_name
        )

    def test_friendly_name_pass(self):
        x = Scope(name='test.dummy_scope.test')
        self.assertEqual(
            "dummy scope",
            x.friendly_name
        )


class TestToken(TestCase):
    """tests for model Token"""

    def setUp(self):

        character_id = 1000
        character_name = 'Bruce Wayne'

        self.user = User.objects.create_user(
            character_name,
            'abc@example.com',
            'password'
        )
        self.token = _store_as_Token(
            _generate_token(
                character_id=character_id,
                character_name=character_name,
                scopes=['esi-universe.read_structures.v1']
            ),
            self.user
        )

    def test_str(self):
        self.assertEqual(
            "Bruce Wayne - esi-universe.read_structures.v1",
            str(self.token)
        )

    def test_repr(self):
        self.assertEqual(
            '<Token(id={}): 1000, Bruce Wayne>'.format(
                self.token.pk
            ),
            repr(self.token)
        )

    def test_get_token(self):
        t = Token.get_token(1000, ['esi-universe.read_structures.v1'])
        self.assertEqual(t, self.token)

    def test_get_token_fail(self):
        t = Token.get_token(1000, ['esi-universe.read_structures.v9000'])
        self.assertEqual(t, False)

    def test_need_refresh_token_for_refresh(self):
        self.assertTrue(self.token.can_refresh)
        self.token.refresh_token = None
        self.assertFalse(self.token.can_refresh)

    @patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    def test_expires(self):
        self.assertEqual(
            self.token.created + timedelta(seconds=120),
            self.token.expires
        )

    @patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    def test_not_expired(self):
        self.assertFalse(self.token.expired)

    @patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    def test_has_expired(self):
        self.token.created -= timedelta(121)
        self.assertTrue(self.token.expired)

    def test_refresh_normal_1(self):
        mock_auth = Mock()
        mock_session = Mock()
        mock_session.refresh_token.return_value = {
            'access_token': 'access_token_2',
            'refresh_token': 'refresh_token_2'
        }

        self.token.refresh(mock_session, mock_auth)
        self.assertEqual(
            self.token.refresh_token, 'refresh_token_2'
        )
        self.assertEqual(
            self.token.access_token, 'access_token_2'
        )
        self.assertGreaterEqual(
            self.token.created, timezone.now() - timedelta(seconds=60)
        )

    @patch('esi.models.HTTPBasicAuth', autospec=True)
    @patch('esi.models.OAuth2Session', autospec=True)
    def test_refresh_normal_2(self, mock_OAuth2Session, mock_HTTPBasicAuth):
        mock_session = Mock()
        mock_session.refresh_token.return_value = {
            'access_token': 'access_token_2',
            'refresh_token': 'refresh_token_2'
        }
        mock_OAuth2Session.return_value = mock_session

        self.token.refresh()
        self.assertEqual(
            self.token.refresh_token,
            'refresh_token_2'
        )
        self.assertEqual(
            self.token.access_token,
            'access_token_2'
        )
        self.assertGreaterEqual(
            self.token.created,
            timezone.now() - timedelta(seconds=60))

    def test_valid_access_token(self):
        self.assertFalse(self.token.expired)
        self.assertEqual(self.token.valid_access_token(), 'access_token')

    @patch('esi.models.HTTPBasicAuth', autospec=True)
    @patch('esi.models.OAuth2Session', autospec=True)
    @patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    def test_valid_access_token_refresh(self, mock_OAuth2Session, mock_HTTPBasicAuth):
        mock_session = Mock()
        mock_session.refresh_token.return_value = {
            'access_token': 'access_token_new',
            'refresh_token': 'refresh_token_2'
        }
        mock_OAuth2Session.return_value = mock_session

        self.token.created -= timedelta(121)
        self.assertTrue(self.token.expired)
        self.assertEqual(
            self.token.valid_access_token(), 'access_token_new')

    @patch('esi.models.HTTPBasicAuth', autospec=True)
    @patch('esi.models.OAuth2Session', autospec=True)
    @patch('esi.models.app_settings.ESI_TOKEN_VALID_DURATION', 120)
    def test_valid_access_token_cant_refresh(
        self, mock_OAuth2Session, mock_HTTPBasicAuth
    ):
        self.token.refresh_token = None
        self.token.created -= timedelta(121)
        self.assertTrue(self.token.expired)
        with self.assertRaises(TokenExpiredError):
            self.token.valid_access_token()

    def test_refresh_errors_1(self):
        mock_auth = Mock()
        mock_session = Mock()
        mock_session.refresh_token.return_value = {
            'access_token': 'access_token_2',
            'refresh_token': 'refresh_token_2'
        }
        self.token.refresh_token = None
        with self.assertRaises(NotRefreshableTokenError):
            self.token.refresh(mock_session, mock_auth)

    def test_refresh_errors_2(self):
        mock_auth = Mock()
        mock_session = Mock()

        mock_session.refresh_token.side_effect = InvalidGrantError
        with self.assertRaises(TokenInvalidError):
            self.token.refresh(mock_session, mock_auth)

        mock_session.refresh_token.side_effect = InvalidTokenError
        with self.assertRaises(TokenInvalidError):
            self.token.refresh(mock_session, mock_auth)

        mock_session.refresh_token.side_effect = InvalidClientIdError
        with self.assertRaises(TokenInvalidError):
            self.token.refresh(mock_session, mock_auth)

        mock_session.refresh_token.side_effect = MissingTokenError
        with self.assertRaises(IncompleteResponseError):
            self.token.refresh(mock_session, mock_auth)

        mock_session.refresh_token.side_effect = InvalidClientError
        with self.assertRaises(ImproperlyConfigured):
            self.token.refresh(mock_session, mock_auth)

    @patch('esi.models.esi_client_factory', autospec=True)
    def test_get_esi_client(self, mock_esi_client):
        mock_esi_client.return_value = "Johnny"
        x = self.token.get_esi_client()
        self.assertEqual(x, "Johnny")
        self.assertEqual(mock_esi_client.call_count, 1)

    """
    @patch('esi.managers.TokenManager')
    def test_get_token_data(self, mock_decode_jwt):
        mock_decode_jwt._decode_jwt.return_value = \
            _generate_token(
                99, 'Bruce Wayne', scopes=[
                    'esi-calendar.read_calendar_events.v1',
                    'esi-location.read_location.v1',
                    'esi-location.read_ship_type.v1',
                    'esi-unknown-scope'
                ]
            )
        data = self.token.get_token_data(access_token='access_token_2')
        self.assertEqual(data['name'], "Bruce Wayne")
    """
    @patch('esi.models.Token.get_token_data')
    def test_update_token_data_normal_1(self, mock_get_token_data):
        mock_get_token_data.return_value = _generate_token(99, 'Bruce Wayne')
        self.token.update_token_data()
        self.token.refresh_from_db()
        self.assertEqual(
            self.token.character_id,
            99
        )
        self.assertEqual(
            self.token.character_name,
            'Bruce Wayne'
        )
        self.assertEqual(
            self.token.character_owner_hash,
            'character_owner_hash'
        )
        self.assertEqual(
            self.token.token_type,
            'character'
        )

    @patch('esi.models.HTTPBasicAuth', autospec=True)
    @patch('esi.models.OAuth2Session', autospec=True)
    @patch('esi.models.Token.get_token_data')
    def test_update_token_data_normal_2(
        self,
        mock_get_token_data,
        mock_OAuth2Session,
        mock_HTTPBasicAuth
    ):
        mock_session = Mock()
        mock_session.refresh_token.return_value = {
            'access_token': 'access_token_2',
            'refresh_token': 'refresh_token_2'
        }
        mock_OAuth2Session.return_value = mock_session

        mock_get_token_data.return_value = {
            'character_id': 99,
            'name': 'CharacterName',
            'owner': 'CharacterOwnerHash',
            'token_type': 'character',
        }
        self.token.created -= timedelta(121)

        self.token.update_token_data()
        self.token.refresh_from_db()
        self.assertEqual(
            self.token.character_id,
            99
        )

    @patch('esi.models.Token.get_token_data')
    def test_update_token_data_normal_3(self, mock_get_token_data):
        mock_get_token_data.return_value = {
            'character_id': 99,
            'name': 'CharacterName',
            'owner': 'CharacterOwnerHash',
            'token_type': 'Character',
        }
        self.token.update_token_data(commit=False)
        self.assertEqual(
            self.token.character_id,
            99
        )
        self.assertEqual(
            self.token.character_name,
            'CharacterName'
        )
        self.assertEqual(
            self.token.character_owner_hash,
            'CharacterOwnerHash'
        )
        self.assertEqual(
            self.token.token_type,
            'Character'
        )

    @patch('esi.models.Token.get_token_data', auto_spec=True, unsafe=True)
    def test_update_token_data_error(
        self,
        mock_get_token_data
    ):
        self.token.refresh_token = None
        self.token.created -= timedelta(121)
        with self.assertRaises(TokenExpiredError):
            self.token.update_token_data()


class TestCallbackRedirect(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.redirect_url = 'https://www.example.com/%s/' % ('x' * (2048 - 25))
        cls.cb = CallbackRedirect.objects.create(
            session_key='abc',
            state='xyz',
            url=cls.redirect_url
        )
        cls.cb.refresh_from_db()

    def test_str(self):
        self.assertEqual('abc: %s' % self.redirect_url, str(self.cb))

    def test_repr(self):
        self.assertEqual(
            '<CallbackRedirect(pk={}): abc to {}>'.format(
                self.cb.pk, self.redirect_url
            ),
            repr(self.cb)
        )

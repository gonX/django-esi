from datetime import timedelta
from unittest.mock import patch

from celery import current_app as celery_app
from django.utils.timezone import now

from esi.models import CallbackRedirect, Token
from esi.tasks import cleanup_callbackredirect, cleanup_token

from . import NoSocketsTestCase
from .factories_2 import TokenFactory, CallbackRedirectFactory

MANAGERS_PATH = "esi.managers"
MODELS_PATH = "esi.models"


class CeleryTestCase(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True


class TestCleanupCallbackredirect(CeleryTestCase):
    def test_should_remove_expired(self):
        # given
        cb_valid = CallbackRedirectFactory()
        with patch("django.utils.timezone.now") as m:
            m.return_value = now() - timedelta(minutes=5, seconds=1)
            cb_expired = CallbackRedirectFactory()
        # when
        cleanup_callbackredirect.delay(max_age=300)
        # then
        self.assertTrue(CallbackRedirect.objects.filter(pk=cb_valid.pk).exists())
        self.assertFalse(CallbackRedirect.objects.filter(pk=cb_expired.pk).exists())


@patch(MANAGERS_PATH + '.app_settings.ESI_TOKEN_VALID_DURATION', 120)
@patch(MODELS_PATH + '.Token.refresh', spec=True)
class TestCleanupToken(CeleryTestCase):
    def test_should_delete_orphaned_tokens(self, mock_token_refresh):
        # given
        token_1 = TokenFactory(user=None)
        token_2 = TokenFactory()
        # when
        cleanup_token.delay()
        # then
        self.assertFalse(Token.objects.filter(pk=token_1.pk).exists())
        self.assertTrue(Token.objects.filter(pk=token_2.pk).exists())

    def test_should_refresh_expired_tokens_only(self, mock_token_refresh):
        # given
        TokenFactory()
        with patch("django.utils.timezone.now") as m:
            m.return_value = now() - timedelta(minutes=3)
            TokenFactory()
        # when
        cleanup_token.delay()
        # then
        self.assertEqual(mock_token_refresh.call_count, 1)

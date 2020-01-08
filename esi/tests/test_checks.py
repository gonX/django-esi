"""unit tests for esi checks"""

import logging
from unittest.mock import patch, Mock

from django.test import TestCase

from . import _set_logger
from ..checks import check_sso_application_settings


logger = _set_logger(logging.getLogger('esi.checks'), __file__)


class TestCheckSsoApplicationSettings(TestCase):

    @patch('esi.checks.settings.ESI_SSO_CLIENT_ID', '123')
    @patch('esi.checks.settings.ESI_SSO_CLIENT_SECRET', 'abc')
    @patch('esi.checks.settings.ESI_SSO_CALLBACK_URL', 'xyz')
    def test_settings_ok(self):
        errors = check_sso_application_settings()
        self.assertEqual(len(errors), 0)

    @patch('esi.checks.settings.ESI_SSO_CLIENT_ID', None)
    @patch('esi.checks.settings.ESI_SSO_CLIENT_SECRET', 'abc')
    @patch('esi.checks.settings.ESI_SSO_CALLBACK_URL', 'xyz')
    def test_settings_incomplete_ESI_SSO_CLIENT_ID(self):
        errors = check_sso_application_settings()
        self.assertEqual(len(errors), 1)

    @patch('esi.checks.settings.ESI_SSO_CLIENT_ID', '123')
    @patch('esi.checks.settings.ESI_SSO_CLIENT_SECRET', None)
    @patch('esi.checks.settings.ESI_SSO_CALLBACK_URL', 'xyz')
    def test_settings_incomplete_ESI_SSO_CLIENT_SECRET(self):
        errors = check_sso_application_settings()
        self.assertEqual(len(errors), 1)

    @patch('esi.checks.settings.ESI_SSO_CLIENT_ID', '123')
    @patch('esi.checks.settings.ESI_SSO_CLIENT_SECRET', 'abc')
    @patch('esi.checks.settings.ESI_SSO_CALLBACK_URL', None)
    def test_settings_incomplete_ESI_SSO_CALLBACK_URL(self):
        errors = check_sso_application_settings()
        self.assertEqual(len(errors), 1)

    @patch('esi.checks.settings.ESI_SSO_CLIENT_ID', '123')
    @patch('esi.checks.settings.ESI_SSO_CLIENT_SECRET', 'abc')
    @patch('esi.checks.settings.ESI_SSO_CALLBACK_URL', None)
    @patch('esi.checks.settings.DEBUG', True)
    def test_settings_incomplete_debug_mode(self):
        errors = check_sso_application_settings()
        self.assertEqual(len(errors), 1)

    @patch('esi.checks.settings.ESI_SSO_CLIENT_ID', '123')
    @patch('esi.checks.settings.ESI_SSO_CLIENT_SECRET', 'abc')
    @patch('esi.checks.settings.ESI_SSO_CALLBACK_URL', None)
    @patch('esi.checks.settings.DEBUG', False)
    def test_settings_incomplete_non_debug_mode(self):
        errors = check_sso_application_settings()
        self.assertEqual(len(errors), 1)


"""unit tests for esi"""

import logging

from django.test import TestCase
from ..templatetags.scope_tags import scope_friendly_name
from . import _set_logger

_set_logger(logging.getLogger('esi'), __file__)


class TestScope(TestCase):
    """tests for template tag"""

    def test_friendly_name_fail(self):
        x = scope_friendly_name('dummy_scope')
        self.assertEqual(
            "dummy_scope",
            x
        )

    def test_friendly_name_pass(self):
        x = scope_friendly_name('test.dummy_scope.test')
        self.assertEqual(
            "dummy scope",
            x
        )

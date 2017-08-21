# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import unittest

from mixpanel_jql import JQL, raw
from mixpanel_jql.query import _f
from mixpanel_jql.exceptions import InvalidJavaScriptText


class TestJavaScriptArgs(unittest.TestCase):

    def setUp(self):
        self.query = JQL(None, None)

    def _assert_invalid_arg(self, arg):
        with self.assertRaises(InvalidJavaScriptText):
            self.query.filter(arg)

    def test_valid_javascript_arg(self):
        self.query.filter("e.x == 'y'")
        self._assert_invalid_arg(4)
        self._assert_invalid_arg(list)
        self._assert_invalid_arg(True)

    def test_auto_function(self):
        self.assertEqual(_f(raw("test")), "test")
        self.assertEqual(_f("test"), "function(e){return test}")

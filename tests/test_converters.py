# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import unittest

from mixpanel_jql import Converter


class TestConverters(unittest.TestCase):

    def test_to_number(self):
        self.assertEqual(
            str(Converter.to_number('e.properties.y')),
            'mixpanel.to_number(function(e){return e.properties.y})')

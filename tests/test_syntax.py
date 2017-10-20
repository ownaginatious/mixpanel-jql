# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import datetime
import unittest
import warnings

from mixpanel_jql import JQL, raw, Events, People
from mixpanel_jql.query import _f
from mixpanel_jql.exceptions import InvalidJavaScriptText, JQLSyntaxError


class TestJavaScriptArgs(unittest.TestCase):

    def setUp(self):
        self.query = JQL(api_secret=None, events=Events())

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


class TestSourceParameters(unittest.TestCase):

    def _try_invalid_events(self, params):
        try:
            Events(params)
            self.fail("Expected Events syntax error with params: %s" % params)
        except JQLSyntaxError as e:
            return e

    def _try_invalid_people(self, params):
        try:
            People(params)
            self.fail("Expected People syntax error with params: %s" % params)
        except JQLSyntaxError as e:
            return e

    def _try_invalid_join(self, params):
        try:
            JQL(api_secret="asas", events=Events(), people=People(), join_params=params)
            self.fail("Expected Events syntax error with params: %s" % params)
        except JQLSyntaxError as e:
            return e

    def test_bad_event_key(self):
        e = self._try_invalid_events({'mew': 32})
        self.assertEqual('"mew" is not a valid key in event_params', str(e))

    def test_event_date_keys(self):
        for k in ('to_date', 'from_date'):
            for v in ('2017-10-19', datetime(2017, 10, 19), datetime(2017, 10, 19).date()):
                q = Events({k: v})
                self.assertIn('2017-10-19', str(q))

        # Now a bad key.
        e = self._try_invalid_events({'to_date': 232})
        self.assertEqual(str(e), 'to_date must be datetime, datetime.date, or str')

    def test_event_event_selectors(self):

        def good_params():
            return {
                'event_selectors': [{
                    'event': 'my_event',
                    'selector': 'my selector',
                    'label': 'my label'
                }]
            }

        # Test valid
        Events(good_params())

        # Bad array
        bad_params = good_params()
        bad_params['event_selectors'] = 3
        e = self._try_invalid_events(bad_params)
        self.assertEqual(
            str(e), "event_params['event_selectors'] must be iterable")

        # Bad key types
        for key in ('event', 'selector', 'label'):
            bad_params = good_params()
            bad_params['event_selectors'][0][key] = 3
            e = self._try_invalid_events(bad_params)
            self.assertEqual(
                str(e), "event_params['event_selectors'][0].%s must be a string" % key)

        # Bad key
        bad_params = good_params()
        bad_params['event_selectors'][0]['mrao'] = 3
        e = self._try_invalid_events(bad_params)
        self.assertEqual(
            str(e), "'mrao' is not a valid key in event_params['event_selectors'][0]")

    def test_bad_people_key(self):
        e = self._try_invalid_people({'mew': 32})
        self.assertEqual('"mew" is not a valid key in people_params', str(e))

    def test_people_user_selectors(self):

        def good_params():
            return {
                'user_selectors': [{
                    'selector': 'my selector',
                }]
            }

        # Test valid
        People(good_params())

        # Bad key types
        bad_params = good_params()
        bad_params['user_selectors'][0]['selector'] = 3
        e = self._try_invalid_people(bad_params)
        self.assertEqual(
            str(e), "people_params['user_selectors'][0].selector must be a string")

        # Bad key
        bad_params = good_params()
        bad_params['user_selectors'][0]['mrao'] = 3
        e = self._try_invalid_people(bad_params)
        self.assertEqual(
            str(e), "'mrao' is not a valid key in people_params['user_selectors'][0]")

    def test_bad_join_key(self):
        e = self._try_invalid_join({'mew': 32})
        self.assertEqual('"mew" is not a valid key in join_params', str(e))

    def test_join_types(self):
        # Good types
        for t in ('full', 'left', 'right', 'inner'):
            JQL('some_key', events=Events(), people=People(), join_params={'type': t})

        # Bad type
        e = self._try_invalid_join({'type': 'mew'})
        self.assertEqual(
            '"mew" is not a valid join type (valid types: full, left, right, inner)',
            str(e))

    def test_join_selectors(self):

        def good_params():
            return {
                'selectors': [{
                    'event': 'my_event',
                    'selector': 'my selector'
                }]
            }

        # Test valid
        JQL('some_api_key', events=Events(), people=People(), join_params=good_params())

        # Bad array
        bad_params = good_params()
        bad_params['selectors'] = 3
        e = self._try_invalid_join(bad_params)
        self.assertEqual(
            str(e), "join_params['selectors'] must be iterable")

        # Bad key types
        for key in ('event', 'selector'):
            bad_params = good_params()
            bad_params['selectors'][0][key] = 3
            e = self._try_invalid_join(bad_params)
            self.assertEqual(
                str(e), "join_params['selectors'][0].%s must be a string" % key)

        # Bad key
        bad_params = good_params()
        bad_params['selectors'][0]['mrao'] = 3
        e = self._try_invalid_join(bad_params)
        self.assertEqual(
            str(e), "'mrao' is not a valid key in join_params['selectors'][0]")


class TestDeprecatedSyntaxWarnings(unittest.TestCase):

    def test_query_plan(self):
        with warnings.catch_warnings(record=True) as w:
            q = JQL('key', events=Events(), people=People())
            q.query_plan()
            self.assertIs(w[-1].category, DeprecationWarning)
            self.assertIn('query_plan', str(w[-1].message))

    def test_params(self):
        with warnings.catch_warnings(record=True) as w:
            JQL('key', params={})
            self.assertEqual(len(w), 1)
            self.assertIs(w[-1].category, DeprecationWarning)
            self.assertIn('params', str(w[-1].message))

    def test_events_boolean(self):
        with warnings.catch_warnings(record=True) as w:
            JQL('key', events=True)
            self.assertEqual(len(w), 1)
            self.assertIs(w[-1].category, DeprecationWarning)
            self.assertIn('events', str(w[-1].message))

    def test_people_boolean(self):
        with warnings.catch_warnings(record=True) as w:
            JQL('key', people=True)
            self.assertEqual(len(w), 1)
            self.assertIs(w[-1].category, DeprecationWarning)
            self.assertIn('people', str(w[-1].message))

# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import unittest

from mixpanel_jql import JQL, raw, Events, Reducer


class TestAccessorOnlyTransformations(unittest.TestCase):

    def setUp(self):
        self.query = JQL(api_secret=None, events=Events())

    def _test(self, manipulator, expected_function):
        manipulator = getattr(self.query, manipulator)
        self.assertEqual(
            str(manipulator('e.properties.some_accessor')),
            'function main() { return Events({}).'
            '%s(function(e){'
            'return e.properties.some_accessor}); }' % expected_function)
        self.assertEqual(
            str(manipulator(raw('"a"'))),
            'function main() { return Events({}).%s("a"); }' % expected_function)

    def test_filter(self):
        self._test('filter', 'filter')

    def test_map(self):
        self._test('map', 'map')

    def test_sort_asc(self):
        self._test('sort_asc', 'sortAsc')

    def test_sort_desc(self):
        self._test('sort_desc', 'sortDesc')

    def test_reduce(self):
        self._test('reduce', 'reduce')
        self.assertEqual(
            str(self.query.reduce(Reducer.any())),
            'function main() { return Events({}).reduce(mixpanel.reducer.any()); }'
        )


class TestGroupTransformations(unittest.TestCase):

    def setUp(self):
        self.query = JQL(api_secret=None, events=Events())

    def _test(self, grouper, expected_function):
        grouper = getattr(self.query, grouper)
        self.assertEqual(
            str(grouper(['e.a', 'e.b', 'e.c'], 'e.properties.some_accessor')),
            'function main() { return Events({}).'
            '%s(['
            'function(e){return e.a}, function(e){return e.b}, function(e){return e.c}'
            '], function(e){return e.properties.some_accessor}); }' % expected_function)

        self.assertEqual(
            str(grouper([
                raw('e.a'), raw('e.b'), raw('e.c')], raw('e.properties.some_accessor'))),
            'function main() { return Events({}).'
            '%s([e.a, e.b, e.c], e.properties.some_accessor); }' % expected_function)

        self.assertEqual(
            str(grouper([
                raw('e.a'), raw('e.b'), raw('e.c')], Reducer.count())),
            'function main() { return Events({}).'
            '%s([e.a, e.b, e.c], mixpanel.reducer.count()); }' % expected_function)

        # Non iterable key.
        self.assertEqual(
            str(grouper(raw('e.a'), raw('e.properties.some_accessor'))),
            'function main() { return Events({}).'
            '%s([e.a], e.properties.some_accessor); }' % expected_function)

    def test_group_by(self):
        self._test('group_by', 'groupBy')

    def test_group_by_user(self):
        self._test('group_by_user', 'groupByUser')

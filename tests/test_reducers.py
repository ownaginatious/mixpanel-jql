# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import unittest

from mixpanel_jql import Reducer, raw
from mixpanel_jql.exceptions import JQLSyntaxError


class TestParameterlessReducers(unittest.TestCase):

    def _test(self, reducer, expected_function):
        self.assertEqual(str(reducer()), 'mixpanel.reducer.%s()' % expected_function)

    def test_count(self):
        self._test(Reducer.count, 'count')

    def test_null(self):
        self._test(Reducer.null, 'null')

    def test_any(self):
        self._test(Reducer.any, 'any')

    def test_object_merge(self):
        self._test(Reducer.object_merge, 'object_merge')


class TestAccessorOnlyReducers(unittest.TestCase):

    def _test(self, reducer, expected_function):
        self.assertEqual(
            str(reducer('e.properties.some_accessor')),
            'mixpanel.reducer.%s(function(e){'
            'return e.properties.some_accessor})' % expected_function)
        self.assertEqual(
            str(reducer(raw('"a"'))), 'mixpanel.reducer.%s("a")' % expected_function)

    def test_sum(self):
        self._test(Reducer.sum, 'sum')

    def test_avg(self):
        self._test(Reducer.avg, 'avg')

    def test_min(self):
        self._test(Reducer.min, 'min')

    def test_min_by(self):
        self._test(Reducer.min_by, 'min_by')

    def test_max(self):
        self._test(Reducer.max, 'max')

    def test_max_by(self):
        self._test(Reducer.max_by, 'max_by')

    def test_numeric_summary(self):
        self._test(Reducer.numeric_summary, 'numeric_summary')


class TestComplexReducers(unittest.TestCase):

    def test_top(self):
        self.assertEqual(str(Reducer.top(7)), 'mixpanel.reducer.top(7)')
        with self.assertRaises(JQLSyntaxError):
            Reducer.top('meow')

    def test_numeric_percentiles(self):
        self.assertEqual(
            str(Reducer.numeric_percentiles('e.properties.x', 1)),
            'mixpanel.reducer.numeric_percentiles(function(e){return e.properties.x}, 1)')
        self.assertEqual(
            str(Reducer.numeric_percentiles('e.properties.x', [1, 2, 3])),
            'mixpanel.reducer.numeric_percentiles(function(e){return e.properties.x}, [1, 2, 3])')
        self.assertEqual(
            str(Reducer.numeric_percentiles(raw('e.properties.x'), 1)),
            'mixpanel.reducer.numeric_percentiles(e.properties.x, 1)')
        self.assertEqual(
            str(Reducer.numeric_percentiles(raw('e.properties.x'), [1, 2, 3])),
            'mixpanel.reducer.numeric_percentiles(e.properties.x, [1, 2, 3])')

        with self.assertRaises(JQLSyntaxError):
            Reducer.numeric_percentiles(raw('e.properties.x'), [1, 2, 'a'])

        with self.assertRaises(JQLSyntaxError):
            Reducer.numeric_percentiles(raw('e.properties.x'), 'meow')

    def test_numeric_bucket(self):
        self.assertEqual(
            str(Reducer.numeric_bucket('e.properties.x', {'a': 1})),
            'mixpanel.reducer.numeric_bucket(function(e){return e.properties.x}, {\'a\': 1})')
        self.assertEqual(
            str(Reducer.numeric_bucket('e.properties.x', [1, 2, 3])),
            'mixpanel.reducer.numeric_bucket(function(e){return e.properties.x}, [1, 2, 3])')
        self.assertEqual(
            str(Reducer.numeric_bucket(raw('e.properties.x'), {'a': 1})),
            'mixpanel.reducer.numeric_bucket(e.properties.x, {\'a\': 1})')
        self.assertEqual(
            str(Reducer.numeric_bucket(raw('e.properties.x'), [1, 2, 3])),
            'mixpanel.reducer.numeric_bucket(e.properties.x, [1, 2, 3])')

        with self.assertRaises(JQLSyntaxError):
            Reducer.numeric_bucket(raw('e.properties.x'), 'a')

    def test_apply_group_limits(self):
        self.assertEqual(
            str(Reducer.apply_group_limits([1, 2, 3], 1)),
            'mixpanel.reducer.applyGroupLimits([1, 2, 3], 1)')

        with self.assertRaises(JQLSyntaxError):
            Reducer.apply_group_limits([1, 2, 3], 'a')

        with self.assertRaises(JQLSyntaxError):
            Reducer.apply_group_limits(77, 77)

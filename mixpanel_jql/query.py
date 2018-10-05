from __future__ import absolute_import

import collections
from contextlib import closing
from datetime import datetime, date
import json
import warnings

from itertools import chain, islice

import ijson
import jsbeautifier
import requests
from requests.auth import HTTPBasicAuth
import six

from .exceptions import JQLSyntaxError, InvalidJavaScriptText

warnings.simplefilter('default')


def _decode(entity):
    """
    Decodes all unicode characters to avoid the `u` prefix from
    proliferating in complex data structures. We should probably
    instead JSON encode everything, but for now, this is fine.

    This is only needed as long as Python 2 support is necessary.

    :param entity: The entity to decode.
    :return: The iterable without unicode.
    """

    # Only necessary for Python 2
    if six.PY3:
        return entity
    if isinstance(entity, tuple):
        return tuple(_decode(e) for e in entity)
    elif isinstance(entity, list):
        return list(_decode(e) for e in entity)
    elif isinstance(entity, dict):
        return {_decode(k): _decode(v) for k, v in entity.items()}
    elif isinstance(entity, six.text_type):
        return entity.encode('utf8')
    return entity


class RawJavaScript(object):

    def __init__(self, java_script):
        if not isinstance(java_script, (str, six.text_type)):
            raise InvalidJavaScriptText(
                "Must be a text type (str, unicode)")
        self.java_script = java_script

    def __repr__(self):
        return "RawJavaScript('%s')" % self.java_script


class Converter(object):

    def __init__(self, func):
        self._func = func

    def __str__(self):
        return "mixpanel.%s" % self._func

    def __repr__(self):
        return "Converter('%s')" % str(self)

    @staticmethod
    def to_number(accessor):
        return Converter('to_number(%s)' % _f(accessor))


class Reducer(object):

    def __init__(self, func):
        self._func = func

    def __str__(self):
        return "mixpanel.reducer.%s" % self._func

    def __repr__(self):
        return "Reducer('%s')" % str(self)

    @staticmethod
    def _r(f):
        return Reducer(f)

    @staticmethod
    def count():
        return Reducer._r("count()")

    @staticmethod
    def top(limit):
        if not isinstance(limit, int):
            raise JQLSyntaxError('limit in top must be an integer')
        return Reducer._r("top(%d)" % limit)

    @staticmethod
    def sum(accessor):
        return Reducer._r("sum(%s)" % _f(accessor))

    @staticmethod
    def avg(accessor):
        return Reducer._r("avg(%s)" % _f(accessor))

    @staticmethod
    def min(accessor):
        return Reducer._r("min(%s)" % _f(accessor))

    @staticmethod
    def min_by(accessor):
        return Reducer._r("min_by(%s)" % _f(accessor))

    @staticmethod
    def max(accessor):
        return Reducer._r("max(%s)" % _f(accessor))

    @staticmethod
    def max_by(accessor):
        return Reducer._r("max_by(%s)" % _f(accessor))

    @staticmethod
    def null():
        return Reducer._r("null()")

    @staticmethod
    def any():
        return Reducer._r("any()")

    @staticmethod
    def numeric_summary(accessor):
        return Reducer._r("numeric_summary(%s)" % _f(accessor))

    @staticmethod
    def numeric_percentiles(accessor, percentiles):
        if not isinstance(percentiles, (int, tuple, list)):
            raise JQLSyntaxError(
                'percentiles in numeric_percentiles must be an integer or array')
        if isinstance(percentiles, (tuple, list)):
            for e in percentiles:
                if not isinstance(e, int):
                    raise JQLSyntaxError(
                        'percentiles in numeric_percentiles as an array '
                        'must only contain integers'
                    )
        return Reducer._r("numeric_percentiles(%s, %s)" % (_f(accessor), _decode(percentiles)))

    @staticmethod
    def numeric_bucket(accessor, buckets):
        if not isinstance(buckets, (tuple, list, dict)):
            raise JQLSyntaxError('buckets in numeric_bucket must be an array or dict')
        return Reducer._r("numeric_bucket(%s, %s)" % (_f(accessor), _decode(buckets)))

    @staticmethod
    def object_merge():
        return Reducer._r("object_merge()")

    @staticmethod
    def apply_group_limits(limits, global_limit):
        if not isinstance(limits, (tuple, list)):
            raise JQLSyntaxError('limits in apply_group_limits must be iterable')
        if not isinstance(global_limit, int):
            raise JQLSyntaxError('global_limit in apply_group_limits must be an integer')
        return Reducer._r("applyGroupLimits(%s, %s)" % (_decode(limits), global_limit))


def _f(e):
    if not isinstance(e, (RawJavaScript, str, six.text_type)):
        raise InvalidJavaScriptText(
            "Must be a text type (str, unicode) or wrapped "
            "as raw(str||unicode)")
    if isinstance(e, RawJavaScript):
        return e.java_script
    return "function(e){return %s}" % e


def raw(e):
    return RawJavaScript(e)


class RequestsStreamWrapper(object):
    """
    A wrapper around a requests response payload for converting
    the returned generator into a file-like object.
    """

    def __init__(self, resp):
        self.data = chain.from_iterable(resp.iter_content())

    def read(self, n):
        if six.PY3:
            return bytes(islice(self.data, None, n))
        else:
            return "".join(islice(self.data, None, n))


class Events(object):

    def __init__(self, params=None):
        self.src = self._validate_event_params(params)

    def _validate_event_params(self, params):
        if not params:
            return "{}"
        if not isinstance(params, dict):
            raise JQLSyntaxError("event_params must be a dict")
        params = dict(params)
        for k, v in params.items():
            if k in ('to_date', 'from_date'):
                if isinstance(v, (datetime, date,)):
                    params[k] = v.strftime('%Y-%m-%d')
                elif not isinstance(v, six.string_types):
                    raise JQLSyntaxError('to_date must be datetime, datetime.date, or str')
            elif k == 'event_selectors':
                if not isinstance(v, collections.Iterable):
                    raise JQLSyntaxError("event_params['event_selectors'] must be iterable")
                for i, e in enumerate(v):
                    if not isinstance(e, dict):
                        raise JQLSyntaxError("event_params['event_selectors'][x] must be a dict")
                    for ek, ev in e.items():
                        if ek not in ('event', 'selector', 'label'):
                            raise JQLSyntaxError(
                                "'%s' is not a valid key in "
                                "event_params['event_selectors'][%s]" % (ek, i))
                        elif not isinstance(ev, six.string_types):
                            raise JQLSyntaxError(
                                "event_params['event_selectors'][%s].%s "
                                "must be a string" % (i, ek))
            else:
                raise JQLSyntaxError('"%s" is not a valid key in event_params' % k)
        return json.dumps(params)

    def __str__(self):
        return "Events(%s)" % self.src


class People(object):

    def __init__(self, params=None):
        self.src = self._validate_people_params(params)

    def _validate_people_params(self, params):
        if not params:
            return "{}"
        if not isinstance(params, dict):
            raise JQLSyntaxError("people_params must be a dict")
        for k, v in params.items():
            if k != 'user_selectors':
                raise JQLSyntaxError('"%s" is not a valid key in people_params' % k)
            if not isinstance(v, collections.Iterable):
                raise JQLSyntaxError("people_params['user_selectors'] must be iterable")
            for i, e in enumerate(v):
                for ek, ev in e.items():
                    if ek not in ('selector',):
                        raise JQLSyntaxError(
                            "'%s' is not a valid key in "
                            "people_params['user_selectors'][%s]" % (ek, i))
                    elif not isinstance(ev, six.string_types):
                        raise JQLSyntaxError(
                                "people_params['user_selectors'][%s].%s "
                                "must be a string" % (i, ek))
        return json.dumps(params)

    def __str__(self):
        return "People(%s)" % self.src


class JQL(object):

    ENDPOINT = 'https://mixpanel.com/api/%s/jql'
    VERSION = '2.0'
    VALID_JOIN_TYPES = ('full', 'left', 'right', 'inner')

    def __init__(
            self, api_secret, params=None, events=None, people=None, join_params=None):
        """
        Creates a new immutable JQL instance.

        :param api_secret: Mixpanel API key for query authorization.
        :param params: parameters for event filtering (only matters if events=True).
        :param events: include events as an input (default: None)
        :param people: include people as an input (default: None)
        :param join_params: parameters for join filtering (only matters if
                             people=True and events=True).
        """

        if params is not None:
            warnings.warn(
                "The params=... kwarg is being deprecated in favor of events=Events(params). "
                "The params argument will be removed in 1.0.",
                DeprecationWarning)
            events = Events(params)

        if events is not None:
            if events in (True, False):
                warnings.warn(
                    "The events kwarg should only take an Event(...) as its argument. "
                    "Taking a boolean will no longer be supported in 1.0.",
                    DeprecationWarning)
                if events:
                    events = Events()

        if people is not None:
            if people in (True, False):
                warnings.warn(
                    "The people kwarg should only take an People(...) as its argument. "
                    "Taking a boolean will no longer be supported in 1.0.",
                    DeprecationWarning)
                if people:
                    people = People()

        self.api_secret = api_secret
        self.operations = ()
        if events and people:
            self.source = (
                "join(%s, %s, %s)" % (events, people, self._validate_join_params(join_params)))
        elif events and not people:
            self.source = str(events)
        elif not events and people:
            self.source = str(people)
        else:
            raise JQLSyntaxError("No data sources specified (events=... or people=...)")

    def _validate_join_params(self, params):
        if not params:
            return "{}"
        if not isinstance(params, dict):
            raise JQLSyntaxError("join_params must be a dict")
        for k, v in params.items():
            if k == 'type':
                if v not in self.VALID_JOIN_TYPES:
                    raise JQLSyntaxError(
                        '"%s" is not a valid join type (valid types: %s)'
                        % (v, ', '.join(self.VALID_JOIN_TYPES))
                    )
            elif k == 'selectors':
                if not isinstance(v, collections.Iterable):
                    raise JQLSyntaxError("join_params['selectors'] must be iterable")
                for i, e in enumerate(v):
                    if not isinstance(e, dict):
                        raise JQLSyntaxError("join_params['selectors'][x] must be a dict")
                    for ek, ev in e.items():
                        if ek not in ('event', 'selector'):
                            raise JQLSyntaxError(
                                "'%s' is not a valid key in "
                                "join_params['selectors'][%s]" % (ek, i))
                        elif not isinstance(ev, six.string_types):
                            raise JQLSyntaxError(
                                "join_params['selectors'][%s].%s "
                                "must be a string" % (i, ek))
            else:
                raise JQLSyntaxError('"%s" is not a valid key in join_params' % k)
        return json.dumps(params)

    def _clone(self):
        jql = JQL(self.api_secret, events=Events())
        jql.source = self.source
        jql.operations = self.operations
        return jql

    def filter(self, f):
        jql = self._clone()
        jql.operations += ("filter(%s)" % _f(f),)
        return jql

    def map(self, f):
        jql = self._clone()
        jql.operations += ("map(%s)" % _f(f),)
        return jql

    def flatten(self):
        jql = self._clone()
        jql.operations += ("flatten()",)
        return jql

    def sort_asc(self, accessor):
        jql = self._clone()
        jql.operations += ("sortAsc(%s)" % _f(accessor),)
        return jql

    def sort_desc(self, accessor):
        jql = self._clone()
        jql.operations += ("sortDesc(%s)" % _f(accessor),)
        return jql

    def reduce(self, accumulator):
        if not isinstance(accumulator, Reducer):
            accumulator = _f(accumulator)
        jql = self._clone()
        jql.operations += ("reduce(%s)" % accumulator,)
        return jql

    def group_by(self, keys, accumulator):
        return self._group_by(False, keys, accumulator)

    def group_by_user(self, keys, accumulator):
        return self._group_by(True, keys, accumulator)

    def _group_by(self, user, keys, accumulator):
        if not isinstance(keys, (tuple, set, list)):
            keys = [keys]
        if not isinstance(accumulator, Reducer):
            accumulator = _f(accumulator)
        jql = self._clone()
        op = "groupByUser" if user else "groupBy"
        jql.operations += ("%s([%s], %s)" % (op, ", ".join(_f(k) for k in keys), accumulator),)
        return jql

    def query_plan(self):
        warnings.warn(
            "JQL(...).query_plan is being deprecated in favor or str(JQL(...))",
            DeprecationWarning)
        return str(self)

    @property
    def pretty(self):
        return jsbeautifier.beautify(str(self))

    def __str__(self):
        script = "function main() { return %s%s; }" %\
           (self.source, "".join(".%s" % i for i in self.operations))
        return script

    def send(self):
        with closing(requests.post(self.ENDPOINT % self.VERSION,
                                   auth=HTTPBasicAuth(self.api_secret, ''),
                                   data={'script': str(self)},
                                   stream=True)) as resp:
            resp.raise_for_status()
            for row in ijson.items(RequestsStreamWrapper(resp), 'item'):
                yield row

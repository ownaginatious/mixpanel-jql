from contextlib import closing
import json
from itertools import chain, islice
import ijson
import requests
from requests.auth import HTTPBasicAuth
import six


class JQLError(Exception):
    pass


class Reducer(object):

    @staticmethod
    def count():
        return "mixpanel.reducer.count()"

    @staticmethod
    def top(limit):
        return "mixpanel.reducer.top(%d)" % limit

    @staticmethod
    def sum(accessor):
        return "mixpanel.reducer.sum(%s)" % accessor

    @staticmethod
    def numeric_summary(accessor):
        return "mixpanel.reducer.numeric_summary(%s)" % accessor

    @staticmethod
    def object_merge(accessor):
        return "mixpanel.reducer.object_merge(%s)" % accessor


def _f(e):
    return "function(e){return %s}" % e


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


class JQL(object):

    ENDPOINT = 'https://mixpanel.com/api/%s/jql'
    VERSION = '2.0'

    def __init__(self, api_secret, params, events=True, people=False):
        """
        params      - parameters to the script
        filters     - an iterable of filters to apply (use list to guarantee a
                      certain sequence)
        group_by    - a dictionary of values to group by (key is the label in
                      the output)
        accumulator - the value to accumulate in the grouping function
        events      - include events as an input (default: True)
        people      - include people as an input (default: false)
        """
        self.api_secret = api_secret
        self.params = params
        self.operations = ()
        if events and people:
            self.source = "join(Events(params), People())"
        elif events:
            self.source = "Events(params)"
        elif people:
            self.source = "People()"
        else:
            raise JQLError("No data source specified ('Event' or 'People')")

    def _clone(self):
        jql = JQL(self.api_secret, self.params)
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

    def group_by(self, keys, accumulator):
        if isinstance(keys, str) or isinstance(keys, six.text_type):
            keys = [keys]
        jql = self._clone()
        jql.operations += ("groupBy([%s], %s)"
                           % (",".join(_f(k) for k in keys), accumulator),)
        return jql

    def group_by_user(self, keys, accumulator):
        if isinstance(keys, str) or isinstance(keys, six.text_type):
            keys = [keys]
        jql = self._clone()
        jql.operations += ("groupByUser([%s], %s)"
                           % (",".join(_f(k) for k in keys), accumulator),)
        return jql

    def query_plan(self):
        script = "function main() { return %s%s; }" %\
           (self.source, "".join(".%s" % i for i in self.operations))
        return script

    def send(self):
        with closing(requests.post(self.ENDPOINT % self.VERSION,
                                   auth=HTTPBasicAuth(self.api_secret, ''),
                                   data={'params': json.dumps(self.params),
                                         'script': self.query_plan()},
                                   stream=True)) as resp:
            resp.raise_for_status()
            for row in ijson.items(RequestsStreamWrapper(resp), 'item'):
                yield row


mixpanel-jql
============

A small Python library for running `JQL <https://mixpanel.com/jql/>`__
queries against Mixpanel's JQL API. The data returned from the API is
automatically decompressed as it arrives, making it available for
processing as soon as the first row arrives. This is to avoid buffering
large result sets in memory.

Installation
------------

To install the ``mixpanel-jql`` library, simply run the following in
your terminal:

``pip install mixpanel-jql``

Simple example
--------------

Let's do a simple count of our number of 'X' events over each day of May 2016. Our key for grouping will be the date the event was sent to Mixpanel in the format ``YYYY-MM-DD``. We can get that from our event's ``time`` property by specifying our key as ``new Date(e.time).toISOString().split('T')[0]``.

This is simple and fast to do with this library.

.. code:: python

    from mixpanel_jql import JQL, Reducer

    api_secret = '...'

    params = {
        'event_selectors': [{'event': "X"}],
        'from_date': '2016-05-01',
        'to_date': '2016-05-31'
    }

    query = JQL(api_secret, params)\
              .group_by(
                  keys=[
                      "new Date(e.time).toISOString().split('T')[0]",
                  ],
                  accumulator=Reducer.count())

    for row in query.send():
        date = row['key'][0]
        value = row['value']
        print("[%s] => %d" % (date, value))
    # [2016-05-01] => 302
    # [2016-05-02] => 1102
    # ...
    # [2016-05-31] => 120

But what if we only want to count unique events? That is to say, what if we care about how many users spawned each event per day and not just the overall number of times the event occurred?

With some minor modification to our previous code, we can achieve this:

.. code:: python

    query = JQL(api_secret, params)\
              .group_by_user(
                  keys=[
                      "new Date(e.time).toISOString().split('T')[0]",
                  ],
                  accumulator="function(){ return 1;}")\
              .group_by(
                  keys=["e.key.slice(1)"],
                  accumulator=Reducer.count())

We replace our ``accumulator`` keyward argument with a JavaScript function returning ``1``, since each user will only be counted for once. ``group_by_user`` also adds the user ID into the key of our results. We can regroup our results by slicing that detail off with ``e.key.slice(1)`` and recounting.

More advanced examples
----------------------

Let's assume we want to count all events 'A' with a property 'B' that is
equal to 2 and a property F that is equal to "hello". Events 'A' also
have a property 'C', which is some random string value. We want the
results grouped and tallied by values of 'C' to see how many property
'C' events occurred over each day in the month of April 2016.

.. code:: python

    from mixpanel_jql import JQL, Reducer

    api_secret = '...'

    params = {
        'event_selectors': [{'event': "A"}],
        'from_date': '2016-04-01',
        'to_date': '2016-04-30'
    }

    query = JQL(api_secret, params)\
              .filter('e.property.B == 2')\
              .filter('e.property.F == "hello"')\
              .group_by(
                  keys=[
                      "new Date(e.time).toISOString().split('T')[0]",
                      "e.property.C"
                  ],
                  accumulator=Reducer.count())

    for row in query.send():
        date, c = row['key'][0]
        value = row['value']
        print("[%s] %s => %d" % (date, c, value))
    # [2016-04-01] abc => 3
    # [2016-04-01] xyz => 1
    # ...

If we wanted to count only *unique* events (i.e. count each user causing
the event only once), we can change our query to *group by user*, to
reduce the number of times they caused a particular ``e.properties.C``
to just 1.

.. code:: python

    query = JQL(api_secret, params)\
              .filter('e.property.B == 2')\
              .filter('e.property.F == "hello"')\
              .group_by_user(
                  keys=[
                      "new Date(e.time).toISOString().split('T')[0]",
                      "e.property.C"
                  ],
                  accumulator="function(){ return 1;}")\
              .group_by(
                  keys=["e.key.slice(1)"],
                  accumulator=Reducer.count())

Why are your filters not joined with ``&&``?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We could have also combined our ``.filter(...)`` methods into 1 method
by doing, ``.filter('e.property.B == 2 && e.property.F == "hello"')``.
Successive ``.filter(...)`` expressions are automatically ``&&``'ed. The
method of expression you choose is stylistic.

What is that ``Reducer`` thing?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``Reducer`` class is for convenience and contains shortcuts to all
the reducer functions (e.g. ``Reducer.count()`` returns
``mixpanel.reducer.count()``, and ``Reducer.top(limit)`` returns
``mixpanel.reducer.top(limit)``). Refer to the code for a list of all
reducer shortcuts.

To write your own reducer, make sure to include a full JavaScript
function body (i.e. ``function(){ ... }``).

How do I see what the final JavaScript sent to Mixpanel will be?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the ``.query_plan()`` method on your JQL query to view what the
equivalent JavaScript will be.

.. code:: python

    >>> query.query_plan()
    'function main() { return Events(params).filter(function(e){return e.property.B == 2}).filter(function(e){return e.property.F == "hello"}).groupByUser([function(e){return new Date(e.time)).toISOString().split(\'T\')[0]},function(e){return e.property.C}], function(){ return 1;}).groupBy([function(e){return e.key.slice(1)}], mixpanel.reducer.count()); }'

This can be quite helpful during debugging.

Caveats
-------

``.filter(...)`` automatically transforms whatever is within the
parenthesis' into ``function(e){ return ... }``. This library does
**not** support the ``properties.x`` shortcut syntax and requires
``e.properties.x``.

This library cannot easily express everything possible in Mixpanel's JQL
language, but does try to simplify the general cases. If you have some
ideas for making this library more user friendly to a wider range of
potential queries, please submit a pull request or create an issue.

Contributions are very welcome!

Where can I learn more about Mixpanel's JQL?
--------------------------------------------

For more information on what you can do with JQL, refer to Mixpanel's
documentation `here <https://mixpanel.com/help/reference/jql>`__.

from .query import JQL, Events, People, Reducer, Converter, raw  # noqa
from ._version import get_versions    # noqa
__version__ = get_versions()['version']  # noqa
del get_versions  # noqa

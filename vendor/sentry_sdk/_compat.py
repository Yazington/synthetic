# coding: utf-8
import sys
from ..sentry_sdk._types import MYPY
if MYPY:
    from typing import Optional
    from typing import Tuple
    from typing import Any
    from typing import Type
    from typing import TypeVar
    T = TypeVar('T')
PY2 = sys.version_info[0] == 2
if PY2:
    import urlparse
    text_type = unicode
    string_types = (str, text_type)
    number_types = (int, long, float)
    int_types = (int, long)
    iteritems = lambda x: x.iteritems()

    def implements_str(cls): # type: (T) -> T
        cls.__unicode__ = cls.__str__
        cls.__str__ = lambda x: unicode(x).encode('utf-8')
        return cls
    exec('def reraise(tp, value, tb=None):\n raise tp, value, tb')
else:
    import urllib.parse as urlparse
    text_type = str
    string_types = (text_type,) # type: Tuple[type]
    number_types = (int, float) # type: Tuple[type, type]
    int_types = (int,)
    iteritems = lambda x: x.items()

    def implements_str(x): # type: (T) -> T
        return x

    def reraise(tp, value, tb=None): # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[Any]) -> None
        assert value is not None
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

def with_metaclass(meta, *bases): # type: (Any, *Any) -> Any

    class MetaClass(type):

        def __new__(metacls, name, this_bases, d): # type: (Any, Any, Any, Any) -> Any
            return meta(name, bases, d)
    return type.__new__(MetaClass, 'temporary_class', (), {})

def check_thread_support(): # type: () -> None
    try:
        from uwsgi import opt
    except ImportError:
        return
    if 'threads' in opt:
        return
    if str(opt.get('enable-threads', '0')).lower() in ('false', 'off', 'no', '0'):
        from warnings import warn
        warn(Warning('We detected the use of uwsgi with disabled threads.  This will cause issues with the transport you are trying to use.  Please enable threading for uwsgi.  (Add the "enable-threads" flag).'))

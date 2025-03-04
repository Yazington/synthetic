# coding: utf-8
import inspect
from ..sentry_sdk.hub import Hub
from ..sentry_sdk.scope import Scope
from ..sentry_sdk._types import MYPY
if MYPY:
    from typing import Any
    from typing import Dict
    from typing import Optional
    from typing import overload
    from typing import Callable
    from typing import TypeVar
    from typing import ContextManager
    from typing import Union
    from ..sentry_sdk._types import Event, Hint, Breadcrumb, BreadcrumbHint, ExcInfo
    from ..sentry_sdk.tracing import Span, Transaction
    T = TypeVar('T')
    F = TypeVar('F', bound=Callable[..., Any])
else:

    def overload(x): # type: (T) -> T
        return x
__all__ = ['capture_event', 'capture_message', 'capture_exception', 'add_breadcrumb', 'configure_scope', 'push_scope', 'flush', 'last_event_id', 'start_span', 'start_transaction', 'set_tag', 'set_context', 'set_extra', 'set_user', 'set_level']

def hubmethod(f): # type: (F) -> F
    f.__doc__ = '%s\n\n%s' % ('Alias for :py:meth:`sentry_sdk.Hub.%s`' % f.__name__, inspect.getdoc(getattr(Hub, f.__name__)))
    return f

def scopemethod(f): # type: (F) -> F
    f.__doc__ = '%s\n\n%s' % ('Alias for :py:meth:`sentry_sdk.Scope.%s`' % f.__name__, inspect.getdoc(getattr(Scope, f.__name__)))
    return f

@hubmethod
def capture_event(event, hint=None, scope=None, **scope_args): # type: (...) -> Optional[str]
    return Hub.current.capture_event(event, hint, scope=scope, **scope_args)

@hubmethod
def capture_message(message, level=None, scope=None, **scope_args): # type: (...) -> Optional[str]
    return Hub.current.capture_message(message, level, scope=scope, **scope_args)

@hubmethod
def capture_exception(error=None, scope=None, **scope_args): # type: (...) -> Optional[str]
    return Hub.current.capture_exception(error, scope=scope, **scope_args)

@hubmethod
def add_breadcrumb(crumb=None, hint=None, **kwargs): # type: (...) -> None
    return Hub.current.add_breadcrumb(crumb, hint, **kwargs)

@overload
def configure_scope(): # type: () -> ContextManager[Scope]
    pass

@overload
def configure_scope(callback): # type: (...) -> None
    pass

@hubmethod
def configure_scope(callback=None): # type: (...) -> Optional[ContextManager[Scope]]
    return Hub.current.configure_scope(callback)

@overload
def push_scope(): # type: () -> ContextManager[Scope]
    pass

@overload
def push_scope(callback): # type: (...) -> None
    pass

@hubmethod
def push_scope(callback=None): # type: (...) -> Optional[ContextManager[Scope]]
    return Hub.current.push_scope(callback)

@scopemethod
def set_tag(key, value): # type: (str, Any) -> None
    return Hub.current.scope.set_tag(key, value)

@scopemethod
def set_context(key, value): # type: (str, Dict[str, Any]) -> None
    return Hub.current.scope.set_context(key, value)

@scopemethod
def set_extra(key, value): # type: (str, Any) -> None
    return Hub.current.scope.set_extra(key, value)

@scopemethod
def set_user(value): # type: (Optional[Dict[str, Any]]) -> None
    return Hub.current.scope.set_user(value)

@scopemethod
def set_level(value): # type: (str) -> None
    return Hub.current.scope.set_level(value)

@hubmethod
def flush(timeout=None, callback=None): # type: (...) -> None
    return Hub.current.flush(timeout=timeout, callback=callback)

@hubmethod
def last_event_id(): # type: () -> Optional[str]
    return Hub.current.last_event_id()

@hubmethod
def start_span(span=None, **kwargs): # type: (...) -> Span
    return Hub.current.start_span(span=span, **kwargs)

@hubmethod
def start_transaction(transaction=None, **kwargs): # type: (...) -> Transaction
    return Hub.current.start_transaction(transaction, **kwargs)

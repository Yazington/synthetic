# coding: utf-8
from ..sentry_sdk._types import MYPY
if MYPY:
    __import__('.'.join(__package__.split('.')[:-1] + ['sentry_sdk']), globals(), locals(), [], 0)
    from .. import sentry_sdk
    from typing import Optional
    from typing import Callable
    from typing import Union
    from typing import List
    from typing import Type
    from typing import Dict
    from typing import Any
    from typing import Sequence
    from typing_extensions import TypedDict
    from ..sentry_sdk.integrations import Integration
    from ..sentry_sdk._types import BreadcrumbProcessor, Event, EventProcessor, TracesSampler
    Experiments = TypedDict('Experiments', {'max_spans': Optional[int], 'record_sql_params': Optional[bool], 'smart_transaction_trimming': Optional[bool], 'propagate_tracestate': Optional[bool]}, total=False)
DEFAULT_QUEUE_SIZE = 100
DEFAULT_MAX_BREADCRUMBS = 100

class ClientConstructor(object):

    def __init__(self, dsn=None, with_locals=True, max_breadcrumbs=DEFAULT_MAX_BREADCRUMBS, release=None, environment=None, server_name=None, shutdown_timeout=2, integrations=[], in_app_include=[], in_app_exclude=[], default_integrations=True, dist=None, transport=None, transport_queue_size=DEFAULT_QUEUE_SIZE, sample_rate=1.0, send_default_pii=False, http_proxy=None, https_proxy=None, ignore_errors=[], request_bodies='medium', before_send=None, before_breadcrumb=None, debug=False, attach_stacktrace=False, ca_certs=None, propagate_traces=True, traces_sample_rate=None, traces_sampler=None, auto_enabling_integrations=True, auto_session_tracking=True, send_client_reports=True, _experiments={}): # type: (...) -> None
        pass

def _get_default_options(): # type: () -> Dict[str, Any]
    import inspect
    if hasattr(inspect, 'getfullargspec'):
        getargspec = inspect.getfullargspec
    else:
        getargspec = inspect.getargspec # type: ignore
    a = getargspec(ClientConstructor.__init__)
    defaults = a.defaults or ()
    return dict(zip(a.args[-len(defaults):], defaults))
DEFAULT_OPTIONS = _get_default_options()
del _get_default_options
VERSION = '1.5.4'
SDK_INFO = {'name': 'sentry.python', 'version': VERSION, 'packages': [{'name': 'pypi:sentry-sdk', 'version': VERSION}]}

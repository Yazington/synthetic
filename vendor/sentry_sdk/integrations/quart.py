# coding: utf-8
from __future__ import absolute_import
from ...sentry_sdk.hub import _should_send_default_pii, Hub
from ...sentry_sdk.integrations import DidNotEnable, Integration
from ...sentry_sdk.integrations._wsgi_common import _filter_headers
from ...sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from ...sentry_sdk.utils import capture_internal_exceptions, event_from_exception
from ...sentry_sdk._types import MYPY
if MYPY:
    from typing import Any
    from typing import Dict
    from typing import Union
    from ...sentry_sdk._types import EventProcessor
try:
    import quart_auth
except ImportError:
    quart_auth = None
try:
    from quart import Request, Quart, _request_ctx_stack, _websocket_ctx_stack, _app_ctx_stack
    from quart.signals import got_background_exception, got_request_exception, got_websocket_exception, request_started, websocket_started
except ImportError:
    raise DidNotEnable('Quart is not installed')
TRANSACTION_STYLE_VALUES = ('endpoint', 'url')

class QuartIntegration(Integration):
    identifier = 'quart'
    transaction_style = None

    def __init__(self, transaction_style='endpoint'): # type: (str) -> None
        if transaction_style not in TRANSACTION_STYLE_VALUES:
            raise ValueError('Invalid value for transaction_style: %s (must be in %s)' % (transaction_style, TRANSACTION_STYLE_VALUES))
        self.transaction_style = transaction_style

    @staticmethod
    def setup_once(): # type: () -> None
        request_started.connect(_request_websocket_started)
        websocket_started.connect(_request_websocket_started)
        got_background_exception.connect(_capture_exception)
        got_request_exception.connect(_capture_exception)
        got_websocket_exception.connect(_capture_exception)
        old_app = Quart.__call__

        async def sentry_patched_asgi_app(self, scope, receive, send): # type: (Any, Any, Any, Any) -> Any
            if Hub.current.get_integration(QuartIntegration) is None:
                return await old_app(self, scope, receive, send)
            middleware = SentryAsgiMiddleware(lambda *a, **kw: old_app(self, *a, **kw))
            middleware.__call__ = middleware._run_asgi3
            return await middleware(scope, receive, send)
        Quart.__call__ = sentry_patched_asgi_app

def _request_websocket_started(sender, **kwargs): # type: (Quart, **Any) -> None
    hub = Hub.current
    integration = hub.get_integration(QuartIntegration)
    if integration is None:
        return
    app = _app_ctx_stack.top.app
    with hub.configure_scope() as scope:
        if _request_ctx_stack.top is not None:
            request_websocket = _request_ctx_stack.top.request
        if _websocket_ctx_stack.top is not None:
            request_websocket = _websocket_ctx_stack.top.websocket
        try:
            if integration.transaction_style == 'endpoint':
                scope.transaction = request_websocket.url_rule.endpoint
            elif integration.transaction_style == 'url':
                scope.transaction = request_websocket.url_rule.rule
        except Exception:
            pass
        evt_processor = _make_request_event_processor(app, request_websocket, integration)
        scope.add_event_processor(evt_processor)

def _make_request_event_processor(app, request, integration): # type: (Quart, Request, QuartIntegration) -> EventProcessor

    def inner(event, hint): # type: (Dict[str, Any], Dict[str, Any]) -> Dict[str, Any]
        if request is None:
            return event
        with capture_internal_exceptions():
            request_info = event.setdefault('request', {})
            request_info['url'] = request.url
            request_info['query_string'] = request.query_string
            request_info['method'] = request.method
            request_info['headers'] = _filter_headers(dict(request.headers))
            if _should_send_default_pii():
                request_info['env'] = {'REMOTE_ADDR': request.access_route[0]}
                _add_user_to_event(event)
        return event
    return inner

def _capture_exception(sender, exception, **kwargs): # type: (Quart, Union[ValueError, BaseException], **Any) -> None
    hub = Hub.current
    if hub.get_integration(QuartIntegration) is None:
        return
    client = hub.client # type: Any
    (event, hint) = event_from_exception(exception, client_options=client.options, mechanism={'type': 'quart', 'handled': False})
    hub.capture_event(event, hint=hint)

def _add_user_to_event(event): # type: (Dict[str, Any]) -> None
    if quart_auth is None:
        return
    user = quart_auth.current_user
    if user is None:
        return
    with capture_internal_exceptions():
        user_info = event.setdefault('user', {})
        user_info['id'] = quart_auth.current_user._auth_id

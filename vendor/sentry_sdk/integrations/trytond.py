# coding: utf-8
__import__('.'.join(__package__.split('.')[:-2] + ['sentry_sdk.hub']), globals(), locals(), [], 0)
from ... import sentry_sdk
__import__('.'.join(__package__.split('.')[:-2] + ['sentry_sdk.utils']), globals(), locals(), [], 0)
from ... import sentry_sdk
__import__('.'.join(__package__.split('.')[:-2] + ['sentry_sdk.integrations']), globals(), locals(), [], 0)
from ... import sentry_sdk
__import__('.'.join(__package__.split('.')[:-2] + ['sentry_sdk.integrations.wsgi']), globals(), locals(), [], 0)
from ... import sentry_sdk
from ...sentry_sdk._types import MYPY
from trytond.exceptions import TrytonException
from trytond.wsgi import app
if MYPY:
    from typing import Any

class TrytondWSGIIntegration(sentry_sdk.integrations.Integration):
    identifier = 'trytond_wsgi'

    def __init__(self): # type: () -> None
        pass

    @staticmethod
    def setup_once(): # type: () -> None
        app.wsgi_app = sentry_sdk.integrations.wsgi.SentryWsgiMiddleware(app.wsgi_app)

        def error_handler(e): # type: (Exception) -> None
            hub = sentry_sdk.hub.Hub.current
            if hub.get_integration(TrytondWSGIIntegration) is None:
                return
            elif isinstance(e, TrytonException):
                return
            else:
                client = hub.client # type: Any
                (event, hint) = sentry_sdk.utils.event_from_exception(e, client_options=client.options, mechanism={'type': 'trytond', 'handled': False})
                hub.capture_event(event, hint=hint)
        if hasattr(app, 'error_handler'):

            @app.error_handler
            def _(app, request, e): # type: ignore
                error_handler(e)
        else:
            app.error_handlers.append(error_handler)

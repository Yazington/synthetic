# coding: utf-8
from __future__ import absolute_import
import sys
from threading import Thread, current_thread
from ...sentry_sdk import Hub
from ...sentry_sdk._compat import reraise
from ...sentry_sdk._types import MYPY
from ...sentry_sdk.integrations import Integration
from ...sentry_sdk.utils import event_from_exception, capture_internal_exceptions
if MYPY:
    from typing import Any
    from typing import TypeVar
    from typing import Callable
    from typing import Optional
    from ...sentry_sdk._types import ExcInfo
    F = TypeVar('F', bound=Callable[..., Any])

class ThreadingIntegration(Integration):
    identifier = 'threading'

    def __init__(self, propagate_hub=False): # type: (bool) -> None
        self.propagate_hub = propagate_hub

    @staticmethod
    def setup_once(): # type: () -> None
        old_start = Thread.start

        def sentry_start(self, *a, **kw): # type: (Thread, *Any, **Any) -> Any
            hub = Hub.current
            integration = hub.get_integration(ThreadingIntegration)
            if integration is not None:
                if not integration.propagate_hub:
                    hub_ = None
                else:
                    hub_ = Hub(hub)
                with capture_internal_exceptions():
                    new_run = _wrap_run(hub_, getattr(self.run, '__func__', self.run))
                    self.run = new_run # type: ignore
            return old_start(self, *a, **kw)
        Thread.start = sentry_start # type: ignore

def _wrap_run(parent_hub, old_run_func): # type: (Optional[Hub], F) -> F

    def run(*a, **kw): # type: (*Any, **Any) -> Any
        hub = parent_hub or Hub.current
        with hub:
            try:
                self = current_thread()
                return old_run_func(self, *a, **kw)
            except Exception:
                reraise(*_capture_exception())
    return run

def _capture_exception(): # type: () -> ExcInfo
    hub = Hub.current
    exc_info = sys.exc_info()
    if hub.get_integration(ThreadingIntegration) is not None:
        client = hub.client # type: Any
        (event, hint) = event_from_exception(exc_info, client_options=client.options, mechanism={'type': 'threading', 'handled': False})
        hub.capture_event(event, hint=hint)
    return exc_info

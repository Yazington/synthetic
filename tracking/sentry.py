import atexit
import platform
import re
import sys
from pathlib import Path
from pprint import pformat
from random import random
from threading import Lock, Timer
from types import TracebackType
from typing import Any, Type

import bpy

from .. import utils
from ..vendor import sentry_sdk
from ..vendor.sentry_sdk.utils import capture_internal_exceptions, event_from_exception


class TimerSet:

    def __init__(self, time: float):
        self._time = time
        self._lock = Lock()
        self._set = set()

    def __contains__(self, value: Any) -> bool:
        with self._lock:
            return value in self._set

    def add(self, value: Any):
        with self._lock:
            self._set.add(value)

        timer = Timer(self._time, self.discard, [value])
        timer.daemon = True
        timer.start()

    def discard(self, value: Any):
        with self._lock:
            self._set.discard(value)


class ScrubData:
    _pattern = re.compile(r'([\/\\]+(?:home|users)[\/\\]+)([^\"\'\/\\]+)', re.I | re.M)

    def __init__(self, value: str):
        self.value = value

    def __repr__(self) -> str:
        return self.value

    @classmethod
    def object(cls, object: object) -> object:
        return cls(cls.string(pformat(object)))

    @classmethod
    def string(cls, string: str) -> str:
        return cls._pattern.sub(cls._repl, string)

    @classmethod
    def _repl(cls, match: re.Match) -> str:
        return f'{match.group(1)}USER'


class SentryHub:

    def __init__(self):
        self._hub = sentry_sdk.Hub(client_or_hub=sentry_sdk.Client(
            dsn='https://3793646e5d254c8e9ad9e423ec3186c4@o1108424.ingest.sentry.io/6182044',
            default_integrations=False,
            auto_enabling_integrations=False,
            in_app_include=[utils.getters.get_package()],
        ))

        self._hub.client.options['server_name'] = None
        self._hub.client.options['release'] = '.'.join(str(n) for n in utils.getters.get_version())
        self._hub.scope.set_tag('platform.system', platform.system())
        self._hub.scope.set_tag('platform.release', platform.release())
        self._hub.scope.set_tag('platform.version', platform.version())
        self._hub.scope.set_tag('platform.machine', platform.machine())
        self._hub.scope.set_tag('python.implementation', platform.python_implementation())
        self._hub.scope.set_tag('python.version', platform.python_version())
        self._hub.scope.set_tag('blender.cycle', bpy.app.version_cycle)
        self._hub.scope.set_tag('blender.version', '.'.join(str(n) for n in bpy.app.version))

        self._exceptions = TimerSet(60.0)
        atexit.register(self._hub.flush, timeout=1.0)

    def _should_capture(self, value: BaseException, traceback: TracebackType, rate: float) -> bool:
        if str(value) in self._exceptions:
            return False

        if random() > rate:
            return False

        prefs = utils.getters.get_preferences()
        allow_networking = utils.getters.get_allow_networking()
        if not prefs.tracking_errors and allow_networking:
            return False

        while traceback is not None:
            path = Path(traceback.tb_frame.f_code.co_filename).as_posix()
            if f'/addons/{utils.getters.get_package()}/' in path:
                return True
            traceback = traceback.tb_next
        return False

    def capture(self, type: Type[BaseException], value: BaseException, traceback: TracebackType, rate: float):
        with capture_internal_exceptions():
            if self._should_capture(value, traceback, rate):
                exc_info = (type, value, traceback)
                client_options = self._hub.client.options
                mechanism = {'type': 'excepthook', 'handled': False}
                event, hint = event_from_exception(exc_info, client_options, mechanism)

                for exception in event['exception']['values']:
                    exception['value'] = ScrubData.string(exception['value'])
                    for frame in exception['stacktrace']['frames']:
                        frame['abs_path'] = ScrubData.string(frame['abs_path'])
                        for k, v in frame['vars'].items():
                            frame['vars'][k] = ScrubData.object(v)

                self._hub.capture_event(event, hint)
                self._exceptions.add(str(value))


_hub: SentryHub = None


def capture(type: Type[BaseException], value: BaseException, traceback: TracebackType, rate: float = 0.1):
    global _hub
    _hub.capture(type, value, traceback, rate)


class SentryHook:

    def __init__(self):
        self._func_old = sys.excepthook
        self._func_cur = self._capture
        sys.excepthook = lambda *args: self._func_cur(*args)

    def _capture(self, type: Type[BaseException], value: BaseException, traceback: TracebackType):
        capture(type, value, traceback)
        return self._func_old(type, value, traceback)

    def disable(self):
        self._func_cur = self._func_old


_hook: SentryHook = None


def register():
    global _hub
    global _hook

    if _hook is not None:
        _hook.disable()

    _hub = SentryHub()
    _hook = SentryHook()


def unregister():
    global _hub
    global _hook

    if _hook is not None:
        _hook.disable()

    _hub = None
    _hook = None

# coding: utf-8
from __future__ import print_function
import io
import urllib3
import certifi
import gzip
import time
from datetime import datetime, timedelta
from collections import defaultdict
from ..sentry_sdk.utils import Dsn, logger, capture_internal_exceptions, json_dumps
from ..sentry_sdk.worker import BackgroundWorker
from ..sentry_sdk.envelope import Envelope, Item, PayloadRef
from ..sentry_sdk._types import MYPY
if MYPY:
    from typing import Any
    from typing import Callable
    from typing import Dict
    from typing import Iterable
    from typing import Optional
    from typing import Tuple
    from typing import Type
    from typing import Union
    from typing import DefaultDict
    from urllib3.poolmanager import PoolManager
    from urllib3.poolmanager import ProxyManager
    from ..sentry_sdk._types import Event, EndpointType
    DataCategory = Optional[str]
try:
    from urllib.request import getproxies
except ImportError:
    from urllib import getproxies

class Transport(object):
    """Baseclass for all transports.

    A transport is used to send an event to sentry.
    """
    parsed_dsn = None # type: Optional[Dsn]

    def __init__(self, options=None): # type: (...) -> None
        self.options = options
        if options and options['dsn'] is not None and options['dsn']:
            self.parsed_dsn = Dsn(options['dsn'])
        else:
            self.parsed_dsn = None

    def capture_event(self, event): # type: (...) -> None
        """
        This gets invoked with the event dictionary when an event should
        be sent to sentry.
        """
        raise NotImplementedError()

    def capture_envelope(self, envelope): # type: (...) -> None
        """
        Send an envelope to Sentry.

        Envelopes are a data container format that can hold any type of data
        submitted to Sentry. We use it for transactions and sessions, but
        regular "error" events should go through `capture_event` for backwards
        compat.
        """
        raise NotImplementedError()

    def flush(self, timeout, callback=None): # type: (...) -> None
        """Wait `timeout` seconds for the current events to be sent out."""
        pass

    def kill(self): # type: () -> None
        """Forcefully kills the transport."""
        pass

    def record_lost_event(self, reason, data_category=None, item=None): # type: (...) -> None
        """This increments a counter for event loss by reason and
        data category.
        """
        return None

    def __del__(self): # type: () -> None
        try:
            self.kill()
        except Exception:
            pass

def _parse_rate_limits(header, now=None): # type: (Any, Optional[datetime]) -> Iterable[Tuple[DataCategory, datetime]]
    if now is None:
        now = datetime.utcnow()
    for limit in header.split(','):
        try:
            (retry_after, categories, _) = limit.strip().split(':', 2)
            retry_after = now + timedelta(seconds=int(retry_after))
            for category in categories and categories.split(';') or (None,):
                yield (category, retry_after)
        except (LookupError, ValueError):
            continue

class HttpTransport(Transport):
    """The default HTTP transport."""

    def __init__(self, options): # type: (...) -> None
        from ..sentry_sdk.consts import VERSION
        Transport.__init__(self, options)
        assert self.parsed_dsn is not None
        self.options = options # type: Dict[str, Any]
        self._worker = BackgroundWorker(queue_size=options['transport_queue_size'])
        self._auth = self.parsed_dsn.to_auth('sentry.python/%s' % VERSION)
        self._disabled_until = {} # type: Dict[DataCategory, datetime]
        self._retry = urllib3.util.Retry()
        self._discarded_events = defaultdict(int) # type: DefaultDict[Tuple[str, str], int]
        self._last_client_report_sent = time.time()
        self._pool = self._make_pool(self.parsed_dsn, http_proxy=options['http_proxy'], https_proxy=options['https_proxy'], ca_certs=options['ca_certs'])
        from ..sentry_sdk import Hub
        self.hub_cls = Hub

    def record_lost_event(self, reason, data_category=None, item=None): # type: (...) -> None
        if not self.options['send_client_reports']:
            return
        quantity = 1
        if item is not None:
            data_category = item.data_category
            if data_category == 'attachment':
                quantity = len(item.get_bytes()) or 1
        elif data_category is None:
            raise TypeError('data category not provided')
        self._discarded_events[data_category, reason] += quantity

    def _update_rate_limits(self, response): # type: (urllib3.HTTPResponse) -> None
        header = response.headers.get('x-sentry-rate-limits')
        if header:
            logger.warning('Rate-limited via x-sentry-rate-limits')
            self._disabled_until.update(_parse_rate_limits(header))
        elif response.status == 429:
            logger.warning('Rate-limited via 429')
            self._disabled_until[None] = datetime.utcnow() + timedelta(seconds=self._retry.get_retry_after(response) or 60)

    def _send_request(self, body, headers, endpoint_type='store', envelope=None): # type: (...) -> None

        def record_loss(reason): # type: (str) -> None
            if envelope is None:
                self.record_lost_event(reason, data_category='error')
            else:
                for item in envelope.items:
                    self.record_lost_event(reason, item=item)
        headers.update({'User-Agent': str(self._auth.client), 'X-Sentry-Auth': str(self._auth.to_header())})
        try:
            response = self._pool.request('POST', str(self._auth.get_api_url(endpoint_type)), body=body, headers=headers)
        except Exception:
            self.on_dropped_event('network')
            record_loss('network_error')
            raise
        try:
            self._update_rate_limits(response)
            if response.status == 429:
                self.on_dropped_event('status_429')
                pass
            elif response.status >= 300 or response.status < 200:
                logger.error('Unexpected status code: %s (body: %s)', response.status, response.data)
                self.on_dropped_event('status_{}'.format(response.status))
                record_loss('network_error')
        finally:
            response.close()

    def on_dropped_event(self, reason): # type: (str) -> None
        return None

    def _fetch_pending_client_report(self, force=False, interval=60): # type: (bool, int) -> Optional[Item]
        if not self.options['send_client_reports']:
            return None
        if not (force or self._last_client_report_sent < time.time() - interval):
            return None
        discarded_events = self._discarded_events
        self._discarded_events = defaultdict(int)
        self._last_client_report_sent = time.time()
        if not discarded_events:
            return None
        return Item(PayloadRef(json={'timestamp': time.time(), 'discarded_events': [{'reason': reason, 'category': category, 'quantity': quantity} for ((category, reason), quantity) in discarded_events.items()]}), type='client_report')

    def _flush_client_reports(self, force=False): # type: (bool) -> None
        client_report = self._fetch_pending_client_report(force=force, interval=60)
        if client_report is not None:
            self.capture_envelope(Envelope(items=[client_report]))

    def _check_disabled(self, category): # type: (str) -> bool

        def _disabled(bucket): # type: (Any) -> bool
            ts = self._disabled_until.get(bucket)
            return ts is not None and ts > datetime.utcnow()
        return _disabled(category) or _disabled(None)

    def _send_event(self, event): # type: (...) -> None
        if self._check_disabled('error'):
            self.on_dropped_event('self_rate_limits')
            self.record_lost_event('ratelimit_backoff', data_category='error')
            return None
        body = io.BytesIO()
        with gzip.GzipFile(fileobj=body, mode='w') as f:
            f.write(json_dumps(event))
        assert self.parsed_dsn is not None
        logger.debug('Sending event, type:%s level:%s event_id:%s project:%s host:%s' % (event.get('type') or 'null', event.get('level') or 'null', event.get('event_id') or 'null', self.parsed_dsn.project_id, self.parsed_dsn.host))
        self._send_request(body.getvalue(), headers={'Content-Type': 'application/json', 'Content-Encoding': 'gzip'})
        return None

    def _send_envelope(self, envelope): # type: (...) -> None
        new_items = []
        for item in envelope.items:
            if self._check_disabled(item.data_category):
                if item.data_category in ('transaction', 'error', 'default'):
                    self.on_dropped_event('self_rate_limits')
                self.record_lost_event('ratelimit_backoff', item=item)
            else:
                new_items.append(item)
        envelope = Envelope(headers=envelope.headers, items=new_items)
        if not envelope.items:
            return None
        client_report_item = self._fetch_pending_client_report(interval=30)
        if client_report_item is not None:
            envelope.items.append(client_report_item)
        body = io.BytesIO()
        with gzip.GzipFile(fileobj=body, mode='w') as f:
            envelope.serialize_into(f)
        assert self.parsed_dsn is not None
        logger.debug('Sending envelope [%s] project:%s host:%s', envelope.description, self.parsed_dsn.project_id, self.parsed_dsn.host)
        self._send_request(body.getvalue(), headers={'Content-Type': 'application/x-sentry-envelope', 'Content-Encoding': 'gzip'}, endpoint_type='envelope', envelope=envelope)
        return None

    def _get_pool_options(self, ca_certs): # type: (Optional[Any]) -> Dict[str, Any]
        return {'num_pools': 2, 'cert_reqs': 'CERT_REQUIRED', 'ca_certs': ca_certs or certifi.where()}

    def _in_no_proxy(self, parsed_dsn): # type: (Dsn) -> bool
        no_proxy = getproxies().get('no')
        if not no_proxy:
            return False
        for host in no_proxy.split(','):
            host = host.strip()
            if parsed_dsn.host.endswith(host) or parsed_dsn.netloc.endswith(host):
                return True
        return False

    def _make_pool(self, parsed_dsn, http_proxy, https_proxy, ca_certs): # type: (...) -> Union[PoolManager, ProxyManager]
        proxy = None
        no_proxy = self._in_no_proxy(parsed_dsn)
        if parsed_dsn.scheme == 'https' and https_proxy != '':
            proxy = https_proxy or (not no_proxy and getproxies().get('https'))
        if not proxy and http_proxy != '':
            proxy = http_proxy or (not no_proxy and getproxies().get('http'))
        opts = self._get_pool_options(ca_certs)
        if proxy:
            return urllib3.ProxyManager(proxy, **opts)
        else:
            return urllib3.PoolManager(**opts)

    def capture_event(self, event): # type: (...) -> None
        hub = self.hub_cls.current

        def send_event_wrapper(): # type: () -> None
            with hub:
                with capture_internal_exceptions():
                    self._send_event(event)
                    self._flush_client_reports()
        if not self._worker.submit(send_event_wrapper):
            self.on_dropped_event('full_queue')
            self.record_lost_event('queue_overflow', data_category='error')

    def capture_envelope(self, envelope): # type: (...) -> None
        hub = self.hub_cls.current

        def send_envelope_wrapper(): # type: () -> None
            with hub:
                with capture_internal_exceptions():
                    self._send_envelope(envelope)
                    self._flush_client_reports()
        if not self._worker.submit(send_envelope_wrapper):
            self.on_dropped_event('full_queue')
            for item in envelope.items:
                self.record_lost_event('queue_overflow', item=item)

    def flush(self, timeout, callback=None): # type: (...) -> None
        logger.debug('Flushing HTTP transport')
        if timeout > 0:
            self._worker.submit(lambda : self._flush_client_reports(force=True))
            self._worker.flush(timeout, callback)

    def kill(self): # type: () -> None
        logger.debug('Killing HTTP transport')
        self._worker.kill()

class _FunctionTransport(Transport):

    def __init__(self, func): # type: (...) -> None
        Transport.__init__(self)
        self._func = func

    def capture_event(self, event): # type: (...) -> None
        self._func(event)
        return None

def make_transport(options): # type: (Dict[str, Any]) -> Optional[Transport]
    ref_transport = options['transport']
    if ref_transport is None:
        transport_cls = HttpTransport # type: Type[Transport]
    elif isinstance(ref_transport, Transport):
        return ref_transport
    elif isinstance(ref_transport, type) and issubclass(ref_transport, Transport):
        transport_cls = ref_transport
    elif callable(ref_transport):
        return _FunctionTransport(ref_transport)
    if options['dsn']:
        return transport_cls(options)
    return None

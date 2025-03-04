# coding: utf-8
import uuid
import random
import time
from datetime import datetime, timedelta
__import__('.'.join(__package__.split('.')[:-1] + ['sentry_sdk']), globals(), locals(), [], 0)
from .. import sentry_sdk
from ..sentry_sdk.utils import logger
from ..sentry_sdk._types import MYPY
if MYPY:
    import typing
    from typing import Optional
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Tuple
    from typing import Iterator
    from ..sentry_sdk._types import SamplingContext

class _SpanRecorder(object):
    """Limits the number of spans recorded in a transaction."""
    __slots__ = ('maxlen', 'spans')

    def __init__(self, maxlen): # type: (int) -> None
        self.maxlen = maxlen - 1
        self.spans = [] # type: List[Span]

    def add(self, span): # type: (Span) -> None
        if len(self.spans) > self.maxlen:
            span._span_recorder = None
        else:
            self.spans.append(span)

class Span(object):
    __slots__ = ('trace_id', 'span_id', 'parent_span_id', 'same_process_as_parent', 'sampled', 'op', 'description', 'start_timestamp', '_start_timestamp_monotonic', 'status', 'timestamp', '_tags', '_data', '_span_recorder', 'hub', '_context_manager_state', '_containing_transaction')

    def __new__(cls, **kwargs): # type: (**Any) -> Any
        """
        Backwards-compatible implementation of Span and Transaction
        creation.
        """
        if 'transaction' in kwargs:
            return object.__new__(Transaction)
        return object.__new__(cls)

    def __init__(self, trace_id=None, span_id=None, parent_span_id=None, same_process_as_parent=True, sampled=None, op=None, description=None, hub=None, status=None, transaction=None, containing_transaction=None): # type: (...) -> None
        self.trace_id = trace_id or uuid.uuid4().hex
        self.span_id = span_id or uuid.uuid4().hex[16:]
        self.parent_span_id = parent_span_id
        self.same_process_as_parent = same_process_as_parent
        self.sampled = sampled
        self.op = op
        self.description = description
        self.status = status
        self.hub = hub
        self._tags = {} # type: Dict[str, str]
        self._data = {} # type: Dict[str, Any]
        self._containing_transaction = containing_transaction
        self.start_timestamp = datetime.utcnow()
        try:
            self._start_timestamp_monotonic = time.perf_counter()
        except AttributeError:
            pass
        self.timestamp = None # type: Optional[datetime]
        self._span_recorder = None # type: Optional[_SpanRecorder]

    def init_span_recorder(self, maxlen): # type: (int) -> None
        if self._span_recorder is None:
            self._span_recorder = _SpanRecorder(maxlen)

    def __repr__(self): # type: () -> str
        return '<%s(op=%r, description:%r, trace_id=%r, span_id=%r, parent_span_id=%r, sampled=%r)>' % (self.__class__.__name__, self.op, self.description, self.trace_id, self.span_id, self.parent_span_id, self.sampled)

    def __enter__(self): # type: () -> Span
        hub = self.hub or sentry_sdk.Hub.current
        (_, scope) = hub._stack[-1]
        old_span = scope.span
        scope.span = self
        self._context_manager_state = (hub, scope, old_span)
        return self

    def __exit__(self, ty, value, tb): # type: (Optional[Any], Optional[Any], Optional[Any]) -> None
        if value is not None:
            self.set_status('internal_error')
        (hub, scope, old_span) = self._context_manager_state
        del self._context_manager_state
        self.finish(hub)
        scope.span = old_span

    @property
    def containing_transaction(self): # type: () -> Optional[Transaction]
        return self._containing_transaction

    def start_child(self, **kwargs): # type: (**Any) -> Span
        """
        Start a sub-span from the current span or transaction.

        Takes the same arguments as the initializer of :py:class:`Span`. The
        trace id, sampling decision, transaction pointer, and span recorder are
        inherited from the current span/transaction.
        """
        kwargs.setdefault('sampled', self.sampled)
        child = Span(trace_id=self.trace_id, parent_span_id=self.span_id, containing_transaction=self.containing_transaction, **kwargs)
        span_recorder = self.containing_transaction and self.containing_transaction._span_recorder
        if span_recorder:
            span_recorder.add(child)
        return child

    def new_span(self, **kwargs): # type: (**Any) -> Span
        """Deprecated: use start_child instead."""
        logger.warning('Deprecated: use Span.start_child instead of Span.new_span.')
        return self.start_child(**kwargs)

    @classmethod
    def continue_from_environ(cls, environ, **kwargs): # type: (...) -> Transaction
        """
        Create a Transaction with the given params, then add in data pulled from
        the 'sentry-trace' and 'tracestate' headers from the environ (if any)
        before returning the Transaction.

        This is different from `continue_from_headers` in that it assumes header
        names in the form "HTTP_HEADER_NAME" - such as you would get from a wsgi
        environ - rather than the form "header-name".
        """
        if cls is Span:
            logger.warning('Deprecated: use Transaction.continue_from_environ instead of Span.continue_from_environ.')
        return Transaction.continue_from_headers(EnvironHeaders(environ), **kwargs)

    @classmethod
    def continue_from_headers(cls, headers, **kwargs): # type: (...) -> Transaction
        """
        Create a transaction with the given params (including any data pulled from
        the 'sentry-trace' and 'tracestate' headers).
        """
        if cls is Span:
            logger.warning('Deprecated: use Transaction.continue_from_headers instead of Span.continue_from_headers.')
        kwargs.update(extract_sentrytrace_data(headers.get('sentry-trace')))
        kwargs.update(extract_tracestate_data(headers.get('tracestate')))
        transaction = Transaction(**kwargs)
        transaction.same_process_as_parent = False
        return transaction

    def iter_headers(self): # type: () -> Iterator[Tuple[str, str]]
        """
        Creates a generator which returns the span's `sentry-trace` and
        `tracestate` headers.

        If the span's containing transaction doesn't yet have a
        `sentry_tracestate` value, this will cause one to be generated and
        stored.
        """
        yield ('sentry-trace', self.to_traceparent())
        tracestate = self.to_tracestate() if has_tracestate_enabled(self) else None
        if tracestate:
            yield ('tracestate', tracestate)

    @classmethod
    def from_traceparent(cls, traceparent, **kwargs): # type: (...) -> Optional[Transaction]
        """
        DEPRECATED: Use Transaction.continue_from_headers(headers, **kwargs)

        Create a Transaction with the given params, then add in data pulled from
        the given 'sentry-trace' header value before returning the Transaction.

        """
        logger.warning('Deprecated: Use Transaction.continue_from_headers(headers, **kwargs) instead of from_traceparent(traceparent, **kwargs)')
        if not traceparent:
            return None
        return cls.continue_from_headers({'sentry-trace': traceparent}, **kwargs)

    def to_traceparent(self): # type: () -> str
        sampled = ''
        if self.sampled is True:
            sampled = '1'
        if self.sampled is False:
            sampled = '0'
        return '%s-%s-%s' % (self.trace_id, self.span_id, sampled)

    def to_tracestate(self): # type: () -> Optional[str]
        """
        Computes the `tracestate` header value using data from the containing
        transaction.

        If the containing transaction doesn't yet have a `sentry_tracestate`
        value, this will cause one to be generated and stored.

        If there is no containing transaction, a value will be generated but not
        stored.

        Returns None if there's no client and/or no DSN.
        """
        sentry_tracestate = self.get_or_set_sentry_tracestate()
        third_party_tracestate = self.containing_transaction._third_party_tracestate if self.containing_transaction else None
        if not sentry_tracestate:
            return None
        header_value = sentry_tracestate
        if third_party_tracestate:
            header_value = header_value + ',' + third_party_tracestate
        return header_value

    def get_or_set_sentry_tracestate(self): # type: (Span) -> Optional[str]
        """
        Read sentry tracestate off of the span's containing transaction.

        If the transaction doesn't yet have a `_sentry_tracestate` value,
        compute one and store it.
        """
        transaction = self.containing_transaction
        if transaction:
            if not transaction._sentry_tracestate:
                transaction._sentry_tracestate = compute_tracestate_entry(self)
            return transaction._sentry_tracestate
        return compute_tracestate_entry(self)

    def set_tag(self, key, value): # type: (str, Any) -> None
        self._tags[key] = value

    def set_data(self, key, value): # type: (str, Any) -> None
        self._data[key] = value

    def set_status(self, value): # type: (str) -> None
        self.status = value

    def set_http_status(self, http_status): # type: (int) -> None
        self.set_tag('http.status_code', str(http_status))
        if http_status < 400:
            self.set_status('ok')
        elif 400 <= http_status < 500:
            if http_status == 403:
                self.set_status('permission_denied')
            elif http_status == 404:
                self.set_status('not_found')
            elif http_status == 429:
                self.set_status('resource_exhausted')
            elif http_status == 413:
                self.set_status('failed_precondition')
            elif http_status == 401:
                self.set_status('unauthenticated')
            elif http_status == 409:
                self.set_status('already_exists')
            else:
                self.set_status('invalid_argument')
        elif 500 <= http_status < 600:
            if http_status == 504:
                self.set_status('deadline_exceeded')
            elif http_status == 501:
                self.set_status('unimplemented')
            elif http_status == 503:
                self.set_status('unavailable')
            else:
                self.set_status('internal_error')
        else:
            self.set_status('unknown_error')

    def is_success(self): # type: () -> bool
        return self.status == 'ok'

    def finish(self, hub=None): # type: (Optional[sentry_sdk.Hub]) -> Optional[str]
        if self.timestamp is not None:
            return None
        hub = hub or self.hub or sentry_sdk.Hub.current
        try:
            duration_seconds = time.perf_counter() - self._start_timestamp_monotonic
            self.timestamp = self.start_timestamp + timedelta(seconds=duration_seconds)
        except AttributeError:
            self.timestamp = datetime.utcnow()
        maybe_create_breadcrumbs_from_span(hub, self)
        return None

    def to_json(self): # type: () -> Dict[str, Any]
        rv = {'trace_id': self.trace_id, 'span_id': self.span_id, 'parent_span_id': self.parent_span_id, 'same_process_as_parent': self.same_process_as_parent, 'op': self.op, 'description': self.description, 'start_timestamp': self.start_timestamp, 'timestamp': self.timestamp} # type: Dict[str, Any]
        if self.status:
            self._tags['status'] = self.status
        tags = self._tags
        if tags:
            rv['tags'] = tags
        data = self._data
        if data:
            rv['data'] = data
        return rv

    def get_trace_context(self): # type: () -> Any
        rv = {'trace_id': self.trace_id, 'span_id': self.span_id, 'parent_span_id': self.parent_span_id, 'op': self.op, 'description': self.description}
        if self.status:
            rv['status'] = self.status
        sentry_tracestate = self.get_or_set_sentry_tracestate()
        if sentry_tracestate:
            rv['tracestate'] = sentry_tracestate
        return rv

class Transaction(Span):
    __slots__ = ('name', 'parent_sampled', '_sentry_tracestate', '_third_party_tracestate')

    def __init__(self, name='', parent_sampled=None, sentry_tracestate=None, third_party_tracestate=None, **kwargs): # type: (...) -> None
        if not name and 'transaction' in kwargs:
            logger.warning('Deprecated: use Transaction(name=...) to create transactions instead of Span(transaction=...).')
            name = kwargs.pop('transaction')
        Span.__init__(self, **kwargs)
        self.name = name
        self.parent_sampled = parent_sampled
        self._sentry_tracestate = sentry_tracestate
        self._third_party_tracestate = third_party_tracestate

    def __repr__(self): # type: () -> str
        return '<%s(name=%r, op=%r, trace_id=%r, span_id=%r, parent_span_id=%r, sampled=%r)>' % (self.__class__.__name__, self.name, self.op, self.trace_id, self.span_id, self.parent_span_id, self.sampled)

    @property
    def containing_transaction(self): # type: () -> Transaction
        return self

    def finish(self, hub=None): # type: (Optional[sentry_sdk.Hub]) -> Optional[str]
        if self.timestamp is not None:
            return None
        hub = hub or self.hub or sentry_sdk.Hub.current
        client = hub.client
        if client is None:
            return None
        if self._span_recorder is None:
            logger.debug('Discarding transaction because sampled = False')
            if client.transport and has_tracing_enabled(client.options):
                client.transport.record_lost_event('sample_rate', data_category='transaction')
            return None
        if not self.name:
            logger.warning('Transaction has no name, falling back to `<unlabeled transaction>`.')
            self.name = '<unlabeled transaction>'
        Span.finish(self, hub)
        if not self.sampled:
            if self.sampled is None:
                logger.warning('Discarding transaction without sampling decision.')
            return None
        finished_spans = [span.to_json() for span in self._span_recorder.spans if span.timestamp is not None]
        self._span_recorder = None
        return hub.capture_event({'type': 'transaction', 'transaction': self.name, 'contexts': {'trace': self.get_trace_context()}, 'tags': self._tags, 'timestamp': self.timestamp, 'start_timestamp': self.start_timestamp, 'spans': finished_spans})

    def to_json(self): # type: () -> Dict[str, Any]
        rv = super(Transaction, self).to_json()
        rv['name'] = self.name
        rv['sampled'] = self.sampled
        return rv

    def _set_initial_sampling_decision(self, sampling_context): # type: (SamplingContext) -> None
        """
        Sets the transaction's sampling decision, according to the following
        precedence rules:

        1. If a sampling decision is passed to `start_transaction`
        (`start_transaction(name: "my transaction", sampled: True)`), that
        decision will be used, regardless of anything else

        2. If `traces_sampler` is defined, its decision will be used. It can
        choose to keep or ignore any parent sampling decision, or use the
        sampling context data to make its own decision or to choose a sample
        rate for the transaction.

        3. If `traces_sampler` is not defined, but there's a parent sampling
        decision, the parent sampling decision will be used.

        4. If `traces_sampler` is not defined and there's no parent sampling
        decision, `traces_sample_rate` will be used.
        """
        hub = self.hub or sentry_sdk.Hub.current
        client = hub.client
        options = client and client.options or {}
        transaction_description = '{op}transaction <{name}>'.format(op='<' + self.op + '> ' if self.op else '', name=self.name)
        if not client or not has_tracing_enabled(options):
            self.sampled = False
            return
        if self.sampled is not None:
            return
        sample_rate = options['traces_sampler'](sampling_context) if callable(options.get('traces_sampler')) else sampling_context['parent_sampled'] if sampling_context['parent_sampled'] is not None else options['traces_sample_rate']
        if not is_valid_sample_rate(sample_rate):
            logger.warning('[Tracing] Discarding {transaction_description} because of invalid sample rate.'.format(transaction_description=transaction_description))
            self.sampled = False
            return
        if not sample_rate:
            logger.debug('[Tracing] Discarding {transaction_description} because {reason}'.format(transaction_description=transaction_description, reason='traces_sampler returned 0 or False' if callable(options.get('traces_sampler')) else 'traces_sample_rate is set to 0'))
            self.sampled = False
            return
        self.sampled = random.random() < float(sample_rate)
        if self.sampled:
            logger.debug('[Tracing] Starting {transaction_description}'.format(transaction_description=transaction_description))
        else:
            logger.debug("[Tracing] Discarding {transaction_description} because it's not included in the random sample (sampling rate = {sample_rate})".format(transaction_description=transaction_description, sample_rate=float(sample_rate)))
from ..sentry_sdk.tracing_utils import EnvironHeaders, compute_tracestate_entry, extract_sentrytrace_data, extract_tracestate_data, has_tracestate_enabled, has_tracing_enabled, is_valid_sample_rate, maybe_create_breadcrumbs_from_span

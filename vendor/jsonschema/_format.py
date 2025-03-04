# coding: utf-8
from __future__ import annotations
from contextlib import suppress
from uuid import UUID
import datetime
import ipaddress
import re
import typing
from ..jsonschema.exceptions import FormatError

class FormatChecker(object):
    """
    A ``format`` property checker.

    JSON Schema does not mandate that the ``format`` property actually do any
    validation. If validation is desired however, instances of this class can
    be hooked into validators to enable format validation.

    `FormatChecker` objects always return ``True`` when asked about
    formats that they do not know how to validate.

    To check a custom format using a function that takes an instance and
    returns a ``bool``, use the `FormatChecker.checks` or
    `FormatChecker.cls_checks` decorators.

    Arguments:

        formats (~collections.abc.Iterable):

            The known formats to validate. This argument can be used to
            limit which formats will be used during validation.
    """
    checkers: dict[str, tuple[typing.Callable[[typing.Any], bool], Exception | tuple[Exception, ...]]] = {}

    def __init__(self, formats=None):
        if formats is None:
            self.checkers = self.checkers.copy()
        else:
            self.checkers = dict(((k, self.checkers[k]) for k in formats))

    def __repr__(self):
        return '<FormatChecker checkers={}>'.format(sorted(self.checkers))

    def checks(self, format, raises=()):
        """
        Register a decorated function as validating a new format.

        Arguments:

            format (str):

                The format that the decorated function will check.

            raises (Exception):

                The exception(s) raised by the decorated function when an
                invalid instance is found.

                The exception object will be accessible as the
                `jsonschema.exceptions.ValidationError.cause` attribute of the
                resulting validation error.
        """

        def _checks(func):
            self.checkers[format] = (func, raises)
            return func
        return _checks
    cls_checks = classmethod(checks)

    def check(self, instance, format):
        """
        Check whether the instance conforms to the given format.

        Arguments:

            instance (*any primitive type*, i.e. str, number, bool):

                The instance to check

            format (str):

                The format that instance should conform to


        Raises:

            FormatError: if the instance does not conform to ``format``
        """
        if format not in self.checkers:
            return
        (func, raises) = self.checkers[format]
        (result, cause) = (None, None)
        try:
            result = func(instance)
        except raises as e:
            cause = e
        if not result:
            raise FormatError(f'{instance!r} is not a {format!r}', cause=cause)

    def conforms(self, instance, format):
        """
        Check whether the instance conforms to the given format.

        Arguments:

            instance (*any primitive type*, i.e. str, number, bool):

                The instance to check

            format (str):

                The format that instance should conform to

        Returns:

            bool: whether it conformed
        """
        try:
            self.check(instance, format)
        except FormatError:
            return False
        else:
            return True
draft3_format_checker = FormatChecker()
draft4_format_checker = FormatChecker()
draft6_format_checker = FormatChecker()
draft7_format_checker = FormatChecker()
draft201909_format_checker = FormatChecker()
draft202012_format_checker = FormatChecker()
_draft_checkers = dict(draft3=draft3_format_checker, draft4=draft4_format_checker, draft6=draft6_format_checker, draft7=draft7_format_checker, draft201909=draft201909_format_checker, draft202012=draft202012_format_checker)

def _checks_drafts(name=None, draft3=None, draft4=None, draft6=None, draft7=None, draft201909=None, draft202012=None, raises=()):
    draft3 = draft3 or name
    draft4 = draft4 or name
    draft6 = draft6 or name
    draft7 = draft7 or name
    draft201909 = draft201909 or name
    draft202012 = draft202012 or name

    def wrap(func):
        if draft3:
            func = _draft_checkers['draft3'].checks(draft3, raises)(func)
        if draft4:
            func = _draft_checkers['draft4'].checks(draft4, raises)(func)
        if draft6:
            func = _draft_checkers['draft6'].checks(draft6, raises)(func)
        if draft7:
            func = _draft_checkers['draft7'].checks(draft7, raises)(func)
        if draft201909:
            func = _draft_checkers['draft201909'].checks(draft201909, raises)(func)
        if draft202012:
            func = _draft_checkers['draft202012'].checks(draft202012, raises)(func)
        FormatChecker.cls_checks(draft202012 or draft201909 or draft7 or draft6 or draft4 or draft3, raises)(func)
        return func
    return wrap

@_checks_drafts(name='idn-email')
@_checks_drafts(name='email')
def is_email(instance):
    if not isinstance(instance, str):
        return True
    return '@' in instance

@_checks_drafts(draft3='ip-address', draft4='ipv4', draft6='ipv4', draft7='ipv4', draft201909='ipv4', draft202012='ipv4', raises=ipaddress.AddressValueError)
def is_ipv4(instance):
    if not isinstance(instance, str):
        return True
    return ipaddress.IPv4Address(instance)

@_checks_drafts(name='ipv6', raises=ipaddress.AddressValueError)
def is_ipv6(instance):
    if not isinstance(instance, str):
        return True
    address = ipaddress.IPv6Address(instance)
    return not getattr(address, 'scope_id', '')
with suppress(ImportError):
    from fqdn import FQDN

    @_checks_drafts(draft3='host-name', draft4='hostname', draft6='hostname', draft7='hostname', draft201909='hostname', draft202012='hostname')
    def is_host_name(instance):
        if not isinstance(instance, str):
            return True
        return FQDN(instance).is_valid
with suppress(ImportError):
    import idna

    @_checks_drafts(draft7='idn-hostname', draft201909='idn-hostname', draft202012='idn-hostname', raises=(idna.IDNAError, UnicodeError))
    def is_idn_host_name(instance):
        if not isinstance(instance, str):
            return True
        idna.encode(instance)
        return True
try:
    import rfc3987
except ImportError:
    with suppress(ImportError):
        from rfc3986_validator import validate_rfc3986

        @_checks_drafts(name='uri')
        def is_uri(instance):
            if not isinstance(instance, str):
                return True
            return validate_rfc3986(instance, rule='URI')

        @_checks_drafts(draft6='uri-reference', draft7='uri-reference', draft201909='uri-reference', draft202012='uri-reference', raises=ValueError)
        def is_uri_reference(instance):
            if not isinstance(instance, str):
                return True
            return validate_rfc3986(instance, rule='URI_reference')
else:

    @_checks_drafts(draft7='iri', draft201909='iri', draft202012='iri', raises=ValueError)
    def is_iri(instance):
        if not isinstance(instance, str):
            return True
        return rfc3987.parse(instance, rule='IRI')

    @_checks_drafts(draft7='iri-reference', draft201909='iri-reference', draft202012='iri-reference', raises=ValueError)
    def is_iri_reference(instance):
        if not isinstance(instance, str):
            return True
        return rfc3987.parse(instance, rule='IRI_reference')

    @_checks_drafts(name='uri', raises=ValueError)
    def is_uri(instance):
        if not isinstance(instance, str):
            return True
        return rfc3987.parse(instance, rule='URI')

    @_checks_drafts(draft6='uri-reference', draft7='uri-reference', draft201909='uri-reference', draft202012='uri-reference', raises=ValueError)
    def is_uri_reference(instance):
        if not isinstance(instance, str):
            return True
        return rfc3987.parse(instance, rule='URI_reference')
with suppress(ImportError):
    from rfc3339_validator import validate_rfc3339

    @_checks_drafts(name='date-time')
    def is_datetime(instance):
        if not isinstance(instance, str):
            return True
        return validate_rfc3339(instance.upper())

    @_checks_drafts(draft7='time', draft201909='time', draft202012='time')
    def is_time(instance):
        if not isinstance(instance, str):
            return True
        return is_datetime('1970-01-01T' + instance)

@_checks_drafts(name='regex', raises=re.error)
def is_regex(instance):
    if not isinstance(instance, str):
        return True
    return re.compile(instance)

@_checks_drafts(draft3='date', draft7='date', draft201909='date', draft202012='date', raises=ValueError)
def is_date(instance):
    if not isinstance(instance, str):
        return True
    return instance.isascii() and datetime.date.fromisoformat(instance)

@_checks_drafts(draft3='time', raises=ValueError)
def is_draft3_time(instance):
    if not isinstance(instance, str):
        return True
    return datetime.datetime.strptime(instance, '%H:%M:%S')
with suppress(ImportError):
    from webcolors import CSS21_NAMES_TO_HEX
    import webcolors

    def is_css_color_code(instance):
        return webcolors.normalize_hex(instance)

    @_checks_drafts(draft3='color', raises=(ValueError, TypeError))
    def is_css21_color(instance):
        if not isinstance(instance, str) or instance.lower() in CSS21_NAMES_TO_HEX:
            return True
        return is_css_color_code(instance)
with suppress(ImportError):
    import jsonpointer

    @_checks_drafts(draft6='json-pointer', draft7='json-pointer', draft201909='json-pointer', draft202012='json-pointer', raises=jsonpointer.JsonPointerException)
    def is_json_pointer(instance):
        if not isinstance(instance, str):
            return True
        return jsonpointer.JsonPointer(instance)

    @_checks_drafts(draft7='relative-json-pointer', draft201909='relative-json-pointer', draft202012='relative-json-pointer', raises=jsonpointer.JsonPointerException)
    def is_relative_json_pointer(instance):
        if not isinstance(instance, str):
            return True
        (non_negative_integer, rest) = ([], '')
        for (i, character) in enumerate(instance):
            if character.isdigit():
                if i > 0 and int(instance[i - 1]) == 0:
                    return False
                non_negative_integer.append(character)
                continue
            if not non_negative_integer:
                return False
            rest = instance[i:]
            break
        return rest == '#' or jsonpointer.JsonPointer(rest)
with suppress(ImportError):
    import uri_template

    @_checks_drafts(draft6='uri-template', draft7='uri-template', draft201909='uri-template', draft202012='uri-template')
    def is_uri_template(instance):
        if not isinstance(instance, str):
            return True
        return uri_template.validate(instance)
with suppress(ImportError):
    import isoduration

    @_checks_drafts(draft201909='duration', draft202012='duration', raises=isoduration.DurationParsingException)
    def is_duration(instance):
        if not isinstance(instance, str):
            return True
        return isoduration.parse_duration(instance)

@_checks_drafts(draft201909='uuid', draft202012='uuid', raises=ValueError)
def is_uuid(instance):
    if not isinstance(instance, str):
        return True
    UUID(instance)
    return all((instance[position] == '-' for position in (8, 13, 18, 23)))

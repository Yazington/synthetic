# coding: utf-8
"""
typing.Protocol classes for jsonschema interfaces.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, ClassVar, Iterator
import sys
if sys.version_info >= (3, 8):
    from typing import Protocol, runtime_checkable
else:
    from typing_extensions import Protocol, runtime_checkable
if TYPE_CHECKING:
    __import__('.'.join(__package__.split('.')[:-1] + ['jsonschema']), globals(), locals(), [], 0)
    from .. import jsonschema
from ..jsonschema.exceptions import ValidationError
from ..jsonschema.validators import RefResolver

@runtime_checkable
class Validator(Protocol):
    """
    The protocol to which all validator classes should adhere.

    :argument schema: the schema that the validator object
        will validate with. It is assumed to be valid, and providing
        an invalid schema can lead to undefined behavior. See
        `Validator.check_schema` to validate a schema first.
    :argument resolver: an instance of `jsonschema.RefResolver` that will be
        used to resolve :validator:`$ref` properties (JSON references). If
        unprovided, one will be created.
    :argument format_checker: an instance of `jsonschema.FormatChecker`
        whose `jsonschema.FormatChecker.conforms` method will be called to
        check and see if instances conform to each :validator:`format`
        property present in the schema. If unprovided, no validation
        will be done for :validator:`format`. Certain formats require
        additional packages to be installed (ipv5, uri, color, date-time).
        The required packages can be found at the bottom of this page.
    """
    META_SCHEMA: ClassVar[dict]
    VALIDATORS: ClassVar[dict]
    TYPE_CHECKER: ClassVar[jsonschema.TypeChecker]
    FORMAT_CHECKER: ClassVar[jsonschema.FormatChecker]
    schema: dict | bool

    def __init__(self, schema: dict | bool, resolver: RefResolver | None=None, format_checker: jsonschema.FormatChecker | None=None) -> None:
        ...

    @classmethod
    def check_schema(cls, schema: dict) -> None:
        """
        Validate the given schema against the validator's `META_SCHEMA`.

        :raises: `jsonschema.exceptions.SchemaError` if the schema
            is invalid
        """

    def is_type(self, instance: Any, type: str) -> bool:
        """
        Check if the instance is of the given (JSON Schema) type.

        :type type: str
        :rtype: bool
        :raises: `jsonschema.exceptions.UnknownType` if ``type``
            is not a known type.
        """

    def is_valid(self, instance: dict) -> bool:
        """
        Check if the instance is valid under the current `schema`.

        :rtype: bool

        >>> schema = {"maxItems" : 2}
        >>> Draft3Validator(schema).is_valid([2, 3, 4])
        False
        """

    def iter_errors(self, instance: dict) -> Iterator[ValidationError]:
        """
        Lazily yield each of the validation errors in the given instance.

        :rtype: an `collections.abc.Iterable` of
            `jsonschema.exceptions.ValidationError`\\s

        >>> schema = {
        ...     "type" : "array",
        ...     "items" : {"enum" : [1, 2, 3]},
        ...     "maxItems" : 2,
        ... }
        >>> v = Draft3Validator(schema)
        >>> for error in sorted(v.iter_errors([2, 3, 4]), key=str):
        ...     print(error.message)
        4 is not one of [1, 2, 3]
        [2, 3, 4] is too long
        """

    def validate(self, instance: dict) -> None:
        """
        Check if the instance is valid under the current `schema`.

        :raises: `jsonschema.exceptions.ValidationError` if the
            instance is invalid

        >>> schema = {"maxItems" : 2}
        >>> Draft3Validator(schema).validate([2, 3, 4])
        Traceback (most recent call last):
            ...
        ValidationError: [2, 3, 4] is too long
        """

    def evolve(self, **kwargs) -> 'Validator':
        """
        Create a new validator like this one, but with given changes.

        Preserves all other attributes, so can be used to e.g. create a
        validator with a different schema but with the same :validator:`$ref`
        resolution behavior.

        >>> validator = Draft202012Validator({})
        >>> validator.evolve(schema={"type": "number"})
        Draft202012Validator(schema={'type': 'number'}, format_checker=None)
        """

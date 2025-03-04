# coding: utf-8
"""
Commonly used hooks for on_setattr.
"""
from . import _config
from .exceptions import FrozenAttributeError

def pipe(*setters):
    """
    Run all *setters* and return the return value of the last one.

    .. versionadded:: 20.1.0
    """

    def wrapped_pipe(instance, attrib, new_value):
        rv = new_value
        for setter in setters:
            rv = setter(instance, attrib, rv)
        return rv
    return wrapped_pipe

def frozen(_, __, ___):
    """
    Prevent an attribute to be modified.

    .. versionadded:: 20.1.0
    """
    raise FrozenAttributeError()

def validate(instance, attrib, new_value):
    """
    Run *attrib*'s validator on *new_value* if it has one.

    .. versionadded:: 20.1.0
    """
    if _config._run_validators is False:
        return new_value
    v = attrib.validator
    if not v:
        return new_value
    v(instance, attrib, new_value)
    return new_value

def convert(instance, attrib, new_value):
    """
    Run *attrib*'s converter -- if it has one -- on *new_value* and return the
    result.

    .. versionadded:: 20.1.0
    """
    c = attrib.converter
    if c:
        from ._make import Converter
        if not isinstance(c, Converter):
            return c(new_value)
        return c(new_value, instance, attrib)
    return new_value
NO_OP = object()

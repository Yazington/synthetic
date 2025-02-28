# coding: utf-8
"""Binary input/output support routines."""
from __future__ import annotations
from struct import pack, unpack_from

def i8(c: bytes) -> int:
    return c[0]

def o8(i: int) -> bytes:
    return bytes((i & 255,))

def i16le(c: bytes, o: int=0) -> int:
    """
    Converts a 2-bytes (16 bits) string to an unsigned integer.

    :param c: string containing bytes to convert
    :param o: offset of bytes to convert in string
    """
    return unpack_from('<H', c, o)[0]

def si16le(c: bytes, o: int=0) -> int:
    """
    Converts a 2-bytes (16 bits) string to a signed integer.

    :param c: string containing bytes to convert
    :param o: offset of bytes to convert in string
    """
    return unpack_from('<h', c, o)[0]

def si16be(c: bytes, o: int=0) -> int:
    """
    Converts a 2-bytes (16 bits) string to a signed integer, big endian.

    :param c: string containing bytes to convert
    :param o: offset of bytes to convert in string
    """
    return unpack_from('>h', c, o)[0]

def i32le(c: bytes, o: int=0) -> int:
    """
    Converts a 4-bytes (32 bits) string to an unsigned integer.

    :param c: string containing bytes to convert
    :param o: offset of bytes to convert in string
    """
    return unpack_from('<I', c, o)[0]

def si32le(c: bytes, o: int=0) -> int:
    """
    Converts a 4-bytes (32 bits) string to a signed integer.

    :param c: string containing bytes to convert
    :param o: offset of bytes to convert in string
    """
    return unpack_from('<i', c, o)[0]

def si32be(c: bytes, o: int=0) -> int:
    """
    Converts a 4-bytes (32 bits) string to a signed integer, big endian.

    :param c: string containing bytes to convert
    :param o: offset of bytes to convert in string
    """
    return unpack_from('>i', c, o)[0]

def i16be(c: bytes, o: int=0) -> int:
    return unpack_from('>H', c, o)[0]

def i32be(c: bytes, o: int=0) -> int:
    return unpack_from('>I', c, o)[0]

def o16le(i: int) -> bytes:
    return pack('<H', i)

def o32le(i: int) -> bytes:
    return pack('<I', i)

def o16be(i: int) -> bytes:
    return pack('>H', i)

def o32be(i: int) -> bytes:
    return pack('>I', i)

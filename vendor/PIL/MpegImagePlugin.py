# coding: utf-8
from __future__ import annotations
from . import Image, ImageFile
from ._binary import i8
from ._typing import SupportsRead

class BitStream:

    def __init__(self, fp: SupportsRead[bytes]) -> None:
        self.fp = fp
        self.bits = 0
        self.bitbuffer = 0

    def next(self) -> int:
        return i8(self.fp.read(1))

    def peek(self, bits: int) -> int:
        while self.bits < bits:
            c = self.next()
            if c < 0:
                self.bits = 0
                continue
            self.bitbuffer = (self.bitbuffer << 8) + c
            self.bits += 8
        return self.bitbuffer >> self.bits - bits & (1 << bits) - 1

    def skip(self, bits: int) -> None:
        while self.bits < bits:
            self.bitbuffer = (self.bitbuffer << 8) + i8(self.fp.read(1))
            self.bits += 8
        self.bits = self.bits - bits

    def read(self, bits: int) -> int:
        v = self.peek(bits)
        self.bits = self.bits - bits
        return v

def _accept(prefix: bytes) -> bool:
    return prefix[:4] == b'\x00\x00\x01\xb3'

class MpegImageFile(ImageFile.ImageFile):
    format = 'MPEG'
    format_description = 'MPEG'

    def _open(self) -> None:
        assert self.fp is not None
        s = BitStream(self.fp)
        if s.read(32) != 435:
            msg = 'not an MPEG file'
            raise SyntaxError(msg)
        self._mode = 'RGB'
        self._size = (s.read(12), s.read(12))
Image.register_open(MpegImageFile.format, MpegImageFile, _accept)
Image.register_extensions(MpegImageFile.format, ['.mpg', '.mpeg'])
Image.register_mime(MpegImageFile.format, 'video/mpeg')

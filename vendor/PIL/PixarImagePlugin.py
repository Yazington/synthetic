# coding: utf-8
from __future__ import annotations
from . import Image, ImageFile
from ._binary import i16le as i16

def _accept(prefix: bytes) -> bool:
    return prefix[:4] == b'\x80\xe8\x00\x00'

class PixarImageFile(ImageFile.ImageFile):
    format = 'PIXAR'
    format_description = 'PIXAR raster image'

    def _open(self) -> None:
        assert self.fp is not None
        s = self.fp.read(4)
        if not _accept(s):
            msg = 'not a PIXAR file'
            raise SyntaxError(msg)
        s = s + self.fp.read(508)
        self._size = (i16(s, 418), i16(s, 416))
        mode = (i16(s, 424), i16(s, 426))
        if mode == (14, 2):
            self._mode = 'RGB'
        self.tile = [ImageFile._Tile('raw', (0, 0) + self.size, 1024, (self.mode, 0, 1))]
Image.register_open(PixarImageFile.format, PixarImageFile, _accept)
Image.register_extension(PixarImageFile.format, '.pxr')

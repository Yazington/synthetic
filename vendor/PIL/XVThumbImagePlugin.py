# coding: utf-8
from __future__ import annotations
from . import Image, ImageFile, ImagePalette
from ._binary import o8
_MAGIC = b'P7 332'
PALETTE = b''
for r in range(8):
    for g in range(8):
        for b in range(4):
            PALETTE = PALETTE + (o8(r * 255 // 7) + o8(g * 255 // 7) + o8(b * 255 // 3))

def _accept(prefix: bytes) -> bool:
    return prefix[:6] == _MAGIC

class XVThumbImageFile(ImageFile.ImageFile):
    format = 'XVThumb'
    format_description = 'XV thumbnail image'

    def _open(self) -> None:
        assert self.fp is not None
        if not _accept(self.fp.read(6)):
            msg = 'not an XV thumbnail file'
            raise SyntaxError(msg)
        self.fp.readline()
        while True:
            s = self.fp.readline()
            if not s:
                msg = 'Unexpected EOF reading XV thumbnail file'
                raise SyntaxError(msg)
            if s[0] != 35:
                break
        s = s.strip().split()
        self._mode = 'P'
        self._size = (int(s[0]), int(s[1]))
        self.palette = ImagePalette.raw('RGB', PALETTE)
        self.tile = [ImageFile._Tile('raw', (0, 0) + self.size, self.fp.tell(), (self.mode, 0, 1))]
Image.register_open(XVThumbImageFile.format, XVThumbImageFile, _accept)

# coding: utf-8
from __future__ import annotations
import struct
from . import Image, ImageFile

def _accept(prefix: bytes) -> bool:
    return prefix[:8] == b'\x00\x00\x00\x00\x00\x00\x00\x04'

class McIdasImageFile(ImageFile.ImageFile):
    format = 'MCIDAS'
    format_description = 'McIdas area file'

    def _open(self) -> None:
        assert self.fp is not None
        s = self.fp.read(256)
        if not _accept(s) or len(s) != 256:
            msg = 'not an McIdas area file'
            raise SyntaxError(msg)
        self.area_descriptor_raw = s
        self.area_descriptor = w = [0] + list(struct.unpack('!64i', s))
        if w[11] == 1:
            mode = rawmode = 'L'
        elif w[11] == 2:
            mode = 'I'
            rawmode = 'I;16B'
        elif w[11] == 4:
            mode = 'I'
            rawmode = 'I;32B'
        else:
            msg = 'unsupported McIdas format'
            raise SyntaxError(msg)
        self._mode = mode
        self._size = (w[10], w[9])
        offset = w[34] + w[15]
        stride = w[15] + w[10] * w[11] * w[14]
        self.tile = [ImageFile._Tile('raw', (0, 0) + self.size, offset, (rawmode, stride, 1))]
Image.register_open(McIdasImageFile.format, McIdasImageFile, _accept)

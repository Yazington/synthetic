# coding: utf-8
from __future__ import annotations
import re
from . import Image, ImageFile
field = re.compile(b'([a-z]*) ([^ \\r\\n]*)')

class ImtImageFile(ImageFile.ImageFile):
    format = 'IMT'
    format_description = 'IM Tools'

    def _open(self) -> None:
        assert self.fp is not None
        buffer = self.fp.read(100)
        if b'\n' not in buffer:
            msg = 'not an IM file'
            raise SyntaxError(msg)
        xsize = ysize = 0
        while True:
            if buffer:
                s = buffer[:1]
                buffer = buffer[1:]
            else:
                s = self.fp.read(1)
            if not s:
                break
            if s == b'\x0c':
                self.tile = [ImageFile._Tile('raw', (0, 0) + self.size, self.fp.tell() - len(buffer), (self.mode, 0, 1))]
                break
            else:
                if b'\n' not in buffer:
                    buffer += self.fp.read(100)
                lines = buffer.split(b'\n')
                s += lines.pop(0)
                buffer = b'\n'.join(lines)
                if len(s) == 1 or len(s) > 100:
                    break
                if s[0] == ord(b'*'):
                    continue
                m = field.match(s)
                if not m:
                    break
                (k, v) = m.group(1, 2)
                if k == b'width':
                    xsize = int(v)
                    self._size = (xsize, ysize)
                elif k == b'height':
                    ysize = int(v)
                    self._size = (xsize, ysize)
                elif k == b'pixel' and v == b'n8':
                    self._mode = 'L'
Image.register_open(ImtImageFile.format, ImtImageFile)

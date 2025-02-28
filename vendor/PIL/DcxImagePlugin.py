# coding: utf-8
from __future__ import annotations
from . import Image
from ._binary import i32le as i32
from .PcxImagePlugin import PcxImageFile
MAGIC = 987654321

def _accept(prefix: bytes) -> bool:
    return len(prefix) >= 4 and i32(prefix) == MAGIC

class DcxImageFile(PcxImageFile):
    format = 'DCX'
    format_description = 'Intel DCX'
    _close_exclusive_fp_after_loading = False

    def _open(self) -> None:
        s = self.fp.read(4)
        if not _accept(s):
            msg = 'not a DCX file'
            raise SyntaxError(msg)
        self._offset = []
        for i in range(1024):
            offset = i32(self.fp.read(4))
            if not offset:
                break
            self._offset.append(offset)
        self._fp = self.fp
        self.frame = -1
        self.n_frames = len(self._offset)
        self.is_animated = self.n_frames > 1
        self.seek(0)

    def seek(self, frame: int) -> None:
        if not self._seek_check(frame):
            return
        self.frame = frame
        self.fp = self._fp
        self.fp.seek(self._offset[frame])
        PcxImageFile._open(self)

    def tell(self) -> int:
        return self.frame
Image.register_open(DcxImageFile.format, DcxImageFile, _accept)
Image.register_extension(DcxImageFile.format, '.dcx')

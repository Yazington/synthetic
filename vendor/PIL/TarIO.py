# coding: utf-8
from __future__ import annotations
import io
from . import ContainerIO

class TarIO(ContainerIO.ContainerIO[bytes]):
    """A file object that provides read access to a given member of a TAR file."""

    def __init__(self, tarfile: str, file: str) -> None:
        """
        Create file object.

        :param tarfile: Name of TAR file.
        :param file: Name of member file.
        """
        self.fh = open(tarfile, 'rb')
        while True:
            s = self.fh.read(512)
            if len(s) != 512:
                msg = 'unexpected end of tar file'
                raise OSError(msg)
            name = s[:100].decode('utf-8')
            i = name.find('\x00')
            if i == 0:
                msg = 'cannot find subfile'
                raise OSError(msg)
            if i > 0:
                name = name[:i]
            size = int(s[124:135], 8)
            if file == name:
                break
            self.fh.seek(size + 511 & ~511, io.SEEK_CUR)
        super().__init__(self.fh, self.fh.tell(), size)

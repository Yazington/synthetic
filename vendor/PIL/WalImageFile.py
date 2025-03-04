# coding: utf-8
"""
This reader is based on the specification available from:
https://www.flipcode.com/archives/Quake_2_BSP_File_Format.shtml
and has been tested with a few sample files found using google.

.. note::
    This format cannot be automatically recognized, so the reader
    is not registered for use with :py:func:`PIL.Image.open()`.
    To open a WAL file, use the :py:func:`PIL.WalImageFile.open()` function instead.
"""
from __future__ import annotations
from typing import IO
from . import Image, ImageFile
from ._binary import i32le as i32
from ._typing import StrOrBytesPath

class WalImageFile(ImageFile.ImageFile):
    format = 'WAL'
    format_description = 'Quake2 Texture'

    def _open(self) -> None:
        self._mode = 'P'
        header = self.fp.read(32 + 24 + 32 + 12)
        self._size = (i32(header, 32), i32(header, 36))
        Image._decompression_bomb_check(self.size)
        offset = i32(header, 40)
        self.fp.seek(offset)
        self.info['name'] = header[:32].split(b'\x00', 1)[0]
        next_name = header[56:56 + 32].split(b'\x00', 1)[0]
        if next_name:
            self.info['next_name'] = next_name

    def load(self) -> Image.core.PixelAccess | None:
        if self._im is None:
            self.im = Image.core.new(self.mode, self.size)
            self.frombytes(self.fp.read(self.size[0] * self.size[1]))
            self.putpalette(quake2palette)
        return Image.Image.load(self)

def open(filename: StrOrBytesPath | IO[bytes]) -> WalImageFile:
    """
    Load texture from a Quake2 WAL texture file.

    By default, a Quake2 standard palette is attached to the texture.
    To override the palette, use the :py:func:`PIL.Image.Image.putpalette()` method.

    :param filename: WAL file name, or an opened file handle.
    :returns: An image instance.
    """
    return WalImageFile(filename)
quake2palette = b'\x01\x01\x01\x0b\x0b\x0b\x12\x12\x12\x17\x17\x17\x1b\x1b\x1b\x1e\x1e\x1e"""&&&))),,,///222555777:::<<<$\x1e\x13"\x1c\x12 \x1b\x12\x1f\x1a\x10\x1d\x19\x10\x1b\x17\x0f\x1a\x16\x0f\x18\x14\r\x17\x13\r\x16\x12\r\x14\x10\x0b\x13\x0f\x0b\x10\r\n\x0f\x0b\n\r\x0b\x07\x0b\n\x07##&""%" #!\x1f" \x1e \x1f\x1d\x1e\x1d\x1b\x1c\x1b\x1a\x1a\x1a\x19\x19\x18\x17\x17\x17\x16\x16\x14\x14\x14\x13\x13\x13\x10\x10\x10\x0f\x0f\x0f\r\r\r-( )$\x1c\'"\x1a%\x1f\x178.\x1e1)\x1a,%\x17& \x14<0\x147,\x133(\x12-$\x10(\x1f\x0f"\x1a\x0b\x1b\x14\n\x13\x0f\x071\x1a\x160\x17\x13.\x16\x10,\x14\r*\x12\x0b\'\x0f\n%\x0f\x07!\r\x01\x1e\x0b\x01\x1c\x0b\x01\x1a\x0b\x01\x18\n\x01\x16\n\x01\x13\n\x01\x10\x07\x01\r\x07\x01)#\x1e\'!\x1c& \x1b%\x1f\x1a#\x1d\x19!\x1c\x18 \x1b\x17\x1e\x19\x16\x1c\x18\x14\x1b\x17\x13\x19\x14\x10\x17\x13\x0f\x14\x10\r\x12\x0f\x0b\x0f\x0b\n\x0b\n\x07&\x1a\x0f#\x19\x0f \x17\x0f\x1c\x16\x0f\x19\x13\r\x14\x10\x0b\x10\r\n\x0b\n\x073"\x1f5)&7/-95479:379046+14\'.1"+/\x1d(,\x17%*\x0f &\r\x1e%\x0b\x1c"\n\x1b \x07\x19\x1e\x07\x17\x1b\x07\x14\x18\x01\x12\x16\x01\x0f\x12\x01\x0b\r\x01\x07\n\x01\x01\x01,!!*\x1f\x1f)\x1d\x1d\'\x1c\x1c&\x1a\x1a$\x18\x18"\x17\x17!\x16\x16\x1e\x13\x13\x1b\x12\x12\x18\x10\x10\x16\r\r\x12\x0b\x0b\r\n\n\n\x07\x07\x01\x01\x01.0)-.\'+,&**$()#\'\'!&&\x1f$$\x1d""\x1c\x1f\x1f\x1a\x1c\x1c\x18\x19\x19\x16\x17\x17\x13\x13\x13\x10\x0f\x0f\r\x0b\x0b\n0\x1e\x1b-\x1c\x19,\x1a\x17*\x19\x14(\x17\x13&\x16\x10$\x13\x0f!\x12\r\x1f\x10\x0b\x1c\x0f\n\x19\r\n\x16\x0b\x07\x12\n\x07\x0f\x07\x01\n\x01\x01\x01\x01\x01()8&\'6%&4$$1""/ !-\x1e\x1f*\x1d\x1d\'\x1b\x1b%\x19\x19!\x17\x17\x1e\x14\x14\x1b\x13\x12\x17\x10\x0f\x13\r\x0b\x0f\n\x07\x07/2)-0&+.$),!\'*\x1e%(\x1c#&\x1a!%\x18\x1e"\x14\x1b\x1f\x10\x19\x1c\r\x17\x1a\n\x13\x17\x07\x10\x13\x01\r\x0f\x01\n\x0b\x01\x01?\x01\x13<\x0b\x1b9\x10 5\x14#1\x17#-\x18#)\x18?????9??1??*?? ??\x14?<\x12?9\x0f?5\x0b?2\x07?-\x01=*\x01;&\x019!\x017\x1d\x014\x1a\x012\x16\x01/\x12\x01-\x0f\x01*\x0b\x01\'\x07\x01#\x01\x01\x1d\x01\x01\x17\x01\x01\x10\x01\x01=\x01\x01\x19\x19??\x01\x01\x01\x01?\x16\x16\x13\x10\x10\x0f\r\r\x0b<.*6\' 0!\x18)\x1b\x10<9772/1,(+&!0" '

# coding: utf-8
from __future__ import annotations
import warnings
from io import BytesIO
from math import ceil, log
from typing import IO, NamedTuple
from . import BmpImagePlugin, Image, ImageFile, PngImagePlugin
from ._binary import i16le as i16
from ._binary import i32le as i32
from ._binary import o8
from ._binary import o16le as o16
from ._binary import o32le as o32
_MAGIC = b'\x00\x00\x01\x00'

def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    fp.write(_MAGIC)
    bmp = im.encoderinfo.get('bitmap_format') == 'bmp'
    sizes = im.encoderinfo.get('sizes', [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    frames = []
    provided_ims = [im] + im.encoderinfo.get('append_images', [])
    (width, height) = im.size
    for size in sorted(set(sizes)):
        if size[0] > width or size[1] > height or size[0] > 256 or (size[1] > 256):
            continue
        for provided_im in provided_ims:
            if provided_im.size != size:
                continue
            frames.append(provided_im)
            if bmp:
                bits = BmpImagePlugin.SAVE[provided_im.mode][1]
                bits_used = [bits]
                for other_im in provided_ims:
                    if other_im.size != size:
                        continue
                    bits = BmpImagePlugin.SAVE[other_im.mode][1]
                    if bits not in bits_used:
                        frames.append(other_im)
                        bits_used.append(bits)
            break
        else:
            frame = provided_im.copy()
            frame.thumbnail(size, Image.Resampling.LANCZOS, reducing_gap=None)
            frames.append(frame)
    fp.write(o16(len(frames)))
    offset = fp.tell() + len(frames) * 16
    for frame in frames:
        (width, height) = frame.size
        fp.write(o8(width if width < 256 else 0))
        fp.write(o8(height if height < 256 else 0))
        (bits, colors) = BmpImagePlugin.SAVE[frame.mode][1:] if bmp else (32, 0)
        fp.write(o8(colors))
        fp.write(b'\x00')
        fp.write(b'\x00\x00')
        fp.write(o16(bits))
        image_io = BytesIO()
        if bmp:
            frame.save(image_io, 'dib')
            if bits != 32:
                and_mask = Image.new('1', size)
                ImageFile._save(and_mask, image_io, [ImageFile._Tile('raw', (0, 0) + size, 0, ('1', 0, -1))])
        else:
            frame.save(image_io, 'png')
        image_io.seek(0)
        image_bytes = image_io.read()
        if bmp:
            image_bytes = image_bytes[:8] + o32(height * 2) + image_bytes[12:]
        bytes_len = len(image_bytes)
        fp.write(o32(bytes_len))
        fp.write(o32(offset))
        current = fp.tell()
        fp.seek(offset)
        fp.write(image_bytes)
        offset = offset + bytes_len
        fp.seek(current)

def _accept(prefix: bytes) -> bool:
    return prefix[:4] == _MAGIC

class IconHeader(NamedTuple):
    width: int
    height: int
    nb_color: int
    reserved: int
    planes: int
    bpp: int
    size: int
    offset: int
    dim: tuple[int, int]
    square: int
    color_depth: int

class IcoFile:

    def __init__(self, buf: IO[bytes]) -> None:
        """
        Parse image from file-like object containing ico file data
        """
        s = buf.read(6)
        if not _accept(s):
            msg = 'not an ICO file'
            raise SyntaxError(msg)
        self.buf = buf
        self.entry = []
        self.nb_items = i16(s, 4)
        for i in range(self.nb_items):
            s = buf.read(16)
            width = s[0] or 256
            height = s[1] or 256
            nb_color = s[2]
            bpp = i16(s, 6)
            icon_header = IconHeader(width=width, height=height, nb_color=nb_color, reserved=s[3], planes=i16(s, 4), bpp=i16(s, 6), size=i32(s, 8), offset=i32(s, 12), dim=(width, height), square=width * height, color_depth=bpp or (nb_color != 0 and ceil(log(nb_color, 2))) or 256)
            self.entry.append(icon_header)
        self.entry = sorted(self.entry, key=lambda x: x.color_depth)
        self.entry = sorted(self.entry, key=lambda x: x.square, reverse=True)

    def sizes(self) -> set[tuple[int, int]]:
        """
        Get a set of all available icon sizes and color depths.
        """
        return {(h.width, h.height) for h in self.entry}

    def getentryindex(self, size: tuple[int, int], bpp: int | bool=False) -> int:
        for (i, h) in enumerate(self.entry):
            if size == h.dim and (bpp is False or bpp == h.color_depth):
                return i
        return 0

    def getimage(self, size: tuple[int, int], bpp: int | bool=False) -> Image.Image:
        """
        Get an image from the icon
        """
        return self.frame(self.getentryindex(size, bpp))

    def frame(self, idx: int) -> Image.Image:
        """
        Get an image from frame idx
        """
        header = self.entry[idx]
        self.buf.seek(header.offset)
        data = self.buf.read(8)
        self.buf.seek(header.offset)
        im: Image.Image
        if data[:8] == PngImagePlugin._MAGIC:
            im = PngImagePlugin.PngImageFile(self.buf)
            Image._decompression_bomb_check(im.size)
        else:
            im = BmpImagePlugin.DibImageFile(self.buf)
            Image._decompression_bomb_check(im.size)
            im._size = (im.size[0], int(im.size[1] / 2))
            (d, e, o, a) = im.tile[0]
            im.tile[0] = ImageFile._Tile(d, (0, 0) + im.size, o, a)
            if header.bpp == 32:
                self.buf.seek(o)
                alpha_bytes = self.buf.read(im.size[0] * im.size[1] * 4)[3::4]
                try:
                    mask = Image.frombuffer('L', im.size, alpha_bytes, 'raw', ('L', 0, -1))
                except ValueError:
                    if ImageFile.LOAD_TRUNCATED_IMAGES:
                        mask = None
                    else:
                        raise
            else:
                w = im.size[0]
                if w % 32 > 0:
                    w += 32 - im.size[0] % 32
                total_bytes = int(w * im.size[1] / 8)
                and_mask_offset = header.offset + header.size - total_bytes
                self.buf.seek(and_mask_offset)
                mask_data = self.buf.read(total_bytes)
                try:
                    mask = Image.frombuffer('1', im.size, mask_data, 'raw', ('1;I', int(w / 8), -1))
                except ValueError:
                    if ImageFile.LOAD_TRUNCATED_IMAGES:
                        mask = None
                    else:
                        raise
            if mask:
                im = im.convert('RGBA')
                im.putalpha(mask)
        return im

class IcoImageFile(ImageFile.ImageFile):
    """
    PIL read-only image support for Microsoft Windows .ico files.

    By default the largest resolution image in the file will be loaded. This
    can be changed by altering the 'size' attribute before calling 'load'.

    The info dictionary has a key 'sizes' that is a list of the sizes available
    in the icon file.

    Handles classic, XP and Vista icon formats.

    When saving, PNG compression is used. Support for this was only added in
    Windows Vista. If you are unable to view the icon in Windows, convert the
    image to "RGBA" mode before saving.

    This plugin is a refactored version of Win32IconImagePlugin by Bryan Davis
    <casadebender@gmail.com>.
    https://code.google.com/archive/p/casadebender/wikis/Win32IconImagePlugin.wiki
    """
    format = 'ICO'
    format_description = 'Windows Icon'

    def _open(self) -> None:
        self.ico = IcoFile(self.fp)
        self.info['sizes'] = self.ico.sizes()
        self.size = self.ico.entry[0].dim
        self.load()

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    @size.setter
    def size(self, value: tuple[int, int]) -> None:
        if value not in self.info['sizes']:
            msg = 'This is not one of the allowed sizes of this image'
            raise ValueError(msg)
        self._size = value

    def load(self) -> Image.core.PixelAccess | None:
        if self._im is not None and self.im.size == self.size:
            return Image.Image.load(self)
        im = self.ico.getimage(self.size)
        im.load()
        self.im = im.im
        self._mode = im.mode
        if im.palette:
            self.palette = im.palette
        if im.size != self.size:
            warnings.warn('Image was not the expected size')
            index = self.ico.getentryindex(self.size)
            sizes = list(self.info['sizes'])
            sizes[index] = im.size
            self.info['sizes'] = set(sizes)
            self.size = im.size
        return None

    def load_seek(self, pos: int) -> None:
        pass
Image.register_open(IcoImageFile.format, IcoImageFile, _accept)
Image.register_save(IcoImageFile.format, _save)
Image.register_extension(IcoImageFile.format, '.ico')
Image.register_mime(IcoImageFile.format, 'image/x-icon')

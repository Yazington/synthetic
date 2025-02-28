# coding: utf-8
from __future__ import annotations
import itertools
import logging
import re
import struct
import warnings
import zlib
from collections.abc import Callable
from enum import IntEnum
from typing import IO, TYPE_CHECKING, Any, NamedTuple, NoReturn, cast
from . import Image, ImageChops, ImageFile, ImagePalette, ImageSequence
from ._binary import i16be as i16
from ._binary import i32be as i32
from ._binary import o8
from ._binary import o16be as o16
from ._binary import o32be as o32
if TYPE_CHECKING:
    from . import _imaging
logger = logging.getLogger(__name__)
is_cid = re.compile(b'\\w\\w\\w\\w').match
_MAGIC = b'\x89PNG\r\n\x1a\n'
_MODES = {(1, 0): ('1', '1'), (2, 0): ('L', 'L;2'), (4, 0): ('L', 'L;4'), (8, 0): ('L', 'L'), (16, 0): ('I;16', 'I;16B'), (8, 2): ('RGB', 'RGB'), (16, 2): ('RGB', 'RGB;16B'), (1, 3): ('P', 'P;1'), (2, 3): ('P', 'P;2'), (4, 3): ('P', 'P;4'), (8, 3): ('P', 'P'), (8, 4): ('LA', 'LA'), (16, 4): ('RGBA', 'LA;16B'), (8, 6): ('RGBA', 'RGBA'), (16, 6): ('RGBA', 'RGBA;16B')}
_simple_palette = re.compile(b'^\xff*\x00\xff*$')
MAX_TEXT_CHUNK = ImageFile.SAFEBLOCK
'\nMaximum decompressed size for a iTXt or zTXt chunk.\nEliminates decompression bombs where compressed chunks can expand 1000x.\nSee :ref:`Text in PNG File Format<png-text>`.\n'
MAX_TEXT_MEMORY = 64 * MAX_TEXT_CHUNK
'\nSet the maximum total text chunk size.\nSee :ref:`Text in PNG File Format<png-text>`.\n'

class Disposal(IntEnum):
    OP_NONE = 0
    '\n    No disposal is done on this frame before rendering the next frame.\n    See :ref:`Saving APNG sequences<apng-saving>`.\n    '
    OP_BACKGROUND = 1
    '\n    This frame’s modified region is cleared to fully transparent black before rendering\n    the next frame.\n    See :ref:`Saving APNG sequences<apng-saving>`.\n    '
    OP_PREVIOUS = 2
    '\n    This frame’s modified region is reverted to the previous frame’s contents before\n    rendering the next frame.\n    See :ref:`Saving APNG sequences<apng-saving>`.\n    '

class Blend(IntEnum):
    OP_SOURCE = 0
    '\n    All color components of this frame, including alpha, overwrite the previous output\n    image contents.\n    See :ref:`Saving APNG sequences<apng-saving>`.\n    '
    OP_OVER = 1
    '\n    This frame should be alpha composited with the previous output image contents.\n    See :ref:`Saving APNG sequences<apng-saving>`.\n    '

def _safe_zlib_decompress(s: bytes) -> bytes:
    dobj = zlib.decompressobj()
    plaintext = dobj.decompress(s, MAX_TEXT_CHUNK)
    if dobj.unconsumed_tail:
        msg = 'Decompressed data too large for PngImagePlugin.MAX_TEXT_CHUNK'
        raise ValueError(msg)
    return plaintext

def _crc32(data: bytes, seed: int=0) -> int:
    return zlib.crc32(data, seed) & 4294967295

class ChunkStream:

    def __init__(self, fp: IO[bytes]) -> None:
        self.fp: IO[bytes] | None = fp
        self.queue: list[tuple[bytes, int, int]] | None = []

    def read(self) -> tuple[bytes, int, int]:
        """Fetch a new chunk. Returns header information."""
        cid = None
        assert self.fp is not None
        if self.queue:
            (cid, pos, length) = self.queue.pop()
            self.fp.seek(pos)
        else:
            s = self.fp.read(8)
            cid = s[4:]
            pos = self.fp.tell()
            length = i32(s)
        if not is_cid(cid):
            if not ImageFile.LOAD_TRUNCATED_IMAGES:
                msg = f'broken PNG file (chunk {repr(cid)})'
                raise SyntaxError(msg)
        return (cid, pos, length)

    def __enter__(self) -> ChunkStream:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self.queue = self.fp = None

    def push(self, cid: bytes, pos: int, length: int) -> None:
        assert self.queue is not None
        self.queue.append((cid, pos, length))

    def call(self, cid: bytes, pos: int, length: int) -> bytes:
        """Call the appropriate chunk handler"""
        logger.debug('STREAM %r %s %s', cid, pos, length)
        return getattr(self, f"chunk_{cid.decode('ascii')}")(pos, length)

    def crc(self, cid: bytes, data: bytes) -> None:
        """Read and verify checksum"""
        if ImageFile.LOAD_TRUNCATED_IMAGES and cid[0] >> 5 & 1:
            self.crc_skip(cid, data)
            return
        assert self.fp is not None
        try:
            crc1 = _crc32(data, _crc32(cid))
            crc2 = i32(self.fp.read(4))
            if crc1 != crc2:
                msg = f'broken PNG file (bad header checksum in {repr(cid)})'
                raise SyntaxError(msg)
        except struct.error as e:
            msg = f'broken PNG file (incomplete checksum in {repr(cid)})'
            raise SyntaxError(msg) from e

    def crc_skip(self, cid: bytes, data: bytes) -> None:
        """Read checksum"""
        assert self.fp is not None
        self.fp.read(4)

    def verify(self, endchunk: bytes=b'IEND') -> list[bytes]:
        cids = []
        assert self.fp is not None
        while True:
            try:
                (cid, pos, length) = self.read()
            except struct.error as e:
                msg = 'truncated PNG file'
                raise OSError(msg) from e
            if cid == endchunk:
                break
            self.crc(cid, ImageFile._safe_read(self.fp, length))
            cids.append(cid)
        return cids

class iTXt(str):
    """
    Subclass of string to allow iTXt chunks to look like strings while
    keeping their extra information

    """
    lang: str | bytes | None
    tkey: str | bytes | None

    @staticmethod
    def __new__(cls, text: str, lang: str | None=None, tkey: str | None=None) -> iTXt:
        """
        :param cls: the class to use when creating the instance
        :param text: value for this key
        :param lang: language code
        :param tkey: UTF-8 version of the key name
        """
        self = str.__new__(cls, text)
        self.lang = lang
        self.tkey = tkey
        return self

class PngInfo:
    """
    PNG chunk container (for use with save(pnginfo=))

    """

    def __init__(self) -> None:
        self.chunks: list[tuple[bytes, bytes, bool]] = []

    def add(self, cid: bytes, data: bytes, after_idat: bool=False) -> None:
        """Appends an arbitrary chunk. Use with caution.

        :param cid: a byte string, 4 bytes long.
        :param data: a byte string of the encoded data
        :param after_idat: for use with private chunks. Whether the chunk
                           should be written after IDAT

        """
        self.chunks.append((cid, data, after_idat))

    def add_itxt(self, key: str | bytes, value: str | bytes, lang: str | bytes='', tkey: str | bytes='', zip: bool=False) -> None:
        """Appends an iTXt chunk.

        :param key: latin-1 encodable text key name
        :param value: value for this key
        :param lang: language code
        :param tkey: UTF-8 version of the key name
        :param zip: compression flag

        """
        if not isinstance(key, bytes):
            key = key.encode('latin-1', 'strict')
        if not isinstance(value, bytes):
            value = value.encode('utf-8', 'strict')
        if not isinstance(lang, bytes):
            lang = lang.encode('utf-8', 'strict')
        if not isinstance(tkey, bytes):
            tkey = tkey.encode('utf-8', 'strict')
        if zip:
            self.add(b'iTXt', key + b'\x00\x01\x00' + lang + b'\x00' + tkey + b'\x00' + zlib.compress(value))
        else:
            self.add(b'iTXt', key + b'\x00\x00\x00' + lang + b'\x00' + tkey + b'\x00' + value)

    def add_text(self, key: str | bytes, value: str | bytes | iTXt, zip: bool=False) -> None:
        """Appends a text chunk.

        :param key: latin-1 encodable text key name
        :param value: value for this key, text or an
           :py:class:`PIL.PngImagePlugin.iTXt` instance
        :param zip: compression flag

        """
        if isinstance(value, iTXt):
            return self.add_itxt(key, value, value.lang if value.lang is not None else b'', value.tkey if value.tkey is not None else b'', zip=zip)
        if not isinstance(value, bytes):
            try:
                value = value.encode('latin-1', 'strict')
            except UnicodeError:
                return self.add_itxt(key, value, zip=zip)
        if not isinstance(key, bytes):
            key = key.encode('latin-1', 'strict')
        if zip:
            self.add(b'zTXt', key + b'\x00\x00' + zlib.compress(value))
        else:
            self.add(b'tEXt', key + b'\x00' + value)

class _RewindState(NamedTuple):
    info: dict[str | tuple[int, int], Any]
    tile: list[ImageFile._Tile]
    seq_num: int | None

class PngStream(ChunkStream):

    def __init__(self, fp: IO[bytes]) -> None:
        super().__init__(fp)
        self.im_info: dict[str | tuple[int, int], Any] = {}
        self.im_text: dict[str, str | iTXt] = {}
        self.im_size = (0, 0)
        self.im_mode = ''
        self.im_tile: list[ImageFile._Tile] = []
        self.im_palette: tuple[str, bytes] | None = None
        self.im_custom_mimetype: str | None = None
        self.im_n_frames: int | None = None
        self._seq_num: int | None = None
        self.rewind_state = _RewindState({}, [], None)
        self.text_memory = 0

    def check_text_memory(self, chunklen: int) -> None:
        self.text_memory += chunklen
        if self.text_memory > MAX_TEXT_MEMORY:
            msg = f'Too much memory used in text chunks: {self.text_memory}>MAX_TEXT_MEMORY'
            raise ValueError(msg)

    def save_rewind(self) -> None:
        self.rewind_state = _RewindState(self.im_info.copy(), self.im_tile, self._seq_num)

    def rewind(self) -> None:
        self.im_info = self.rewind_state.info.copy()
        self.im_tile = self.rewind_state.tile
        self._seq_num = self.rewind_state.seq_num

    def chunk_iCCP(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        i = s.find(b'\x00')
        logger.debug('iCCP profile name %r', s[:i])
        comp_method = s[i + 1]
        logger.debug('Compression method %s', comp_method)
        if comp_method != 0:
            msg = f'Unknown compression method {comp_method} in iCCP chunk'
            raise SyntaxError(msg)
        try:
            icc_profile = _safe_zlib_decompress(s[i + 2:])
        except ValueError:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                icc_profile = None
            else:
                raise
        except zlib.error:
            icc_profile = None
        self.im_info['icc_profile'] = icc_profile
        return s

    def chunk_IHDR(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if length < 13:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                return s
            msg = 'Truncated IHDR chunk'
            raise ValueError(msg)
        self.im_size = (i32(s, 0), i32(s, 4))
        try:
            (self.im_mode, self.im_rawmode) = _MODES[s[8], s[9]]
        except Exception:
            pass
        if s[12]:
            self.im_info['interlace'] = 1
        if s[11]:
            msg = 'unknown filter category'
            raise SyntaxError(msg)
        return s

    def chunk_IDAT(self, pos: int, length: int) -> NoReturn:
        if 'bbox' in self.im_info:
            tile = [ImageFile._Tile('zip', self.im_info['bbox'], pos, self.im_rawmode)]
        else:
            if self.im_n_frames is not None:
                self.im_info['default_image'] = True
            tile = [ImageFile._Tile('zip', (0, 0) + self.im_size, pos, self.im_rawmode)]
        self.im_tile = tile
        self.im_idat = length
        msg = 'image data found'
        raise EOFError(msg)

    def chunk_IEND(self, pos: int, length: int) -> NoReturn:
        msg = 'end of PNG image'
        raise EOFError(msg)

    def chunk_PLTE(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if self.im_mode == 'P':
            self.im_palette = ('RGB', s)
        return s

    def chunk_tRNS(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if self.im_mode == 'P':
            if _simple_palette.match(s):
                i = s.find(b'\x00')
                if i >= 0:
                    self.im_info['transparency'] = i
            else:
                self.im_info['transparency'] = s
        elif self.im_mode in ('1', 'L', 'I;16'):
            self.im_info['transparency'] = i16(s)
        elif self.im_mode == 'RGB':
            self.im_info['transparency'] = (i16(s), i16(s, 2), i16(s, 4))
        return s

    def chunk_gAMA(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        self.im_info['gamma'] = i32(s) / 100000.0
        return s

    def chunk_cHRM(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        raw_vals = struct.unpack('>%dI' % (len(s) // 4), s)
        self.im_info['chromaticity'] = tuple((elt / 100000.0 for elt in raw_vals))
        return s

    def chunk_sRGB(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if length < 1:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                return s
            msg = 'Truncated sRGB chunk'
            raise ValueError(msg)
        self.im_info['srgb'] = s[0]
        return s

    def chunk_pHYs(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if length < 9:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                return s
            msg = 'Truncated pHYs chunk'
            raise ValueError(msg)
        (px, py) = (i32(s, 0), i32(s, 4))
        unit = s[8]
        if unit == 1:
            dpi = (px * 0.0254, py * 0.0254)
            self.im_info['dpi'] = dpi
        elif unit == 0:
            self.im_info['aspect'] = (px, py)
        return s

    def chunk_tEXt(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        try:
            (k, v) = s.split(b'\x00', 1)
        except ValueError:
            k = s
            v = b''
        if k:
            k_str = k.decode('latin-1', 'strict')
            v_str = v.decode('latin-1', 'replace')
            self.im_info[k_str] = v if k == b'exif' else v_str
            self.im_text[k_str] = v_str
            self.check_text_memory(len(v_str))
        return s

    def chunk_zTXt(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        try:
            (k, v) = s.split(b'\x00', 1)
        except ValueError:
            k = s
            v = b''
        if v:
            comp_method = v[0]
        else:
            comp_method = 0
        if comp_method != 0:
            msg = f'Unknown compression method {comp_method} in zTXt chunk'
            raise SyntaxError(msg)
        try:
            v = _safe_zlib_decompress(v[1:])
        except ValueError:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                v = b''
            else:
                raise
        except zlib.error:
            v = b''
        if k:
            k_str = k.decode('latin-1', 'strict')
            v_str = v.decode('latin-1', 'replace')
            self.im_info[k_str] = self.im_text[k_str] = v_str
            self.check_text_memory(len(v_str))
        return s

    def chunk_iTXt(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        r = s = ImageFile._safe_read(self.fp, length)
        try:
            (k, r) = r.split(b'\x00', 1)
        except ValueError:
            return s
        if len(r) < 2:
            return s
        (cf, cm, r) = (r[0], r[1], r[2:])
        try:
            (lang, tk, v) = r.split(b'\x00', 2)
        except ValueError:
            return s
        if cf != 0:
            if cm == 0:
                try:
                    v = _safe_zlib_decompress(v)
                except ValueError:
                    if ImageFile.LOAD_TRUNCATED_IMAGES:
                        return s
                    else:
                        raise
                except zlib.error:
                    return s
            else:
                return s
        if k == b'XML:com.adobe.xmp':
            self.im_info['xmp'] = v
        try:
            k_str = k.decode('latin-1', 'strict')
            lang_str = lang.decode('utf-8', 'strict')
            tk_str = tk.decode('utf-8', 'strict')
            v_str = v.decode('utf-8', 'strict')
        except UnicodeError:
            return s
        self.im_info[k_str] = self.im_text[k_str] = iTXt(v_str, lang_str, tk_str)
        self.check_text_memory(len(v_str))
        return s

    def chunk_eXIf(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        self.im_info['exif'] = b'Exif\x00\x00' + s
        return s

    def chunk_acTL(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if length < 8:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                return s
            msg = 'APNG contains truncated acTL chunk'
            raise ValueError(msg)
        if self.im_n_frames is not None:
            self.im_n_frames = None
            warnings.warn('Invalid APNG, will use default PNG image if possible')
            return s
        n_frames = i32(s)
        if n_frames == 0 or n_frames > 2147483648:
            warnings.warn('Invalid APNG, will use default PNG image if possible')
            return s
        self.im_n_frames = n_frames
        self.im_info['loop'] = i32(s, 4)
        self.im_custom_mimetype = 'image/apng'
        return s

    def chunk_fcTL(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if length < 26:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                return s
            msg = 'APNG contains truncated fcTL chunk'
            raise ValueError(msg)
        seq = i32(s)
        if self._seq_num is None and seq != 0 or (self._seq_num is not None and self._seq_num != seq - 1):
            msg = 'APNG contains frame sequence errors'
            raise SyntaxError(msg)
        self._seq_num = seq
        (width, height) = (i32(s, 4), i32(s, 8))
        (px, py) = (i32(s, 12), i32(s, 16))
        (im_w, im_h) = self.im_size
        if px + width > im_w or py + height > im_h:
            msg = 'APNG contains invalid frames'
            raise SyntaxError(msg)
        self.im_info['bbox'] = (px, py, px + width, py + height)
        (delay_num, delay_den) = (i16(s, 20), i16(s, 22))
        if delay_den == 0:
            delay_den = 100
        self.im_info['duration'] = float(delay_num) / float(delay_den) * 1000
        self.im_info['disposal'] = s[24]
        self.im_info['blend'] = s[25]
        return s

    def chunk_fdAT(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        if length < 4:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                s = ImageFile._safe_read(self.fp, length)
                return s
            msg = 'APNG contains truncated fDAT chunk'
            raise ValueError(msg)
        s = ImageFile._safe_read(self.fp, 4)
        seq = i32(s)
        if self._seq_num != seq - 1:
            msg = 'APNG contains frame sequence errors'
            raise SyntaxError(msg)
        self._seq_num = seq
        return self.chunk_IDAT(pos + 4, length - 4)

def _accept(prefix: bytes) -> bool:
    return prefix[:8] == _MAGIC

class PngImageFile(ImageFile.ImageFile):
    format = 'PNG'
    format_description = 'Portable network graphics'

    def _open(self) -> None:
        if not _accept(self.fp.read(8)):
            msg = 'not a PNG file'
            raise SyntaxError(msg)
        self._fp = self.fp
        self.__frame = 0
        self.private_chunks: list[tuple[bytes, bytes] | tuple[bytes, bytes, bool]] = []
        self.png: PngStream | None = PngStream(self.fp)
        while True:
            (cid, pos, length) = self.png.read()
            try:
                s = self.png.call(cid, pos, length)
            except EOFError:
                break
            except AttributeError:
                logger.debug('%r %s %s (unknown)', cid, pos, length)
                s = ImageFile._safe_read(self.fp, length)
                if cid[1:2].islower():
                    self.private_chunks.append((cid, s))
            self.png.crc(cid, s)
        self._mode = self.png.im_mode
        self._size = self.png.im_size
        self.info = self.png.im_info
        self._text: dict[str, str | iTXt] | None = None
        self.tile = self.png.im_tile
        self.custom_mimetype = self.png.im_custom_mimetype
        self.n_frames = self.png.im_n_frames or 1
        self.default_image = self.info.get('default_image', False)
        if self.png.im_palette:
            (rawmode, data) = self.png.im_palette
            self.palette = ImagePalette.raw(rawmode, data)
        if cid == b'fdAT':
            self.__prepare_idat = length - 4
        else:
            self.__prepare_idat = length
        if self.png.im_n_frames is not None:
            self._close_exclusive_fp_after_loading = False
            self.png.save_rewind()
            self.__rewind_idat = self.__prepare_idat
            self.__rewind = self._fp.tell()
            if self.default_image:
                self.n_frames += 1
            self._seek(0)
        self.is_animated = self.n_frames > 1

    @property
    def text(self) -> dict[str, str | iTXt]:
        if self._text is None:
            if self.is_animated:
                frame = self.__frame
                self.seek(self.n_frames - 1)
            self.load()
            if self.is_animated:
                self.seek(frame)
        assert self._text is not None
        return self._text

    def verify(self) -> None:
        """Verify PNG file"""
        if self.fp is None:
            msg = 'verify must be called directly after open'
            raise RuntimeError(msg)
        self.fp.seek(self.tile[0][2] - 8)
        assert self.png is not None
        self.png.verify()
        self.png.close()
        if self._exclusive_fp:
            self.fp.close()
        self.fp = None

    def seek(self, frame: int) -> None:
        if not self._seek_check(frame):
            return
        if frame < self.__frame:
            self._seek(0, True)
        last_frame = self.__frame
        for f in range(self.__frame + 1, frame + 1):
            try:
                self._seek(f)
            except EOFError as e:
                self.seek(last_frame)
                msg = 'no more images in APNG file'
                raise EOFError(msg) from e

    def _seek(self, frame: int, rewind: bool=False) -> None:
        assert self.png is not None
        self.dispose: _imaging.ImagingCore | None
        dispose_extent = None
        if frame == 0:
            if rewind:
                self._fp.seek(self.__rewind)
                self.png.rewind()
                self.__prepare_idat = self.__rewind_idat
                self._im = None
                self.info = self.png.im_info
                self.tile = self.png.im_tile
                self.fp = self._fp
            self._prev_im = None
            self.dispose = None
            self.default_image = self.info.get('default_image', False)
            self.dispose_op = self.info.get('disposal')
            self.blend_op = self.info.get('blend')
            dispose_extent = self.info.get('bbox')
            self.__frame = 0
        else:
            if frame != self.__frame + 1:
                msg = f'cannot seek to frame {frame}'
                raise ValueError(msg)
            self.load()
            if self.dispose:
                self.im.paste(self.dispose, self.dispose_extent)
            self._prev_im = self.im.copy()
            self.fp = self._fp
            if self.__prepare_idat:
                ImageFile._safe_read(self.fp, self.__prepare_idat)
                self.__prepare_idat = 0
            frame_start = False
            while True:
                self.fp.read(4)
                try:
                    (cid, pos, length) = self.png.read()
                except (struct.error, SyntaxError):
                    break
                if cid == b'IEND':
                    msg = 'No more images in APNG file'
                    raise EOFError(msg)
                if cid == b'fcTL':
                    if frame_start:
                        msg = 'APNG missing frame data'
                        raise SyntaxError(msg)
                    frame_start = True
                try:
                    self.png.call(cid, pos, length)
                except UnicodeDecodeError:
                    break
                except EOFError:
                    if cid == b'fdAT':
                        length -= 4
                        if frame_start:
                            self.__prepare_idat = length
                            break
                    ImageFile._safe_read(self.fp, length)
                except AttributeError:
                    logger.debug('%r %s %s (unknown)', cid, pos, length)
                    ImageFile._safe_read(self.fp, length)
            self.__frame = frame
            self.tile = self.png.im_tile
            self.dispose_op = self.info.get('disposal')
            self.blend_op = self.info.get('blend')
            dispose_extent = self.info.get('bbox')
            if not self.tile:
                msg = 'image not found in APNG frame'
                raise EOFError(msg)
        if dispose_extent:
            self.dispose_extent: tuple[float, float, float, float] = dispose_extent
        if self._prev_im is None and self.dispose_op == Disposal.OP_PREVIOUS:
            self.dispose_op = Disposal.OP_BACKGROUND
        self.dispose = None
        if self.dispose_op == Disposal.OP_PREVIOUS:
            if self._prev_im:
                self.dispose = self._prev_im.copy()
                self.dispose = self._crop(self.dispose, self.dispose_extent)
        elif self.dispose_op == Disposal.OP_BACKGROUND:
            self.dispose = Image.core.fill(self.mode, self.size)
            self.dispose = self._crop(self.dispose, self.dispose_extent)

    def tell(self) -> int:
        return self.__frame

    def load_prepare(self) -> None:
        """internal: prepare to read PNG file"""
        if self.info.get('interlace'):
            self.decoderconfig = self.decoderconfig + (1,)
        self.__idat = self.__prepare_idat
        ImageFile.ImageFile.load_prepare(self)

    def load_read(self, read_bytes: int) -> bytes:
        """internal: read more image data"""
        assert self.png is not None
        while self.__idat == 0:
            self.fp.read(4)
            (cid, pos, length) = self.png.read()
            if cid not in [b'IDAT', b'DDAT', b'fdAT']:
                self.png.push(cid, pos, length)
                return b''
            if cid == b'fdAT':
                try:
                    self.png.call(cid, pos, length)
                except EOFError:
                    pass
                self.__idat = length - 4
            else:
                self.__idat = length
        if read_bytes <= 0:
            read_bytes = self.__idat
        else:
            read_bytes = min(read_bytes, self.__idat)
        self.__idat = self.__idat - read_bytes
        return self.fp.read(read_bytes)

    def load_end(self) -> None:
        """internal: finished reading image data"""
        assert self.png is not None
        if self.__idat != 0:
            self.fp.read(self.__idat)
        while True:
            self.fp.read(4)
            try:
                (cid, pos, length) = self.png.read()
            except (struct.error, SyntaxError):
                break
            if cid == b'IEND':
                break
            elif cid == b'fcTL' and self.is_animated:
                self.__prepare_idat = 0
                self.png.push(cid, pos, length)
                break
            try:
                self.png.call(cid, pos, length)
            except UnicodeDecodeError:
                break
            except EOFError:
                if cid == b'fdAT':
                    length -= 4
                try:
                    ImageFile._safe_read(self.fp, length)
                except OSError as e:
                    if ImageFile.LOAD_TRUNCATED_IMAGES:
                        break
                    else:
                        raise e
            except AttributeError:
                logger.debug('%r %s %s (unknown)', cid, pos, length)
                s = ImageFile._safe_read(self.fp, length)
                if cid[1:2].islower():
                    self.private_chunks.append((cid, s, True))
        self._text = self.png.im_text
        if not self.is_animated:
            self.png.close()
            self.png = None
        elif self._prev_im and self.blend_op == Blend.OP_OVER:
            updated = self._crop(self.im, self.dispose_extent)
            if self.im.mode == 'RGB' and 'transparency' in self.info:
                mask = updated.convert_transparent('RGBA', self.info['transparency'])
            else:
                if self.im.mode == 'P' and 'transparency' in self.info:
                    t = self.info['transparency']
                    if isinstance(t, bytes):
                        updated.putpalettealphas(t)
                    elif isinstance(t, int):
                        updated.putpalettealpha(t)
                mask = updated.convert('RGBA')
            self._prev_im.paste(updated, self.dispose_extent, mask)
            self.im = self._prev_im

    def _getexif(self) -> dict[int, Any] | None:
        if 'exif' not in self.info:
            self.load()
        if 'exif' not in self.info and 'Raw profile type exif' not in self.info:
            return None
        return self.getexif()._get_merged_dict()

    def getexif(self) -> Image.Exif:
        if 'exif' not in self.info:
            self.load()
        return super().getexif()
_OUTMODES = {'1': ('1', b'\x01', b'\x00'), 'L;1': ('L;1', b'\x01', b'\x00'), 'L;2': ('L;2', b'\x02', b'\x00'), 'L;4': ('L;4', b'\x04', b'\x00'), 'L': ('L', b'\x08', b'\x00'), 'LA': ('LA', b'\x08', b'\x04'), 'I': ('I;16B', b'\x10', b'\x00'), 'I;16': ('I;16B', b'\x10', b'\x00'), 'I;16B': ('I;16B', b'\x10', b'\x00'), 'P;1': ('P;1', b'\x01', b'\x03'), 'P;2': ('P;2', b'\x02', b'\x03'), 'P;4': ('P;4', b'\x04', b'\x03'), 'P': ('P', b'\x08', b'\x03'), 'RGB': ('RGB', b'\x08', b'\x02'), 'RGBA': ('RGBA', b'\x08', b'\x06')}

def putchunk(fp: IO[bytes], cid: bytes, *data: bytes) -> None:
    """Write a PNG chunk (including CRC field)"""
    byte_data = b''.join(data)
    fp.write(o32(len(byte_data)) + cid)
    fp.write(byte_data)
    crc = _crc32(byte_data, _crc32(cid))
    fp.write(o32(crc))

class _idat:

    def __init__(self, fp: IO[bytes], chunk: Callable[..., None]) -> None:
        self.fp = fp
        self.chunk = chunk

    def write(self, data: bytes) -> None:
        self.chunk(self.fp, b'IDAT', data)

class _fdat:

    def __init__(self, fp: IO[bytes], chunk: Callable[..., None], seq_num: int) -> None:
        self.fp = fp
        self.chunk = chunk
        self.seq_num = seq_num

    def write(self, data: bytes) -> None:
        self.chunk(self.fp, b'fdAT', o32(self.seq_num), data)
        self.seq_num += 1

class _Frame(NamedTuple):
    im: Image.Image
    bbox: tuple[int, int, int, int] | None
    encoderinfo: dict[str, Any]

def _write_multiple_frames(im: Image.Image, fp: IO[bytes], chunk: Callable[..., None], mode: str, rawmode: str, default_image: Image.Image | None, append_images: list[Image.Image]) -> Image.Image | None:
    duration = im.encoderinfo.get('duration')
    loop = im.encoderinfo.get('loop', im.info.get('loop', 0))
    disposal = im.encoderinfo.get('disposal', im.info.get('disposal', Disposal.OP_NONE))
    blend = im.encoderinfo.get('blend', im.info.get('blend', Blend.OP_SOURCE))
    if default_image:
        chain = itertools.chain(append_images)
    else:
        chain = itertools.chain([im], append_images)
    im_frames: list[_Frame] = []
    frame_count = 0
    for im_seq in chain:
        for im_frame in ImageSequence.Iterator(im_seq):
            if im_frame.mode == mode:
                im_frame = im_frame.copy()
            else:
                im_frame = im_frame.convert(mode)
            encoderinfo = im.encoderinfo.copy()
            if isinstance(duration, (list, tuple)):
                encoderinfo['duration'] = duration[frame_count]
            elif duration is None and 'duration' in im_frame.info:
                encoderinfo['duration'] = im_frame.info['duration']
            if isinstance(disposal, (list, tuple)):
                encoderinfo['disposal'] = disposal[frame_count]
            if isinstance(blend, (list, tuple)):
                encoderinfo['blend'] = blend[frame_count]
            frame_count += 1
            if im_frames:
                previous = im_frames[-1]
                prev_disposal = previous.encoderinfo.get('disposal')
                prev_blend = previous.encoderinfo.get('blend')
                if prev_disposal == Disposal.OP_PREVIOUS and len(im_frames) < 2:
                    prev_disposal = Disposal.OP_BACKGROUND
                if prev_disposal == Disposal.OP_BACKGROUND:
                    base_im = previous.im.copy()
                    dispose = Image.core.fill('RGBA', im.size, (0, 0, 0, 0))
                    bbox = previous.bbox
                    if bbox:
                        dispose = dispose.crop(bbox)
                    else:
                        bbox = (0, 0) + im.size
                    base_im.paste(dispose, bbox)
                elif prev_disposal == Disposal.OP_PREVIOUS:
                    base_im = im_frames[-2].im
                else:
                    base_im = previous.im
                delta = ImageChops.subtract_modulo(im_frame.convert('RGBA'), base_im.convert('RGBA'))
                bbox = delta.getbbox(alpha_only=False)
                if not bbox and prev_disposal == encoderinfo.get('disposal') and (prev_blend == encoderinfo.get('blend')) and ('duration' in encoderinfo):
                    previous.encoderinfo['duration'] += encoderinfo['duration']
                    continue
            else:
                bbox = None
            im_frames.append(_Frame(im_frame, bbox, encoderinfo))
    if len(im_frames) == 1 and (not default_image):
        return im_frames[0].im
    chunk(fp, b'acTL', o32(len(im_frames)), o32(loop))
    if default_image:
        if im.mode != mode:
            im = im.convert(mode)
        ImageFile._save(im, cast(IO[bytes], _idat(fp, chunk)), [ImageFile._Tile('zip', (0, 0) + im.size, 0, rawmode)])
    seq_num = 0
    for (frame, frame_data) in enumerate(im_frames):
        im_frame = frame_data.im
        if not frame_data.bbox:
            bbox = (0, 0) + im_frame.size
        else:
            bbox = frame_data.bbox
            im_frame = im_frame.crop(bbox)
        size = im_frame.size
        encoderinfo = frame_data.encoderinfo
        frame_duration = int(round(encoderinfo.get('duration', 0)))
        frame_disposal = encoderinfo.get('disposal', disposal)
        frame_blend = encoderinfo.get('blend', blend)
        chunk(fp, b'fcTL', o32(seq_num), o32(size[0]), o32(size[1]), o32(bbox[0]), o32(bbox[1]), o16(frame_duration), o16(1000), o8(frame_disposal), o8(frame_blend))
        seq_num += 1
        if frame == 0 and (not default_image):
            ImageFile._save(im_frame, cast(IO[bytes], _idat(fp, chunk)), [ImageFile._Tile('zip', (0, 0) + im_frame.size, 0, rawmode)])
        else:
            fdat_chunks = _fdat(fp, chunk, seq_num)
            ImageFile._save(im_frame, cast(IO[bytes], fdat_chunks), [ImageFile._Tile('zip', (0, 0) + im_frame.size, 0, rawmode)])
            seq_num = fdat_chunks.seq_num
    return None

def _save_all(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    _save(im, fp, filename, save_all=True)

def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes, chunk: Callable[..., None]=putchunk, save_all: bool=False) -> None:
    if save_all:
        default_image = im.encoderinfo.get('default_image', im.info.get('default_image'))
        modes = set()
        sizes = set()
        append_images = im.encoderinfo.get('append_images', [])
        for im_seq in itertools.chain([im], append_images):
            for im_frame in ImageSequence.Iterator(im_seq):
                modes.add(im_frame.mode)
                sizes.add(im_frame.size)
        for mode in ('RGBA', 'RGB', 'P'):
            if mode in modes:
                break
        else:
            mode = modes.pop()
        size = tuple((max((frame_size[i] for frame_size in sizes)) for i in range(2)))
    else:
        size = im.size
        mode = im.mode
    outmode = mode
    if mode == 'P':
        if 'bits' in im.encoderinfo:
            colors = min(1 << im.encoderinfo['bits'], 256)
        elif im.palette:
            colors = max(min(len(im.palette.getdata()[1]) // 3, 256), 1)
        else:
            colors = 256
        if colors <= 16:
            if colors <= 2:
                bits = 1
            elif colors <= 4:
                bits = 2
            else:
                bits = 4
            outmode += f';{bits}'
    im.encoderconfig = (im.encoderinfo.get('optimize', False), im.encoderinfo.get('compress_level', -1), im.encoderinfo.get('compress_type', -1), im.encoderinfo.get('dictionary', b''))
    try:
        (rawmode, bit_depth, color_type) = _OUTMODES[outmode]
    except KeyError as e:
        msg = f'cannot write mode {mode} as PNG'
        raise OSError(msg) from e
    fp.write(_MAGIC)
    chunk(fp, b'IHDR', o32(size[0]), o32(size[1]), bit_depth, color_type, b'\x00', b'\x00', b'\x00')
    chunks = [b'cHRM', b'gAMA', b'sBIT', b'sRGB', b'tIME']
    icc = im.encoderinfo.get('icc_profile', im.info.get('icc_profile'))
    if icc:
        name = b'ICC Profile'
        data = name + b'\x00\x00' + zlib.compress(icc)
        chunk(fp, b'iCCP', data)
        chunks.remove(b'sRGB')
    info = im.encoderinfo.get('pnginfo')
    if info:
        chunks_multiple_allowed = [b'sPLT', b'iTXt', b'tEXt', b'zTXt']
        for info_chunk in info.chunks:
            (cid, data) = info_chunk[:2]
            if cid in chunks:
                chunks.remove(cid)
                chunk(fp, cid, data)
            elif cid in chunks_multiple_allowed:
                chunk(fp, cid, data)
            elif cid[1:2].islower():
                after_idat = len(info_chunk) == 3 and info_chunk[2]
                if not after_idat:
                    chunk(fp, cid, data)
    if im.mode == 'P':
        palette_byte_number = colors * 3
        palette_bytes = im.im.getpalette('RGB')[:palette_byte_number]
        while len(palette_bytes) < palette_byte_number:
            palette_bytes += b'\x00'
        chunk(fp, b'PLTE', palette_bytes)
    transparency = im.encoderinfo.get('transparency', im.info.get('transparency', None))
    if transparency or transparency == 0:
        if im.mode == 'P':
            alpha_bytes = colors
            if isinstance(transparency, bytes):
                chunk(fp, b'tRNS', transparency[:alpha_bytes])
            else:
                transparency = max(0, min(255, transparency))
                alpha = b'\xff' * transparency + b'\x00'
                chunk(fp, b'tRNS', alpha[:alpha_bytes])
        elif im.mode in ('1', 'L', 'I', 'I;16'):
            transparency = max(0, min(65535, transparency))
            chunk(fp, b'tRNS', o16(transparency))
        elif im.mode == 'RGB':
            (red, green, blue) = transparency
            chunk(fp, b'tRNS', o16(red) + o16(green) + o16(blue))
        elif 'transparency' in im.encoderinfo:
            msg = 'cannot use transparency for this mode'
            raise OSError(msg)
    elif im.mode == 'P' and im.im.getpalettemode() == 'RGBA':
        alpha = im.im.getpalette('RGBA', 'A')
        alpha_bytes = colors
        chunk(fp, b'tRNS', alpha[:alpha_bytes])
    dpi = im.encoderinfo.get('dpi')
    if dpi:
        chunk(fp, b'pHYs', o32(int(dpi[0] / 0.0254 + 0.5)), o32(int(dpi[1] / 0.0254 + 0.5)), b'\x01')
    if info:
        chunks = [b'bKGD', b'hIST']
        for info_chunk in info.chunks:
            (cid, data) = info_chunk[:2]
            if cid in chunks:
                chunks.remove(cid)
                chunk(fp, cid, data)
    exif = im.encoderinfo.get('exif')
    if exif:
        if isinstance(exif, Image.Exif):
            exif = exif.tobytes(8)
        if exif.startswith(b'Exif\x00\x00'):
            exif = exif[6:]
        chunk(fp, b'eXIf', exif)
    single_im: Image.Image | None = im
    if save_all:
        single_im = _write_multiple_frames(im, fp, chunk, mode, rawmode, default_image, append_images)
    if single_im:
        ImageFile._save(single_im, cast(IO[bytes], _idat(fp, chunk)), [ImageFile._Tile('zip', (0, 0) + single_im.size, 0, rawmode)])
    if info:
        for info_chunk in info.chunks:
            (cid, data) = info_chunk[:2]
            if cid[1:2].islower():
                after_idat = len(info_chunk) == 3 and info_chunk[2]
                if after_idat:
                    chunk(fp, cid, data)
    chunk(fp, b'IEND', b'')
    if hasattr(fp, 'flush'):
        fp.flush()

def getchunks(im: Image.Image, **params: Any) -> list[tuple[bytes, bytes, bytes]]:
    """Return a list of PNG chunks representing this image."""
    from io import BytesIO
    chunks = []

    def append(fp: IO[bytes], cid: bytes, *data: bytes) -> None:
        byte_data = b''.join(data)
        crc = o32(_crc32(byte_data, _crc32(cid)))
        chunks.append((cid, byte_data, crc))
    fp = BytesIO()
    try:
        im.encoderinfo = params
        _save(im, fp, '', append)
    finally:
        del im.encoderinfo
    return chunks
Image.register_open(PngImageFile.format, PngImageFile, _accept)
Image.register_save(PngImageFile.format, _save)
Image.register_save_all(PngImageFile.format, _save_all)
Image.register_extensions(PngImageFile.format, ['.png', '.apng'])
Image.register_mime(PngImageFile.format, 'image/png')

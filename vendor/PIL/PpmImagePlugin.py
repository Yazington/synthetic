# coding: utf-8
from __future__ import annotations
import math
from typing import IO
from . import Image, ImageFile
from ._binary import i16be as i16
from ._binary import o8
from ._binary import o32le as o32
b_whitespace = b' \t\n\x0b\x0c\r'
MODES = {b'P1': '1', b'P2': 'L', b'P3': 'RGB', b'P4': '1', b'P5': 'L', b'P6': 'RGB', b'P0CMYK': 'CMYK', b'Pf': 'F', b'PyP': 'P', b'PyRGBA': 'RGBA', b'PyCMYK': 'CMYK'}

def _accept(prefix: bytes) -> bool:
    return prefix[0:1] == b'P' and prefix[1] in b'0123456fy'

class PpmImageFile(ImageFile.ImageFile):
    format = 'PPM'
    format_description = 'Pbmplus image'

    def _read_magic(self) -> bytes:
        assert self.fp is not None
        magic = b''
        for _ in range(6):
            c = self.fp.read(1)
            if not c or c in b_whitespace:
                break
            magic += c
        return magic

    def _read_token(self) -> bytes:
        assert self.fp is not None
        token = b''
        while len(token) <= 10:
            c = self.fp.read(1)
            if not c:
                break
            elif c in b_whitespace:
                if not token:
                    continue
                break
            elif c == b'#':
                while self.fp.read(1) not in b'\r\n':
                    pass
                continue
            token += c
        if not token:
            msg = 'Reached EOF while reading header'
            raise ValueError(msg)
        elif len(token) > 10:
            msg = f'Token too long in file header: {token.decode()}'
            raise ValueError(msg)
        return token

    def _open(self) -> None:
        assert self.fp is not None
        magic_number = self._read_magic()
        try:
            mode = MODES[magic_number]
        except KeyError:
            msg = 'not a PPM file'
            raise SyntaxError(msg)
        self._mode = mode
        if magic_number in (b'P1', b'P4'):
            self.custom_mimetype = 'image/x-portable-bitmap'
        elif magic_number in (b'P2', b'P5'):
            self.custom_mimetype = 'image/x-portable-graymap'
        elif magic_number in (b'P3', b'P6'):
            self.custom_mimetype = 'image/x-portable-pixmap'
        self._size = (int(self._read_token()), int(self._read_token()))
        decoder_name = 'raw'
        if magic_number in (b'P1', b'P2', b'P3'):
            decoder_name = 'ppm_plain'
        args: str | tuple[str | int, ...]
        if mode == '1':
            args = '1;I'
        elif mode == 'F':
            scale = float(self._read_token())
            if scale == 0.0 or not math.isfinite(scale):
                msg = 'scale must be finite and non-zero'
                raise ValueError(msg)
            self.info['scale'] = abs(scale)
            rawmode = 'F;32F' if scale < 0 else 'F;32BF'
            args = (rawmode, 0, -1)
        else:
            maxval = int(self._read_token())
            if not 0 < maxval < 65536:
                msg = 'maxval must be greater than 0 and less than 65536'
                raise ValueError(msg)
            if maxval > 255 and mode == 'L':
                self._mode = 'I'
            rawmode = mode
            if decoder_name != 'ppm_plain':
                if maxval == 65535 and mode == 'L':
                    rawmode = 'I;16B'
                elif maxval != 255:
                    decoder_name = 'ppm'
            args = rawmode if decoder_name == 'raw' else (rawmode, maxval)
        self.tile = [ImageFile._Tile(decoder_name, (0, 0) + self.size, self.fp.tell(), args)]

class PpmPlainDecoder(ImageFile.PyDecoder):
    _pulls_fd = True
    _comment_spans: bool

    def _read_block(self) -> bytes:
        assert self.fd is not None
        return self.fd.read(ImageFile.SAFEBLOCK)

    def _find_comment_end(self, block: bytes, start: int=0) -> int:
        a = block.find(b'\n', start)
        b = block.find(b'\r', start)
        return min(a, b) if a * b > 0 else max(a, b)

    def _ignore_comments(self, block: bytes) -> bytes:
        if self._comment_spans:
            while block:
                comment_end = self._find_comment_end(block)
                if comment_end != -1:
                    block = block[comment_end + 1:]
                    break
                else:
                    block = self._read_block()
        self._comment_spans = False
        while True:
            comment_start = block.find(b'#')
            if comment_start == -1:
                break
            comment_end = self._find_comment_end(block, comment_start)
            if comment_end != -1:
                block = block[:comment_start] + block[comment_end + 1:]
            else:
                block = block[:comment_start]
                self._comment_spans = True
                break
        return block

    def _decode_bitonal(self) -> bytearray:
        """
        This is a separate method because in the plain PBM format, all data tokens are
        exactly one byte, so the inter-token whitespace is optional.
        """
        data = bytearray()
        total_bytes = self.state.xsize * self.state.ysize
        while len(data) != total_bytes:
            block = self._read_block()
            if not block:
                break
            block = self._ignore_comments(block)
            tokens = b''.join(block.split())
            for token in tokens:
                if token not in (48, 49):
                    msg = b'Invalid token for this mode: %s' % bytes([token])
                    raise ValueError(msg)
            data = (data + tokens)[:total_bytes]
        invert = bytes.maketrans(b'01', b'\xff\x00')
        return data.translate(invert)

    def _decode_blocks(self, maxval: int) -> bytearray:
        data = bytearray()
        max_len = 10
        out_byte_count = 4 if self.mode == 'I' else 1
        out_max = 65535 if self.mode == 'I' else 255
        bands = Image.getmodebands(self.mode)
        total_bytes = self.state.xsize * self.state.ysize * bands * out_byte_count
        half_token = b''
        while len(data) != total_bytes:
            block = self._read_block()
            if not block:
                if half_token:
                    block = bytearray(b' ')
                else:
                    break
            block = self._ignore_comments(block)
            if half_token:
                block = half_token + block
                half_token = b''
            tokens = block.split()
            if block and (not block[-1:].isspace()):
                half_token = tokens.pop()
                if len(half_token) > max_len:
                    msg = b'Token too long found in data: %s' % half_token[:max_len + 1]
                    raise ValueError(msg)
            for token in tokens:
                if len(token) > max_len:
                    msg = b'Token too long found in data: %s' % token[:max_len + 1]
                    raise ValueError(msg)
                value = int(token)
                if value < 0:
                    msg_str = f'Channel value is negative: {value}'
                    raise ValueError(msg_str)
                if value > maxval:
                    msg_str = f'Channel value too large for this mode: {value}'
                    raise ValueError(msg_str)
                value = round(value / maxval * out_max)
                data += o32(value) if self.mode == 'I' else o8(value)
                if len(data) == total_bytes:
                    break
        return data

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        self._comment_spans = False
        if self.mode == '1':
            data = self._decode_bitonal()
            rawmode = '1;8'
        else:
            maxval = self.args[-1]
            data = self._decode_blocks(maxval)
            rawmode = 'I;32' if self.mode == 'I' else self.mode
        self.set_as_raw(bytes(data), rawmode)
        return (-1, 0)

class PpmDecoder(ImageFile.PyDecoder):
    _pulls_fd = True

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        assert self.fd is not None
        data = bytearray()
        maxval = self.args[-1]
        in_byte_count = 1 if maxval < 256 else 2
        out_byte_count = 4 if self.mode == 'I' else 1
        out_max = 65535 if self.mode == 'I' else 255
        bands = Image.getmodebands(self.mode)
        dest_length = self.state.xsize * self.state.ysize * bands * out_byte_count
        while len(data) < dest_length:
            pixels = self.fd.read(in_byte_count * bands)
            if len(pixels) < in_byte_count * bands:
                break
            for b in range(bands):
                value = pixels[b] if in_byte_count == 1 else i16(pixels, b * in_byte_count)
                value = min(out_max, round(value / maxval * out_max))
                data += o32(value) if self.mode == 'I' else o8(value)
        rawmode = 'I;32' if self.mode == 'I' else self.mode
        self.set_as_raw(bytes(data), rawmode)
        return (-1, 0)

def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if im.mode == '1':
        (rawmode, head) = ('1;I', b'P4')
    elif im.mode == 'L':
        (rawmode, head) = ('L', b'P5')
    elif im.mode in ('I', 'I;16'):
        (rawmode, head) = ('I;16B', b'P5')
    elif im.mode in ('RGB', 'RGBA'):
        (rawmode, head) = ('RGB', b'P6')
    elif im.mode == 'F':
        (rawmode, head) = ('F;32F', b'Pf')
    else:
        msg = f'cannot write mode {im.mode} as PPM'
        raise OSError(msg)
    fp.write(head + b'\n%d %d\n' % im.size)
    if head == b'P6':
        fp.write(b'255\n')
    elif head == b'P5':
        if rawmode == 'L':
            fp.write(b'255\n')
        else:
            fp.write(b'65535\n')
    elif head == b'Pf':
        fp.write(b'-1.0\n')
    row_order = -1 if im.mode == 'F' else 1
    ImageFile._save(im, fp, [ImageFile._Tile('raw', (0, 0) + im.size, 0, (rawmode, 0, row_order))])
Image.register_open(PpmImageFile.format, PpmImageFile, _accept)
Image.register_save(PpmImageFile.format, _save)
Image.register_decoder('ppm', PpmDecoder)
Image.register_decoder('ppm_plain', PpmPlainDecoder)
Image.register_extensions(PpmImageFile.format, ['.pbm', '.pgm', '.ppm', '.pnm', '.pfm'])
Image.register_mime(PpmImageFile.format, 'image/x-portable-anymap')

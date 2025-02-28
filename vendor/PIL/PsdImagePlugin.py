# coding: utf-8
from __future__ import annotations
import io
from functools import cached_property
from typing import IO
from . import Image, ImageFile, ImagePalette
from ._binary import i8
from ._binary import i16be as i16
from ._binary import i32be as i32
from ._binary import si16be as si16
from ._binary import si32be as si32
MODES = {(0, 1): ('1', 1), (0, 8): ('L', 1), (1, 8): ('L', 1), (2, 8): ('P', 1), (3, 8): ('RGB', 3), (4, 8): ('CMYK', 4), (7, 8): ('L', 1), (8, 8): ('L', 1), (9, 8): ('LAB', 3)}

def _accept(prefix: bytes) -> bool:
    return prefix[:4] == b'8BPS'

class PsdImageFile(ImageFile.ImageFile):
    format = 'PSD'
    format_description = 'Adobe Photoshop'
    _close_exclusive_fp_after_loading = False

    def _open(self) -> None:
        read = self.fp.read
        s = read(26)
        if not _accept(s) or i16(s, 4) != 1:
            msg = 'not a PSD file'
            raise SyntaxError(msg)
        psd_bits = i16(s, 22)
        psd_channels = i16(s, 12)
        psd_mode = i16(s, 24)
        (mode, channels) = MODES[psd_mode, psd_bits]
        if channels > psd_channels:
            msg = 'not enough channels'
            raise OSError(msg)
        if mode == 'RGB' and psd_channels == 4:
            mode = 'RGBA'
            channels = 4
        self._mode = mode
        self._size = (i32(s, 18), i32(s, 14))
        size = i32(read(4))
        if size:
            data = read(size)
            if mode == 'P' and size == 768:
                self.palette = ImagePalette.raw('RGB;L', data)
        self.resources = []
        size = i32(read(4))
        if size:
            end = self.fp.tell() + size
            while self.fp.tell() < end:
                read(4)
                id = i16(read(2))
                name = read(i8(read(1)))
                if not len(name) & 1:
                    read(1)
                data = read(i32(read(4)))
                if len(data) & 1:
                    read(1)
                self.resources.append((id, name, data))
                if id == 1039:
                    self.info['icc_profile'] = data
        self._layers_position = None
        size = i32(read(4))
        if size:
            end = self.fp.tell() + size
            size = i32(read(4))
            if size:
                self._layers_position = self.fp.tell()
                self._layers_size = size
            self.fp.seek(end)
        self._n_frames: int | None = None
        self.tile = _maketile(self.fp, mode, (0, 0) + self.size, channels)
        self._fp = self.fp
        self.frame = 1
        self._min_frame = 1

    @cached_property
    def layers(self) -> list[tuple[str, str, tuple[int, int, int, int], list[ImageFile._Tile]]]:
        layers = []
        if self._layers_position is not None:
            self._fp.seek(self._layers_position)
            _layer_data = io.BytesIO(ImageFile._safe_read(self._fp, self._layers_size))
            layers = _layerinfo(_layer_data, self._layers_size)
        self._n_frames = len(layers)
        return layers

    @property
    def n_frames(self) -> int:
        if self._n_frames is None:
            self._n_frames = len(self.layers)
        return self._n_frames

    @property
    def is_animated(self) -> bool:
        return len(self.layers) > 1

    def seek(self, layer: int) -> None:
        if not self._seek_check(layer):
            return
        try:
            (_, mode, _, tile) = self.layers[layer - 1]
            self._mode = mode
            self.tile = tile
            self.frame = layer
            self.fp = self._fp
        except IndexError as e:
            msg = 'no such layer'
            raise EOFError(msg) from e

    def tell(self) -> int:
        return self.frame

def _layerinfo(fp: IO[bytes], ct_bytes: int) -> list[tuple[str, str, tuple[int, int, int, int], list[ImageFile._Tile]]]:
    layers = []

    def read(size: int) -> bytes:
        return ImageFile._safe_read(fp, size)
    ct = si16(read(2))
    if ct_bytes < abs(ct) * 20:
        msg = 'Layer block too short for number of layers requested'
        raise SyntaxError(msg)
    for _ in range(abs(ct)):
        y0 = si32(read(4))
        x0 = si32(read(4))
        y1 = si32(read(4))
        x1 = si32(read(4))
        bands = []
        ct_types = i16(read(2))
        if ct_types > 4:
            fp.seek(ct_types * 6 + 12, io.SEEK_CUR)
            size = i32(read(4))
            fp.seek(size, io.SEEK_CUR)
            continue
        for _ in range(ct_types):
            type = i16(read(2))
            if type == 65535:
                b = 'A'
            else:
                b = 'RGBA'[type]
            bands.append(b)
            read(4)
        bands.sort()
        if bands == ['R']:
            mode = 'L'
        elif bands == ['B', 'G', 'R']:
            mode = 'RGB'
        elif bands == ['A', 'B', 'G', 'R']:
            mode = 'RGBA'
        else:
            mode = ''
        read(12)
        name = ''
        size = i32(read(4))
        if size:
            data_end = fp.tell() + size
            length = i32(read(4))
            if length:
                fp.seek(length - 16, io.SEEK_CUR)
            length = i32(read(4))
            if length:
                fp.seek(length, io.SEEK_CUR)
            length = i8(read(1))
            if length:
                name = read(length).decode('latin-1', 'replace')
            fp.seek(data_end)
        layers.append((name, mode, (x0, y0, x1, y1)))
    layerinfo = []
    for (i, (name, mode, bbox)) in enumerate(layers):
        tile = []
        for m in mode:
            t = _maketile(fp, m, bbox, 1)
            if t:
                tile.extend(t)
        layerinfo.append((name, mode, bbox, tile))
    return layerinfo

def _maketile(file: IO[bytes], mode: str, bbox: tuple[int, int, int, int], channels: int) -> list[ImageFile._Tile]:
    tiles = []
    read = file.read
    compression = i16(read(2))
    xsize = bbox[2] - bbox[0]
    ysize = bbox[3] - bbox[1]
    offset = file.tell()
    if compression == 0:
        for channel in range(channels):
            layer = mode[channel]
            if mode == 'CMYK':
                layer += ';I'
            tiles.append(ImageFile._Tile('raw', bbox, offset, layer))
            offset = offset + xsize * ysize
    elif compression == 1:
        i = 0
        bytecount = read(channels * ysize * 2)
        offset = file.tell()
        for channel in range(channels):
            layer = mode[channel]
            if mode == 'CMYK':
                layer += ';I'
            tiles.append(ImageFile._Tile('packbits', bbox, offset, layer))
            for y in range(ysize):
                offset = offset + i16(bytecount, i)
                i += 2
    file.seek(offset)
    if offset & 1:
        read(1)
    return tiles
Image.register_open(PsdImageFile.format, PsdImageFile, _accept)
Image.register_extension(PsdImageFile.format, '.psd')
Image.register_mime(PsdImageFile.format, 'image/vnd.adobe.photoshop')
